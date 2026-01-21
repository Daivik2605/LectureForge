"""
Narration cache utilities for storing/retrieving slide narrations.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def normalize_slide_text(text: str) -> str:
    """Normalize slide text for stable cache keys."""
    return " ".join(text.split()).strip()


def build_cache_key(language: str, slide_text: str, pipeline_type: str) -> str:
    """Build a stable cache key for narration text."""
    normalized = normalize_slide_text(slide_text)
    raw_key = f"{language}|{pipeline_type}|{normalized}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _cache_path(key: str) -> Path:
    return settings.narration_cache_dir / f"{key}.json"


def load_cached_payload(key: str) -> Optional[dict[str, Any]]:
    """Load cached payload from cache, if present."""
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.warning(f"Narration cache corrupt at {path}: {exc}")
        return None
    if isinstance(payload, dict) and payload:
        return payload
    return None


def load_cached_narration(key: str) -> Optional[str]:
    """Load narration from cache, if present."""
    payload = load_cached_payload(key)
    if not payload:
        return None
    narration = payload.get("narration")
    if isinstance(narration, str) and narration.strip():
        return narration.strip()
    return None


def save_cached_payload(key: str, payload: dict[str, Any]) -> None:
    """Persist payload to cache as JSON."""
    path = _cache_path(key)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def save_cached_narration(
    key: str,
    narration: str,
    language: str,
    pipeline_type: str,
) -> None:
    """Persist narration to cache as JSON."""
    payload = {
        "narration": narration.strip(),
        "language": language,
        "pipeline_type": pipeline_type,
        "created_at": datetime.utcnow().isoformat(),
    }
    save_cached_payload(key, payload)
