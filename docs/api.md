# API

Base URL: `http://localhost:8000`

All REST endpoints are under `/api/v1`.

## Upload & Process

`POST /api/v1/process` (multipart/form-data)

Fields:
- `file`: PPT/PPTX, PDF, or TXT file
- `language`: `en` | `fr` | `hi`
- `mode`: `ppt` | `pdf` | `policy` | `auto`
- `max_slides`: integer
- `generate_video`: `true` | `false`
- `generate_mcqs`: `true` | `false`

Notes:
- `mode=auto` selects a pipeline based on file extension.

Response:
```json
{
  "job_id": "uuid",
  "status": "processing",
  "message": "Processing started for file.pptx"
}
```

## Job Status

`GET /api/v1/jobs/{job_id}/status`

Response:
```json
{
  "job_id": "uuid",
  "status": "processing",
  "progress": 45,
  "current_slide": 3,
  "total_slides": 10,
  "current_step": "Generating narrations",
  "slides_progress": [
    {
      "slide_number": 1,
      "narration": "completed",
      "mcq": "completed",
      "video": "completed"
    }
  ]
}
```

## Job Result

`GET /api/v1/jobs/{job_id}/result`

Response (trimmed):
```json
{
  "job_id": "uuid",
  "status": "completed",
  "filename": "demo.pptx",
  "mode": "ppt",
  "slides": [
    {
      "slide_number": 1,
      "text": "Slide content...",
      "narration": "Spoken explanation...",
      "audio_path": "data/audio/...",
      "image_path": "data/images/...",
      "video_path": "data/videos/..."
    }
  ],
  "final_video_path": "storage/outputs/{job_id}/final.mp4"
}
```

## Job Control

- `POST /api/v1/jobs/{job_id}/cancel`
- `GET /api/v1/jobs` (recent jobs)

## Download Helper

`GET /api/v1/jobs/download?path={relative_path}`

Downloads a generated file within `data/`. For storage outputs, use the static `/storage/` mount.

## Health

`GET /api/v1/health`

Response:
```json
{ "status": "ok" }
```

## WebSocket

`WS /ws/jobs/{job_id}`

Server pushes progress and completion events:

```json
{
  "type": "progress",
  "job_id": "uuid",
  "data": { "progress": 60, "current_step": "TTS" }
}
```

## Legacy Endpoints

These endpoints are still available but the async `/process` flow is preferred:

- `POST /api/v1/process-ppt`
- `POST /api/v1/process-ppt-video`
