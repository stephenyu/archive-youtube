#!/usr/bin/env python3
"""
YouTube Archiver Web Interface

This web application provides a user interface for:
1. Managing YouTube playlists to archive
2. Viewing downloaded videos
3. Syncing playlists manually or automatically
4. Viewing storage statistics

Requirements:
- flask
- schedule
- youtube_archiver

Usage:
    python -m youtube_archiver.app
    # Then open a browser to http://localhost:8899
"""

import os
import time
import json
import threading
import schedule
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from .core import YouTubeArchiver

# Configuration
CONFIG_DIR = os.path.abspath("./config")
DOWNLOAD_DIR = os.path.abspath("./youtube_archive")
DEFAULT_PORT = 8899
TEMPLATES_DIR = os.path.abspath("./templates")
STATIC_DIR = os.path.abspath("./static")

# Create necessary directories
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Initialize Flask app
app = Flask(__name__, 
            template_folder=os.path.abspath(TEMPLATES_DIR),
            static_folder=os.path.abspath(STATIC_DIR))
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Configure application to work in a subdirectory
# Use BASENAME as our environment variable for the URL prefix
app.config['APPLICATION_ROOT'] = os.environ.get('BASENAME', '')

# Fix Flask to work with proxied apps in subdirectories
class PrefixMiddleware:
    def __init__(self, app, prefix=''):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        if self.prefix:
            environ['SCRIPT_NAME'] = self.prefix
            path_info = environ['PATH_INFO']
            if path_info.startswith(self.prefix):
                environ['PATH_INFO'] = path_info[len(self.prefix):]
        return self.app(environ, start_response)

# Apply prefix middleware immediately if running in a subdirectory
prefix = app.config['APPLICATION_ROOT']
if prefix:
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix=prefix)
    print(f"Running with prefix: {prefix}")

# Initialize YouTube Archiver
archiver = YouTubeArchiver(config_dir=CONFIG_DIR, download_dir=DOWNLOAD_DIR)

# Global variables for sync status
sync_status = {
    "is_syncing": False,
    "current_task": "",
    "progress": 0,
    "last_run": None
}

# Flag to track if scheduler is running
scheduler_running = False

def update_sync_status(task, progress):
    """Update the sync status for display in the UI"""
    sync_status["current_task"] = task
    sync_status["progress"] = progress

def schedule_sync():
    """Schedule automatic syncing based on configuration"""
    if archiver.config.get("auto_sync", False):
        interval = archiver.config.get("sync_interval", 24)
        sync_time = archiver.config.get("sync_time", "00:00")
        
        def run_sync():
            """Run the sync operation"""
            if not sync_status["is_syncing"]:
                print(f"Running scheduled sync at {datetime.now().isoformat()}")
                sync_all_playlists()
        
        # Clear existing schedule
        schedule.clear()
        
        # Add daily schedule at specific time
        if interval == 24:
            # Parse hours and minutes from sync_time
            try:
                hours, minutes = map(int, sync_time.split(':'))
                schedule.every().day.at(sync_time).do(run_sync)
                print(f"Scheduled automatic sync daily at {sync_time}")
            except ValueError:
                # Fall back to interval-based if time format is invalid
                schedule.every(interval).hours.do(run_sync)
                print(f"Scheduled automatic sync every {interval} hours (invalid time format)")
        else:
            # For non-daily intervals, continue with hour-based scheduling
            schedule.every(interval).hours.do(run_sync)
            print(f"Scheduled automatic sync every {interval} hours")

def run_scheduler():
    """Run the scheduler in a background thread"""
    global scheduler_running
    scheduler_running = True
    print("Scheduler thread started")
    
    while True:
        try:
            pending_jobs = schedule.get_jobs()
            if pending_jobs:
                next_job = min((job.next_run, job) for job in pending_jobs)[1]
                print(f"Next scheduled job will run at: {next_job.next_run}")
            
            schedule.run_pending()
        except Exception as e:
            print(f"Error in scheduler: {str(e)}")
        
        time.sleep(60)

