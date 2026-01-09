import subprocess
import uuid
from pathlib import Path

VIDEO_DIR = Path("data/videos")
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

def create_video(image_path: str, audio_path: str) -> str:
    output = VIDEO_DIR / f"{uuid.uuid4()}.mp4"

    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-r", "30",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        "-pix_fmt", "yuv420p",
        str(output)
    ], check=True)


    return str(output)
