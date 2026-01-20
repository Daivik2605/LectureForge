"""
Presentation Understanding Engine - Main Application Entry Point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import PPTEngineError
from app.api.health import router as health_router
from app.api.process import router as process_router
from app.api.jobs import router as jobs_router
from app.api.websocket import router as websocket_router

# Setup logging
setup_logging(
    level="DEBUG" if settings.debug else "INFO",
    json_format=settings.environment == "production"
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Ollama URL: {settings.ollama_base_url}")
    logger.info(f"Model: {settings.ollama_model}")
    
    # Ensure directories exist
    settings.ensure_directories()
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="""
    AI-powered backend system that performs semantic understanding of PowerPoint presentations 
    to automatically generate teacher-style narrations and structured MCQ assessments.
    
    ## Features
    - 📤 Upload PowerPoint files via REST API
    - 🎙️ AI-generated narration using LLMs
    - 📝 AI-generated MCQs with schema-safe JSON output
    - 🎬 Video generation with TTS audio
    - 🌍 Multilingual support (English, French, Hindi)
    - ⚡ Async processing with progress tracking
    - 🔄 WebSocket support for real-time updates
    """,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware - Allow all origins in development
if settings.environment == "production":
    origins = settings.cors_origins
    allow_credentials = True
else:
    origins = ["*"]
    allow_credentials = False  # Can't use credentials with wildcard origin

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler for custom exceptions
@app.exception_handler(PPTEngineError)
async def ppt_engine_exception_handler(request: Request, exc: PPTEngineError):
    """Handle custom PPT Engine exceptions."""
    logger.error(f"PPTEngineError: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=400,
        content=exc.to_dict()
    )


# Include routers with API prefix
API_PREFIX = "/api/v1"
app.include_router(health_router, prefix=API_PREFIX)
app.include_router(process_router, prefix=API_PREFIX)
app.include_router(jobs_router, prefix=API_PREFIX)
app.include_router(websocket_router)


@app.get("/", tags=["Root"])
def root():
    """Root endpoint - API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


# Mount static files for serving generated content AFTER all routes
# This allows direct access to generated files like /data/final_videos/file.mp4
data_dir = Path("data")
if data_dir.exists():
    app.mount("/data", StaticFiles(directory="data"), name="data")

storage_dir = Path("storage")
if storage_dir.exists():
    app.mount("/storage", StaticFiles(directory="storage"), name="storage")
