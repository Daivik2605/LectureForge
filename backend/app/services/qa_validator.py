import json
from app.services.language_utils import is_text_in_language

def validate_and_fix_mcqs(raw_output: str) -> dict:
    """
    Validates and fixes MCQ JSON output from LLM.
    Ensures:
    - Valid JSON
    - Correct schema
    - Answer exists in options
    """

    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError:
        return {"questions": []}

    questions = data.get("questions", [])
    validated_questions = []

    for q in questions:
        question = q.get("question")
        options = q.get("options", [])
        answer = q.get("answer")
        difficulty = q.get("difficulty")

        # Basic structural validation
        if not question or not isinstance(options, list):
            continue

        if len(options) != 4:
            continue

        if difficulty not in ("easy", "medium"):
            difficulty = "easy"

        # Fix answer if invalid
        if answer not in options:
            answer = options[0]  # safe fallback

        validated_questions.append({
            "question": question,
            "options": options,
            "answer": answer,
            "difficulty": difficulty
        })

    return {"questions": validated_questions}

def validate_mcq_language(qa: dict, language: str) -> bool:
    """
    Ensures MCQs are written in the requested language.
    """
    for q in qa.get("questions", []):
        if not is_text_in_language(q["question"], language):
            return False
        for opt in q["options"]:
            if not is_text_in_language(opt, language):
                return False
    return True
