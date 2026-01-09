import pytest
from unittest.mock import MagicMock, patch
import sys
import threading

# We mock threading to prevent background tasks from actually starting during import if auto_sync is on
# and to control threading behavior in tests.
with patch('threading.Thread'):
    import web

@pytest.fixture
def client():
    web.app.config['TESTING'] = True
    with web.app.test_client() as client:
        yield client

@pytest.fixture
def mock_archiver():
    # Replace the global archiver instance in web.py with a mock
    original_archiver = web.archiver
    mock = MagicMock()
    web.archiver = mock
    
    # Setup some default return values for the mock
    mock.playlists = {}
    mock.downloaded_videos = {}
    mock.config = {"auto_sync": False}
    mock.get_storage_stats.return_value = {
        "total_size": 0, "total_size_human": "0 B", "video_count": 0, 
        "average_size_human": "0 B"
    }
    mock.get_playlist_storage_stats.return_value = {
        "total_size": 0, "total_size_human": "0 B", "video_count": 0
    }
    mock.get_missing_videos.return_value = []
    
    yield mock
    
    # Restore original
    web.archiver = original_archiver
    
    # Reset sync status
    web.sync_status = {
        "is_syncing": False,
        "current_task": "",
        "progress": 0,
        "last_run": None
    }

def test_index(client, mock_archiver):
    mock_archiver.playlists = {'PL1': {'title': 'My Playlist', 'id': 'PL1', 'video_count': 10, 'last_synced': '2023-01-01'}}
    response = client.get('/')
    assert response.status_code == 200
    assert b'YouTube Archive' in response.data
    # The index page shows the count of playlists, not the titles
    # Since we have 1 playlist in the mock, we might look for that if we wanted to be specific,
    # but checking for the title of the page is sufficient for a basic smoke test.

def test_add_playlist_success(client, mock_archiver):
    mock_archiver.add_playlist.return_value = 'PL123'
    response = client.post('/add_playlist', data={'playlist_url': 'http://url'})
    assert response.status_code == 302 # Redirect
    assert 'playlist/PL123' in response.headers['Location']
    mock_archiver.add_playlist.assert_called_with('http://url')

def test_add_playlist_failure(client, mock_archiver):
    mock_archiver.add_playlist.return_value = None
    response = client.post('/add_playlist', data={'playlist_url': 'http://bad-url'})
    assert response.status_code == 200
    assert b'Failed to add playlist' in response.data

def test_remove_playlist(client, mock_archiver):
    response = client.post('/remove_playlist/PL123')
    assert response.status_code == 302
    mock_archiver.remove_playlist.assert_called_with('PL123')

def test_sync_all_playlists(client, mock_archiver):
    # Mock threading.Thread to run the target immediately
    with patch('threading.Thread') as mock_thread:
        def side_effect(target=None, **kwargs):
            target() # Execute the sync function immediately
            return MagicMock() 
        mock_thread.side_effect = side_effect
        
        mock_archiver.sync_all_playlists.return_value = [{'success': True}]
        
        response = client.post('/sync_all')
        
        assert response.status_code == 200
        assert response.json['status'] == 'success'
        mock_archiver.sync_all_playlists.assert_called()

def test_sync_playlist(client, mock_archiver):
    mock_archiver.playlists = {'PL123': {'title': 'Test Playlist'}}
    
    with patch('threading.Thread') as mock_thread:
        def side_effect(target=None, **kwargs):
            target()
            return MagicMock() 
        mock_thread.side_effect = side_effect
        
        mock_archiver.sync_playlist.return_value = {'success': True, 'new_videos': 5}
        
        response = client.post('/sync_playlist/PL123')
        
        assert response.status_code == 200
        assert response.json['status'] == 'success'
        mock_archiver.sync_playlist.assert_called_with('PL123', callback=web.update_sync_status)

def test_sync_playlist_not_found(client, mock_archiver):
    mock_archiver.playlists = {} # Empty
    response = client.post('/sync_playlist/PL123')
    assert response.json['status'] == 'error'
    assert 'not found' in response.json['message']

