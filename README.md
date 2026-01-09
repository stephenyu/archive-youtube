# YouTube Archiver

A self-hosted web application and Python library to archive your favorite YouTube playlists and videos locally. This tool ensures you have offline access to content by automatically syncing and downloading videos from specified playlists.

## Features

- **Playlist Management:** Easily add and track multiple YouTube playlists.
- **Video Archiving:** Downloads videos using `yt-dlp` with configurable quality settings (defaults to 1080p).
- **Web Interface:** A clean, user-friendly dashboard to manage playlists, view download progress, and watch archived videos.
- **Automatic Syncing:** Schedule background tasks to keep your local archive up-to-date with new uploads.
- **Storage Stats:** Monitor disk usage and video counts per playlist.
- **CLI Support:** Includes a command-line interface for scripting and headless operations.
- **Docker Support:** Ready-to-use Docker configuration for easy deployment.

## Key Software & Dependencies

This project relies on the following key open-source technologies:

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp):** The powerful command-line media downloader used to fetch videos and metadata.
- **[Flask](https://flask.palletsprojects.com/):** A lightweight WSGI web application framework for the user interface.
- **[Schedule](https://schedule.readthedocs.io/):** For handling periodic background synchronization tasks.
- **[Humanize](https://github.com/jmoiron/humanize):** To provide human-readable data (e.g., file sizes).
- **Docker:** For containerized application deployment.

## Installation & Usage

### Option 1: Docker (Recommended)

The easiest way to run the application is using Docker Compose.

1.  Clone the repository and navigate to the directory.
2.  Start the container:
    ```bash
    docker-compose up -d --build
    ```
3.  Access the web interface at: `http://localhost:8899`

**Data Persistence:**
-   Configuration files (databases, settings) are stored in `./config`
-   Downloaded videos are stored in `./youtube_archive`

### Option 2: Manual Installation (Python)

If you prefer to run it directly on your machine:

1.  **Prerequisites:** Ensure you have Python 3.13+ installed.
2.  **Install Dependencies:**
    It is recommended to use [uv](https://github.com/astral-sh/uv) for dependency management.
    ```bash
    # Install uv (if not already installed)
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Sync dependencies
    uv sync
    ```

    Alternatively, using standard pip:
    ```bash
    pip install .
    ```
3.  **Run the Web Application:**
    If using `uv`:
    ```bash
    uv run web.py
    ```
    
    If using standard python:
    ```bash
    python web.py
    ```
    Open your browser to `http://localhost:8899`.

4.  **CLI Usage:**
    You can also use the `youtube_archiver.py` script directly:
    ```bash
    # Add a playlist
    uv run youtube_archiver.py --add-playlist "https://www.youtube.com/playlist?list=PLAYLIST_ID"
    # or: python youtube_archiver.py ...

    # Sync a specific playlist
    python youtube_archiver.py --sync "PLAYLIST_ID"

    # Sync all playlists
    python youtube_archiver.py --sync-all

    # View stats
    python youtube_archiver.py --stats
    ```

## Configuration

You can adjust settings via the **Settings** page in the web interface or by manually editing `config/config.json`:

-   **Download Directory:** Path where videos are saved.
-   **Max Quality:** Format selector for `yt-dlp` (e.g., `bestvideo[height<=1080]+bestaudio/best`).
-   **Concurrent Downloads:** Number of simultaneous downloads (currently limited to 1 for stability).
-   **Auto Sync:** Enable/disable background syncing.
-   **Sync Interval:** Frequency of checks (in hours).

## License

This project is open-source. Please ensure you comply with YouTube's Terms of Service when downloading content.
