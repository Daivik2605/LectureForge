# Pipelines

## Overview

The backend selects a pipeline based on `mode` (`ppt`, `pdf`, `policy`, or `auto`). The PPT and PDF pipelines share the same overall structure but differ in how they extract and structure content before narration.

## PPT Pipeline (Slides → Narration → Video)

1. Parse PPT/PPTX slides (`ppt_parser.py`).
2. Filter slides with text content.
3. For each slide:
   - Generate or load narration (cache).
   - Optionally generate MCQs.
   - Render slide image, synthesize audio, and create a clip.
4. Stitch clips into `storage/outputs/{job_id}/final.mp4`.

Notes:
- Narration caching lives in `data/cache/narrations`.
- Slides without text are skipped by default.

## PDF Pipeline (Pages → Summary → Narration → Video)

1. Extract page text with `pdfminer.six`.
2. Summarize each page into `title`, `bullets`, and `narration`.
3. Optionally generate MCQs per page.
4. Render summary text to images, synthesize narration, and create clips.
5. Stitch clips into `storage/outputs/{job_id}/final.mp4`.

Notes:
- Summary quality depends on text extraction quality.
- Scanned PDFs usually require OCR for good results.

## Policy Mode (Long-Form PDF/TXT)

Policy mode (`mode=policy`) chunks large documents into chapters, generates narration per chunk, and stitches a continuous video.

Use cases:
- Long policy documents or manuals.
- PDF/TXT inputs where slide-level granularity is less important.
