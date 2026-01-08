from app.services.ppt_parser import parse_ppt
from app.services.narration_chain import narration_chain
from app.services.qa_chain import qa_chain

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
            "qa": None
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

            # Generate Q&A
            qa_raw = qa_chain.invoke({
                "slide_text": slide["text"],
                "language": language
            })

            # Ensure API never crashes
            slide_result["qa"] = str(qa_raw)
            
        results.append(slide_result)
    return results