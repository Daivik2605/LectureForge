from app.services.ppt_processor import process_ppt

if __name__ == "__main__":
    ppt_path = "sample.pptx"

    output = process_ppt(ppt_path)
    for slide_output in output:
        print(f"Slide {slide_output['slide_number']}:")
        print(f"TEXT: {slide_output['text']}")
        print(f"NARRATION: {slide_output['narration']}")
        print(f"Q&A: {slide_output['qa']}")
        print("-" * 40)
