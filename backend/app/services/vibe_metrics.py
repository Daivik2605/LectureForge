"""
Utilities for narration quality checks and metrics.
"""

from __future__ import annotations

from collections import Counter
import re
from typing import Any

_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "over",
    "under",
    "between",
    "within",
    "without",
    "your",
    "their",
    "there",
    "these",
    "those",
    "which",
    "where",
    "when",
    "while",
    "about",
    "because",
    "using",
    "used",
    "use",
    "than",
    "then",
    "also",
    "such",
    "some",
    "more",
    "most",
    "many",
    "much",
    "very",
    "into",
    "onto",
    "onto",
    "each",
    "other",
    "over",
    "under",
    "only",
    "same",
    "like",
    "just",
    "make",
    "made",
    "make",
    "will",
    "would",
    "could",
    "should",
    "can",
    "may",
    "might",
    "must",
    "about",
    "therefore",
    "however",
    "overall",
}


def count_words(text: str) -> int:
    return len([w for w in text.split() if w.strip()])


def extract_key_terms(text: str, max_terms: int = 5) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", text)
    lowered = [t.lower() for t in tokens if t.lower() not in _STOPWORDS]
    if not lowered:
        return []
    counts = Counter(lowered)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], -len(item[0]), item[0]))
    return [term for term, _ in ranked[:max_terms]]


def hallucination_check(
    source_text: str,
    narration_text: str,
    min_required: int = 3,
    max_terms: int = 5,
) -> dict[str, Any]:
    terms = extract_key_terms(source_text, max_terms=max_terms)
    narration_tokens = set(re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", narration_text.lower()))
    found = [term for term in terms if term in narration_tokens]
    required = min(min_required, len(terms))
    return {
        "terms": terms,
        "found": found,
        "required": required,
        "pass": len(found) >= required if required > 0 else False,
    }


def build_narration_meta(
    source_text: str,
    narration_text: str,
    json_adherence: bool,
    llm_metrics: dict[str, Any] | None,
) -> dict[str, Any]:
    hallucination = hallucination_check(source_text, narration_text)
    metrics: dict[str, Any] = {
        "narration_word_count": count_words(narration_text),
        "json_adherence": bool(json_adherence),
        "hallucination_ok": hallucination["pass"],
        "hallucination_terms": hallucination["terms"],
        "hallucination_found": hallucination["found"],
        "hallucination_required": hallucination["required"],
        "ttft": None,
        "tps": None,
        "duration": None,
        "memory_kb": None,
        "token_count": None,
    }
    if llm_metrics:
        metrics["ttft"] = llm_metrics.get("ttft")
        metrics["tps"] = llm_metrics.get("tps")
        metrics["duration"] = llm_metrics.get("duration")
        metrics["memory_kb"] = llm_metrics.get("memory_kb")
        metrics["token_count"] = llm_metrics.get("token_count")
    return metrics
