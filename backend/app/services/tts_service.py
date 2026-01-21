import subprocess
import sys
import uuid
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

AUDIO_DIR = settings.audio_dir
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def get_edge_tts_command() -> list:
    """Get the edge-tts command for the current platform."""
    # Try using Python module directly (most reliable)
    return [sys.executable, "-m", "edge_tts"]


def synthesize_speech(text: str, language: str) -> str:
    """Synthesize speech from text using edge-tts."""
    text = text.strip()
    if not text:
        raise ValueError("TTS text is empty")

    audio_path = AUDIO_DIR / f"{uuid.uuid4()}.mp3"

    voice = settings.get_voice_for_language(language)
    
    logger.info(f"Synthesizing speech: voice={voice}, text_length={len(text)}")

    try:
        cmd = get_edge_tts_command() + [
            "--voice", voice,
            "--rate", settings.tts_rate,
            "--text", text,
            "--write-media", str(audio_path)
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"Audio created: {audio_path}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"edge-tts error: {e.stderr}")
        raise RuntimeError(f"TTS synthesis failed: {e.stderr}")
    except FileNotFoundError:
        logger.error("edge-tts not found. Install with: pip install edge-tts")
        raise RuntimeError("edge-tts not found. Please install with: pip install edge-tts")

    return str(audio_path)
