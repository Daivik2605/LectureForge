"""
QA Chain - LLM-based MCQ generation for slides.
"""

from langchain_core.prompts import PromptTemplate

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import LLMConnectionError, LLMGenerationError
from app.services.llm_service import chat_completion_async, chat_completion_sync

logger = get_logger(__name__)


QA_PROMPT = PromptTemplate(
    input_variables=["slide_text", "language"],
    template="""You are an assessment generator creating quiz questions.

TASK:
Generate 1-2 valid MCQ questions based on the slide content.

STRICT RULES (MANDATORY):
- The "answer" MUST be exactly one of the provided options
- ALL questions and options MUST be in {language}
- Generate ALL text strictly in {language}
- If {language} is not "en", DO NOT use English words at all
- Output ONLY valid JSON
- Output MUST start with '{{' and end with '}}'
- Do NOT include any text before or after the JSON
- Do NOT include explanations, comments, or introductions

Return a JSON object with exactly one key: "questions"

Each question MUST include:
- "question": string (the question text)
- "options": list of exactly 4 strings
- "answer": must EXACTLY match one option
- "difficulty": "easy" or "medium"

Slide content:
{slide_text}

JSON Output:"""
)


async def generate_mcqs_async(slide_text: str, language: str) -> str:
    """
    Generate MCQs asynchronously.
    
    Args:
        slide_text: The slide content to generate questions from
        language: Target language code (en, fr, hi)
    
    Returns:
        Raw JSON string with generated MCQs
    
    Raises:
        LLMConnectionError: If cannot connect to Ollama
        LLMGenerationError: If generation fails
    """
    logger.debug(f"Generating MCQs for slide (lang={language})")
    
    try:
        prompt = QA_PROMPT.format(slide_text=slide_text, language=language)
        result = await chat_completion_async(
            [{"role": "user", "content": prompt}],
            temperature=settings.qa_temperature,
        )
        
        raw_output = str(result).strip()
        logger.debug(f"Generated MCQs: {len(raw_output)} chars")
        return raw_output
        
    except ConnectionError as exc:
        logger.error(f"Failed to connect to Ollama: {exc}")
        raise LLMConnectionError("Ollama") from exc
    except Exception as exc:
        logger.error(f"MCQ generation failed: {exc}")
        raise LLMGenerationError("MCQs") from exc


def generate_mcqs_sync(slide_text: str, language: str) -> str:
    """
    Generate MCQs synchronously.
    
    Args:
        slide_text: The slide content to generate questions from
        language: Target language code (en, fr, hi)
    
    Returns:
        Raw JSON string with generated MCQs
    """
    logger.debug(f"Generating MCQs for slide (lang={language})")
    
    try:
        prompt = QA_PROMPT.format(slide_text=slide_text, language=language)
        result = chat_completion_sync(
            [{"role": "user", "content": prompt}],
            temperature=settings.qa_temperature,
        )
        
        raw_output = str(result).strip()
        logger.debug(f"Generated MCQs: {len(raw_output)} chars")
        return raw_output
        
    except ConnectionError as exc:
        logger.error(f"Failed to connect to Ollama: {exc}")
        raise LLMConnectionError("Ollama") from exc
    except Exception as exc:
        logger.error(f"MCQ generation failed: {exc}")
        raise LLMGenerationError("MCQs") from exc
