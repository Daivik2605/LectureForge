"""
PPT pipeline - slide-based processing (1 slide -> 1 narration -> 1 clip).
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import PPTParseError, JobCancelledError
from app.core.logging import get_job_logger
from app.models.job import JobResult, SlideResult, SlideState, MCQuestion
from app.services.job_manager import job_manager
from app.services.narration_chain import generate_narrations_batch, generate_narration_sync
from app.services.narration_cache import build_cache_key, load_cached_narration, save_cached_narration
from app.services.ppt_parser import parse_ppt
from app.services.qa_chain import generate_mcqs_async, generate_mcqs_sync
from app.services.qa_validator import validate_and_fix_mcqs, validate_mcq_language
from app.services.slide_renderer import render_slide_image
from app.services.tts_service import synthesize_speech
from app.services.video_assembler import create_video
from app.services.video_stitcher import stitch_videos


async def process_ppt_job(
    job_id: str,
    ppt_path: str,
    language: str = "en",
    max_slides: int = 5,
    generate_video: bool = True,
    generate_mcqs: bool = True,
) -> JobResult:
    job_logger = get_job_logger(job_id)
    job_logger.info(f"Starting PPT pipeline: {ppt_path}")
    start_time = datetime.utcnow()

    try:
        try:
            all_slides = parse_ppt(ppt_path)
        except Exception as exc:
            raise PPTParseError(str(exc), Path(ppt_path).name)

        job_manager.update_progress(job_id, 10, current_step="Parsing presentation")

        slides = [s for s in all_slides if s["has_text"]][:max_slides]
        total_slides = len(slides)
        if total_slides == 0:
            return JobResult(
                job_id=job_id,
                status="completed",
                filename=Path(ppt_path).name,
                language=language,
                mode="ppt",
                slides=[],
                processing_time_seconds=0,
                cache_hits=0,
                cache_misses=0,
                created_at=start_time,
                completed_at=datetime.utcnow(),
            )

        slide_numbers = [s["slide_number"] for s in slides]
        job_manager.start_processing(job_id, total_slides, slide_numbers)
        job_logger.info(f"PPT slides: {slide_numbers}")

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
            },
        )

        narrations: dict[int, str] = {}
        slides_missing: list[dict] = []
        cache_hits = 0
        cache_misses = 0

        for slide in slides:
            slide_num = slide["slide_number"]
            slide_text = slide["text"]
            cache_key = build_cache_key(
                language=language,
                slide_text=slide_text,
                pipeline_type="ppt",
            )
            cached = load_cached_narration(cache_key)
            if cached:
                job_logger.info(f"Narration cache hit for slide {slide_num}")
                narrations[slide_num] = cached
                cache_hits += 1
                job_manager.update_slide_progress(job_id, slide_num, narration=SlideState.COMPLETED)
            else:
                slides_missing.append({**slide, "cache_key": cache_key})
                cache_misses += 1
                job_manager.update_slide_progress(job_id, slide_num, narration=SlideState.PROCESSING)

        job_logger.info(
            "Narration cache summary",
            extra={"hits": cache_hits, "misses": cache_misses},
        )

        if slides_missing:
            batches = [
                slides_missing[i : i + settings.narration_batch_size]
                for i in range(0, len(slides_missing), settings.narration_batch_size)
            ]
            for idx, batch in enumerate(batches, start=1):
                batch_slide_numbers = [s["slide_number"] for s in batch]
                job_logger.info(
                    f"Narration batch {idx}/{len(batches)} for slides {batch_slide_numbers}"
                )
                async with llm_semaphore:
                    batch_results = await generate_narrations_batch(batch, language)
                for slide in batch:
                    slide_num = slide["slide_number"]
                    narration = batch_results.get(slide_num)
                    if narration:
                        narrations[slide_num] = narration
                        save_cached_narration(
                            slide["cache_key"],
                            narration,
                            language=language,
                            pipeline_type="ppt",
                        )
                        job_manager.update_slide_progress(
                            job_id, slide_num, narration=SlideState.COMPLETED
                        )
                    else:
                        job_logger.warning(f"Narration missing for slide {slide_num}")
                        job_manager.update_slide_progress(
                            job_id, slide_num, narration=SlideState.FAILED
                        )
                job_manager.update_progress(
                    job_id,
                    int(10 + (30 * idx / len(batches))),
                    current_step="Generating narrations",
                )

            job_manager.update_progress(job_id, 40, current_step="LLM batches completed")
        else:
            job_manager.update_progress(job_id, 40, current_step="LLM batches completed")

        job_manager.update_progress(job_id, 40, current_step="LLM batches completed")

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

        async def _process_slide(slide: dict) -> SlideResult:
            slide_num = slide["slide_number"]
            slide_text = slide["text"]
            job_manager.check_cancellation(job_id)

            slide_result = SlideResult(
                slide_number=slide_num,
                text=slide_text,
                has_text=True,
            )

            try:
                narration = narrations.get(slide_num)
                slide_result.narration = narration

                if generate_mcqs:
                    job_logger.info(f"[MCQ] Starting MCQ generation for slide {slide_num}")
                    job_manager.update_slide_progress(job_id, slide_num, mcq=SlideState.PROCESSING)
                    improved_prompt = (
                        f"Generate at least 3 multiple-choice questions (easy, medium, hard) based on the following slide text. "
                        f"Each question should have 4 options, one correct answer, and a difficulty label. "
                        f"Slide text: {slide_text}\n"
                    )
                    async with llm_semaphore:
                        qa_raw = await generate_mcqs_async(improved_prompt, language)
                    validated_qa = validate_and_fix_mcqs(qa_raw)
                    if not validated_qa["questions"] or not validate_mcq_language(validated_qa, language):
                        job_logger.warning(f"[MCQ] Validation failed, retrying...")
                        async with llm_semaphore:
                            qa_raw = await generate_mcqs_async(improved_prompt, language)
                        validated_qa = validate_and_fix_mcqs(qa_raw)
                        if not validate_mcq_language(validated_qa, language):
                            job_logger.error(f"[MCQ] MCQ language validation failed after retry.")
                            validated_qa = {"questions": []}
                    qa_obj = {}
                    for diff in ["easy", "medium", "hard"]:
                        if validated_qa.get(diff):
                            qa_obj[diff] = [
                                MCQuestion(**q) if not isinstance(q, MCQuestion) else q
                                for q in validated_qa[diff]
                            ]
                    slide_result.qa = qa_obj
                    job_manager.update_slide_progress(job_id, slide_num, mcq=SlideState.COMPLETED)

                if generate_video and narration:
                    job_manager.update_slide_progress(job_id, slide_num, video=SlideState.PROCESSING)
                    audio_task = asyncio.create_task(_run_tts(narration))
                    image_task = asyncio.create_task(_run_render(slide_text))
                    audio_path, image_path = await asyncio.gather(audio_task, image_task)
                    slide_result.audio_path = audio_path
                    slide_result.image_path = image_path
                    video_path = await _run_video(image_path, audio_path)
                    slide_result.video_path = video_path
                    video_paths[slide_num] = video_path
                    job_manager.update_slide_progress(job_id, slide_num, video=SlideState.COMPLETED)

            except JobCancelledError:
                raise
            except Exception as exc:
                job_logger.error(f"Error processing slide {slide_num}: {exc}")
                job_manager.update_slide_progress(
                    job_id, slide_num,
                    narration=SlideState.FAILED if not slide_result.narration else SlideState.COMPLETED,
                    mcq=SlideState.FAILED if generate_mcqs and not slide_result.qa else SlideState.COMPLETED,
                    video=SlideState.FAILED if generate_video and not slide_result.video_path else SlideState.COMPLETED,
                    error=str(exc),
                )

            job_logger.info(f"Slide processing completed: {slide_num}")
            return slide_result

        results = await asyncio.gather(*[asyncio.create_task(_process_slide(slide)) for slide in slides])
        job_manager.update_progress(job_id, 80, current_step="TTS and clip generation completed")

        final_video_path = None
        if generate_video and video_paths:
            ordered_paths = [
                video_paths[slide_num]
                for slide_num in slide_numbers
                if slide_num in video_paths
            ]
            output_dir = Path("storage/outputs") / job_id
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / "final.mp4"
            job_manager.update_progress(job_id, 80, current_step="Stitching final video")
            loop = asyncio.get_event_loop()
            final_video_path = await loop.run_in_executor(
                None, stitch_videos, ordered_paths, str(output_path)
            )
            job_manager.update_progress(job_id, 100, current_step="Processing completed")
        else:
            job_manager.update_progress(job_id, 100, current_step="Processing completed")

        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()

        return JobResult(
            job_id=job_id,
            status="completed",
            filename=Path(ppt_path).name,
            language=language,
            mode="ppt",
            slides=results,
            final_video_path=final_video_path,
            processing_time_seconds=processing_time,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            created_at=start_time,
            completed_at=end_time,
        )

    except JobCancelledError:
        job_logger.info("Job was cancelled")
        raise


def process_ppt_sync(
    ppt_path: str,
    language: str = "en",
    max_slides: int = 5,
) -> list[dict]:
    """
    Legacy sync processing (kept for backward compatibility).
    """
    slides = [s for s in parse_ppt(ppt_path) if s["has_text"]][:max_slides]
    results = []

    for slide in slides:
        slide_num = slide["slide_number"]
        slide_text = slide["text"]
        slide_result = {
            "slide_number": slide_num,
            "text": slide_text,
            "has_text": True,
            "narration": None,
            "qa": None,
            "audio": None,
            "video": None,
        }
        cache_key = build_cache_key(language=language, slide_text=slide_text, pipeline_type="ppt")
        cached = load_cached_narration(cache_key)
        if cached:
            narration = cached
        else:
            narration = generate_narration_sync(slide_text, language)
            save_cached_narration(
                cache_key,
                narration,
                language=language,
                pipeline_type="ppt",
            )
        slide_result["narration"] = narration

        audio_path = synthesize_speech(narration, language)
        image_path = render_slide_image(slide_text)
        video_path = create_video(image_path, audio_path)

        slide_result["audio"] = audio_path
        slide_result["video"] = video_path

        qa_raw = generate_mcqs_sync(slide_text, language)
        validated_qa = validate_and_fix_mcqs(qa_raw)
        if not validated_qa["questions"] or not validate_mcq_language(validated_qa, language):
            qa_raw = generate_mcqs_sync(slide_text, language)
            validated_qa = validate_and_fix_mcqs(qa_raw)
            if not validate_mcq_language(validated_qa, language):
                validated_qa = {"questions": []}
        slide_result["qa"] = validated_qa
        results.append(slide_result)

    return results
