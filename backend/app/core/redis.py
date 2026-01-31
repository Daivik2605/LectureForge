"""
Redis manager for job progress tracking.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import redis


class RedisManager:
    def __init__(self) -> None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    async def update_job_progress(
        self,
        job_id: str,
        status: str,
        progress: int,
        meta: dict[str, Any] | None = None,
    ) -> None:
        key = f"job:{job_id}"
        active_statuses = {"pending", "processing"}
        previous_status = self._client.hget(key, "status")
        was_active = previous_status in active_statuses
        is_active = status in active_statuses

        if was_active != is_active:
            self._client.incrby("active_jobs_count", 1 if is_active else -1)
            raw_count = self._client.get("active_jobs_count")
            if raw_count is not None and int(raw_count) < 0:
                self._client.set("active_jobs_count", 0)

        payload: dict[str, Any] = {
            "job_id": job_id,
            "status": status,
            "progress": int(progress),
        }
        if meta:
            for k, v in meta.items():
                payload[str(k)] = v
        self._client.hset(key, mapping=payload)
        self._client.expire(key, 60 * 60 * 24)

    def _collect_metric_values(
        self,
        items: list[dict[str, Any]],
        key: str,
    ) -> list[float]:
        values: list[float] = []
        for item in items:
            value = item.get(key)
            if isinstance(value, (int, float)):
                values.append(float(value))
        return values

    def _collect_bool_values(
        self,
        items: list[dict[str, Any]],
        key: str,
    ) -> list[int]:
        values: list[int] = []
        for item in items:
            value = item.get(key)
            if isinstance(value, bool):
                values.append(1 if value else 0)
        return values

    def _extract_slide_metrics(self, final_meta: dict[str, Any]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for key in ("slides", "per_slide", "slide_metrics", "slides_meta"):
            value = final_meta.get(key)
            if isinstance(value, list):
                candidates = [v for v in value if isinstance(v, dict)]
                break
            if isinstance(value, dict):
                candidates = [v for v in value.values() if isinstance(v, dict)]
                break
        return candidates

    def archive_benchmark_data(
        self,
        job_id: str,
        model_name: str,
        final_meta: dict[str, Any],
    ) -> None:
        slides = self._extract_slide_metrics(final_meta)
        name = (model_name or "").lower()
        avg_tps = None
        avg_ttft = None
        avg_duration = None
        avg_memory_kb = None
        avg_word_count = None
        json_adherence_rate = None
        hallucination_ok_rate = None
        total_tokens = 0.0
        avg_tokens_per_slide = None
        final_cost = None

        if slides:
            tps_vals = self._collect_metric_values(slides, "tps")
            ttft_vals = self._collect_metric_values(slides, "ttft")
            duration_vals = self._collect_metric_values(slides, "duration")
            memory_vals = self._collect_metric_values(slides, "memory_kb")
            word_vals = self._collect_metric_values(slides, "word_count")
            token_vals = self._collect_metric_values(slides, "token_count")
            json_vals = self._collect_bool_values(slides, "json_valid")
            halluc_vals = self._collect_bool_values(slides, "hallucination_ok")

            if tps_vals:
                avg_tps = sum(tps_vals) / len(tps_vals)
            if ttft_vals:
                avg_ttft = sum(ttft_vals) / len(ttft_vals)
            if duration_vals:
                avg_duration = sum(duration_vals) / len(duration_vals)
            if memory_vals:
                avg_memory_kb = sum(memory_vals) / len(memory_vals)
            if word_vals:
                avg_word_count = sum(word_vals) / len(word_vals)
            if json_vals:
                json_adherence_rate = sum(json_vals) / len(json_vals)
            if halluc_vals:
                hallucination_ok_rate = sum(halluc_vals) / len(halluc_vals)
            if token_vals:
                total_tokens = sum(token_vals)
                avg_tokens_per_slide = total_tokens / len(slides)

        if total_tokens and ("gpt" in name or "openai" in name or "claude" in name or "anthropic" in name):
            rate = 12.0
            if "gpt" in name or "openai" in name:
                rate = 10.0
            if "claude" in name or "anthropic" in name:
                rate = 15.0
            final_cost = (total_tokens / 1_000_000) * rate

        payload = {
            "job_id": job_id,
            "model_name": model_name,
            "timestamp": time.time(),
            "summary": {
                "avg_tps": avg_tps,
                "avg_ttft": avg_ttft,
                "avg_duration": avg_duration,
                "avg_memory_kb": avg_memory_kb,
                "avg_word_count": avg_word_count,
                "json_adherence_rate": json_adherence_rate,
                "hallucination_ok_rate": hallucination_ok_rate,
                "total_tokens": total_tokens,
                "avg_tokens_per_slide": avg_tokens_per_slide,
                "final_cost": final_cost,
                "slides_count": len(slides),
            },
            "meta": final_meta,
        }

        serialized = json.dumps(payload, ensure_ascii=True)
        self._client.zadd("benchmarks:history", {serialized: payload["timestamp"]})

    def get_model_comparison(self, job_ids: list[str]) -> list[dict[str, Any]]:
        if not job_ids:
            return []
        raw_items = self._client.zrange("benchmarks:history", 0, -1)
        items: list[dict[str, Any]] = []
        for raw in raw_items:
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if payload.get("job_id") in job_ids:
                items.append(payload)

        index = {item.get("job_id"): item for item in items}
        return [index[job_id] for job_id in job_ids if job_id in index]

    def get_benchmark_history(self, limit: int = 10) -> list[dict[str, Any]]:
        raw_items = self._client.zrevrange("benchmarks:history", 0, max(limit - 1, 0))
        items: list[dict[str, Any]] = []
        for raw in raw_items:
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            items.append(payload)
        return items

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        key = f"job:{job_id}"
        return self._client.hgetall(key)


redis_manager = RedisManager()
