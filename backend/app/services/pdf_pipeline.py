"""
PDF pipeline - one slide per page with summaries, narrations, and optional MCQs.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from pdfminer.high_level import extract_text
from pdfminer.pdfpage import PDFPage

from app.core.config import settings
from app.core.exceptions import JobCancelledError
from app.core.logging import get_job_logger
from app.core.redis import redis_manager
from app.models.job import JobResult, SlideResult, SlideState, MCQuestion
from app.services.job_manager import job_manager
from app.services.llm_service import batch_summarize_pages, batch_generate_mcqs
from app.services.narration_cache import (
    build_cache_key,
    load_cached_payload,
    save_cached_payload,
)
from app.services.slide_renderer import render_slide_image
from app.services.tts_service import synthesize_speech
from app.services.video_assembler import create_video
from app.services.video_stitcher import stitch_videos
from app.services.vibe_metrics import build_narration_meta


def _load_pdf_pages(pdf_path: str) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    with open(pdf_path, "rb") as handle:
        total_pages = len(list(PDFPage.get_pages(handle)))
    for page_index in range(total_pages):
        text = extract_text(pdf_path, page_numbers=[page_index]) or ""
        normalized = " ".join(text.split()).strip()
        pages.append({"page_number": page_index + 1, "text": normalized})
    return pages


def _build_slide_text(title: str, bullets: list[str]) -> str:
    bullet_lines = "\n".join(f"- {bullet}" for bullet in bullets if bullet)
    if bullet_lines:
        return f"{title}\n\n{bullet_lines}"
    return title


def _calc_max_words(total_pages: int) -> int:
    target_minutes = 18
    words_per_minute = 150
    total_word_budget = target_minutes * words_per_minute
    per_page = total_word_budget // max(total_pages, 1)
    return max(15, min(settings.narration_max_words, int(per_page)))


def _progress_for_batches(completed: int, total: int, start: int, end: int) -> int:
    if total <= 0:
        return end
    return int(start + (end - start) * (completed / total))


async def process_pdf_job(
    job_id: str,
    pdf_path: str,
    language: str = "en",
    max_slides: int = 50,
    generate_video: bool = True,
    generate_mcqs: bool = True,
) -> JobResult:
    job_logger = get_job_logger(job_id)
    job_logger.info(f"Starting PDF pipeline: {pdf_path}")
    start_time = datetime.utcnow()

    pages = _load_pdf_pages(pdf_path)

    page_items: list[dict[str, Any]] = []
    for page in pages:
        if not page["text"]:
            continue
        page_id = f"p{page['page_number']}"
        page_items.append(
            {
                "page_id": page_id,
                "page_number": page["page_number"],
                "text": page["text"],
            }
        )

    await job_manager.update_progress(job_id, 10, current_step="Parsing PDF")
    await job_manager.update_progress(
        job_id=job_id,
        progress=10,
        current_step="Extracting",
        extra_meta={"phase": "extraction"},
    )

    if not page_items:
        return JobResult(
            job_id=job_id,
            status="completed",
            filename=Path(pdf_path).name,
            language=language,
            mode="pdf",
            slides=[],
            processing_time_seconds=0,
            cache_hits=0,
            cache_misses=0,
            slide_metrics=[],
            created_at=start_time,
            completed_at=datetime.utcnow(),
        )

    if max_slides:
        page_items = page_items[:max_slides]

    total_pages = len(page_items)
    max_words = _calc_max_words(total_pages)

    llm_semaphore = asyncio.Semaphore(settings.llm_concurrency)
    tts_semaphore = asyncio.Semaphore(settings.tts_concurrency)
    render_semaphore = asyncio.Semaphore(settings.render_concurrency)
    video_semaphore = asyncio.Semaphore(settings.video_concurrency)

    job_logger.info(
        "Concurrency limits",
        extra={
            "llm": settings.llm_concurrency,
            "tts": settings.tts_concurrency,
            "render": settings.render_concurrency,
            "video": settings.video_concurrency,
            "narration_batch_size": settings.narration_batch_size,
            "max_words_per_page": max_words,
        },
    )

    summary_cache_hits = 0
    summary_cache_misses = 0
    summaries: dict[str, dict[str, Any]] = {}
    summary_meta_by_page_id: dict[str, dict[str, Any]] = {}
    missing_pages: list[dict[str, Any]] = []
    last_summary_llm_metrics: dict[str, Any] = {}
    last_summary_json_adherence = True

    for page in page_items:
        cache_key = build_cache_key(
            language=language,
            slide_text=page["text"],
            pipeline_type="pdf_summary",
        )
        cached_payload = load_cached_payload(cache_key)
        if cached_payload and cached_payload.get("summary"):
            summaries[page["page_id"]] = cached_payload["summary"]
            summary_cache_hits += 1
            job_logger.info(f"Summary cache hit for {page['page_id']}")
            summary_meta_by_page_id[page["page_id"]] = {
                "llm_metrics": None,
                "json_adherence": True,
            }
        else:
            missing_pages.append({**page, "cache_key": cache_key})
            summary_cache_misses += 1

    job_logger.info(
        "Summary cache summary",
        extra={"hits": summary_cache_hits, "misses": summary_cache_misses},
    )

    if missing_pages:
        batches = [
            missing_pages[i : i + settings.narration_batch_size]
            for i in range(0, len(missing_pages), settings.narration_batch_size)
        ]
        for idx, batch in enumerate(batches, start=1):
            batch_ids = [p["page_id"] for p in batch]
            job_logger.info(f"Summary batch {idx}/{len(batches)} for pages {batch_ids}")
            try:
                async with llm_semaphore:
                    batch_results, batch_meta = await batch_summarize_pages(
                        batch, language, max_words
                    )
                last_summary_llm_metrics = batch_meta.get("llm_metrics", {})
                last_summary_json_adherence = bool(batch_meta.get("json_adherence", True))
                if last_summary_llm_metrics:
                    job_logger.info(
                        "Summary batch metrics",
                        extra={
                            "ttft": last_summary_llm_metrics.get("ttft"),
                            "tps": last_summary_llm_metrics.get("tps"),
                            "memory_kb": last_summary_llm_metrics.get("memory_kb"),
                        },
                    )
            except Exception:
                batch_results = {}
                batch_meta = {"llm_metrics": None, "json_adherence": False}
                for page in batch:
                    async with llm_semaphore:
                        single_results, single_meta = await batch_summarize_pages(
                            [page], language, max_words
                        )
                        batch_results.update(single_results)
                        summary_meta_by_page_id[page["page_id"]] = {
                            "llm_metrics": single_meta.get("llm_metrics"),
                            "json_adherence": bool(single_meta.get("json_adherence", True)),
                        }

            for page in batch:
                page_id = page["page_id"]
                summary = batch_results.get(page_id)
                if summary:
                    summaries[page_id] = summary
                    save_cached_payload(
                        page["cache_key"],
                        {
                            "summary": summary,
                            "language": language,
                            "pipeline_type": "pdf_summary",
                            "created_at": datetime.utcnow().isoformat(),
                        },
                    )
                    if page_id not in summary_meta_by_page_id:
                        summary_meta_by_page_id[page_id] = {
                            "llm_metrics": batch_meta.get("llm_metrics"),
                            "json_adherence": bool(batch_meta.get("json_adherence", True)),
                        }
                else:
                    job_logger.warning(f"Missing summary for {page_id}")

            await job_manager.update_progress(
                job_id,
                _progress_for_batches(idx, len(batches), 10, 30),
                current_step="Generating summaries",
            )
    else:
        await job_manager.update_progress(job_id, 30, current_step="Generating summaries")

    if not generate_mcqs:
        await job_manager.update_progress(job_id, 40, current_step="LLM batches completed")

    mcq_cache_hits = 0
    mcq_cache_misses = 0
    mcqs: dict[str, list[dict[str, Any]]] = {}

    if generate_mcqs:
        missing_mcq_pages: list[dict[str, Any]] = []
        for page in page_items:
            cache_key = build_cache_key(
                language=language,
                slide_text=page["text"],
                pipeline_type="pdf_mcq",
            )
            cached_payload = load_cached_payload(cache_key)
            if cached_payload and cached_payload.get("questions"):
                mcqs[page["page_id"]] = cached_payload["questions"]
                mcq_cache_hits += 1
                job_logger.info(f"MCQ cache hit for {page['page_id']}")
            else:
                missing_mcq_pages.append({**page, "cache_key": cache_key})
                mcq_cache_misses += 1

        job_logger.info(
            "MCQ cache summary",
            extra={"hits": mcq_cache_hits, "misses": mcq_cache_misses},
        )

        if missing_mcq_pages:
            batches = [
                missing_mcq_pages[i : i + settings.narration_batch_size]
                for i in range(0, len(missing_mcq_pages), settings.narration_batch_size)
            ]
            for idx, batch in enumerate(batches, start=1):
                batch_ids = [p["page_id"] for p in batch]
                job_logger.info(f"MCQ batch {idx}/{len(batches)} for pages {batch_ids}")
                try:
                    async with llm_semaphore:
                        batch_results, _batch_meta = await batch_generate_mcqs(batch, language)
                except Exception:
                    batch_results = {}
                    for page in batch:
                        async with llm_semaphore:
                            single_results, _ = await batch_generate_mcqs([page], language)
                            batch_results.update(single_results)
                for page in batch:
                    page_id = page["page_id"]
                    questions = batch_results.get(page_id)
                    if questions:
                        mcqs[page_id] = questions
                        save_cached_payload(
                            page["cache_key"],
                            {
                                "questions": questions,
                                "language": language,
                                "pipeline_type": "pdf_mcq",
                                "created_at": datetime.utcnow().isoformat(),
                            },
                        )
                await job_manager.update_progress(
                    job_id,
                    _progress_for_batches(idx, len(batches), 30, 40),
                    current_step="Generating MCQs",
                )

        await job_manager.update_progress(job_id, 40, current_step="LLM batches completed")

    await job_manager.update_progress(
        job_id=job_id,
        progress=40,
        current_step="Narrating",
        extra_meta={
            "phase": "narration",
            "ttft": last_summary_llm_metrics.get("ttft"),
            "tps": last_summary_llm_metrics.get("tps"),
            "memory_kb": last_summary_llm_metrics.get("memory_kb"),
            "json_adherence": last_summary_json_adherence,
        },
    )

    slides_data: list[dict[str, Any]] = []
    narration_meta_by_slide: dict[int, dict[str, Any]] = {}
    slide_number = 0
    for page in page_items:
        summary = summaries.get(page["page_id"])
        if not summary:
            continue
        slide_number += 1
        slide_text = _build_slide_text(summary["title"], summary.get("bullets", []))
        narration_text = summary.get("narration", "")
        summary_meta = summary_meta_by_page_id.get(page["page_id"], {})
        narration_meta_by_slide[slide_number] = build_narration_meta(
            page["text"],
            narration_text,
            json_adherence=bool(summary_meta.get("json_adherence", True)),
            llm_metrics=summary_meta.get("llm_metrics"),
        )
        slides_data.append(
            {
                "slide_number": slide_number,
                "page_id": page["page_id"],
                "text": slide_text,
                "source_text": page["text"],
                "title": summary["title"],
                "bullets": summary.get("bullets", []),
                "narration": narration_text,
                "mcqs": mcqs.get(page["page_id"], []),
            }
        )

    total_slides = len(slides_data)
    if total_slides == 0:
        end_time = datetime.utcnow()
        return JobResult(
            job_id=job_id,
            status="completed",
            filename=Path(pdf_path).name,
            language=language,
            mode="pdf",
            slides=[],
            final_video_path=None,
            processing_time_seconds=(end_time - start_time).total_seconds(),
            cache_hits=summary_cache_hits + mcq_cache_hits,
            cache_misses=summary_cache_misses + mcq_cache_misses,
            slide_metrics=[],
            created_at=start_time,
            completed_at=end_time,
        )

    slide_numbers = [s["slide_number"] for s in slides_data]
    job_manager.start_processing(job_id, total_slides, slide_numbers)
    for slide in slides_data:
        job_manager.update_slide_progress(job_id, slide["slide_number"], narration=SlideState.COMPLETED)
        if generate_mcqs:
            job_manager.update_slide_progress(job_id, slide["slide_number"], mcq=SlideState.COMPLETED)

    async def _run_tts(text: str) -> str:
        async with tts_semaphore:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, synthesize_speech, text, language)

    async def _run_render(text: str) -> str:
        async with render_semaphore:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, render_slide_image, text)

    async def _run_video(image_path: str, audio_path: str) -> str:
        async with video_semaphore:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, create_video, image_path, audio_path)

    video_paths: dict[int, str] = {}
    slide_index_map = {slide_num: idx + 1 for idx, slide_num in enumerate(slide_numbers)}
    last_reported_index = [0]
    progress_lock = asyncio.Lock()

    async def _process_slide(slide: dict[str, Any]) -> SlideResult:
        slide_num = slide["slide_number"]
        job_manager.check_cancellation(job_id)

        result = SlideResult(
            slide_number=slide_num,
            text=slide["text"],
            has_text=True,
            title=slide.get("title"),
            bullets=slide.get("bullets"),
            narration=slide.get("narration"),
        )

        current_index = slide_index_map.get(slide_num, 0)
        if current_index:
            async with progress_lock:
                    if current_index > last_reported_index[0]:
                        last_reported_index[0] = current_index
                        progress = int(40 + (current_index / total_slides) * 40)
                        slide_meta = narration_meta_by_slide.get(slide_num, {})
                        await job_manager.update_progress(
                            job_id=job_id,
                            progress=progress,
                            current_step=f"Processing Slide {current_index} of {total_slides}",
                            extra_meta={
                                "phase": "rendering",
                                "slide_number": slide_num,
                                **slide_meta,
                            },
                        )

        if slide.get("mcqs"):
            qa_obj: dict[str, list[MCQuestion]] = {"easy": [], "medium": [], "hard": []}
            for question in slide["mcqs"]:
                if question.get("difficulty") in qa_obj:
                    qa_obj[question["difficulty"]].append(MCQuestion(**question))
            result.qa = {k: v for k, v in qa_obj.items() if v}

        try:
            if generate_video and result.narration:
                job_manager.update_slide_progress(job_id, slide_num, video=SlideState.PROCESSING)
                audio_task = asyncio.create_task(_run_tts(result.narration))
                image_task = asyncio.create_task(_run_render(slide["text"]))
                audio_path, image_path = await asyncio.gather(audio_task, image_task)
                result.audio_path = audio_path
                result.image_path = image_path
                video_path = await _run_video(image_path, audio_path)
                result.video_path = video_path
                video_paths[slide_num] = video_path
                job_manager.update_slide_progress(job_id, slide_num, video=SlideState.COMPLETED)
        except JobCancelledError:
            raise
        except Exception as exc:
            job_logger.error(f"PDF slide {slide_num} failed: {exc}")
            job_manager.update_slide_progress(
                job_id,
                slide_num,
                video=SlideState.FAILED if generate_video and not result.video_path else SlideState.COMPLETED,
                error=str(exc),
            )

        job_logger.info(f"PDF slide completed: {slide_num}")
        return result

    results = await asyncio.gather(*[asyncio.create_task(_process_slide(slide)) for slide in slides_data])
    await job_manager.update_progress(job_id, 80, current_step="TTS and clip generation completed")
    await job_manager.update_progress(
        job_id=job_id,
        progress=80,
        current_step="Rendering",
        extra_meta={"phase": "rendering"},
    )

    final_video_path = None
    model_name = settings.ollama_model or "unknown"
    slide_metrics = []
    for slide_num in slide_numbers:
        meta = narration_meta_by_slide.get(slide_num, {})
        slide_metrics.append(
            {
                "tps": meta.get("tps"),
                "ttft": meta.get("ttft"),
                "word_count": meta.get("narration_word_count"),
                "json_valid": meta.get("json_adherence"),
                "hallucination_ok": meta.get("hallucination_ok"),
                "memory_kb": meta.get("memory_kb"),
                "token_count": meta.get("token_count"),
            }
        )
    final_meta = {"slide_metrics": slide_metrics}
    if generate_video and video_paths:
        ordered_paths = [video_paths[num] for num in slide_numbers if num in video_paths]
        output_dir = settings.storage_output_dir / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "final.mp4"
        await job_manager.update_progress(job_id, 80, current_step="Stitching final video")
        loop = asyncio.get_event_loop()
        final_video_path = await loop.run_in_executor(
            None, stitch_videos, ordered_paths, str(output_path)
        )
        redis_manager.archive_benchmark_data(job_id, model_name, final_meta)
        job_logger.info(
            f"Benchmark archived for model {model_name} on job {job_id}"
        )
        await job_manager.update_progress(job_id, 100, current_step="Processing completed")
    else:
        redis_manager.archive_benchmark_data(job_id, model_name, final_meta)
        job_logger.info(
            f"Benchmark archived for model {model_name} on job {job_id}"
        )
        await job_manager.update_progress(job_id, 100, current_step="Processing completed")

    end_time = datetime.utcnow()
    return JobResult(
        job_id=job_id,
        status="completed",
        filename=Path(pdf_path).name,
        language=language,
        mode="pdf",
        slides=results,
        final_video_path=final_video_path,
        processing_time_seconds=(end_time - start_time).total_seconds(),
        cache_hits=summary_cache_hits + mcq_cache_hits,
        cache_misses=summary_cache_misses + mcq_cache_misses,
        slide_metrics=slide_metrics,
        created_at=start_time,
        completed_at=end_time,
    )
