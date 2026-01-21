# Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libreoffice \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY backend/requirements/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application code
COPY backend /app/backend

# Create runtime directories
RUN mkdir -p \
    /app/backend/data/uploads \
    /app/backend/data/audio \
    /app/backend/data/images \
    /app/backend/data/videos \
    /app/backend/data/final_videos \
    /app/backend/data/cache/narrations \
    /app/backend/storage/uploads \
    /app/backend/storage/outputs \
    /app/backend/storage/temp \
    /app/backend/logs

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
