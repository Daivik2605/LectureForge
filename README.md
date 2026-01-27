# LectureForge  
[![CI](https://github.com/Daivik2605/LectureForge/actions/workflows/ci.yml/badge.svg)](https://github.com/Daivik2605/LectureForge/actions)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](https://github.com/Daivik2605/LectureForge/actions)

*Turn slide decks and PDFs into narrated, lesson‑style videos or immersive narrative journeys.*

## 📖 Overview

LectureForge is a FastAPI + Next.js system that converts PPT/X and PDF documents into narrated video content. By leveraging local LLMs and TTS engines, it extracts document content, produces AI-driven scripts, and renders a fully stitched video lesson.

**Project Status:** Stable containerized prototype. Now expanding into **StoryGenerator** capabilities.

## 🚀 Quick Start (Docker)

The professional way to run LectureForge is via Docker Compose. This ensures all system dependencies (FFmpeg, LibreOffice) and the AI engine (Ollama) are perfectly configured.

### 1. Start the Stack
```bash
git clone <repo-url>
cd LectureForge
docker-compose up -d --build

```

### 2. Initialize the AI Model

Since models are large, they are not bundled in the image. You must pull your preferred model into the container once it's up:

```bash
# Recommended for MacBook Air (Fast & Efficient)
docker exec -it lectureforge-ollama ollama pull llama3.2:3b

# For Higher Accuracy (Requires 8GB+ RAM)
docker exec -it lectureforge-ollama ollama pull llama3.1:8b

```

Access the UI at: **http://localhost:3000**

---

## ✨ Features

* **Local-First AI:** All processing stays on your hardware via Ollama. No external API keys required.
* **Narrative Personas:** Switch between **Professor** (educational summaries) and **Storyteller** (hero's journey narratives).
* **Format Support:** High-fidelity extraction from `.pptx` and `.pdf` files.
* **Async Processing:** (In Progress) Refactoring to Redis-backed queues for handling large 50+ page documents.

## 🛠 Architecture

LectureForge operates as a microservices ecosystem within a shared Docker network:

* **Frontend (Next.js):** React interface for uploads, progress tracking, and video playback.
* **Backend (FastAPI):** Orchestrates the pipeline: extraction → LLM scripting → TTS synthesis → FFmpeg rendering.
* **AI Engine (Ollama):** Serves the LLM locally on port 11434.
* **Data Volume:** Persistent storage for your uploads and generated video artifacts.

---

## ⚙️ Configuration

The system is pre-configured for Docker. Key environment variables in the `backend` service include:

| Variable | Default (Docker) | Description |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Internal DNS for the AI service. |
| `OLLAMA_MODEL` | `llama3.2:3b` | The model used for scripts & quizzes. |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed frontend communication. |

---

## 🧪 Testing the Pipeline

To verify the setup without using your own documents, use the included test generator:

1. **Generate Test PDF:**
```bash
pip install reportlab
python scripts/generate_test_pdf.py

```


2. **Upload:** Use the resulting `ai_lecture_test.pdf` in the web UI.
3. **Monitor:** Run `docker-compose logs -f backend` to watch the AI generate the narration in real-time.

---

## 🗺 Roadmap

* [ ] **Redis Task Queue:** Offload heavy video rendering to background workers to prevent UI timeouts.
* [ ] **Story Mode Toggle:** Add a UI switch to change LLM prompts from "Lecture" to "Storytelling."
* [ ] **Multi-Model Benchmarking:** Integrated scripts to compare speed/quality of Llama, Mistral, and GPT-4.
* [ ] **Automated Progress Bars:** WebSocket integration for real-time per-slide status updates.

## 🛡 Security & Privacy

LectureForge is built with a **Privacy-First** philosophy. When using local providers, your documents and generated videos never leave your local machine.

*Note: This project is a development prototype. For production deployment, ensure you configure an Nginx reverse proxy with SSL.*

## 📄 License

MIT — see `LICENSE`.

```

---

### **Next Step**
Now that your documentation is complete and your code is pushed, we can start on the **Redis integration**. This will solve the "WebSocket disconnected" and "Timeout" issues you were seeing by allowing the backend to work on the video while the frontend just waits for status updates.

**Would you like me to provide the `redis` service block for your `docker-compose.yml` and the updated `app/core/redis.py` client?**

```
