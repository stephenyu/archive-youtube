#!/usr/bin/env python3
"""
YouTube Archiver Library

This module provides core functionality for:
1. Scanning YouTube playlists
2. Downloading videos using yt-dlp
3. Managing a local database of playlists and videos
4. Calculating storage statistics

Requirements:
- yt-dlp
- humanize

Usage:
    from youtube_archiver import YouTubeArchiver
    archiver = YouTubeArchiver(download_dir="./videos")
    archiver.add_playlist("https://www.youtube.com/playlist?list=PLAYLIST_ID")
    archiver.sync_playlist("PLAYLIST_ID")
"""

import os
import json
import glob
from datetime import datetime
import yt_dlp
import humanize

class YouTubeArchiver:
    def __init__(self, config_dir="./config", download_dir="./youtube_archive"):
        """Initialize YouTube Archiver with configuration"""
        self.config_dir = config_dir
        self.download_dir = download_dir
        self.playlists_file = os.path.join(config_dir, "playlists.json")
        self.videos_file = os.path.join(config_dir, "downloaded_videos.json")
        self.config_file = os.path.join(config_dir, "config.json")
        
        # Create necessary directories
        os.makedirs(config_dir, exist_ok=True)
        os.makedirs(download_dir, exist_ok=True)
        
        # Load configuration and data
        self.config = self._load_config()
        self.playlists = self._load_playlists()
        self.downloaded_videos = self._load_downloaded_videos()
        
    def _load_config(self):
        """Load application configuration"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            # Default configuration
            config = {
                "download_dir": self.download_dir,
                "max_quality": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "concurrent_downloads": 1,
                "auto_sync": False,
                "sync_interval": 24,  # hours
                "sync_time": "00:00"  # Default to midnight
            }
            self._save_config(config)
            return config
    
    def _save_config(self, config=None):
        """Save application configuration"""
        if config is not None:
            self.config = config
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def _load_playlists(self):
        """Load playlist data"""
        if os.path.exists(self.playlists_file):
            with open(self.playlists_file, 'r') as f:
                return json.load(f)
        else:
            # Empty playlists dictionary
            playlists = {}
            self._save_playlists(playlists)
            return playlists
    
    def _save_playlists(self, playlists=None):
        """Save playlist data"""
        if playlists is not None:
            self.playlists = playlists
        with open(self.playlists_file, 'w') as f:
            json.dump(self.playlists, f, indent=2)
    
    def _load_downloaded_videos(self):
        """Load downloaded videos data"""
        if os.path.exists(self.videos_file):
            with open(self.videos_file, 'r') as f:
                return json.load(f)
        else:
            # Empty videos dictionary
            videos = {}
            self._save_downloaded_videos(videos)
            return videos
    
    def _save_downloaded_videos(self, videos=None):
        """Save downloaded videos data"""
        if videos is not None:
            self.downloaded_videos = videos
        with open(self.videos_file, 'w') as f:
            json.dump(self.downloaded_videos, f, indent=2)
    
    def get_playlist_info(self, playlist_url):
        """Extract information about a playlist using yt-dlp"""
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'skip_download': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                return {
                    "id": playlist_info.get('id', ''),
                    "title": playlist_info.get('title', 'Unknown Playlist'),
                    "uploader": playlist_info.get('uploader', 'Unknown'),
                    "url": playlist_url,
                    "video_count": len(playlist_info.get('entries', [])),
                    "last_synced": None
                }
        except Exception as e:
            print(f"Error extracting playlist info: {str(e)}")
            return None
    
    def add_playlist(self, playlist_url):
        """Add a playlist to the archiver"""
        playlist_info = self.get_playlist_info(playlist_url)
        if playlist_info:
            self.playlists[playlist_info['id']] = playlist_info
            self._save_playlists()
            return playlist_info['id']
        return None
    
    def remove_playlist(self, playlist_id):
        """Remove a playlist from the archiver"""
        if playlist_id in self.playlists:
            del self.playlists[playlist_id]
            self._save_playlists()
            return True
        return False
    
    def get_playlist_videos(self, playlist_url):
        """Get all videos in a playlist"""
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_dict = ydl.extract_info(playlist_url, download=False)
            videos = playlist_dict.get('entries', [])
        
        return videos
    
    def download_video(self, video_id, video_title, playlist_id=None):
        """Download a single video using yt-dlp"""
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        output_template = os.path.join(self.download_dir, '%(title)s-%(id)s.%(ext)s')
        
        ydl_opts = {
            'format': self.config.get("max_quality", "bestvideo[height<=1080]+bestaudio/best[height<=1080]"),
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            'concurrent_fragment_downloads': 5,
            'throttledratelimit': 100000,  # 100KB/s minimum
            'merge_output_format': 'mp4',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            # Update the database with download information
            self.downloaded_videos[video_id] = {
                "title": video_title,
                "downloaded_at": datetime.now().isoformat(),
                "url": video_url,
                "playlist_id": playlist_id
            }
            self._save_downloaded_videos()
            return True
        except Exception as e:
            print(f"Error downloading {video_title}: {str(e)}")
            return False
    
    def sync_playlist(self, playlist_id, callback=None):
        """Sync a playlist, downloading any new videos
        
        Args:
            playlist_id: ID of the playlist to sync
            callback: Optional function(current_task, progress) to report progress
        
        Returns:
            dict: A summary of the sync operation
        """
        if playlist_id not in self.playlists:
            return {"success": False, "error": "Playlist not found"}
        
        playlist = self.playlists[playlist_id]
        
        if callback:
            callback(f"Syncing playlist: {playlist['title']}", 0)
        
        try:
            # Get videos in the playlist
            videos = self.get_playlist_videos(playlist["url"])
            
            total_videos = len(videos)
            new_videos = 0
            
            for index, video in enumerate(videos):
                video_id = video['id']
                title = video.get('title', f"Video {video_id}")
                
                if callback:
                    callback(f"Processing: {title}", int((index / total_videos) * 100))
                
                if video_id not in self.downloaded_videos:
                    print(f"New video found: {title}")
                    if self.download_video(video_id, title, playlist_id):
                        new_videos += 1
                else:
                    print(f"Already downloaded: {title}")
            
            # Update playlist information
            self.playlists[playlist_id]["last_synced"] = datetime.now().isoformat()
            self.playlists[playlist_id]["video_count"] = total_videos
            self._save_playlists()
            
            if callback:
                callback(f"Finished syncing {playlist['title']}", 100)
            
            result = {
                "success": True,
                "playlist_id": playlist_id,
                "playlist_title": playlist["title"],
                "total_videos": total_videos,
                "new_videos": new_videos,
                "completed_at": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            error_msg = f"Error syncing playlist {playlist['title']}: {str(e)}"
            print(error_msg)
            
            if callback:
                callback(f"Error: {str(e)}", 0)
            
            return {"success": False, "error": error_msg}
    
    def sync_all_playlists(self, callback=None):
        """Sync all playlists
        
        Args:
            callback: Optional function(current_task, progress) to report progress
        
        Returns:
            list: Results of all sync operations
        """
        results = []
        
        for playlist_id in self.playlists:
            if callback:
                callback(f"Starting sync of playlist: {self.playlists[playlist_id]['title']}", 0)
            
            result = self.sync_playlist(playlist_id, callback)
            results.append(result)
        
        return results
    
    def get_storage_stats(self):
        """Get storage statistics for downloaded videos"""
        if not os.path.exists(self.download_dir):
            return {
                "total_size": 0,
                "total_size_human": "0 B",
                "video_count": 0,
                "average_size": 0,
                "average_size_human": "0 B"
            }
        
        total_size = 0
        file_extensions = ['.mp4', '.webm', '.mkv', '.m4a', '.mp3']
        video_files = []
        
        for ext in file_extensions:
            video_files.extend(glob.glob(os.path.join(self.download_dir, f"*{ext}")))
        
        for file_path in video_files:
            total_size += os.path.getsize(file_path)
        
        video_count = len(video_files)
        average_size = total_size / video_count if video_count > 0 else 0
        
        return {
            "total_size": total_size,
            "total_size_human": humanize.naturalsize(total_size),
            "video_count": video_count,
            "average_size": average_size,
            "average_size_human": humanize.naturalsize(average_size)
        }
    
    def find_video_file(self, video_id):
        """Find the file path for a downloaded video"""
        file_extensions = ['.mp4', '.webm', '.mkv', '.m4a', '.mp3']
        
        for ext in file_extensions:
            video_files = glob.glob(os.path.join(self.download_dir, f"*{video_id}*{ext}"))
            if video_files:
                return video_files[0]  # Return the first matching file
        
        return None
    
    def get_missing_videos(self, playlist_id):
        """Get list of videos in a playlist that haven't been downloaded yet"""
        if playlist_id not in self.playlists:
            return []
        
        playlist = self.playlists[playlist_id]
        videos = self.get_playlist_videos(playlist["url"])
        
        missing_videos = []
        for video in videos:
            video_id = video['id']
            if video_id not in self.downloaded_videos:
                missing_videos.append(video)
        
        return missing_videos
    
    def get_playlist_storage_stats(self, playlist_id):
        """Get storage statistics for a specific playlist"""
        if playlist_id not in self.playlists:
            return None
        
        total_size = 0
        video_count = 0
        
        # Get all videos from this playlist
        playlist_videos = [vid_id for vid_id, vid_info in self.downloaded_videos.items() 
                          if vid_info.get('playlist_id') == playlist_id]
        
        for video_id in playlist_videos:
            video_file = self.find_video_file(video_id)
            if video_file:
                total_size += os.path.getsize(video_file)
                video_count += 1
        
        return {
            "total_size": total_size,
            "total_size_human": humanize.naturalsize(total_size),
            "video_count": video_count,
            "playlist_title": self.playlists[playlist_id]["title"]
        }
    
    def update_config(self, new_config):
        """Update the configuration"""
        self.config.update(new_config)
        self._save_config()
        
        # Update download directory if needed
        if "download_dir" in new_config:
            self.download_dir = new_config["download_dir"]
            os.makedirs(self.download_dir, exist_ok=True)
        
        return self.config

    def delete_video(self, video_id):
        """Delete a video from the archive

        Args:
            video_id: ID of the video to delete

        Returns:
            bool: True if successfully deleted, False otherwise
        """
        if video_id not in self.downloaded_videos:
            return False

        try:
            # Find the video file
            video_file = self.find_video_file(video_id)

            if video_file and os.path.exists(video_file):
                # Delete the actual file
                os.remove(video_file)

            # Remove from the downloaded videos database
            del self.downloaded_videos[video_id]
            self._save_downloaded_videos()

            return True
        except Exception as e:
            print(f"Error deletin

# If script is run directly, provide command-line functionality
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube Playlist Archiver")
    parser.add_argument("--add-playlist", help="Add a playlist URL to archive")
    parser.add_argument("--sync", help="Sync a playlist by ID", metavar="PLAYLIST_ID")
    parser.add_argument("--sync-all", action="store_true", help="Sync all playlists")
    parser.add_argument("--list", action="store_true", help="List all playlists")
    parser.add_argument("--stats", action="store_true", help="Show storage statistics")
    parser.add_argument("--config-dir", default="./config", help="Configuration directory")
    parser.add_argument("--download-dir", help="Download directory")
    args = parser.parse_args()
    
    archiver = YouTubeArchiver(config_dir=args.config_dir)
    
    if args.download_dir:
        archiver.update_config({"download_dir": args.download_dir})
    
    if args.add_playlist:
        playlist_id = archiver.add_playlist(args.add_playlist)
        if playlist_id:
            print(f"Added playlist: {archiver.playlists[playlist_id]['title']} (ID: {playlist_id})")
        else:
            print("Failed to add playlist")
    
    if args.sync:
        print(f"Syncing playlist {args.sync}...")
        result = archiver.sync_playlist(args.sync, 
                                       callback=lambda task, progress: print(f"{task} - {progress}%"))
        if result["success"]:
            print(f"Sync completed: {result['new_videos']} new videos downloaded")
        else:
            print(f"Sync failed: {result['error']}")
    
    if args.sync_all:
        print("Syncing all playlists...")
        results = archiver.sync_all_playlists(
            callback=lambda task, progress: print(f"{task} - {progress}%"))
        
        success_count = sum(1 for r in results if r["success"])
        print(f"Sync completed: {success_count}/{len(results)} playlists synced successfully")
    
    if args.list:
        print("Your playlists:")
        for playlist_id, playlist in archiver.playlists.items():
            print(f"- {playlist['title']} (ID: {playlist_id})")
            print(f"  Videos: {playlist['video_count']}")
            print(f"  Last synced: {playlist['last_synced'] or 'Never'}")
            print()
    
    if args.stats:
        stats = archiver.get_storage_stats()
        print("Storage Statistics:")
        print(f"Total videos: {stats['video_count']}")
        print(f"Total storage used: {stats['total_size_human']}")
        if stats['video_count'] > 0:
            print(f"Average video size: {stats['average_size_human']}")
