"""
Batch LLM utilities for page summaries, narrations, and MCQ generation.
"""

from __future__ import annotations

import json
from time import perf_counter
from typing import Any

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import LLMConnectionError, LLMGenerationError

logger = get_logger(__name__)


def create_llm() -> OllamaLLM:
    return OllamaLLM(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=settings.narration_temperature,
        num_predict=2048,
    )


SUMMARY_PROMPT = PromptTemplate(
    input_variables=["pages_payload", "language", "max_words"],
    template="""You are an expert teacher summarizing document pages.

TASK:
For each page, produce:
- title (short, clear)
- bullets (3-6 short bullet points copied verbatim from the page text)
- narration (short spoken explanation of the page that elaborates on the bullets)

OUTPUT FORMAT (STRICT JSON ONLY):
{{"pages":[{{"page_id":"...","title":"...","bullets":["..."],"narration":"..."}}]}}

RULES:
- Narration must be <= {max_words} words per page.
- Bullets must be exact phrases from the page text (no paraphrasing).
- If a bullet cannot be copied verbatim, omit it.
- No markdown, no code fences, no extra keys.
- Use language: {language}

Pages:
{pages_payload}
"""
)


MCQ_PROMPT = PromptTemplate(
    input_variables=["pages_payload", "language"],
    template="""You are an expert teacher generating multiple-choice questions.

TASK:
For each page, generate 3 questions (easy, medium, hard) based on the content.

OUTPUT FORMAT (STRICT JSON ONLY):
{{"pages":[{{"page_id":"...","questions":[{{"question":"...","options":["...","...","...","..."],"answer":"...","difficulty":"easy"}}]}}]}}

RULES:
- Exactly 4 options per question.
- Answer must match one of the options.
- Use language: {language}
- No markdown, no code fences, no extra keys.

Pages:
{pages_payload}
"""
)


llm = create_llm()
summary_chain = SUMMARY_PROMPT | llm
mcq_chain = MCQ_PROMPT | llm


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1]
    if stripped.endswith("```"):
        stripped = stripped.rsplit("\n", 1)[0]
    return stripped.strip()


def _extract_json_object(text: str) -> str:
    cleaned = _strip_code_fences(text)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response")
    return cleaned[start : end + 1]


def _trim_to_max_words(text: str, max_words: int) -> str:
    words = [w for w in text.split() if w.strip()]
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).strip()


def _normalize_summary_payload(payload: dict[str, Any], max_words: int) -> dict[str, dict[str, Any]]:
    pages = payload.get("pages", [])
    if not isinstance(pages, list):
        raise ValueError("Invalid pages payload")
    results: dict[str, dict[str, Any]] = {}
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_id = page.get("page_id")
        title = page.get("title")
        bullets = page.get("bullets")
        narration = page.get("narration")
        if not isinstance(page_id, str) or not isinstance(title, str) or not isinstance(bullets, list) or not isinstance(narration, str):
            continue
        clean_bullets = [str(b).strip() for b in bullets if str(b).strip()]
        clean_narration = _trim_to_max_words(narration, max_words)
        results[page_id] = {
            "title": title.strip(),
            "bullets": clean_bullets,
            "narration": clean_narration,
        }
    return results


