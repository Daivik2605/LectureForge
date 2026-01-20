import subprocess
import uuid
import shutil
import os
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

VIDEO_DIR = Path("data/videos")
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

# FFmpeg path detection for Windows
def get_ffmpeg_path() -> str:
    """Get FFmpeg executable path."""
    # Check if ffmpeg is in PATH
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    
    # Common Windows installation paths
    common_paths = [
        r"C:\Users\sourj\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    # Fallback to hoping it's in PATH
    return "ffmpeg"

FFMPEG = get_ffmpeg_path()
logger.info(f"Using FFmpeg: {FFMPEG}")


def create_video(image_path: str, audio_path: str, output_path: str | None = None) -> str:
    """Create a video from an image and audio file."""
    output = Path(output_path) if output_path else VIDEO_DIR / f"{uuid.uuid4()}.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Creating video: image={image_path}, audio={audio_path}")

    try:
        subprocess.run([
            FFMPEG, "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-r", "30",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        "-pix_fmt", "yuv420p",
        str(output)
    ], check=True, capture_output=True, text=True)
        
        logger.info(f"Video created: {output}")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        raise RuntimeError(f"Video creation failed: {e.stderr}")
    except FileNotFoundError:
        logger.error(f"FFmpeg not found at: {FFMPEG}")
        raise RuntimeError(f"FFmpeg not found. Please install FFmpeg and add it to PATH.")

    return str(output)