def sync_all_playlists():
    """Sync all playlists with progress reporting"""
    if sync_status["is_syncing"]:
        return {"status": "error", "message": "Sync already in progress"}
    
    def run_sync():
        """Run the sync operation in a thread"""
        sync_status["is_syncing"] = True
        try:
            print(f"Starting sync of all playlists at {datetime.now().isoformat()}")
            results = archiver.sync_all_playlists(callback=update_sync_status)
            
            success_count = sum(1 for r in results if r["success"])
            sync_status["current_task"] = f"Completed: {success_count}/{len(results)} playlists synced"
            sync_status["last_run"] = datetime.now().isoformat()
            print(f"Completed sync of all playlists at {datetime.now().isoformat()}")
        except Exception as e:
            sync_status["current_task"] = f"Error: {str(e)}"
            print(f"Error syncing playlists: {str(e)}")
        finally:
            sync_status["is_syncing"] = False
    
    # Start sync in a background thread
    thread = threading.Thread(target=run_sync)
    thread.daemon = True  # Make thread a daemon so it exits when main thread exits
    thread.start()
    
    return {"status": "success", "message": "Started syncing all playlists"}

def sync_playlist(playlist_id):
    """Sync a specific playlist with progress reporting"""
    if sync_status["is_syncing"]:
        return {"status": "error", "message": "Sync already in progress"}
    
    if playlist_id not in archiver.playlists:
        return {"status": "error", "message": "Playlist not found"}
    
    def run_sync():
        """Run the sync operation in a thread"""
        sync_status["is_syncing"] = True
        try:
            result = archiver.sync_playlist(playlist_id, callback=update_sync_status)
            
            if result["success"]:
                sync_status["current_task"] = f"Completed: {result['new_videos']} new videos downloaded"
            else:
                sync_status["current_task"] = f"Error: {result['error']}"
                
            sync_status["last_run"] = datetime.now().isoformat()
        except Exception as e:
            sync_status["current_task"] = f"Error: {str(e)}"
        finally:
            sync_status["is_syncing"] = False
    
    # Start sync in a background thread
    thread = threading.Thread(target=run_sync)
    thread.daemon = True  # Make thread a daemon so it exits when main thread exits
    thread.start()
    
    return {"status": "success", "message": f"Started syncing: {archiver.playlists[playlist_id]['title']}"}

# Route handlers
@app.route('/')
def index():
    """Home page with dashboard"""
    stats = archiver.get_storage_stats()
    return render_template('index.html', 
                          playlists=archiver.playlists,
                          stats=stats,
                          sync_status=sync_status)

@app.route('/playlists')
def playlists():
    """Playlists management page"""
    return render_template('playlists.html',
                          playlists=archiver.playlists,
                          sync_status=sync_status)

@app.route('/playlist/<playlist_id>')
def playlist_detail(playlist_id):
    """Playlist detail page with videos"""
    if playlist_id not in archiver.playlists:
        return redirect(url_for('playlists'))
    
    playlist = archiver.playlists[playlist_id]
    stats = archiver.get_playlist_storage_stats(playlist_id)
    
    # Get videos in this playlist
    playlist_videos = {vid_id: vid_info for vid_id, vid_info in archiver.downloaded_videos.items() 
                      if vid_info.get('playlist_id') == playlist_id}
    
    # Get videos not yet downloaded
    missing_videos = archiver.get_missing_videos(playlist_id)
    
    return render_template('playlist_detail.html',
                          playlist=playlist,
                          stats=stats,
                          videos=playlist_videos,
                          missing_videos=missing_videos,
                          sync_status=sync_status)

@app.route('/videos')
def videos():
    """All videos page"""
    return render_template('videos.html',
                          videos=archiver.downloaded_videos,
                          sync_status=sync_status)

@app.route('/add_playlist', methods=['GET', 'POST'])
def add_playlist():
    """Add a new playlist"""
    error = None
    
    if request.method == 'POST':
        playlist_url = request.form.get('playlist_url', '').strip()
        
        if playlist_url:
            playlist_id = archiver.add_playlist(playlist_url)
            
            if playlist_id:
                return redirect(url_for('playlist_detail', playlist_id=playlist_id))
            else:
                error = "Failed to add playlist. Please check the URL."
    
    return render_template('add_playlist.html',
                          error=error,
                          sync_status=sync_status)

@app.route('/remove_playlist/<playlist_id>', methods=['POST'])
def remove_playlist(playlist_id):
    """Remove a playlist"""
    archiver.remove_playlist(playlist_id)
    return redirect(url_for('playlists'))

@app.route('/sync_all', methods=['POST'])
def handle_sync_all():
    """API endpoint to sync all playlists"""
    result = sync_all_playlists()
    return jsonify(result)

