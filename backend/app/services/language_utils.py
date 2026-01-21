from langdetect import detect, LangDetectException

LANG_MAP = {
    "en": "en",
    "fr": "fr",
    "hi": "hi"
}

def is_text_in_language(text: str, expected_language: str) -> bool:
    """
    Returns True if detected language matches expected_language.
    """
    try:
        detected = detect(text)
        return detected == LANG_MAP.get(expected_language, expected_language)
    except LangDetectException:
        return False
