# Configuration

## Backend Environment

Create `backend/.env` from the example file:

```bash
cp backend/.env.example backend/.env
```

The backend uses Pydantic Settings and loads `backend/.env` from `backend/app/core/config.py`.

Core settings:

| Variable | Default | Notes |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | `development` \| `staging` \| `production`. |
| `DEBUG` | `false` | Enables debug logging. |
| `API_HOST` | `0.0.0.0` | Bind host. |
| `API_PORT` | `8000` | Bind port. |
| `CORS_ORIGINS` | `["http://localhost:3000","http://127.0.0.1:3000"]` | JSON list. |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server base URL. |
| `OLLAMA_MODEL` | `llama3.1:8b` | Model name. |
| `TTS_VOICE_EN` | `en-US-GuyNeural` | Edge-TTS voice. |
| `VIDEO_WIDTH` | `1280` | Render width. |
| `VIDEO_HEIGHT` | `720` | Render height. |
| `MAX_FILE_SIZE_MB` | `50` | Max upload size. |

For the full list of tunables, see `backend/.env.example`.

## Frontend Environment

Create `frontend/.env.local` from the example file:

```bash
cp frontend/.env.example frontend/.env.local
```

| Variable | Default | Notes |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend base URL. |

## Docker Compose

Docker Compose uses the same environment variables. Override values by editing `backend/.env`, `frontend/.env.local`, or passing environment variables directly to `docker-compose`.
