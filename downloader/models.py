from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import os
from django.conf import settings

class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    download_directory = models.CharField(max_length=500, blank=True)

    def get_download_directory(self):
        if self.download_directory:
            return self.download_directory
        # default to a "downloads" folder under settings.BASE_DIR
        default_dir = os.path.join(settings.BASE_DIR, 'downloads')
        if not os.path.exists(default_dir):
            os.makedirs(default_dir, exist_ok=True)
        return default_dir

    def __str__(self):
        return f"Settings for {self.user.username}"

@receiver(post_save, sender=User)
def create_user_settings(sender, instance, created, **kwargs):
    if created:
        UserSettings.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_settings(sender, instance, **kwargs):
    if hasattr(instance, 'settings'):
        instance.settings.save()
    else:
        UserSettings.objects.create(user=instance)


class DownloadHistory(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('downloading', 'Downloading'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='downloads')
    video_title = models.CharField(max_length=500)
    youtube_url = models.URLField(max_length=1000)
    thumbnail_url = models.URLField(max_length=1000)
    download_format = models.CharField(max_length=10) # MP4 or MP3
    video_quality = models.CharField(max_length=50) # 360p, 720p, 1080p, best
    file_size = models.BigIntegerField(null=True, blank=True) # in bytes
    download_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.IntegerField(default=0) # 0 to 100
    speed = models.CharField(max_length=50, default='', blank=True) # speed in string format
    file_location = models.CharField(max_length=1000, default='', blank=True)
    download_id = models.CharField(max_length=100, unique=True)
    error_message = models.TextField(default='', blank=True)
    duration = models.IntegerField(default=0) # duration in seconds

    def __str__(self):
        return f"{self.video_title} ({self.download_format}) - {self.status}"
