"""
Narration Chain - LLM-based narration generation for slides.
"""

import json

from langchain_core.prompts import PromptTemplate

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import LLMConnectionError, LLMGenerationError
from app.services.llm_service import (
    chat_completion_async,
    chat_completion_sync,
    build_messages,
    PROFESSOR_SYSTEM_PROMPT,
)

logger = get_logger(__name__)


NARRATION_PROMPT = PromptTemplate(
    input_variables=["slide_text", "language"],
    template="""You are an experienced teacher explaining content to students.

TASK:
Create a natural spoken narration for the following slide content.

IMPORTANT RULES:
- Generate narration ONLY (spoken explanation)
- Do NOT ask questions or generate quizzes
- Do NOT generate JSON or structured data
- Do NOT mention "questions", "MCQs", or "quiz"
- Generate the narration in: {language}
- Use a natural, engaging teaching tone
- Explain concepts clearly without repeating text verbatim
- Keep it concise but informative (<=300 words)
- Include a brief narrative transition that connects to the next slide's idea

Slide content:
{slide_text}

Narration:"""
)


NARRATION_BATCH_PROMPT = PromptTemplate(
    input_variables=["slides_payload", "language", "min_words", "max_words"],
    template="""You are an experienced teacher generating spoken narration.

TASK:
Create narrations for multiple slides.

OUTPUT FORMAT (STRICT):
Return ONLY valid JSON in the following format:
{{"narrations":[{{"slide_number":1,"narration":"..."}},{{"slide_number":2,"narration":"..."}}]}}

IMPORTANT RULES:
- One narration per slide_number
- Narration must be {min_words}-{max_words} words (target ~200)
- Do NOT include extra keys
- Do NOT include code fences, markdown, or commentary
- Use language: {language}
- Include a short narrative transition in each narration that leads into the next slide
- For the final slide, include a concise wrap-up instead of a transition

Slides:
{slides_payload}
"""
)


def _count_words(text: str) -> int:
    return len([w for w in text.split() if w.strip()])


def _trim_to_max_words(text: str, max_words: int) -> str:
    words = [w for w in text.split() if w.strip()]
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).strip()


def _postprocess_narration(text: str) -> str:
    word_count = _count_words(text)
    trimmed = _trim_to_max_words(text, settings.narration_max_words)
    if len(trimmed) != len(text):
        logger.info(
            "Trimming narration to max words",
            extra={"word_count": word_count, "max_words": settings.narration_max_words},
        )
    if word_count < settings.narration_min_words:
        logger.info(
            "Narration below minimum word target",
            extra={"word_count": word_count, "min_words": settings.narration_min_words},
        )
    return trimmed


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


def _parse_batch_response(text: str) -> dict[int, str]:
    json_text = _extract_json_object(text)
    payload = json.loads(json_text)
    narrations = payload.get("narrations", [])
    if not isinstance(narrations, list):
        raise ValueError("Invalid narrations payload")
    results: dict[int, str] = {}
    for item in narrations:
        if not isinstance(item, dict):
            continue
        slide_number = item.get("slide_number")
        narration = item.get("narration")
        if isinstance(slide_number, int) and isinstance(narration, str):
            results[slide_number] = narration.strip()
    return results


async def generate_narration_async(slide_text: str, language: str) -> str:
    """
    Generate narration asynchronously.
    
    Args:
        slide_text: The slide content to narrate
        language: Target language code (en, fr, hi)
    
    Returns:
        Generated narration text
    
    Raises:
        LLMConnectionError: If cannot connect to Ollama
        LLMGenerationError: If generation fails
    """
    logger.debug(f"Generating narration for slide (lang={language})")
    
    try:
        prompt = NARRATION_PROMPT.format(slide_text=slide_text, language=language)
        result = await chat_completion_async(
            build_messages(prompt, system_prompt=PROFESSOR_SYSTEM_PROMPT),
            temperature=settings.narration_temperature,
        )
        
        narration = _postprocess_narration(str(result["text"]).strip())
        logger.debug(f"Generated narration: {len(narration)} chars")
        return narration
        
    except ConnectionError as exc:
        logger.error(f"Failed to connect to Ollama: {exc}")
        raise LLMConnectionError("Ollama") from exc
    except Exception as exc:
        logger.error(f"Narration generation failed: {exc}")
        raise LLMGenerationError("narration") from exc


