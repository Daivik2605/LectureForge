# Presentation Understanding Engine

An AI-powered backend system that performs **semantic understanding of PowerPoint presentations** to automatically generate:
- teacher-style narrated explanations
- structured multiple-choice assessments (MCQs)

Designed for **EdTech**, **training automation**, and **instructional content pipelines**.

---

## Overview

The **Presentation Understanding Engine** ingests PowerPoint (`.pptx`) files and applies large language models (LLMs) to understand slide-level content.

From this understanding, it automatically produces:
- concise instructional narration (not verbatim repetition)
- evaluative MCQs with difficulty levels in strict JSON format

The system is exposed via a **FastAPI backend** and returns structured outputs suitable for LMS platforms, assessment systems, or downstream APIs.

---

## Key Capabilities

- Upload PowerPoint files via REST API
- Robust slide text extraction (handles empty or image-only slides)
- AI-generated narration using LLMs
- AI-generated MCQs with schema-safe JSON output
- Slide-level semantic understanding for explanation and assessment
- Modular orchestration layer (parser, AI chains, processor)
- FastAPI backend with interactive Swagger UI
- Local LLM inference using Ollama (cloud-ready design)

---

## Architecture (High Level)

PPT Upload
↓
Slide Text Extraction
↓
LLM-based Semantic Understanding
├── Narration Generation
└── Q&A Generation
↓
Structured JSON Output (API Response)

---

## Tech Stack

- **Python**
- **FastAPI** (API layer)
- **LangChain** (RunnableSequence for prompt orchestration)
- **Ollama** (local LLM inference)
- **python-pptx** (PowerPoint parsing)

---

## Getting Started (Local Setup)

---

````md
## Getting Started (Local Setup)

### 1. Clone the Repository
```bash
git clone https://github.com/Daivik2605/presentation-understanding-engine.git
cd presentation-understanding-engine
````

### 2. Create and Activate Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start Ollama

```bash
ollama serve
```

Ensure the required model (e.g., `llama3:8b`) is available in Ollama.

### 5. Run the API Server

```bash
uvicorn app.main:app --reload
```

### 6. Open Swagger UI

```
http://127.0.0.1:8000/docs
```

````

---

## Why this fixes it

- Closed all code blocks correctly
- Removed stray `'''`
- Ensured numbering renders properly
- Ensured GitHub Markdown compatibility

---

## Next step

After replacing this section:

```bash
git add README.md
git commit -m "Fix README setup instructions formatting"
git push
````

