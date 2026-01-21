"""
Jobs API - Endpoints for job status and results.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import JobNotFoundError
from app.services.job_manager import job_manager
from app.models.job import JobStatus, JobResult, JobSummary

logger = get_logger(__name__)
router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/{job_id}/status", response_model=JobStatus)
async def get_job_status(job_id: str):
    """
    Get the current status of a processing job.
    
    Returns progress information including:
    - Overall progress percentage
    - Current slide being processed
    - Per-slide progress breakdown
    """
    try:
        status = job_manager.get_job_status(job_id)
        return status
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")


@router.get("/{job_id}/result", response_model=JobResult)
async def get_job_result(job_id: str):
    """
    Get the complete result of a finished job.
    
    Only available when job status is 'completed'.
    Returns all slides with narrations, MCQs, and file paths.
    """
    try:
        # First check status
        status = job_manager.get_job_status(job_id)
        
        if status.status.value == "failed":
            raise HTTPException(
                status_code=400,
                detail=f"Job failed: {status.error}"
            )
        
        if status.status.value != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Job not completed. Current status: {status.status.value}"
            )
        
        result = job_manager.get_job_result(job_id)
        return result
        
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel a running job.
    
    Only works for jobs in 'pending' or 'processing' state.
    """
    try:
        cancelled = job_manager.cancel_job(job_id)
        if cancelled:
            return {"message": "Job cancelled successfully", "job_id": job_id}
        else:
            return {"message": "Job cannot be cancelled (already completed or failed)", "job_id": job_id}
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")


@router.get("", response_model=list[JobSummary])
async def list_jobs(limit: int = 10):
    """
    List recent jobs.
    
    Returns a summary of the most recent jobs.
    """
    jobs = job_manager.store.list_jobs(limit=limit)
    return [
        JobSummary(
            job_id=job["job_id"],
            filename=job["filename"],
            status=job["status"],
            progress=job["progress"],
            created_at=job["created_at"],
        )
        for job in jobs
    ]


@router.get("/download")
async def download_file(path: str):
    """
    Download a generated file (audio, video, image).
    
    The path should be a relative path from the data directory.
    """
    file_path = Path(path)
    
    # Security: Ensure path is within data directory
    try:
        file_path = file_path.resolve()
        data_dir = settings.base_data_dir.resolve()
        
        if not str(file_path).startswith(str(data_dir)):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type
    suffix = file_path.suffix.lower()
    media_types = {
        ".mp4": "video/mp4",
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".json": "application/json",
    }
    media_type = media_types.get(suffix, "application/octet-stream")
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=file_path.name
    )
