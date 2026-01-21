# Presentation Understanding Engine

Presentation Understanding Engine is a FastAPI + Next.js system that converts PPT/PPTX and PDF documents into narrated video lessons, per-slide/page summaries, and optional quiz questions using local LLM + TTS tooling. It is designed for teams who want repeatable, automated content production without manual video editing or external SaaS dependencies.

## Who This Is For / What It Solves

- Learning and enablement teams producing training content at scale.
- Product teams embedding document-to-video workflows into internal tools.
- Developers who want a local-first pipeline for structured narration and video generation.

## Architecture Overview

- **Frontend (Next.js)** handles upload, progress, and results.
- **Backend (FastAPI)** orchestrates jobs, pipelines, and storage.
- **Pipelines** process PPT or PDF inputs with LLM narration, optional MCQs, TTS, and FFmpeg stitching.
- **Storage** persists uploads, intermediate assets, and final outputs under `data/` and `storage/`.

Detailed docs: `docs/architecture.md`, `docs/pipelines.md`, `docs/api.md`.

## Features

- PPT pipeline with slide parsing, narration, per-slide clips, and stitched video.
- PDF pipeline with page summaries, narration, and optional MCQs.
- Policy mode for long-form PDF/TXT chunking and narrated output.
- Live progress updates via WebSocket + polling.
- Local LLM via Ollama and speech synthesis via edge-tts.
- Clean upload → processing → results UI.

## Tech Stack

- **Backend:** FastAPI, Pydantic Settings, Ollama, edge-tts, FFmpeg, Pillow
- **Frontend:** Next.js (App Router), React Query, Tailwind CSS, shadcn/ui
- **Infra:** Docker Compose, Nginx (optional)

## Local Setup (Development)

Prerequisites:
- Python 3.11+
- Node.js 20+
- FFmpeg
- Ollama

Backend:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements/requirements.txt
cp backend/.env.example backend/.env
ollama serve
ollama pull llama3.1:8b
uvicorn backend.app.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

## Local Setup (Production)

```bash
docker-compose up -d
```

Services:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

## How to Run

Backend (from repo root):
```bash
uvicorn backend.app.main:app --reload
```

Frontend (from `frontend/`):
```bash
npm run dev
```

## Screenshots

See `docs/screenshots/` for placeholders.

![Upload](docs/screenshots/upload.png)
![Processing](docs/screenshots/processing.png)
![Results](docs/screenshots/results.png)

## Known Limitations

- PDF quality depends on text extraction; scanned PDFs may require OCR.
- Large decks increase processing time; defaults target small/medium inputs.
- Outputs are local-file based by default (no object storage integration).

## Roadmap

Planned enhancements live in `docs/roadmap.md`.

## Project Status

Active development. Core upload → processing → results flow is stable for local use.

## License

MIT. See `LICENSE`.
