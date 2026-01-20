"""
Simple dev script to exercise the pipeline and report timings.
"""

from __future__ import annotations

import argparse
import asyncio
import time
import uuid
from pathlib import Path

from app.core.config import settings
from app.services.async_processor import process_ppt_async
from app.services.job_manager import job_manager
from app.services.narration_cache import build_cache_key, load_cached_narration
from app.services.ppt_parser import parse_ppt
from app.services.policy_pipeline.policy_processor import (
    _extract_policy_text,
    _split_chapters,
    process_policy_job,
)


def _cache_hit_ratio(slides: list[dict], language: str, mode: str) -> float:
    if not slides:
        return 0.0
    hits = 0
    for slide in slides:
        key = build_cache_key(
            language=language,
            slide_text=slide.get("text", ""),
            pipeline_type=mode,
        )
        if load_cached_narration(key):
            hits += 1
    return hits / len(slides)


async def _run_ppt(args: argparse.Namespace) -> None:
    slides = [s for s in parse_ppt(args.ppt_path) if s.get("has_text")][: args.max_slides]
    cache_ratio = _cache_hit_ratio(slides, args.language, mode="ppt")

    job_id = job_manager.create_job(
        filename=Path(args.ppt_path).name,
        language=args.language,
        max_slides=args.max_slides,
        generate_video=not args.skip_video,
        generate_mcqs=not args.skip_mcqs,
    )

    start = time.monotonic()
    result = await process_ppt_async(
        job_id=job_id,
        ppt_path=args.ppt_path,
        language=args.language,
        max_slides=args.max_slides,
        generate_video=not args.skip_video,
        generate_mcqs=not args.skip_mcqs,
    )
    job_manager.complete_job(job_id, result)
    duration = time.monotonic() - start

    print("Perf summary (ppt)")
    print(f"Total time: {duration:.2f}s")
    print(f"Slides processed: {len(result.slides)}")
    print(f"Cache hit ratio: {cache_ratio:.2%}")
    print(f"Batch size: {settings.narration_batch_size}")


def _run_policy(args: argparse.Namespace) -> None:
    text = _extract_policy_text(args.ppt_path)
    chapters = _split_chapters(text)
    slides = [{"text": chapter} for chapter in chapters]
    cache_ratio = _cache_hit_ratio(slides, args.language, mode="policy")

    job_id = str(uuid.uuid4())
    start = time.monotonic()
    final_video_path = process_policy_job(job_id, args.ppt_path, args.language)
    duration = time.monotonic() - start

    print("Perf summary (policy)")
    print(f"Total time: {duration:.2f}s")
    print(f"Chapters processed: {len(chapters)}")
    print(f"Cache hit ratio: {cache_ratio:.2%}")
    print(f"Batch size: {settings.narration_batch_size}")
    print(f"Final video: {final_video_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local perf test.")
    parser.add_argument("ppt_path", help="Path to PPT/PDF/TXT input")
    parser.add_argument("--language", default="en", help="Language code (default: en)")
    parser.add_argument("--max-slides", type=int, default=5, help="Max slides to process")
    parser.add_argument("--mode", choices=["ppt", "policy"], default="ppt")
    parser.add_argument("--skip-video", action="store_true", help="Skip video generation")
    parser.add_argument("--skip-mcqs", action="store_true", help="Skip MCQ generation")
    args = parser.parse_args()

    if args.mode == "policy":
        _run_policy(args)
    else:
        asyncio.run(_run_ppt(args))


if __name__ == "__main__":
    main()
