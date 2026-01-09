import os
import json
import pytest
from unittest.mock import MagicMock, patch
from youtube_archiver import YouTubeArchiver

@pytest.fixture
def archiver(tmp_path):
    config_dir = tmp_path / "config"
    download_dir = tmp_path / "downloads"
    return YouTubeArchiver(config_dir=str(config_dir), download_dir=str(download_dir))

def test_init(archiver, tmp_path):
    assert os.path.exists(archiver.config_dir)
    assert os.path.exists(archiver.download_dir)
    assert os.path.exists(archiver.playlists_file)
    assert os.path.exists(archiver.videos_file)
    assert os.path.exists(archiver.config_file)
    assert archiver.playlists == {}
    assert archiver.downloaded_videos == {}

def test_add_playlist(archiver):
    with patch('yt_dlp.YoutubeDL') as mock_ydl:
        mock_instance = mock_ydl.return_value
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.extract_info.return_value = {
            'id': 'PL123',
            'title': 'Test Playlist',
            'uploader': 'Test Uploader',
            'entries': [1, 2, 3]
        }

        playlist_id = archiver.add_playlist('https://youtube.com/playlist?list=PL123')
        
        assert playlist_id == 'PL123'
        assert 'PL123' in archiver.playlists
        assert archiver.playlists['PL123']['title'] == 'Test Playlist'
        assert archiver.playlists['PL123']['video_count'] == 3

def test_remove_playlist(archiver):
    # Setup initial state
    archiver.playlists = {'PL123': {'title': 'Test Playlist'}}
    archiver._save_playlists()
    
    result = archiver.remove_playlist('PL123')
    
    assert result is True
    assert 'PL123' not in archiver.playlists
    
    result = archiver.remove_playlist('NONEXISTENT')
    assert result is False

def test_download_video(archiver):
    with patch('yt_dlp.YoutubeDL') as mock_ydl:
        mock_instance = mock_ydl.return_value
        mock_instance.__enter__.return_value = mock_instance
        
        # Determine expected file path
        # archiver.download_dir is a string from str(tmp_path / "downloads")
        # In download_video, os.path.join(self.download_dir, '%(title)s-%(id)s.%(ext)s') is used as template
        # However, we can't easily verify the file creation unless we mock os.path.exists or similar if we want to be strict,
        # but the method primarily calls ydl.download and updates DB.
        
        result = archiver.download_video('vid123', 'Test Video', 'PL123')
        
        assert result is True
        assert 'vid123' in archiver.downloaded_videos
        assert archiver.downloaded_videos['vid123']['title'] == 'Test Video'
        mock_instance.download.assert_called_once()

def test_sync_playlist(archiver):
    # Setup playlist
    archiver.playlists = {'PL123': {'title': 'Test Playlist', 'url': 'http://url'}}
    archiver._save_playlists()
    
    with patch('yt_dlp.YoutubeDL') as mock_ydl:
        mock_instance = mock_ydl.return_value
        mock_instance.__enter__.return_value = mock_instance
        
        # Mock extract_info for get_playlist_videos
        mock_instance.extract_info.return_value = {
            'entries': [
                {'id': 'vid1', 'title': 'Video 1'},
                {'id': 'vid2', 'title': 'Video 2'}
            ]
        }
        
        # Mock download for download_video
        mock_instance.download.return_value = None
        
        result = archiver.sync_playlist('PL123')
        
        assert result['success'] is True
        assert result['new_videos'] == 2
        assert 'vid1' in archiver.downloaded_videos
        assert 'vid2' in archiver.downloaded_videos
        assert archiver.playlists['PL123']['video_count'] == 2

def test_sync_playlist_not_found(archiver):
    result = archiver.sync_playlist('NONEXISTENT')
    assert result['success'] is False

def test_delete_video(archiver):
    # Setup
    video_id = 'vid123'
    archiver.downloaded_videos = {
        video_id: {
            'title': 'Test Video', 
            'url': 'http://url', 
            'playlist_id': 'PL123'
        }
    }
    archiver._save_downloaded_videos()
    
    # Create a dummy file to simulate the video
    # Note: find_video_file searches for *video_id*
    # We create a dummy file in the download directory
    dummy_file = os.path.join(archiver.download_dir, f"Test Video-{video_id}.mp4")
    with open(dummy_file, 'w') as f:
        f.write("dummy content")
        
    assert os.path.exists(dummy_file)
    
    result = archiver.delete_video(video_id)
    
    assert result is True
    assert video_id not in archiver.downloaded_videos
    assert not os.path.exists(dummy_file)

