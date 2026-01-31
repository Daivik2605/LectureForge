"""
Policy pipeline orchestration focused on chapter clip assembly.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ppt_parser import parse_ppt
from app.services.narration_chain import generate_narration_sync
from app.services.narration_cache import (
    build_cache_key,
    load_cached_narration,
    save_cached_narration,
)
from app.services.tts_service import synthesize_speech
from app.services.slide_renderer import render_slide_image
from app.services.video_assembler import create_video
from app.services.video_stitcher import stitch_videos
from app.models.job import JobState
from app.services.job_manager import job_manager

logger = get_logger(__name__)


def _extract_policy_text(input_path: str) -> str:
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Policy file not found: {input_path}")

    suffix = path.suffix.lower()
    if suffix in {".ppt", ".pptx"}:
        slides = [s for s in parse_ppt(str(path)) if s.get("has_text")]
        return "\n\n".join(s.get("text", "") for s in slides if s.get("text"))

    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":
        try:
            from pdfminer.high_level import extract_text
        except ImportError as exc:
            raise RuntimeError("pdfminer.six is required for PDF policy inputs") from exc
        return extract_text(str(path)) or ""

    raise ValueError("Unsupported policy input format")


def _split_chapters(text: str) -> list[str]:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if not blocks:
        return []
    chapters: list[str] = []
    current: list[str] = []
    for block in blocks:
        current.append(block)
        if len(current) >= 2:
            chapters.append("\n\n".join(current))
            current = []
    if current:
        chapters.append("\n\n".join(current))
    return chapters


def _chapter_title(text: str, index: int) -> str:
    first_line = text.splitlines()[0].strip()
    if first_line:
        return first_line[:80]
    return f"Chapter {index}"


async def process_policy_job(job_id: str, input_path: str, language: str = "en") -> str:
    """
    Process a policy document into a single stitched video.
    """
    loop = asyncio.get_running_loop()
    text = await loop.run_in_executor(None, _extract_policy_text, input_path)
    chapters = _split_chapters(text)
    if not chapters:
        raise ValueError("No policy content detected")

    await job_manager.update_progress(
        job_id,
        10,
        current_step="Parsing and chunking policy",
        status=JobState.PROCESSING.value,
        extra_meta={"phase": "extraction", "mode": "policy"},
    )

    temp_dir = settings.storage_temp_dir
    output_dir = settings.storage_output_dir / job_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    chapter_clips: list[str] = []
    for idx, chapter_text in enumerate(chapters, start=1):
        title = _chapter_title(chapter_text, idx)
        cache_key = build_cache_key(
            language=language,
            slide_text=chapter_text,
            pipeline_type="policy",
        )
        cached = load_cached_narration(cache_key)
        if cached:
            logger.info(f"Narration cache hit for policy chapter {idx}")
            narration = cached
        else:
            try:
                narration = await asyncio.wait_for(
                    loop.run_in_executor(None, generate_narration_sync, chapter_text, language),
                    timeout=settings.llm_timeout,
                )
            except asyncio.TimeoutError as exc:
                raise RuntimeError("Ollama timed out generating policy narration") from exc
            save_cached_narration(
                cache_key,
                narration,
                language=language,
                pipeline_type="policy",
            )
        if idx == 1:
            await job_manager.update_progress(
                job_id,
                40,
                current_step="LLM batches completed",
                status=JobState.PROCESSING.value,
                extra_meta={"phase": "narration", "mode": "policy"},
            )
        slide_text = f"{title}\n\n{chapter_text}"

        audio_path = await loop.run_in_executor(None, synthesize_speech, narration, language)
        image_path = await loop.run_in_executor(None, render_slide_image, slide_text)
        slide_clip = await loop.run_in_executor(
            None,
            create_video,
            image_path,
            audio_path,
            str(temp_dir / f"chapter_{idx}_slide_1.mp4"),
        )

        logger.info(f"Assembling chapter clip {idx}")
        chapter_clip = await loop.run_in_executor(
            None,
            stitch_videos,
            [slide_clip],
            str(temp_dir / f"chapter_{idx}.mp4"),
        )
        chapter_clips.append(chapter_clip)

        await job_manager.update_progress(
            job_id,
            int(40 + (idx / max(len(chapters), 1)) * 40),
            current_step=f"Rendering chapter {idx} of {len(chapters)}",
            status=JobState.PROCESSING.value,
            extra_meta={
                "phase": "rendering",
                "mode": "policy",
                "chapter_index": idx,
                "total_chapters": len(chapters),
                "chapter_title": title,
            },
        )

    await job_manager.update_progress(
        job_id,
        80,
        current_step="TTS and clip generation completed",
        status=JobState.PROCESSING.value,
        extra_meta={"phase": "rendering", "mode": "policy"},
    )

    logger.info(f"Stitching final video from {len(chapter_clips)} chapters")
    final_path = await loop.run_in_executor(
        None,
        stitch_videos,
        chapter_clips,
        str(output_dir / "final.mp4"),
    )
    await job_manager.update_progress(
        job_id,
        100,
        current_step="Processing completed",
        status=JobState.COMPLETED.value,
        extra_meta={"phase": "completed", "mode": "policy"},
    )
    return final_path