def generate_narration_sync(slide_text: str, language: str) -> str:
    """
    Generate narration synchronously.
    
    Args:
        slide_text: The slide content to narrate
        language: Target language code (en, fr, hi)
    
    Returns:
        Generated narration text
    """
    logger.debug(f"Generating narration for slide (lang={language})")
    
    try:
        prompt = NARRATION_PROMPT.format(slide_text=slide_text, language=language)
        result = chat_completion_sync(
            build_messages(prompt, system_prompt=PROFESSOR_SYSTEM_PROMPT),
            temperature=settings.narration_temperature,
        )
        
        narration = _postprocess_narration(str(result["text"]).strip())
        logger.debug(f"Generated narration: {len(narration)} chars")
        return narration
        
    except ConnectionError as exc:
        logger.error(f"Failed to connect to Ollama: {exc}")
        raise LLMConnectionError("Ollama") from exc
    except Exception as exc:
        logger.error(f"Narration generation failed: {exc}")
        raise LLMGenerationError("narration") from exc


async def generate_narrations_batch(slides: list[dict], language: str) -> tuple[dict[int, str], dict[str, object]]:
    """
    Generate narrations for a batch of slides.

    Args:
        slides: List of slide dicts with slide_number and text
        language: Target language code

    Returns:
        Mapping of slide_number to narration text
    """
    if not slides:
        return {}, {"json_adherence": True, "llm_metrics": {}, "fallback_slide_numbers": []}

    slides_payload_parts = []
    for slide in slides:
        slide_number = slide.get("slide_number")
        slide_text = slide.get("text", "")
        slides_payload_parts.append(f"[Slide {slide_number}]\n{slide_text}")
    slides_payload = "\n\n".join(slides_payload_parts)

    def _fallback_message() -> dict[int, str]:
        return {}

    try:
        prompt = NARRATION_BATCH_PROMPT.format(
            slides_payload=slides_payload,
            language=language,
            min_words=settings.narration_min_words,
            max_words=settings.narration_max_words,
        )
        result = await chat_completion_async(
            build_messages(prompt, system_prompt=PROFESSOR_SYSTEM_PROMPT),
            temperature=settings.narration_temperature,
        )
        parsed = _parse_batch_response(str(result["text"]))
        batch_meta: dict[str, object] = {
            "json_adherence": True,
            "llm_metrics": {
                "ttft": result.get("ttft"),
                "tps": result.get("tps"),
                "duration": result.get("duration"),
                "memory_kb": result.get("memory_kb"),
                "token_count": result.get("token_count"),
            },
            "fallback_slide_numbers": [],
        }
    except Exception as exc:
        logger.warning(f"Batch narration parsing failed, retrying strictly: {exc}")
        try:
            strict_prompt = (
                "Return ONLY JSON, no extra text. "
                "Format: {\"narrations\":[{\"slide_number\":1,\"narration\":\"...\"}]}"
            )
            prompt = NARRATION_BATCH_PROMPT.format(
                slides_payload=f"{strict_prompt}\n\n{slides_payload}",
                language=language,
                min_words=settings.narration_min_words,
                max_words=settings.narration_max_words,
            )
            result = await chat_completion_async(
                build_messages(prompt, system_prompt=PROFESSOR_SYSTEM_PROMPT),
                temperature=settings.narration_temperature,
            )
            parsed = _parse_batch_response(str(result["text"]))
            batch_meta = {
                "json_adherence": False,
                "llm_metrics": {
                    "ttft": result.get("ttft"),
                    "tps": result.get("tps"),
                    "duration": result.get("duration"),
                    "memory_kb": result.get("memory_kb"),
                    "token_count": result.get("token_count"),
                },
                "fallback_slide_numbers": [],
            }
        except Exception as retry_exc:
            logger.error(f"Batch narration retry failed: {retry_exc}")
            parsed = _fallback_message()
            batch_meta = {"json_adherence": False, "llm_metrics": {}, "fallback_slide_numbers": []}

    results: dict[int, str] = {}
    missing_slides = []
    for slide in slides:
        slide_number = slide.get("slide_number")
        narration = parsed.get(slide_number)
        if narration:
            results[slide_number] = _postprocess_narration(narration)
        else:
            missing_slides.append(slide)

    if missing_slides:
        logger.warning(
            "Falling back to per-slide narration for missing items",
            extra={"missing": [s.get("slide_number") for s in missing_slides]},
        )
        for slide in missing_slides:
            slide_number = slide.get("slide_number")
            slide_text = slide.get("text", "")
            results[slide_number] = await generate_narration_async(slide_text, language)
            batch_meta["fallback_slide_numbers"] = [
                *batch_meta.get("fallback_slide_numbers", []),
                slide_number,
            ]

    return results, batch_meta