def test_get_storage_stats(archiver):
    # Create dummy files
    f1 = os.path.join(archiver.download_dir, "video1.mp4")
    f2 = os.path.join(archiver.download_dir, "video2.mp4")
    
    with open(f1, 'wb') as f:
        f.write(b'0' * 1000) # 1000 bytes
    with open(f2, 'wb') as f:
        f.write(b'0' * 2000) # 2000 bytes
        
    stats = archiver.get_storage_stats()
    
    assert stats['video_count'] == 2
    assert stats['total_size'] == 3000

def test_update_config(archiver):
    initial_config = archiver.config.copy()
    new_config = {
        "sync_interval": 48,
        "max_quality": "worst",
        "download_dir": os.path.join(archiver.config_dir, "new_downloads")
    }
    
    archiver.update_config(new_config)
    
    # Check in-memory update
    assert archiver.config["sync_interval"] == 48
    assert archiver.config["max_quality"] == "worst"
    assert archiver.download_dir == new_config["download_dir"]
    
    # Check file persistence
    with open(archiver.config_file, 'r') as f:
        saved_config = json.load(f)
    
    assert saved_config["sync_interval"] == 48
    assert saved_config["max_quality"] == "worst"

def test_get_missing_videos(archiver):
    archiver.playlists = {'PL123': {'title': 'Test Playlist', 'url': 'http://url'}}
    archiver.downloaded_videos = {'vid1': {'title': 'Video 1'}}
    archiver._save_playlists()
    archiver._save_downloaded_videos()
    
    with patch('yt_dlp.YoutubeDL') as mock_ydl:
        mock_instance = mock_ydl.return_value
        mock_instance.__enter__.return_value = mock_instance
        
        # Mock returns 3 videos, one of which (vid1) is already downloaded
        mock_instance.extract_info.return_value = {
            'entries': [
                {'id': 'vid1', 'title': 'Video 1'},
                {'id': 'vid2', 'title': 'Video 2'},
                {'id': 'vid3', 'title': 'Video 3'}
            ]
        }
        
        missing = archiver.get_missing_videos('PL123')
        
        assert len(missing) == 2
        assert missing[0]['id'] == 'vid2'
        assert missing[1]['id'] == 'vid3'
        
        # Test nonexistent playlist
        assert archiver.get_missing_videos('NONEXISTENT') == []

def test_get_playlist_storage_stats(archiver):
    # Setup: 2 videos in PL1, 1 video in PL2
    archiver.playlists = {
        'PL1': {'title': 'Playlist 1'},
        'PL2': {'title': 'Playlist 2'}
    }
    
    archiver.downloaded_videos = {
        'v1': {'playlist_id': 'PL1'},
        'v2': {'playlist_id': 'PL1'},
        'v3': {'playlist_id': 'PL2'},
        'v4': {'playlist_id': 'PL1'} # This one won't have a file, simulating deleted file
    }
    
    # Create dummy files for v1, v2, v3
    # We need to mock find_video_file or create files that match what find_video_file looks for
    # find_video_file looks for *video_id* in download_dir
    
    f1 = os.path.join(archiver.download_dir, "Video 1-v1.mp4")
    f2 = os.path.join(archiver.download_dir, "Video 2-v2.mp4")
    f3 = os.path.join(archiver.download_dir, "Video 3-v3.mp4")
    
    with open(f1, 'wb') as f: f.write(b'0' * 100)
    with open(f2, 'wb') as f: f.write(b'0' * 200)
    with open(f3, 'wb') as f: f.write(b'0' * 300)
    
    stats_pl1 = archiver.get_playlist_storage_stats('PL1')
    
    assert stats_pl1['video_count'] == 2 # v4 is missing file
    assert stats_pl1['total_size'] == 300
    assert stats_pl1['playlist_title'] == 'Playlist 1'
    
    stats_pl2 = archiver.get_playlist_storage_stats('PL2')
    assert stats_pl2['video_count'] == 1
    assert stats_pl2['total_size'] == 300
    
    assert archiver.get_playlist_storage_stats('NONEXISTENT') is None

def test_add_playlist_failure(archiver):
    with patch('yt_dlp.YoutubeDL') as mock_ydl:
        mock_instance = mock_ydl.return_value
        mock_instance.__enter__.return_value = mock_instance
        # Simulate error
        mock_instance.extract_info.side_effect = Exception("Download error")
        
        result = archiver.add_playlist('http://bad-url')
        
        assert result is None
        assert archiver.playlists == {}

def test_download_video_failure(archiver):
    with patch('yt_dlp.YoutubeDL') as mock_ydl:
        mock_instance = mock_ydl.return_value
        mock_instance.__enter__.return_value = mock_instance
        # Simulate error during download
        mock_instance.download.side_effect = Exception("Download failed")
        
        result = archiver.download_video('vid1', 'Title')
        
        assert result is False
        assert 'vid1' not in archiver.downloaded_videos



