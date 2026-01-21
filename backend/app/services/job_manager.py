"""
Job Manager - Handles job creation, tracking, and execution.
Uses in-memory storage (can be extended to Redis for production).
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional, Callable, Any
from collections import OrderedDict
import threading

from app.core.logging import get_logger
from app.core.config import settings
from app.core.exceptions import (
    JobNotFoundError,
    JobTimeoutError,
    JobCancelledError,
    TooManyJobsError,
)
from app.models.job import (
    JobStatus,
    JobState,
    JobResult,
    SlideProgress,
    SlideState,
    SlideResult,
)

logger = get_logger(__name__)


class JobStore:
    """Thread-safe in-memory job storage."""
    
    def __init__(self, max_jobs: int = 100):
        self._jobs: OrderedDict[str, dict] = OrderedDict()
        self._results: dict[str, JobResult] = {}
        self._lock = threading.Lock()
        self._max_jobs = max_jobs
    
    def create(self, job_id: str, data: dict) -> None:
        """Create a new job entry."""
        with self._lock:
            # Evict oldest jobs if at capacity
            while len(self._jobs) >= self._max_jobs:
                oldest = next(iter(self._jobs))
                del self._jobs[oldest]
                if oldest in self._results:
                    del self._results[oldest]
            
            self._jobs[job_id] = data
    
    def get(self, job_id: str) -> Optional[dict]:
        """Get job data by ID."""
        with self._lock:
            return self._jobs.get(job_id)
    
    def update(self, job_id: str, data: dict) -> None:
        """Update job data."""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(data)
    
    def set_result(self, job_id: str, result: JobResult) -> None:
        """Store job result."""
        with self._lock:
            self._results[job_id] = result
    
    def get_result(self, job_id: str) -> Optional[JobResult]:
        """Get job result."""
        with self._lock:
            return self._results.get(job_id)
    
    def delete(self, job_id: str) -> None:
        """Delete job and its result."""
        with self._lock:
            self._jobs.pop(job_id, None)
            self._results.pop(job_id, None)
    
    def get_active_count(self) -> int:
        """Count jobs in pending or processing state."""
        with self._lock:
            return sum(
                1 for job in self._jobs.values()
                if job.get("status") in [JobState.PENDING, JobState.PROCESSING]
            )
    
    def list_jobs(self, limit: int = 10) -> list[dict]:
        """List recent jobs."""
        with self._lock:
            jobs = list(self._jobs.values())[-limit:]
            return list(reversed(jobs))


class JobManager:
    """
    Manages job lifecycle: creation, execution, progress tracking.
    """
    
    def __init__(self):
        self.store = JobStore(max_jobs=100)
        self._websocket_callbacks: dict[str, list[Callable]] = {}
        self._cancel_flags: dict[str, bool] = {}
    
    def create_job(
        self,
        filename: str,
        language: str,
        max_slides: int,
        generate_video: bool = True,
        generate_mcqs: bool = True,
    ) -> str:
        """
        Create a new processing job.
        
        Returns:
            job_id: Unique identifier for the job
        """
        # Check concurrent job limit
        active_count = self.store.get_active_count()
        if active_count >= settings.max_concurrent_jobs:
            raise TooManyJobsError(settings.max_concurrent_jobs)
        
        job_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        job_data = {
            "job_id": job_id,
            "filename": filename,
            "language": language,
            "max_slides": max_slides,
            "generate_video": generate_video,
            "generate_mcqs": generate_mcqs,
            "status": JobState.PENDING,
            "progress": 0,
            "current_slide": None,
            "total_slides": None,
            "current_step": "Queued",
            "slides_progress": [],
            "error": None,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
        }
        
        self.store.create(job_id, job_data)
        logger.info(f"Created job {job_id} for {filename}")
        
        return job_id
    
    def get_job_status(self, job_id: str) -> JobStatus:
        """Get current job status."""
        job_data = self.store.get(job_id)
        if not job_data:
            raise JobNotFoundError(job_id)
        
        return JobStatus(**job_data)
    
    def get_job_result(self, job_id: str) -> JobResult:
        """Get job result (only available when completed)."""
        result = self.store.get_result(job_id)
        if not result:
            job_data = self.store.get(job_id)
            if not job_data:
                raise JobNotFoundError(job_id)
            if job_data["status"] != JobState.COMPLETED:
                raise JobNotFoundError(f"Job {job_id} not completed yet")
        return result
    
    def update_progress(
        self,
        job_id: str,
        progress: int,
        current_slide: Optional[int] = None,
        current_step: Optional[str] = None,
        slides_progress: Optional[list[SlideProgress]] = None,
    ) -> None:
        """Update job progress."""
        update_data = {
            "progress": min(progress, 100),
            "updated_at": datetime.utcnow(),
        }
        
        if current_slide is not None:
            update_data["current_slide"] = current_slide
        if current_step is not None:
            update_data["current_step"] = current_step
        if slides_progress is not None:
            update_data["slides_progress"] = [sp.model_dump() for sp in slides_progress]
        
        self.store.update(job_id, update_data)
        
        # Notify WebSocket subscribers
        asyncio.create_task(self._notify_progress(job_id))
    
    def start_processing(self, job_id: str, total_slides: int, slide_numbers: list[int] = None) -> None:
        """Mark job as processing."""
        # Initialize slide progress with actual slide numbers
        if slide_numbers:
            slides_progress = [
                SlideProgress(slide_number=num).model_dump()
                for num in slide_numbers
            ]
        else:
            slides_progress = [
                SlideProgress(slide_number=i + 1).model_dump()
                for i in range(total_slides)
            ]
        
        self.store.update(job_id, {
            "status": JobState.PROCESSING,
            "total_slides": total_slides,
            "current_step": "Starting processing",
            "slides_progress": slides_progress,
            "updated_at": datetime.utcnow(),
        })
        
        asyncio.create_task(self._notify_progress(job_id))
    
    def update_slide_progress(
        self,
        job_id: str,
        slide_number: int,
        narration: Optional[SlideState] = None,
        mcq: Optional[SlideState] = None,
        video: Optional[SlideState] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update progress for a specific slide."""
        job_data = self.store.get(job_id)
        if not job_data:
            return
        
        slides_progress = job_data.get("slides_progress", [])
        for sp in slides_progress:
            if sp["slide_number"] == slide_number:
                if narration is not None:
                    sp["narration"] = narration.value
                if mcq is not None:
                    sp["mcq"] = mcq.value
                if video is not None:
                    sp["video"] = video.value
                if error is not None:
                    sp["error"] = error
                break
        
        self.store.update(job_id, {
            "slides_progress": slides_progress,
            "updated_at": datetime.utcnow(),
        })
        
        asyncio.create_task(self._notify_progress(job_id))
    
    def complete_job(self, job_id: str, result: JobResult) -> None:
        """Mark job as completed with result."""
        now = datetime.utcnow()
        
        self.store.update(job_id, {
            "status": JobState.COMPLETED,
            "progress": 100,
            "current_step": "Completed",
            "completed_at": now,
            "updated_at": now,
        })
        
        self.store.set_result(job_id, result)
        logger.info(f"Job {job_id} completed successfully")
        
        asyncio.create_task(self._notify_completed(job_id, result))
    
    def fail_job(self, job_id: str, error: str) -> None:
        """Mark job as failed."""
        self.store.update(job_id, {
            "status": JobState.FAILED,
            "error": error,
            "current_step": "Failed",
            "updated_at": datetime.utcnow(),
        })
        
        logger.error(f"Job {job_id} failed: {error}")
        asyncio.create_task(self._notify_error(job_id, error))
    
    def cancel_job(self, job_id: str) -> bool:
        """Request job cancellation."""
        job_data = self.store.get(job_id)
        if not job_data:
            raise JobNotFoundError(job_id)
        
        if job_data["status"] in [JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED]:
            return False
        
        self._cancel_flags[job_id] = True
        self.store.update(job_id, {
            "status": JobState.CANCELLED,
            "current_step": "Cancelled",
            "updated_at": datetime.utcnow(),
        })
        
        logger.info(f"Job {job_id} cancelled")
        return True
    
    def is_cancelled(self, job_id: str) -> bool:
        """Check if job cancellation was requested."""
        return self._cancel_flags.get(job_id, False)
    
    def check_cancellation(self, job_id: str) -> None:
        """Raise exception if job was cancelled."""
        if self.is_cancelled(job_id):
            raise JobCancelledError(job_id)
    
    # ===================
    # WebSocket Support
    # ===================
    
    def subscribe(self, job_id: str, callback: Callable) -> None:
        """Subscribe to job updates."""
        if job_id not in self._websocket_callbacks:
            self._websocket_callbacks[job_id] = []
        self._websocket_callbacks[job_id].append(callback)
    
    def unsubscribe(self, job_id: str, callback: Callable) -> None:
        """Unsubscribe from job updates."""
        if job_id in self._websocket_callbacks:
            self._websocket_callbacks[job_id] = [
                cb for cb in self._websocket_callbacks[job_id]
                if cb != callback
            ]
    
    async def _notify_progress(self, job_id: str) -> None:
        """Notify all subscribers of progress update."""
        callbacks = self._websocket_callbacks.get(job_id, [])
        job_data = self.store.get(job_id)
        
        if job_data and callbacks:
            message = {
                "type": "progress",
                "job_id": job_id,
                "data": {
                    "progress": job_data["progress"],
                    "current_slide": job_data.get("current_slide"),
                    "current_step": job_data.get("current_step"),
                    "slides_progress": job_data.get("slides_progress", []),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            for callback in callbacks:
                try:
                    await callback(message)
                except Exception as e:
                    logger.error(f"WebSocket callback error: {e}")
    
    async def _notify_completed(self, job_id: str, result: JobResult) -> None:
        """Notify all subscribers of completion."""
        callbacks = self._websocket_callbacks.get(job_id, [])
        
        if callbacks:
            message = {
                "type": "completed",
                "job_id": job_id,
                "data": {"result": result.model_dump()},
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            for callback in callbacks:
                try:
                    await callback(message)
                except Exception as e:
                    logger.error(f"WebSocket callback error: {e}")
    
    async def _notify_error(self, job_id: str, error: str) -> None:
        """Notify all subscribers of error."""
        callbacks = self._websocket_callbacks.get(job_id, [])
        
        if callbacks:
            message = {
                "type": "error",
                "job_id": job_id,
                "data": {"error": error},
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            for callback in callbacks:
                try:
                    await callback(message)
                except Exception as e:
                    logger.error(f"WebSocket callback error: {e}")


# Global job manager instance
job_manager = JobManager()
