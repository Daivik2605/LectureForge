"""
Application configuration management using Pydantic Settings.
All configuration values can be overridden via environment variables.
"""

from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_project_root() -> Path:
    backend_root = Path(__file__).resolve().parents[2]
    repo_root = backend_root.parent
    if (repo_root / "frontend").exists():
        return repo_root
    return backend_root


PROJECT_ROOT = _resolve_project_root()
BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_ROOT / ".env"


def _resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ===================
    # Application Settings
    # ===================
    app_name: str = "Presentation Understanding Engine"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"
    
    # ===================
    # API Settings
    # ===================
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # ===================
    # LLM Settings (Ollama)
    # ===================
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1:8b"
    narration_temperature: float = 0.4
    qa_temperature: float = 0.3
    llm_timeout: int = 120  # seconds
    llm_max_retries: int = 3
    
    # ===================
    # TTS Settings (Edge-TTS)
    # ===================
    tts_voice_en: str = "en-US-GuyNeural"
    tts_voice_fr: str = "fr-FR-DeniseNeural"
    tts_voice_hi: str = "hi-IN-SwaraNeural"
    tts_rate: str = "+0%"  # Speech rate adjustment
    
    # ===================
    # Video Settings
    # ===================
    video_width: int = 1280
    video_height: int = 720
    video_fps: int = 30
    video_crf: int = 23  # Quality (lower = better, 18-28 recommended)
    video_preset: str = "fast"  # FFmpeg preset
    
    # ===================
    # Storage Settings
    # ===================
    base_data_dir: Path = Path("data")
    upload_dir: Path = Path("data/uploads")
    audio_dir: Path = Path("data/audio")
    image_dir: Path = Path("data/images")
    video_dir: Path = Path("data/videos")
    final_video_dir: Path = Path("data/final_videos")
    narration_cache_dir: Path = Path("data/cache/narrations")
    storage_dir: Path = Path("storage")
    storage_upload_dir: Path = Path("storage/uploads")
    storage_output_dir: Path = Path("storage/outputs")
    storage_temp_dir: Path = Path("storage/temp")
    
    # ===================
    # Processing Limits
    # ===================
    max_slides: int = 10
    max_file_size_mb: int = 50
    max_concurrent_jobs: int = 3
    job_timeout_minutes: int = 30
    narration_batch_size: int = 5
    llm_concurrency: int = 2
    tts_concurrency: int = 3
    render_concurrency: int = 3
    video_concurrency: int = 3
    narration_min_words: int = 15
    narration_max_words: int = 300
    
    # ===================
    # File Cleanup
    # ===================
    cleanup_enabled: bool = True
    cleanup_max_age_hours: int = 24
    
    # ===================
    # Rate Limiting
    # ===================
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 10
    rate_limit_window_minutes: int = 1
    
    # ===================
    # Redis Settings (for job queue & caching)
    # ===================
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False  # Set to True when Redis is available
    cache_ttl_seconds: int = 86400  # 24 hours
    
    # ===================
    # Supported Languages
    # ===================
    supported_languages: list[str] = ["en", "fr", "hi"]
    default_language: str = "en"

    def model_post_init(self, __context) -> None:
        paths_to_resolve = [
            "base_data_dir",
            "upload_dir",
            "audio_dir",
            "image_dir",
            "video_dir",
            "final_video_dir",
            "narration_cache_dir",
            "storage_dir",
            "storage_upload_dir",
            "storage_output_dir",
            "storage_temp_dir",
        ]
        for attr in paths_to_resolve:
            value = getattr(self, attr)
            if isinstance(value, Path):
                setattr(self, attr, _resolve_path(value))

    def get_voice_for_language(self, language: str) -> str:
        """Get TTS voice for a given language."""
        voice_map = {
            "en": self.tts_voice_en,
            "fr": self.tts_voice_fr,
            "hi": self.tts_voice_hi,
        }
        return voice_map.get(language, self.tts_voice_en)
    
    def ensure_directories(self) -> None:
        """Create all required data directories."""
        for dir_path in [
            self.base_data_dir,
            self.upload_dir,
            self.audio_dir,
            self.image_dir,
            self.video_dir,
            self.final_video_dir,
            self.narration_cache_dir,
            self.storage_dir,
            self.storage_upload_dir,
            self.storage_output_dir,
            self.storage_temp_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()

# Ensure directories exist on import
settings.ensure_directories()