@app.route('/sync_playlist/<playlist_id>', methods=['POST'])
def handle_sync_playlist(playlist_id):
    """API endpoint to sync a specific playlist"""
    result = sync_playlist(playlist_id)
    return jsonify(result)

@app.route('/watch/<video_id>')
def watch_video(video_id):
    """Watch a downloaded video"""
    print(f"DEBUG: Requested watch page for video_id: {video_id}")
    if video_id not in archiver.downloaded_videos:
        print(f"DEBUG: Video ID {video_id} not found in database.")
        return redirect(url_for('videos'))
    
    video_info = archiver.downloaded_videos[video_id]
    video_file = archiver.find_video_file(video_id)
    
    print(f"DEBUG: Video info: {video_info}")
    print(f"DEBUG: Video file resolved to: {video_file}")
    
    if not video_file:
        print(f"DEBUG: Video file not found on disk for ID {video_id}")
        return redirect(url_for('videos'))
    
    return render_template('watch.html',
                          video=video_info,
                          video_id=video_id,  # Pass video_id explicitly for the delete form
                          video_path=os.path.basename(video_file),
                          sync_status=sync_status)

@app.route('/video/<path:filename>')
def serve_video(filename):
    """Serve a video file"""
    full_path = os.path.join(os.path.abspath(archiver.download_dir), filename)
    print(f"DEBUG: Serving video file: {filename}")
    print(f"DEBUG: Full path: {full_path}")
    
    if not os.path.exists(full_path):
        print(f"ERROR: File not found at {full_path}")
        print(f"DEBUG: filename repr: {repr(filename)}")
        try:
            print(f"DEBUG: listing of {archiver.download_dir}:")
            for f in os.listdir(archiver.download_dir):
                print(f"  - {f} (repr: {repr(f)})")
        except Exception as e:
            print(f"ERROR listing directory: {e}")

    return send_from_directory(os.path.abspath(archiver.download_dir), filename)

@app.route('/status')
def get_status():
    """API endpoint to get current sync status"""
    return jsonify(sync_status)

@app.route('/delete_video/<video_id>', methods=['POST'])
def delete_video(video_id):
    """Delete a video from the archive"""
    if video_id not in archiver.downloaded_videos:
        return redirect(url_for('videos'))
    
    # Store the playlist ID before deleting for redirection
    video_info = archiver.downloaded_videos[video_id]
    playlist_id = video_info.get('playlist_id')
    
    success = archiver.delete_video(video_id)
    
    # Redirect to the appropriate page
    if success:
        if playlist_id and playlist_id in archiver.playlists:
            return redirect(url_for('playlist_detail', playlist_id=playlist_id))
        else:
            return redirect(url_for('videos'))
    else:
        # In case of failure, still redirect to videos page
        return redirect(url_for('videos'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Settings page"""
    if request.method == 'POST':
        # Update settings
        new_config = {
            "download_dir": request.form.get('download_dir', DOWNLOAD_DIR),
            "max_quality": request.form.get('max_quality', "bestvideo[height<=1080]+bestaudio/best[height<=1080]"),
            "concurrent_downloads": int(request.form.get('concurrent_downloads', 1)),
            "auto_sync": 'auto_sync' in request.form,
            "sync_interval": int(request.form.get('sync_interval', 24)),
            "sync_time": request.form.get('sync_time', "00:00")
        }
        
        archiver.update_config(new_config)
        
        # Update the schedule
        schedule_sync()
        
        # Start the scheduler thread if auto_sync is enabled and not already running
        if new_config["auto_sync"] and not scheduler_running:
            start_background_tasks()
        
        return redirect(url_for('settings'))
    
    return render_template('settings.html',
                          config=archiver.config,
                          sync_status=sync_status)

def start_background_tasks():
    """Start background tasks like scheduler"""
    global scheduler_running
    
    # Only start if not already running
    if scheduler_running:
        print("Scheduler already running, skipping")
        return
        
    # Schedule jobs
    if archiver.config.get("auto_sync", False):
        schedule_sync()
        
        # Start scheduler thread
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.daemon = True  # Make thread a daemon so it exits when main thread exits
        scheduler_thread.start()
        
        print("Started scheduler thread")

# Initialize background tasks when the module is loaded
start_background_tasks()

def main():
    port = int(os.environ.get('PORT', DEFAULT_PORT))
    app.run(debug=False, host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()
