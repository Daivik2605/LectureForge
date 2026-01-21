# LectureForge  
[![CI](https://github.com/Daivik2605/LectureForge/actions/workflows/ci.yml/badge.svg)](https://github.com/Daivik2605/LectureForge/actions)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](https://github.com/Daivik2605/LectureForge/actions)
*Turn slide decks and PDFs into narrated, lesson‑style videos with summaries and optional quizzes.*

## Overview

LectureForge is a FastAPI + Next.js system that converts PPT/PPTX and PDF documents into narrated video lessons. It extracts slide/page content, produces summaries, generates narration using local TTS, and can optionally create quiz questions using a local or pluggable LLM.

## 🎥 Live Demo

![Upload and generate interface](screenshots/upload-demo.png)
![Results with narrated lesson preview](screenshots/results-demo.png)

*(Add your actual screenshots here - upload → processing → narrated lesson output)*

**Project status:** Early-stage but functional prototype, actively developed.

### Key Capabilities

- Upload PPT/PPTX or PDF documents from a simple web UI.
- Parse slides/pages and extract structured content.
- Generate per‑slide/page summaries and narration scripts.
- Synthesize narration via local or pluggable TTS.
- Optionally generate quiz questions using a local LLM.
- Produce a stitched, narrated “video‑lesson” output.

## Features

- End‑to‑end pipeline: upload → parse → summarize → narrate → render.
- Local‑first AI integrations (LLM + TTS) with configurable providers.
- Real‑time job progress and result display in the UI.
- Clear separation of backend orchestration and frontend experience.

## Models & Configuration

LectureForge works with pluggable local/cloud LLM + TTS backends:

**Required environment variables:**
- `LLM_PROVIDER` – `local` or `openai_compatible`
- `LLM_MODEL_PATH` – Local GGUF model path or API model name
- `TTS_PROVIDER` – `local` or cloud TTS service
- `TTS_VOICE` – Voice identifier

**Hardware recommendations:**
- CPU: 8GB+ RAM for small models
- GPU: 12GB+ VRAM recommended for 7B+ models
- Large decks (50+ slides): 30-60s processing time per slide

See `.env.example` for full configuration.

## Architecture

The system is split into a Next.js frontend and a FastAPI backend, with local storage for intermediate assets and outputs. A typical request flow is:

**Browser → Next.js → FastAPI → LLM/TTS + Storage → Frontend results**

High‑level components:

- **Frontend (Next.js):** Upload UI, progress tracking, results visualization.
- **Backend (FastAPI):** File ingestion, parsing, orchestration, pipeline execution.
- **LLM + TTS:** Pluggable local providers for summary, narration, and quizzes.
- **Storage:** Source files, intermediate assets, and final outputs.

## API Overview

Core functionality is exposed via FastAPI endpoints that the frontend consumes, and other services can integrate programmatically.

- `POST /api/v1/process` – Upload a PPT/PPTX or PDF and start processing.
- `GET /api/v1/jobs/{job_id}/status` – Retrieve processing status.
- `GET /api/v1/jobs/{job_id}/result` – Retrieve results (summaries, audio, outputs).
- `GET /api/v1/health` – Health check endpoint.

If FastAPI docs are enabled, the OpenAPI schema is available at `/docs` or `/redoc`.

## Project Structure

```text
LectureForge
├── backend/           # FastAPI application (API, services, LLM/TTS integration)
├── frontend/          # Next.js application (UI for upload and results)
├── data/              # Data utilities or configuration
├── docs/              # Additional documentation (architecture, API, etc.)
├── samples/           # Example PPT/PPTX and PDF files
├── scripts/           # Helper scripts (dev, maintenance, etc.)
├── storage/           # Generated artifacts (local dev only; gitignored)
├── logs/              # Log output (local dev only; gitignored)
├── docker-compose.yml # Docker orchestration
├── docker-compose.dev.yml
├── nginx.conf
├── LICENSE
├── README.md
└── ...other root files
```

## Getting Started

### Prerequisites

Backend:
- Python 3.11+
- pip / virtualenv

Frontend:
- Node.js 18+ (20+ recommended)
- npm / yarn / pnpm

Optional:
- Docker + Docker Compose (if running via containers)

### Installation

```bash
git clone <repo-url>
cd LectureForge
```

Backend setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements/requirements.txt
```

Frontend setup:

```bash
cd frontend
npm install
```

### Environment Configuration

Backend:

- Copy `backend/.env.example` to `backend/.env`
- Configure LLM/TTS provider settings, storage paths, limits, etc.

Frontend:

- Copy `frontend/.env.example` to `frontend/.env.local`
- Set the backend base URL and any client‑side config.

### Running Locally

Backend (from repo root):

```bash
uvicorn backend.app.main:app --reload
```

Frontend:

```bash
cd frontend
npm run dev
```

Open in browser:

- Frontend UI: http://localhost:3000  
- Backend API: http://localhost:8000  

## Usage

1. Start backend and frontend.
2. Open the web UI.
3. Upload a PPT/PPTX or PDF (see `samples/` for test files).
4. Configure options (summaries, narration, quizzes).
5. Run the pipeline.
6. View per‑slide/page results and download the narrated output.

Generated artifacts are stored in `storage/` for local development and are typically gitignored.

### How presentations are processed

PPT/PPTX and PDF files are parsed into slides or pages. The LLM typically operates at slide/page granularity, with optional batching for efficiency on longer documents. When text is long, it is chunked into smaller segments before summarization and question generation, and outputs are assembled per slide/page or chunk. Large decks can take noticeably longer to process; work is sequential or batched depending on implementation and available resources.

## Tech Stack

**Backend**
- FastAPI
- Python 3.11+
- Pydantic settings and structured config

**Frontend**
- Next.js
- React
- TypeScript (if enabled)

**AI**
- Local or pluggable LLM provider for summaries/quizzes
- Local or pluggable TTS provider for narration

## Testing & Quality

- Current status: Basic tests for core backend endpoints (and/or tests still to be expanded).
- Planned: Expand unit and integration coverage, add frontend tests, and enforce linting in CI.
- Linting/formatting (planned or recommended): Python with Ruff + Black; frontend with ESLint + Prettier.

### CI (planned or recommended)

On each push/PR:
- Run backend tests
- Lint backend and frontend
- Check formatting

### Running tests

```bash
# Backend tests
pytest

# Frontend tests (if configured)
npm test
```

## Limitations & Trade‑offs

- Large presentations can be slow to process when running fully local pipelines.
- Summary and quiz quality depends on the chosen model and input formatting.
- Multi‑language support may be limited if the model is primarily trained on English.
- Complex slide layouts or image‑heavy decks can reduce extraction accuracy.
- Audio naturalness varies by TTS backend and voice configuration.
- Larger models require significant RAM/VRAM and CPU resources.

## Security & Privacy

- By default, processing is intended to run locally without sending files to third‑party services.
- Uploaded files and outputs are stored under `storage/` for local development; clean this directory regularly.
- If handling sensitive decks, ensure `LLM_PROVIDER` and `TTS_PROVIDER` are configured for local processing.
- This project is a prototype and not a security‑hardened product; production deployments should add access control, encryption at rest, and audit logging.

## Roadmap

- Async/background job queue for long‑running processing.
- Improved slide segmentation and content heuristics.
- Advanced quiz generation and answer validation.
- User accounts and persisted projects.
- Observability: logging, metrics, tracing.

## Deployment

You can run the project via Docker Compose:

```bash
docker-compose up -d
```

Environment variables can be set via `.env` files or environment‑specific configuration. For local models and TTS, a modern CPU and ample RAM are recommended; a GPU can significantly reduce processing time for larger workloads.

For production deployments, consider:
- Running backend and frontend as separate services.
- Using HTTPS and a reverse proxy.
- Setting up logs, metrics, and health checks.

## Contributing

- Open issues for bugs, feature requests, or questions.
- Submit PRs with clear descriptions and test coverage.
- Run linting/formatting and tests before opening a PR.

## License

MIT — see `LICENSE`.
