"""
Job Manager - Handles job creation, tracking, and execution.
Uses in-memory storage (can be extended to Redis for production).
"""

import asyncio
from fileinput import filename
import uuid
from datetime import datetime
from typing import Optional, Callable, Any
from collections import OrderedDict
import threading

import json
from typing import Optional, List
from app.core.redis import redis_manager  # Assuming your singleton exists

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
    """
    Data Access Layer (DAL) for Redis.
    
    This class handles the raw communication with the Redis database. 
    Every method is 'async' because interacting with Redis involves network I/O.
    The 'await' keyword is used inside these methods to pause execution 
    without blocking the CPU while waiting for the database to respond.
    """
    
    def __init__(self):
        # We use your existing redis_manager singleton
        self.redis = redis_manager 
        self.JOB_PREFIX = "job:"
        self.RESULT_PREFIX = "result:"

    async def create(self, job_id: str, data: dict) -> None:
        """Create a new job entry in Redis with a status of 'Queued'."""
        key = f"{self.JOB_PREFIX}{job_id}"
        # Store as a Hash in Redis for easy updates
        await self.redis.update_job_progress(job_id, "Queued", 0, data)

    async def get(self, job_id: str) -> Optional[dict]:
        """Fetch job metadata from Redis."""
        # This is fine because it calls a method on your manager, not the client directly
        return self.redis.get_job_status(job_id)

    async def update(self, job_id: str, data: dict) -> None:
        """Merge new data into the existing Redis hash."""
        key = f"{self.JOB_PREFIX}{job_id}"
        # FIX: Added underscore and removed await
        self.redis._client.hset(key, mapping=data)

    async def set_result(self, job_id: str, result: dict) -> None:
        """Store the final job result."""
        key = f"{self.RESULT_PREFIX}{job_id}"
        # FIX: Added underscore and removed await
        self.redis._client.set(key, json.dumps(result))

    async def get_result(self, job_id: str) -> Optional[dict]:
        """Retrieve the stored result."""
        key = f"{self.RESULT_PREFIX}{job_id}"
        # FIX: Added underscore and removed await
        raw = self.redis._client.get(key)
        return json.loads(raw) if raw else None

    async def delete(self, job_id: str) -> None:
        """Atomic cleanup of job and result keys."""
        # FIX: Added underscore and removed await
        self.redis._client.delete(f"{self.JOB_PREFIX}{job_id}", f"{self.RESULT_PREFIX}{job_id}")

    async def get_active_count(self) -> int:
        raw_count = self.redis._client.get("active_jobs_count")
        if raw_count is None:
            return 0
        # casting the Redis string to a Python int
        return int(raw_count)

    async def list_jobs(self, limit: int = 10) -> List[dict]:
        """Fetch the most recent jobs using Redis keys."""
        # FIX: Added underscore to _client
        keys = self.redis._client.keys(f"{self.JOB_PREFIX}*")
        results = []
        
        # Ensure we don't try to slice an empty list
        if not keys:
            return []

        for key in keys[-limit:]:
            # FIX: Added underscore to _client
            job = self.redis._client.hgetall(key)
            if job:
                results.append(job)
        return results

