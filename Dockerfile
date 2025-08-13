# Use Python 3.11 for better performance
FROM python:3.11-slim

# Install system dependencies for ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Create work directory
WORKDIR /app

# Copy dependencies first
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Create output folder
RUN mkdir -p /app/processed_videos

# Expose FastAPI port
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
