"""
Custom exception classes for the Presentation Understanding Engine.
"""

from typing import Optional, Any


class PPTEngineError(Exception):
    """Base exception for all PPT Engine errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        details: Optional[dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details
        }


# ===================
# File Processing Errors
# ===================

class FileProcessingError(PPTEngineError):
    """Error during file processing."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "FILE_PROCESSING_ERROR", details)


class InvalidFileTypeError(FileProcessingError):
    """Invalid file type uploaded."""
    
    def __init__(self, filename: str, expected_types: list[str]):
        super().__init__(
            f"Invalid file type: {filename}. Expected: {', '.join(expected_types)}",
            {"filename": filename, "expected_types": expected_types}
        )
        self.code = "INVALID_FILE_TYPE"


class FileTooLargeError(FileProcessingError):
    """File exceeds size limit."""
    
    def __init__(self, size_mb: float, max_size_mb: int):
        super().__init__(
            f"File too large: {size_mb:.2f}MB. Maximum allowed: {max_size_mb}MB",
            {"size_mb": size_mb, "max_size_mb": max_size_mb}
        )
        self.code = "FILE_TOO_LARGE"


class EmptyFileError(FileProcessingError):
    """Empty file uploaded."""
    
    def __init__(self):
        super().__init__("Empty file uploaded", {})
        self.code = "EMPTY_FILE"


class PPTParseError(FileProcessingError):
    """Error parsing PowerPoint file."""
    
    def __init__(self, message: str, filename: Optional[str] = None):
        super().__init__(
            f"Failed to parse PowerPoint: {message}",
            {"filename": filename}
        )
        self.code = "PPT_PARSE_ERROR"


# ===================
# LLM Errors
# ===================

class LLMError(PPTEngineError):
    """Base error for LLM-related issues."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "LLM_ERROR", details)


class LLMConnectionError(LLMError):
    """Failed to connect to LLM service."""
    
    def __init__(self, service: str = "Ollama"):
        super().__init__(
            f"Failed to connect to {service}. Ensure the service is running.",
            {"service": service}
        )
        self.code = "LLM_CONNECTION_ERROR"


class LLMGenerationError(LLMError):
    """LLM failed to generate content."""
    
    def __init__(self, task: str, slide_number: Optional[int] = None):
        details = {"task": task}
        if slide_number:
            details["slide_number"] = slide_number
        super().__init__(
            f"LLM failed to generate {task}",
            details
        )
        self.code = "LLM_GENERATION_ERROR"


class LLMTimeoutError(LLMError):
    """LLM request timed out."""
    
    def __init__(self, timeout_seconds: int):
        super().__init__(
            f"LLM request timed out after {timeout_seconds} seconds",
            {"timeout_seconds": timeout_seconds}
        )
        self.code = "LLM_TIMEOUT"


# ===================
# TTS Errors
# ===================

class TTSError(PPTEngineError):
    """Error during text-to-speech conversion."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "TTS_ERROR", details)


class TTSGenerationError(TTSError):
    """Failed to generate speech audio."""
    
    def __init__(self, language: str, text_preview: str = ""):
        super().__init__(
            f"Failed to generate speech in {language}",
            {"language": language, "text_preview": text_preview[:100]}
        )
        self.code = "TTS_GENERATION_ERROR"


# ===================
# Video Errors
# ===================

class VideoError(PPTEngineError):
    """Error during video processing."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "VIDEO_ERROR", details)


class VideoAssemblyError(VideoError):
    """Failed to assemble video from image and audio."""
    
    def __init__(self, slide_number: Optional[int] = None):
        details = {}
        if slide_number:
            details["slide_number"] = slide_number
        super().__init__(
            "Failed to assemble video from image and audio",
            details
        )
        self.code = "VIDEO_ASSEMBLY_ERROR"


class VideoStitchingError(VideoError):
    """Failed to stitch videos together."""
    
    def __init__(self, video_count: int):
        super().__init__(
            f"Failed to stitch {video_count} videos together",
            {"video_count": video_count}
        )
        self.code = "VIDEO_STITCHING_ERROR"


class FFmpegNotFoundError(VideoError):
    """FFmpeg is not installed or not in PATH."""
    
    def __init__(self):
        super().__init__(
            "FFmpeg not found. Please install FFmpeg and add it to PATH.",
            {}
        )
        self.code = "FFMPEG_NOT_FOUND"


# ===================
# Job Errors
# ===================

class JobError(PPTEngineError):
    """Error related to job processing."""
    
    def __init__(self, message: str, job_id: Optional[str] = None, details: Optional[dict] = None):
        details = details or {}
        if job_id:
            details["job_id"] = job_id
        super().__init__(message, "JOB_ERROR", details)


class JobNotFoundError(JobError):
    """Job with given ID not found."""
    
    def __init__(self, job_id: str):
        super().__init__(f"Job not found: {job_id}", job_id)
        self.code = "JOB_NOT_FOUND"


class JobTimeoutError(JobError):
    """Job execution timed out."""
    
    def __init__(self, job_id: str, timeout_minutes: int):
        super().__init__(
            f"Job timed out after {timeout_minutes} minutes",
            job_id,
            {"timeout_minutes": timeout_minutes}
        )
        self.code = "JOB_TIMEOUT"


class JobCancelledError(JobError):
    """Job was cancelled."""
    
    def __init__(self, job_id: str):
        super().__init__(f"Job was cancelled: {job_id}", job_id)
        self.code = "JOB_CANCELLED"


class TooManyJobsError(JobError):
    """Too many concurrent jobs."""
    
    def __init__(self, max_jobs: int):
        super().__init__(
            f"Too many concurrent jobs. Maximum allowed: {max_jobs}",
            details={"max_jobs": max_jobs}
        )
        self.code = "TOO_MANY_JOBS"


# ===================
# Validation Errors
# ===================

class ValidationError(PPTEngineError):
    """Input validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[dict] = None):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, "VALIDATION_ERROR", details)


class UnsupportedLanguageError(ValidationError):
    """Unsupported language requested."""
    
    def __init__(self, language: str, supported: list[str]):
        super().__init__(
            f"Unsupported language: {language}. Supported: {', '.join(supported)}",
            "language",
            {"language": language, "supported": supported}
        )
        self.code = "UNSUPPORTED_LANGUAGE"