class JobManager:
    def __init__(self):
        self.store = JobStore()
        self._websocket_callbacks: dict[str, list[Callable]] = {}

   
    async def create_job(self, filename, language, max_slides, generate_video, generate_mcqs, mode, job_id):
        # 1. Limit Check
        active_count = await self.store.get_active_count()
        if active_count >= settings.max_concurrent_jobs:
            raise TooManyJobsError(settings.max_concurrent_jobs)

        # 2. Prepare Data (Stringified for Redis)
        now_str = datetime.utcnow().isoformat()
        job_data = {
            "job_id": str(job_id),
            "filename": str(filename),
            "language": str(language),
            "mode": str(mode),
            "max_slides": str(int(max_slides or 0)),
            "generate_video": str(bool(generate_video)).lower(),
            "generate_mcqs": str(bool(generate_mcqs)).lower(),
            "status": JobState.PENDING.value,
            "progress": "0",
            "current_step": "Initializing",
            "created_at": now_str,
            "updated_at": now_str,
            "slides_progress": "[]",
        }

        # 3. Use HMSET to ensure all fields are saved as a hash
        # This prevents the "Job Not Found" error by ensuring the key exists immediately
        key = f"job:{job_id}"
        self.store.redis._client.hmset(key, job_data)
        self.store.redis._client.expire(key, 3600) # Auto-delete after 1 hour

        logger.info(f"Successfully created Redis hash for job: {job_id}")
        return job_id
    
    async def get_job_status(self, job_id: str) -> JobStatus:
        job_data = await self.store.get(job_id)
        if not job_data:
            raise JobNotFoundError(job_id)

        normalized_data = self._normalize_job_data(job_data)
        return JobStatus(**normalized_data)

    async def get_job_result(self, job_id: str) -> Optional[JobResult]:
        """Fixes the AttributeError when job finishes"""
        result_data = await self.store.get_result(job_id)
        return JobResult(**result_data) if result_data else None

    async def update_progress(
        self,
        job_id: str,
        progress: int,
        current_step: str | None = None,
        status: str | None = None,
        extra_meta: dict | None = None,
    ) -> None:
        payload = {
            "progress": int(progress),
            "updated_at": datetime.utcnow().isoformat(),
        }
        if current_step is not None:
            payload["current_step"] = current_step
        if extra_meta:
            payload.update(extra_meta)
        await self.store.redis.update_job_progress(
            job_id=job_id,
            status=status or JobState.PROCESSING.value,
            progress=int(progress),
            meta=payload,
        )

    async def complete_job(self, job_id: str, result_url: str | None = None) -> None:
        payload = {
            "status": JobState.COMPLETED.value,
            "progress": 100,
            "completed_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        if result_url:
            payload["result_url"] = result_url
        await self.store.redis.update_job_progress(
            job_id=job_id,
            status=JobState.COMPLETED.value,
            progress=100,
            meta=payload,
        )

    async def fail_job(self, job_id: str, error_message: str) -> None:
        payload = {
            "status": JobState.FAILED.value,
            "progress": 0,
            "error": error_message,
            "updated_at": datetime.utcnow().isoformat(),
        }
        await self.store.redis.update_job_progress(
            job_id=job_id,
            status=JobState.FAILED.value,
            progress=0,
            meta=payload,
        )

    # WebSocket Logic for Async
    def subscribe(self, job_id: str, callback: Callable):
        if job_id not in self._websocket_callbacks:
            self._websocket_callbacks[job_id] = []
        self._websocket_callbacks[job_id].append(callback)

    def unsubscribe(self, job_id: str, callback: Callable):
        if job_id in self._websocket_callbacks:
            self._websocket_callbacks[job_id] = [
                cb for cb in self._websocket_callbacks[job_id] if cb != callback
            ]

    def _normalize_job_data(self, data: dict) -> dict:
        normalized = dict(data)
        now = datetime.utcnow().isoformat()

        # 1. Set Defaults for missing Redis fields
        defaults = {
            "max_slides": 0,
            "progress": 0,
            "generate_video": "true",
            "generate_mcqs": "true",
            "status": "pending",
            "created_at": now,
            "updated_at": now,
            "current_step": "Initializing",
            "slides_progress": "[]"
        }

        for key, default_value in defaults.items():
            if key not in normalized or normalized[key] in (None, "", "None"):
                normalized[key] = default_value

        # 2. Fix Status Enums (Pydantic is case-sensitive for Enums)
        if str(normalized.get("status")).lower() == "queued":
            normalized["status"] = "pending"

        # 3. CRITICAL: Convert JSON strings back to Python objects
        # Redis stores everything as strings; Pydantic needs a real list.
        if isinstance(normalized.get("slides_progress"), str):
            try:
                normalized["slides_progress"] = json.loads(normalized["slides_progress"])
            except (json.JSONDecodeError, TypeError):
                normalized["slides_progress"] = []

        # 4. Handle Boolean strings from Redis ("true" -> True)
        for bool_key in ["generate_video", "generate_mcqs"]:
            val = str(normalized.get(bool_key)).lower()
            normalized[bool_key] = val == "true"

        # 5. Ensure Numeric types
        try:
            normalized["max_slides"] = int(normalized.get("max_slides", 0))
            normalized["progress"] = int(normalized.get("progress", 0))
        except (ValueError, TypeError):
            normalized["max_slides"] = 0
            normalized["progress"] = 0
        
        return normalized
# Global job manager instance
job_manager = JobManager()
