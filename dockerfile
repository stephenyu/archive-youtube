FROM python:3.13.2-slim-bullseye

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY web.py .
COPY youtube_archiver.py .
COPY templates/ templates/
COPY static/ static/

# Create directories that will be mounted
RUN mkdir -p /app/config /app/youtube_archive

# Expose port
EXPOSE 8899

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "web.py"]
