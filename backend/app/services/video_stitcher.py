import os
import shutil
import subprocess
import uuid
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# FFmpeg path detection for Windows
def get_ffmpeg_path() -> str:
    """Get FFmpeg executable path."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    
    common_paths = [
        r"C:\Users\sourj\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return "ffmpeg"

FFMPEG = get_ffmpeg_path()

FINAL_DIR = settings.final_video_dir
FINAL_DIR.mkdir(parents=True, exist_ok=True)

def stitch_videos(video_paths: list[str], output_path: str | None = None) -> str:
    """
    Stitch multiple video files into a single video.
    Uses FFmpeg concat demuxer with re-encoding for compatibility.
    """
    if not video_paths:
        raise ValueError("No video paths provided for stitching")
    
    if len(video_paths) == 1:
        if output_path:
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(video_paths[0], output)
            return str(output)
        return video_paths[0]
    
    # Validate all video files exist
    for path in video_paths:
        if not Path(path).exists():
            raise FileNotFoundError(f"Video file not found: {path}")
    
    concat_file = FINAL_DIR / f"clips_{uuid.uuid4().hex[:8]}.txt"
    output = Path(output_path) if output_path else FINAL_DIR / f"final_{uuid.uuid4().hex[:8]}.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    
    # Write concat file with proper escaping for Windows paths
    with open(concat_file, "w", encoding="utf-8") as f:
        for path in video_paths:
            # Use forward slashes and escape single quotes for FFmpeg
            abs_path = str(Path(path).resolve()).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")
    
    logger.info(f"Stitching {len(video_paths)} videos...")
    
    try:
        # Re-encode for guaranteed compatibility across all clips
        result = subprocess.run([
            FFMPEG,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:v", "libx264",
            "-preset", settings.video_preset,
            "-crf", str(settings.video_crf),
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            str(output)
        ], check=True, capture_output=True, text=True)
        
        logger.info(f"Final video created: {output}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        raise RuntimeError(f"Video stitching failed: {e.stderr}")
    finally:
        # Clean up concat file
        if concat_file.exists():
            concat_file.unlink()
    
    return str(output)
