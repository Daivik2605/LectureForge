# Troubleshooting

## Ollama Not Reachable

Symptoms:
- LLM requests time out or fail on startup.

Fixes:
- Ensure `ollama serve` is running.
- Verify `OLLAMA_BASE_URL` in `backend/.env`.
- Pull the configured model (example: `ollama pull llama3.1:8b`).

## Next.js Dev Server Fails

Symptoms:
- `npm run dev` exits or hangs on startup.

Fixes:
- Use Node.js 20+.
- Delete and reinstall `frontend/node_modules` if lockfile drift occurs.
- Confirm `NEXT_PUBLIC_API_URL` points to the backend.

## TTS Generation Fails

Symptoms:
- Audio files are missing or generation steps fail.

Fixes:
- Ensure `edge-tts` is installed in the backend environment.
- Confirm `TTS_VOICE_*` values are valid for your locale.
- Validate that the host can reach the edge-tts service.

## FFmpeg Not Found

Symptoms:
- Video assembly fails or the final video is missing.

Fixes:
- Install FFmpeg and make sure it is in your PATH.

## Upload or Processing Errors

Symptoms:
- HTTP 400 errors or job fails immediately.

Fixes:
- Verify that `mode` matches the file type (`ppt`, `pdf`, `policy`).
- Check `MAX_FILE_SIZE_MB` in `backend/.env` and update if needed.
- Inspect backend logs for pipeline-specific errors.
