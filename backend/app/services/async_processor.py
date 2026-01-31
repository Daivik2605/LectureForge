"""
Async Processor - Dispatches processing pipelines based on mode/file type.
"""

from datetime import datetime
import json
from pathlib import Path
from app.core.exceptions import JobCancelledError
from app.core.logging import get_logger
from app.models.job import JobResult, JobState
from app.services.job_manager import job_manager
from app.services.ppt_pipeline import process_ppt_job, process_ppt_sync
from app.services.pdf_pipeline import process_pdf_job

logger = get_logger(__name__)


async def process_ppt_async(
    job_id: str,
    ppt_path: str,
    language: str = "en",
    max_slides: int = 5,
    generate_video: bool = True,
    generate_mcqs: bool = True,
) -> JobResult:
    """
    Wrapper for PPT pipeline (kept for backward compatibility).
    """
    return await process_ppt_job(
        job_id=job_id,
        ppt_path=ppt_path,
        language=language,
        max_slides=max_slides,
        generate_video=generate_video,
        generate_mcqs=generate_mcqs,
    )


async def run_processing_job(
    job_id: str,
    ppt_path: str,
    language: str,
    max_slides: int,
    generate_video: bool,
    generate_mcqs: bool,
    mode: str = "ppt",
) -> None:
    """
    Run a processing job in the background.

    This is the entry point for background task execution.
    """
    try:
        await job_manager.update_progress(
            job_id=job_id,
            progress=5,
            current_step="Dispatching job",
            status=JobState.PROCESSING.value,
            extra_meta={"phase": "dispatch", "mode": mode},
        )
        suffix = Path(ppt_path).suffix.lower()
        if mode == "auto":
            if suffix in {".pdf"}:
                mode = "pdf"
            elif suffix in {".txt"}:
                mode = "policy"
            else:
                mode = "ppt"

        if mode == "policy":
            from app.services.policy_pipeline import process_policy_job

            start_time = datetime.utcnow()
            # FIXED: Use update_progress instead
            await job_manager.update_progress(
                job_id=job_id, 
                progress=10, 
                current_step="Starting policy extraction",
                extra_meta={"total_slides": 1}
            )
            final_video_path = await process_policy_job(job_id, ppt_path, language)
            end_time = datetime.utcnow()
            result = JobResult(
                job_id=job_id,
                status="completed",
                filename=Path(ppt_path).name,
                language=language,
                mode="policy",
                slides=[],
                final_video_path=final_video_path,
                processing_time_seconds=(end_time - start_time).total_seconds(),
                cache_hits=0,
                cache_misses=0,
                created_at=start_time,
                completed_at=end_time,
            )
        elif mode == "pdf":
            result = await process_pdf_job(
                job_id=job_id,
                pdf_path=ppt_path,
                language=language,
                max_slides=max_slides,
                generate_video=generate_video,
                generate_mcqs=generate_mcqs,
            )
        else:
            result = await process_ppt_async(
                job_id=job_id,
                ppt_path=ppt_path,
                language=language,
                max_slides=max_slides,
                generate_video=generate_video,
                generate_mcqs=generate_mcqs,
            )

        await job_manager.complete_job(job_id)
        slide_metrics = getattr(result, "slide_metrics", None) or []
        await job_manager.update_progress(
            job_id=job_id,
            progress=100,
            current_step="Completed",
            status=JobState.COMPLETED.value,
            extra_meta={
                "phase": "completed",
                "slide_metrics": json.dumps(slide_metrics, ensure_ascii=True),
            },
        )

    except JobCancelledError:
        await job_manager.update_progress(
            job_id=job_id,
            progress=0,
            current_step="Cancelled",
            status=JobState.CANCELLED.value,
            extra_meta={"phase": "cancelled"},
        )
    except Exception as exc:
        await job_manager.fail_job(job_id, str(exc))
        await job_manager.update_progress(
            job_id=job_id,
            progress=0,
            current_step="Failed",
            status=JobState.FAILED.value,
            extra_meta={"phase": "failed", "error": str(exc)},
        )


# Keep sync version for backward compatibility
def process_ppt(ppt_path: str, language: str = "en", max_slides: int = 5) -> list[dict]:
    """
    Synchronous PPT processing (legacy support).

    For new code, use process_ppt_async instead.
    """
    logger.info(f"Processing PPT synchronously: {ppt_path}")
    return process_ppt_sync(ppt_path, language=language, max_slides=max_slides)