def test_settings_update(client, mock_archiver):
    data = {
        'download_dir': '/tmp/dl',
        'sync_interval': '12',
        'concurrent_downloads': '3',
        'auto_sync': 'on'
    }
    
    with patch('web.schedule_sync') as mock_schedule_sync, \
         patch('web.start_background_tasks') as mock_start_bg:
        
        response = client.post('/settings', data=data)
        
        assert response.status_code == 302
        mock_archiver.update_config.assert_called()
        args = mock_archiver.update_config.call_args[0][0]
        assert args['download_dir'] == '/tmp/dl'
        assert args['sync_interval'] == 12
        assert args['auto_sync'] is True
        
        mock_schedule_sync.assert_called()

def test_playlist_detail(client, mock_archiver):
    mock_archiver.playlists = {'PL1': {'title': 'Detail Playlist', 'id': 'PL1', 'url': 'http://url'}}
    response = client.get('/playlist/PL1')
    assert response.status_code == 200
    assert b'Detail Playlist' in response.data

def test_videos_page(client, mock_archiver):
    mock_archiver.downloaded_videos = {'v1': {'title': 'Vid 1'}}
    response = client.get('/videos')
    assert response.status_code == 200
    assert b'Vid 1' in response.data

def test_delete_video(client, mock_archiver):
    mock_archiver.downloaded_videos = {'v1': {'title': 'Vid 1', 'playlist_id': 'PL1'}}
    mock_archiver.playlists = {'PL1': {}}
    mock_archiver.delete_video.return_value = True
    
    response = client.post('/delete_video/v1')
    
    assert response.status_code == 302
    mock_archiver.delete_video.assert_called_with('v1')

def test_watch_video(client, mock_archiver):
    # Setup
    mock_archiver.downloaded_videos = {'v1': {'title': 'Vid 1'}}
    mock_archiver.find_video_file.return_value = '/path/to/vid1.mp4'
    
    # Success
    response = client.get('/watch/v1')
    assert response.status_code == 200
    assert b'Vid 1' in response.data
    
    # Not in DB
    response = client.get('/watch/NONEXISTENT')
    assert response.status_code == 302 # Redirects to videos
    
    # Not on disk (find_video_file returns None)
    mock_archiver.find_video_file.return_value = None
    response = client.get('/watch/v1')
    assert response.status_code == 302 # Redirects to videos

def test_serve_video(client, mock_archiver):
    # This calls send_from_directory. 
    # Since we can't easily assert on the file content without a real file and directory structure 
    # matched to Flask's expectation in this mocked env, we might mock send_from_directory 
    # or just ensure it calls the right path. 
    # However, send_from_directory is imported in web.py.
    
    with patch('web.send_from_directory') as mock_send:
        mock_send.return_value = "File Content"
        
        response = client.get('/video/test.mp4')
        
        assert response.status_code == 200
        assert b"File Content" in response.data
        mock_send.assert_called_with(mock_archiver.download_dir, 'test.mp4')

def test_get_status(client):
    response = client.get('/status')
    assert response.status_code == 200
    assert 'is_syncing' in response.json
    assert 'current_task' in response.json

def test_schedule_sync_logic(client, mock_archiver):
    # Scenario 1: Interval based
    mock_archiver.config = {
        "auto_sync": True,
        "sync_interval": 12,
        "sync_time": "00:00"
    }
    
    with patch('web.schedule') as mock_schedule:
        web.schedule_sync()
        
        mock_schedule.clear.assert_called()
        mock_schedule.every.assert_called_with(12)
        mock_schedule.every.return_value.hours.do.assert_called()
    
    # Scenario 2: Daily based
    mock_archiver.config = {
        "auto_sync": True,
        "sync_interval": 24,
        "sync_time": "03:00"
    }
    
    with patch('web.schedule') as mock_schedule:
        web.schedule_sync()
        
        mock_schedule.clear.assert_called()
        mock_schedule.every.return_value.day.at.assert_called_with("03:00")
        mock_schedule.every.return_value.day.at.return_value.do.assert_called()
    
    # Scenario 3: Auto sync disabled
    mock_archiver.config = {
        "auto_sync": False
    }
    
    with patch('web.schedule') as mock_schedule:
        web.schedule_sync()
        # Should not schedule anything, but it calls clear() only if auto_sync is True in current logic?
        # Let's check web.py: if archiver.config.get("auto_sync", False): ...
        # So if False, it does NOTHING.
        mock_schedule.clear.assert_not_called()
        mock_schedule.every.assert_not_called()


