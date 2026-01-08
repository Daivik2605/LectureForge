from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

llm = OllamaLLM(
    model="llama3:8b",
    temperature=0.4
)

prompt = PromptTemplate(
    input_variables=["slide_text", "language"],
    template="""
    You are an experienced teacher.

TASK:
Explain the slide content as spoken narration.

IMPORTANT RULES:
- Generate narration ONLY
- Do NOT ask questions
- Do NOT generate quizzes
- Do NOT generate JSON
- Do NOT mention "questions" or "MCQs"
- Generate the narration in the following language: {language}
- Use a natural teaching tone
- Do not repeat text verbatim

Slide content:
{slide_text}
"""
)

# Modern LangChain RunnableSequence
narration_chain = prompt | llm
# Old LangChain LLMChain (if needed)
# from langchain_core.chains import LLMChain
# narration_chain = LLMChain(llm=llm, prompt=prompt)