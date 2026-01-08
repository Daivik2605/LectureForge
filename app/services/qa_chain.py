from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

llm = OllamaLLM(model="llama3:8b", temperature=0.3)

prompt = PromptTemplate(
    input_variables=["slide_text", "language"],
    template="""
You are an assessment generator.

TASK:
Generate assessment questions ONLY.

STRICT RULES (MANDATORY):
- Generate ALL text strictly in {language}
- If {language} is not "en", DO NOT use English words at all
- Output ONLY valid JSON
- Output MUST start with '{{' and end with '}}'
- Do NOT include any text before or after the JSON
- Do NOT include explanations, comments, or introductions
- Do NOT mention JSON, questions, or assessments outside the structure

Return a JSON object with exactly one key: "questions"

Each question MUST include:
- "question": string
- "options": list of exactly 4 strings
- "answer": must EXACTLY match one option
- "difficulty": "easy" or "medium"

Slide content:
{slide_text}
"""
)

qa_chain = prompt | llm