def _normalize_mcq_payload(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    pages = payload.get("pages", [])
    if not isinstance(pages, list):
        raise ValueError("Invalid pages payload")
    results: dict[str, list[dict[str, Any]]] = {}
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_id = page.get("page_id")
        questions = page.get("questions", [])
        if not isinstance(page_id, str) or not isinstance(questions, list):
            continue
        clean_questions: list[dict[str, Any]] = []
        for question in questions:
            if not isinstance(question, dict):
                continue
            options = question.get("options")
            answer = question.get("answer")
            difficulty = question.get("difficulty")
            if not isinstance(options, list) or not isinstance(answer, str) or not isinstance(difficulty, str):
                continue
            clean_questions.append(
                {
                    "question": str(question.get("question", "")).strip(),
                    "options": [str(o).strip() for o in options if str(o).strip()],
                    "answer": answer.strip(),
                    "difficulty": difficulty.strip(),
                }
            )
        if clean_questions:
            results[page_id] = clean_questions
    return results


async def batch_summarize_pages(
    pages: list[dict[str, Any]],
    language: str,
    max_words: int,
) -> dict[str, dict[str, Any]]:
    if not pages:
        return {}

    payload_parts = []
    for page in pages:
        page_id = page.get("page_id")
        text = page.get("text", "")
        payload_parts.append(f"[Page {page_id}]\n{text}")
    pages_payload = "\n\n".join(payload_parts)

    start = perf_counter()
    try:
        result = await summary_chain.ainvoke(
            {
                "pages_payload": pages_payload,
                "language": language,
                "max_words": max_words,
            }
        )
        parsed = _normalize_summary_payload(json.loads(_extract_json_object(str(result))), max_words)
        elapsed = perf_counter() - start
        logger.info(
            "LLM summary batch completed",
            extra={"pages": len(pages), "elapsed_seconds": round(elapsed, 2)},
        )
        return parsed
    except ConnectionError as exc:
        logger.error(f"Failed to connect to Ollama: {exc}")
        raise LLMConnectionError("Ollama") from exc
    except Exception as exc:
        logger.warning(f"Summary batch parsing failed, retrying strictly: {exc}")
        try:
            strict_prefix = (
                "Return ONLY JSON. Format: {\"pages\":[{\"page_id\":\"...\",\"title\":\"...\",\"bullets\":[\"...\"],\"narration\":\"...\"}]}"
            )
            result = await summary_chain.ainvoke(
                {
                    "pages_payload": f"{strict_prefix}\n\n{pages_payload}",
                    "language": language,
                    "max_words": max_words,
                }
            )
            parsed = _normalize_summary_payload(json.loads(_extract_json_object(str(result))), max_words)
            elapsed = perf_counter() - start
            logger.info(
                "LLM summary batch completed (retry)",
                extra={"pages": len(pages), "elapsed_seconds": round(elapsed, 2)},
            )
            return parsed
        except Exception as retry_exc:
            logger.error(f"Summary batch retry failed: {retry_exc}")
            raise LLMGenerationError("summary_batch") from retry_exc


async def batch_generate_mcqs(
    pages: list[dict[str, Any]],
    language: str,
) -> dict[str, list[dict[str, Any]]]:
    if not pages:
        return {}

    payload_parts = []
    for page in pages:
        page_id = page.get("page_id")
        text = page.get("text", "")
        payload_parts.append(f"[Page {page_id}]\n{text}")
    pages_payload = "\n\n".join(payload_parts)

    start = perf_counter()
    try:
        result = await mcq_chain.ainvoke(
            {
                "pages_payload": pages_payload,
                "language": language,
            }
        )
        parsed = _normalize_mcq_payload(json.loads(_extract_json_object(str(result))))
        elapsed = perf_counter() - start
        logger.info(
            "LLM MCQ batch completed",
            extra={"pages": len(pages), "elapsed_seconds": round(elapsed, 2)},
        )
        return parsed
    except ConnectionError as exc:
        logger.error(f"Failed to connect to Ollama: {exc}")
        raise LLMConnectionError("Ollama") from exc
    except Exception as exc:
        logger.warning(f"MCQ batch parsing failed, retrying strictly: {exc}")
        try:
            strict_prefix = (
                "Return ONLY JSON. Format: {\"pages\":[{\"page_id\":\"...\",\"questions\":[{\"question\":\"...\",\"options\":[\"...\"],\"answer\":\"...\",\"difficulty\":\"easy\"}]}]}"
            )
            result = await mcq_chain.ainvoke(
                {
                    "pages_payload": f"{strict_prefix}\n\n{pages_payload}",
                    "language": language,
                }
            )
            parsed = _normalize_mcq_payload(json.loads(_extract_json_object(str(result))))
            elapsed = perf_counter() - start
            logger.info(
                "LLM MCQ batch completed (retry)",
                extra={"pages": len(pages), "elapsed_seconds": round(elapsed, 2)},
            )
            return parsed
        except Exception as retry_exc:
            logger.error(f"MCQ batch retry failed: {retry_exc}")
            raise LLMGenerationError("mcq_batch") from retry_exc
