# Presentation Understanding Engine

An AI-powered system that performs **semantic understanding of PowerPoint presentations** to automatically generate:
- 🎙️ Teacher-style narrated video lectures
- 📝 Structured multiple-choice assessments (MCQs)
- 🎬 Professional video output with TTS narration

Designed for **EdTech**, **training automation**, and **instructional content pipelines**.

---

## ✨ Features

- **Smart Parsing**: Robust slide text extraction (handles empty or image-only slides)
- **AI Narration**: LLM-generated teacher-style explanations (not verbatim repetition)
- **Video Generation**: Automatic video lectures with TTS and slide images
- **Quiz Generation**: MCQs with difficulty levels in strict JSON format
- **Multilingual**: English, French, and Hindi support
- **Real-time Progress**: WebSocket-based live updates during processing
- **Modern UI**: Next.js frontend with beautiful Tailwind CSS design
- **Docker Ready**: Production-ready containerized deployment

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                        │
│  ┌─────────┐  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ Upload  │  │ Processing  │  │   Results    │  │   Quiz    │  │
│  │  Page   │  │    Page     │  │    Page      │  │   Mode    │  │
│  └────┬────┘  └──────┬──────┘  └──────┬───────┘  └───────────┘  │
└───────┼──────────────┼────────────────┼─────────────────────────┘
        │              │                │
        ▼              ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │  REST API   │  │  WebSocket   │  │    Job Manager          │ │
│  │  Endpoints  │  │   Handler    │  │  (Async Processing)     │ │
│  └──────┬──────┘  └──────┬───────┘  └───────────┬─────────────┘ │
└─────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                      │
          ▼                ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Processing Pipeline                          │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────┐  │
│  │   PPT     │  │ Narration │  │    TTS    │  │    Video     │  │
│  │  Parser   │→ │   Chain   │→ │  Service  │→ │  Assembler   │  │
│  └───────────┘  └───────────┘  └───────────┘  └──────────────┘  │
│                      ↓                                           │
│               ┌───────────┐                                      │
│               │   MCQ     │                                      │
│               │   Chain   │                                      │
│               └───────────┘                                      │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Ollama LLM                               │
│               (llama3.1:8b-instruct-q4 or similar)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI** - High-performance API framework
- **LangChain** - LLM orchestration
- **Ollama** - Local LLM inference
- **python-pptx** - PowerPoint parsing
- **edge-tts** - Microsoft neural TTS
- **FFmpeg** - Video processing
- **Pillow** - Image processing

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **shadcn/ui** - Beautiful component library
- **React Query** - Server state management
- **Framer Motion** - Animations

### DevOps
- **Docker & Docker Compose** - Containerization
- **Nginx** - Reverse proxy
- **GitHub Actions** - CI/CD (optional)

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/Daivik2605/presentation-understanding-engine.git
cd presentation-understanding-engine

# Start with Docker Compose
docker-compose up -d

# Pull the LLM model (first time only)
docker exec -it ppt-engine-ollama ollama pull llama3.1:8b-instruct-q4
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Option 2: Local Development

#### Prerequisites
- Python 3.11+
- Node.js 18+
- FFmpeg
- Ollama

#### Backend Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac

# Start Ollama and pull model
ollama serve
ollama pull llama3.1:8b-instruct-q4

# Run the backend
uvicorn app.main:app --reload
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment file
copy .env.example .env.local  # Windows
cp .env.example .env.local    # Linux/Mac

# Run the frontend
npm run dev
```

---

## 📁 Project Structure

```

---

## ⚙️ Performance & Local LLM Settings

Required Ollama model:
- `llama3.1:8b-instruct-q4`

Environment overrides (defaults shown in `app/core/config.py`):
- `OLLAMA_MODEL` (default `llama3.1:8b-instruct-q4`)
- `OLLAMA_BASE_URL` (default `http://localhost:11434`)
- `NARRATION_BATCH_SIZE` (default `5`)
- `LLM_CONCURRENCY` (default `2`)
- `TTS_CONCURRENCY` (default `3`)
- `RENDER_CONCURRENCY` (default `3`)
- `VIDEO_CONCURRENCY` (default `3`)
- `NARRATION_MIN_WORDS` (default `15`)
- `NARRATION_MAX_WORDS` (default `300`)

Example:

```bash
export OLLAMA_MODEL=llama3.1:8b-instruct-q4
export NARRATION_BATCH_SIZE=6
export LLM_CONCURRENCY=1
export TTS_CONCURRENCY=3
```

Pipeline selection:
- `mode=ppt` for `.ppt/.pptx`
- `mode=pdf` for `.pdf`
- `mode=policy` for `.pdf/.txt` (policy pipeline)
- `mode=auto` picks a pipeline based on file extension

PDF processing:
- One slide per page (no chunking)
- Each page is summarized into bullet points with a short narration

Caching:
- Narration cache lives in `data/cache/narrations/`
- Cache key = sha256(language + chunk text + pipeline type)
- Invalidate by deleting the cache folder or changing the chunk text

Quick perf check:

