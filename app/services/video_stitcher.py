import subprocess
import uuid
from pathlib import Path

FINAL_DIR = Path("data/final_videos")
FINAL_DIR.mkdir(parents=True, exist_ok=True)

def stitch_videos(video_paths: list[str]) -> str:
    concat_file = FINAL_DIR / "clips.txt"
    
    # Ensure clips.txt is empty before writing
    concat_file.write_text("", encoding="utf-8")
    with open(concat_file, "w", encoding="utf-8") as f:
        for path in video_paths:
            abs_path = Path(path).resolve()
            f.write(f"file '{abs_path}'\n")

    with open(concat_file, "w") as f:
        for path in video_paths:
            f.write(f"file '{Path(path).resolve()}'\n")

    output = FINAL_DIR / f"{uuid.uuid4()}.mp4"

    subprocess.run([
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output)
    ], check=True)

    return str(output)