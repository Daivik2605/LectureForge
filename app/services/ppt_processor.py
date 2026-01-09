from app.services.ppt_parser import parse_ppt
from app.services.narration_chain import narration_chain
from app.services.qa_chain import qa_chain
from app.services.qa_validator import validate_and_fix_mcqs, validate_mcq_language
from app.services.tts_service import synthesize_speech
from app.services.slide_renderer import render_slide_image
from app.services.video_assembler import create_video

def process_ppt(ppt_path: str, language: str="en", max_slides: int=1) -> list[dict]:
    """
    Orchestrates PPT processing:
    - Parses slides
    - Generates narration
    - Generates Q&A
    """
    # slides = parse_ppt(ppt_path)
    slides = [s for s in parse_ppt(ppt_path) if s["has_text"]][:max_slides]
    results = []

    for slide in slides:
        print(f"Processing slide {slide['slide_number']}...")
        slide_result = {
            "slide_number": slide["slide_number"],
            "text": slide["text"],
            "has_text": slide["has_text"],
            "narration": None,
            "qa": None,
            "audio": None,
            "video": None,
        }
        if slide["has_text"]:
            # Generate narration
            #narration = narration_chain.invoke({"slide_text": slide["text"], "language": language}).content
            #slide_result["narration"] = narration
            narration = str(
                narration_chain.invoke({
                    "slide_text": slide["text"],
                    "language": language
                })
            )

            slide_result["narration"] = narration
            # Phase 9 — Video generation
            audio_path = synthesize_speech(narration, language)
            image_path = render_slide_image(slide["text"])
            video_path = create_video(image_path, audio_path)

            slide_result["audio"] = audio_path
            slide_result["video"] = video_path


            # Generate Q&A
            qa_raw = qa_chain.invoke({
                "slide_text": slide["text"],
                "language": language
            })

            validated_qa = validate_and_fix_mcqs(str(qa_raw))
            slide_result["qa"] = validated_qa

            # Retry once if schema invalid OR language mismatch
            if (
                not validated_qa["questions"]
                or not validate_mcq_language(validated_qa, language)
            ):
                qa_retry = qa_chain.invoke({
                    "slide_text": slide["text"],
                    "language": language
                })
                validated_qa = validate_and_fix_mcqs(str(qa_retry))
            # FINAL enforcement — do NOT allow wrong language
            if not validate_mcq_language(validated_qa, language):
                validated_qa = {"questions": []}

            slide_result["qa"] = validated_qa

        results.append(slide_result)
    return results