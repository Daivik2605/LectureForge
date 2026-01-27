FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libreoffice \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory to where the 'app' folder will live
WORKDIR /app

# Copy the requirements and install them
COPY backend/requirements/requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

# Copy the contents of your backend folder (which contains 'app') into /app
# This places /app/app/... and /app/main.py in the correct spots
COPY backend/ .

# Set PYTHONPATH to the current directory
ENV PYTHONPATH=/app

EXPOSE 8000

# Start uvicorn pointing to the main app module
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]