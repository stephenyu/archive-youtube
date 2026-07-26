FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# yt-dlp needs a JavaScript runtime to solve YouTube's JS challenges
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY README.md .
COPY src/ src/

# Install dependencies and the application
RUN uv pip install --system --no-cache .

# Copy assets
COPY templates/ templates/
COPY static/ static/

# Create directories that will be mounted
RUN mkdir -p /app/config /app/youtube_archive

# Expose port
EXPOSE 8899

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["youtube-archiver-web"]