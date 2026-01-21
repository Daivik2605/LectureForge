# Architecture

## Summary

Presentation Understanding Engine uses a thin Next.js UI and a FastAPI backend to run document pipelines that convert slides or pages into narrated videos. The backend integrates with a local LLM (Ollama), edge-tts, and FFmpeg while persisting artifacts to local storage.

## High-Level Flow

```
User
  -> Frontend (Next.js)
    -> Backend API (FastAPI)
      -> Pipeline (PPT | PDF | Policy)
        -> LLM (Ollama)
        -> TTS (edge-tts)
        -> Rendering (Pillow/FFmpeg)
      -> Storage (data/ + storage/)
```

## Core Components

### Frontend

- Upload UI and mode selection.
- Real-time progress via WebSocket + polling.
- Results view for per-slide/page output and final video.

### Backend

- REST and WebSocket APIs in `backend/app/api`.
- Job management in `backend/app/services/job_manager.py`.
- Pipeline implementations in `backend/app/services`.

### Pipelines

- **PPT pipeline** parses slides, generates narrations, optionally creates MCQs, renders slide images, and stitches per-slide clips.
- **PDF pipeline** extracts text per page, summarizes content, generates narration, and renders clips.
- **Policy pipeline** chunks long-form PDF/TXT input into chapters and stitches narrated output.

### Storage

Runtime artifacts are written to local directories under `data/` and `storage/`:

- `data/uploads`, `data/images`, `data/audio`, `data/videos`, `data/final_videos`
- `data/cache/narrations`
- `storage/uploads`, `storage/outputs`, `storage/temp`

All runtime artifacts are git-ignored; empty folders are preserved with `.gitkeep`.

## Deployment Shapes

- **Local dev:** Run backend + frontend directly from source.
- **Docker Compose:** Single command to start services for local production parity.

See `docs/pipelines.md` for pipeline behavior details and `docs/configuration.md` for configuration.