```bash
python scripts/dev_perf_test.py sample.pptx --max-slides 5
```
presentation-understanding-engine/
├── app/
│   ├── api/
│   │   ├── health.py          # Health check endpoint
│   │   ├── process.py         # Upload & processing endpoint
│   │   ├── jobs.py            # Job management endpoints
│   │   └── websocket.py       # WebSocket for progress updates
│   ├── core/
│   │   ├── config.py          # Pydantic settings
│   │   ├── logging.py         # Structured logging
│   │   └── exceptions.py      # Custom exceptions
│   ├── models/
│   │   └── job.py             # Job & progress models
│   ├── services/
│   │   ├── ppt_parser.py      # PowerPoint extraction
│   │   ├── narration_chain.py # LLM narration generation
│   │   ├── qa_chain.py        # LLM MCQ generation
│   │   ├── tts_service.py     # Text-to-speech
│   │   ├── slide_renderer.py  # Slide image rendering
│   │   ├── video_assembler.py # Individual slide videos
│   │   ├── video_stitcher.py  # Final video assembly
│   │   ├── job_manager.py     # Job tracking
│   │   └── async_processor.py # Async processing pipeline
│   └── main.py                # FastAPI application
├── frontend/
│   ├── app/
│   │   ├── page.tsx           # Home page
│   │   ├── upload/            # Upload page
│   │   ├── processing/        # Processing progress page
│   │   └── results/           # Results display page
│   ├── components/
│   │   ├── ui/                # shadcn/ui components
│   │   ├── upload/            # Upload components
│   │   ├── processing/        # Progress components
│   │   └── results/           # Result components
│   ├── hooks/                 # Custom React hooks
│   └── lib/                   # Utilities & API client
├── storage/
│   ├── uploads/               # Uploaded files
│   ├── outputs/               # Generated outputs
│   └── temp/                  # Temporary files
├── docker-compose.yml         # Production Docker setup
├── docker-compose.dev.yml     # Development Docker setup
├── Dockerfile                 # Backend container
├── nginx.conf                 # Nginx configuration
└── requirements.txt           # Python dependencies
```

---

## 🔧 Configuration

### Backend Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.1:8b-instruct-q4` | LLM model to use |
| `NARRATION_BATCH_SIZE` | `5` | Slides per LLM narration batch |
| `LLM_CONCURRENCY` | `2` | Max concurrent LLM calls |
| `TTS_CONCURRENCY` | `3` | Max concurrent TTS calls |
| `RENDER_CONCURRENCY` | `3` | Max concurrent slide renders |
| `VIDEO_CONCURRENCY` | `3` | Max concurrent clip renders |
| `NARRATION_MIN_WORDS` | `15` | Minimum words per narration |
| `NARRATION_MAX_WORDS` | `300` | Maximum words per narration |
| `TTS_VOICE_EN` | `en-US-GuyNeural` | English TTS voice |
| `TTS_VOICE_FR` | `fr-FR-DeniseNeural` | French TTS voice |
| `TTS_VOICE_HI` | `hi-IN-SwaraNeural` | Hindi TTS voice |
| `NARRATION_CACHE_DIR` | `data/cache/narrations` | Narration cache directory |
| `VIDEO_FPS` | `1` | Video frames per second |
| `VIDEO_RESOLUTION` | `1920x1080` | Video resolution |
| `MAX_SLIDES` | `20` | Maximum slides to process |
| `MAX_FILE_SIZE_MB` | `50` | Maximum upload file size |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENVIRONMENT` | `development` | Environment mode |

### Frontend Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL |

---

## 📖 API Documentation

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/process` | Upload and process PPT |
| `GET` | `/api/v1/jobs/{job_id}/status` | Get job status |
| `GET` | `/api/v1/jobs/{job_id}/result` | Get job result |
| `POST` | `/api/v1/jobs/{job_id}/cancel` | Cancel job |
| `GET` | `/api/v1/jobs` | List all jobs |
| `GET` | `/api/v1/health` | Health check |

### WebSocket

Connect to `/ws/jobs/{job_id}` for real-time progress updates.

### Example Usage

```python
import requests

# Upload a presentation
with open("presentation.pptx", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/process",
        files={"file": f},
        data={
            "language": "en",
            "max_slides": 10,
            "generate_video": True,
            "generate_mcqs": True
        }
    )

job_id = response.json()["job_id"]

# Check status
status = requests.get(f"http://localhost:8000/api/v1/jobs/{job_id}/status")
print(status.json())

# Get results when complete
result = requests.get(f"http://localhost:8000/api/v1/jobs/{job_id}/result")
print(result.json())
```

---

## 🎨 Screenshots

### Home Page
Modern landing page with feature highlights and call-to-action.

### Upload Page
Drag & drop interface with language selection and processing options.

### Processing Page
Real-time progress tracking with WebSocket updates for each slide.

### Results Page
- **Slides Tab**: Browse slides with narration and audio playback
- **Video Tab**: Watch the complete video lecture
- **Quiz Tab**: Interactive MCQ quiz mode with scoring
- **Export Tab**: Download all generated content

---

## 🧪 Testing

```bash
# Run backend tests
pytest

# Run with coverage
pytest --cov=app

# Run frontend tests
cd frontend
npm test
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [LangChain](https://langchain.com/) for LLM orchestration
- [Ollama](https://ollama.ai/) for local LLM inference
- [shadcn/ui](https://ui.shadcn.com/) for beautiful components
- [Microsoft Edge TTS](https://github.com/rany2/edge-tts) for neural voices
