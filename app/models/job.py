"""
Pydantic models for job management and API responses.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field, computed_field


class JobState(str, Enum):
    """Job processing states."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SlideState(str, Enum):
    """Individual slide processing states."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SlideProgress(BaseModel):
    """Progress tracking for a single slide."""
    slide_number: int
    narration: SlideState = SlideState.PENDING
    mcq: SlideState = SlideState.PENDING
    video: SlideState = SlideState.PENDING
    error: Optional[str] = None


class MCQuestion(BaseModel):
    """Multiple choice question model."""
    question: str
    options: list[str] = Field(..., min_length=4, max_length=4)
    answer: str
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$")


class SlideResult(BaseModel):
    """Processing result for a single slide."""
    slide_number: int
    text: str
    has_text: bool
    title: Optional[str] = None
    bullets: Optional[list[str]] = None
    narration: Optional[str] = None
    qa: Optional[dict[str, list[MCQuestion]]] = None
    audio_path: Optional[str] = None
    image_path: Optional[str] = None
    video_path: Optional[str] = None


class JobCreate(BaseModel):
    """Request model for creating a new job."""
    filename: str
    language: str = "en"
    max_slides: int = Field(default=5, ge=1, le=10)
    generate_video: bool = True
    generate_mcqs: bool = True


class JobStatus(BaseModel):
    """Job status response model."""
    job_id: str
    status: JobState
    progress: int = Field(default=0, ge=0, le=100)
    current_slide: Optional[int] = None
    total_slides: Optional[int] = None
    current_step: Optional[str] = None
    slides_progress: list[SlideProgress] = []
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class JobResult(BaseModel):
    """Complete job result response model."""
    job_id: str
    status: JobState
    filename: str
    language: str
    mode: str = "ppt"
    slides: list[SlideResult] = []
    final_video_path: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    cache_hits: int = 0
    cache_misses: int = 0
    created_at: datetime
    completed_at: Optional[datetime] = None

    @computed_field
    def jobId(self) -> str:  # noqa: N802
        return self.job_id

    @computed_field
    def durationSeconds(self) -> Optional[float]:  # noqa: N802
        return self.processing_time_seconds

    @computed_field
    def cacheHits(self) -> int:  # noqa: N802
        return self.cache_hits

    @computed_field
    def cacheMisses(self) -> int:  # noqa: N802
        return self.cache_misses


class JobSummary(BaseModel):
    """Brief job summary for listing."""
    job_id: str
    filename: str
    status: JobState
    progress: int
    created_at: datetime


# ===================
# WebSocket Messages
# ===================

class WSMessageType(str, Enum):
    """WebSocket message types."""
    CONNECTED = "connected"
    PROGRESS = "progress"
    SLIDE_UPDATE = "slide_update"
    COMPLETED = "completed"
    ERROR = "error"


class WSMessage(BaseModel):
    """WebSocket message model."""
    type: WSMessageType
    job_id: str
    data: dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ===================
# API Response Models
# ===================

class UploadResponse(BaseModel):
    """Response after file upload."""
    job_id: str
    status: JobState
    message: str


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    message: str
    details: dict[str, Any] = {}


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    ollama_connected: bool
    redis_connected: bool
