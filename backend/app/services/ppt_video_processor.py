from typing import Dict, List
from app.services.ppt_parser import parse_ppt
from app.services.narration_chain import generate_narration_sync

from app.services.slide_renderer import render_slide_image
from app.services.tts_service import synthesize_speech  # you created this
from app.services.video_assembler import create_video
from app.services.video_stitcher import stitch_videos

def process_ppt_to_video(ppt_path: str, language: str = "en", max_slides: int = 5) -> Dict:
    slides = [s for s in parse_ppt(ppt_path) if s["has_text"]][:max_slides]

    slide_videos: List[str] = []
    slide_outputs: List[dict] = []

    for slide in slides:
        slide_text = slide["text"]

        narration = generate_narration_sync(slide_text, language)

        image_path = render_slide_image(slide_text)
        audio_path = synthesize_speech(text=narration, language=language)
        video_path = create_video(image_path=image_path, audio_path=audio_path)

        slide_videos.append(video_path)

        slide_outputs.append({
            "slide_number": slide["slide_number"],
            "text": slide_text,
            "narration": narration,
            "image_path": image_path,
            "audio_path": audio_path,
            "video_path": video_path
        })

    # 🔍 DEBUG (keep for now)
    print("Slide videos:", slide_videos)

    final_video_path = None
    if slide_videos:
        print("Stitching videos now...")
        final_video_path = stitch_videos(slide_videos)
        print("Final video created:", final_video_path)

    return {
        "slides": slide_outputs,
        "final_video_path": final_video_path
    }
