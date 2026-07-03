from django.test import TestCase, Client
from django.urls import reverse, resolve
from django.contrib.auth.models import User
from downloader.models import UserSettings, DownloadHistory

# Monkeypatch for Django 5.0 template context copying under Python 3.14
from django.template.context import BaseContext
import copy

def custom_copy(self):
    duplicate = self.__class__.__new__(self.__class__)
    for key, value in self.__dict__.items():
        if key == 'dicts':
            duplicate.dicts = self.dicts[:]
        else:
            setattr(duplicate, key, copy.copy(value))
    return duplicate

BaseContext.__copy__ = custom_copy

class DownloaderTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        
    def test_user_settings_creation_on_user_register(self):
        # Verify signals created user settings
        self.assertIsNotNone(self.user.settings)
        self.assertEqual(self.user.settings.download_directory, '')
        
        # Test default directory creation
        default_dir = self.user.settings.get_download_directory()
        self.assertTrue(default_dir.endswith('downloads'))

    def test_dashboard_redirects_if_anonymous(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_dashboard_accessible_when_authenticated(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'downloader/dashboard.html')

    def test_history_search(self):
        self.client.login(username='testuser', password='password123')
        # Create dummy history items
        DownloadHistory.objects.create(
            user=self.user,
            video_title="Interesting Video 1",
            youtube_url="https://youtube.com/watch?v=123",
            thumbnail_url="http://thumb.jpg",
            download_format="MP4",
            video_quality="720p",
            download_id="dl-uuid-1",
            status="completed"
        )
        DownloadHistory.objects.create(
            user=self.user,
            video_title="Boring Tutorial 2",
            youtube_url="https://youtube.com/watch?v=456",
            thumbnail_url="http://thumb.jpg",
            download_format="MP3",
            video_quality="best",
            download_id="dl-uuid-2",
            status="failed"
        )
        
        # Fetch dashboard without search query
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(len(response.context['history_downloads']), 2)
        
        # Search for "Interesting"
        response = self.client.get(reverse('dashboard') + '?q=Interesting')
        self.assertEqual(len(response.context['history_downloads']), 1)
        self.assertEqual(response.context['history_downloads'][0].video_title, "Interesting Video 1")

    def test_fetch_info_requires_post_and_login(self):
        # Test anonymous access
        response = self.client.post(reverse('fetch_info'), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 302)

        # Test authenticated but invalid body
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('fetch_info'), data="invalid", content_type='application/json')
        self.assertEqual(response.status_code, 400)
