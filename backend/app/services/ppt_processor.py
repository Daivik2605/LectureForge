from app.services.ppt_pipeline import process_ppt_sync

def process_ppt(ppt_path: str, language: str = "en", max_slides: int = 1) -> list[dict]:
    """
    Legacy wrapper for synchronous PPT processing.
    """
    return process_ppt_sync(ppt_path, language=language, max_slides=max_slides)
