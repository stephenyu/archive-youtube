"""
YouTube Archiver CLI

Command-line interface for the YouTube Archiver.
"""

import argparse
from .core import YouTubeArchiver

def main():
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

if __name__ == "__main__":
    main()
