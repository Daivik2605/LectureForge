from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Form
from app.services.ppt_processor import process_ppt

router = APIRouter()

SUPPORTED_LANGUAGES = {"en", "fr", "hi"}

@router.post("/process-ppt")
async def process_ppt_endpoint(
    file: UploadFile = File(...),
    max_slides: int = Query(default=1, ge=1, le=5),
    language: str = Form("en"),
):
    # Validate language
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail="language must be one of: en, fr, hi"
        )

    # Validate file type
    if not file.filename.endswith(".pptx"):
        raise HTTPException(
            status_code=400,
            detail="Only .pptx files are allowed"
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Empty file uploaded"
        )

    # Save temporarily
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(contents)

    results = process_ppt(
        ppt_path=temp_path,
        language=language,
        max_slides=max_slides
    )

    return {
        "filename": file.filename,
        "language": language,
        "slides": results
    }