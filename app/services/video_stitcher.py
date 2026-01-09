import subprocess
import uuid
from pathlib import Path
from typing import List

FINAL_DIR = Path("data/final_videos")
FINAL_DIR.mkdir(parents=True, exist_ok=True)

def stitch_videos(video_paths: List[str]) -> str:
    """
    Concatenate multiple MP4s into a single MP4 using ffmpeg concat demuxer.
    """
    if not video_paths:
        raise ValueError("No video paths provided to stitch_videos()")

    # Create concat list file
    list_file = FINAL_DIR / f"concat_{uuid.uuid4()}.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for vp in video_paths:
            # ffmpeg requires this exact format
            f.write(f"file '{Path(vp).as_posix()}'\n")

    output = FINAL_DIR / f"final_{uuid.uuid4()}.mp4"

    # -safe 0 allows absolute paths
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output)
        ],
        check=True
    )

    return str(output)
