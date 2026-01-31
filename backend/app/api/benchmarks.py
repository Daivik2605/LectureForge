"""
Benchmarks API - Endpoints for model comparison and history.
"""

from fastapi import APIRouter, Query

from app.core.redis import redis_manager

router = APIRouter(prefix="/benchmarks", tags=["Benchmarks"])


@router.get("/compare")
async def compare_benchmarks(job_ids: list[str] = Query(default_factory=list)) -> list[dict]:
    """
    Compare benchmark entries for a list of job IDs.
    """
    normalized: list[str] = []
    if len(job_ids) == 1 and "," in job_ids[0]:
        normalized = [item.strip() for item in job_ids[0].split(",") if item.strip()]
    else:
        normalized = [item.strip() for item in job_ids if item.strip()]
    return redis_manager.get_model_comparison(normalized)


@router.get("/history")
async def benchmark_history(limit: int = 10) -> list[dict]:
    """
    Return the most recent benchmark entries.
    """
    return redis_manager.get_benchmark_history(limit=limit)
