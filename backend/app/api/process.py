from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Form, BackgroundTasks
from app.services.ppt_processor import process_ppt
from app.services.job_manager import job_manager
from app.services.async_processor import run_processing_job
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Process"])

# Ensure temp upload directory exists
UPLOAD_DIR = Path(settings.upload_dir)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_LANGUAGES = set(settings.supported_languages)


@router.post("/process")
async def process_ppt_async_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form("en"),
    mode: str = Form("auto"),
    max_slides: int = Form(default=5),
    generate_video: bool = Form(default=True),
    generate_mcqs: bool = Form(default=True),
):
    """
    Upload and process a PowerPoint file asynchronously.
    
    Returns a job_id that can be used to track progress via WebSocket
    or polling the /jobs/{job_id}/status endpoint.
    """
    # Validate language
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Language must be one of: {', '.join(SUPPORTED_LANGUAGES)}"
        )

    allowed_extensions = {
        "ppt": (".ppt", ".pptx"),
        "pdf": (".pdf",),
        "policy": (".pdf", ".txt"),
        "auto": (".ppt", ".pptx", ".pdf", ".txt"),
    }
    if mode not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Mode must be one of: ppt, pdf, policy, auto"
        )

    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in allowed_extensions[mode]:
        allowed_list = ", ".join(allowed_extensions[mode])
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type for mode={mode}. Allowed: {allowed_list}"
        )
    
    # Create job with all required parameters
    try:
        job_id = job_manager.create_job(
            filename=file.filename,
            language=language,
            max_slides=max_slides,
            generate_video=generate_video,
            generate_mcqs=generate_mcqs,
        )
        logger.info(f"Created job {job_id} for file {file.filename}")
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    # Check file size
    if len(contents) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_file_size_mb}MB"
        )

    # Save file
    temp_path = UPLOAD_DIR / file.filename
    with open(temp_path, "wb") as f:
        f.write(contents)
    
    # Start background processing
    background_tasks.add_task(
        run_processing_job,
        job_id=job_id,
        ppt_path=str(temp_path),
        language=language,
        mode=mode,
        max_slides=max_slides,
        generate_video=generate_video,
        generate_mcqs=generate_mcqs,
    )
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": f"Processing started for {file.filename}"
    }


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

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Empty file uploaded"
        )

    # Save temporarily (cross-platform)
    temp_path = UPLOAD_DIR / file.filename
    with open(temp_path, "wb") as f:
        f.write(contents)

    results = process_ppt(
        ppt_path=str(temp_path),
        language=language,
        max_slides=max_slides
    )

    return {
        "filename": file.filename,
        "language": language,
        "slides": results
    }

@router.post("/process-ppt-video")
async def process_ppt_video_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form("en"),
    max_slides: int = Query(default=5, ge=1, le=10),
):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    temp_path = UPLOAD_DIR / file.filename
    with open(temp_path, "wb") as f:
        f.write(contents)

    try:
        job_id = job_manager.create_job(
            filename=file.filename,
            language=language,
            max_slides=max_slides,
            generate_video=True,
            generate_mcqs=False,
        )
        logger.info(f"Created job {job_id} for video generation: {file.filename}")
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")

    background_tasks.add_task(
        run_processing_job,
        job_id=job_id,
        ppt_path=str(temp_path),
        language=language,
        mode="ppt",
        max_slides=max_slides,
        generate_video=True,
        generate_mcqs=False,
    )

    return {
        "job_id": job_id,
        "status": "processing",
        "message": f"Video processing started for {file.filename}"
    }
