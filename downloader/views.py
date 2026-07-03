import os
import json
import uuid
import shutil
import threading
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse, Http404, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from .models import UserSettings, DownloadHistory

def get_ffmpeg_path():
    # 1. Check system PATH
    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        return ffmpeg_in_path
    # 2. Check the WinGet installation path
    winget_path = r"C:\Users\ranau\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe"
    if os.path.exists(winget_path):
        return winget_path
    return None

def make_progress_hook(download_history_id):
    def hook(d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded_bytes = d.get('downloaded_bytes', 0)
            
            progress = 0
            if total_bytes > 0:
                progress = int((downloaded_bytes / total_bytes) * 100)
            elif 'percent' in d:
                progress = int(float(d['percent']))
            
            speed_bytes = d.get('speed', 0) or 0
            speed_str = ""
            if speed_bytes > 1024 * 1024:
                speed_str = f"{speed_bytes / (1024*1024):.2f} MB/s"
            elif speed_bytes > 1024:
                speed_str = f"{speed_bytes / 1024:.2f} KB/s"
            elif speed_bytes > 0:
                speed_str = f"{speed_bytes:.2f} B/s"
            
            try:
                DownloadHistory.objects.filter(id=download_history_id).update(
                    status='downloading',
                    progress=progress,
                    speed=speed_str,
                    file_size=total_bytes
                )
            except Exception:
                pass
                
        elif d['status'] == 'finished':
            try:
                DownloadHistory.objects.filter(id=download_history_id).update(
                    status='processing',
                    progress=100,
                    speed=''
                )
            except Exception:
                pass
    return hook

def download_task_sync(download_history_id):
    import yt_dlp
    
    try:
        history = DownloadHistory.objects.get(id=download_history_id)
    except DownloadHistory.DoesNotExist:
        return
        
    ffmpeg_path = get_ffmpeg_path()
    download_dir = history.user.settings.get_download_directory()
    
    ydl_opts = {
        'progress_hooks': [make_progress_hook(download_history_id)],
        'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
    }
    
    if ffmpeg_path:
        ydl_opts['ffmpeg_location'] = ffmpeg_path
        
    if history.download_format == 'MP3':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else: # MP4
        quality = history.video_quality
        if quality == '360p':
            ydl_opts['format'] = 'bestvideo[height<=360]+bestaudio/best[height<=360]/best[height<=360]'
        elif quality == '720p':
            ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best[height<=720]'
        elif quality == '1080p':
            ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best[height<=1080]'
        else: # best
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
            
        ydl_opts['merge_output_format'] = 'mp4'

    try:
        DownloadHistory.objects.filter(id=download_history_id).update(status='downloading')
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(history.youtube_url, download=True)
            
            # resolve playlist items detail extraction if needed
            thumbnail = info.get('thumbnail') or (info.get('thumbnails', [{}])[-1].get('url') if info.get('thumbnails') else '')
            duration = info.get('duration', 0)
            title = info.get('title') or history.video_title
            
            filename = ydl.prepare_filename(info)
            if history.download_format == 'MP3':
                base, _ = os.path.splitext(filename)
                filename = base + '.mp3'
            elif history.download_format == 'MP4' and not filename.endswith('.mp4'):
                base, _ = os.path.splitext(filename)
                filename = base + '.mp4'
                
            file_size = os.path.getsize(filename) if os.path.exists(filename) else None
            
            DownloadHistory.objects.filter(id=download_history_id).update(
                status='completed',
                progress=100,
                speed='',
                file_location=filename,
                file_size=file_size or history.file_size,
                thumbnail_url=thumbnail or history.thumbnail_url,
                duration=duration or history.duration,
                video_title=title
            )
            
    except Exception as e:
        DownloadHistory.objects.filter(id=download_history_id).update(
            status='failed',
            error_message=str(e)[:1000],
            speed=''
        )

def download_task(download_history_id):
    download_task_sync(download_history_id)

def download_playlist_task(download_ids):
    for dl_id in download_ids:
        try:
            history = DownloadHistory.objects.get(download_id=dl_id)
            download_task_sync(history.id)
        except Exception:
            continue

# Authentication Views
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    error = None
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
        else:
            error = "Registration failed. Please correct the errors below."
    else:
        form = UserCreationForm()
    return render(request, 'downloader/register.html', {'form': form, 'error_error': error})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    error = None
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
        else:
            error = "Invalid username or password."
    else:
        form = AuthenticationForm()
    return render(request, 'downloader/login.html', {'form': form, 'error': error})

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

# Dashboard View
@login_required
def dashboard(request):
    query = request.GET.get('q', '').strip()
    downloads = DownloadHistory.objects.filter(user=request.user)
    if query:
        downloads = downloads.filter(
            Q(video_title__icontains=query) | 
            Q(youtube_url__icontains=query)
        )
    downloads = downloads.order_by('-download_date')
    
    active_downloads = downloads.filter(status__in=['pending', 'downloading', 'processing'])
    history_downloads = downloads.exclude(status__in=['pending', 'downloading', 'processing'])
    
    return render(request, 'downloader/dashboard.html', {
        'active_downloads': active_downloads,
        'history_downloads': history_downloads,
        'query': query
    })

# Settings View
@login_required
def settings_view(request):
    user_settings, created = UserSettings.objects.get_or_create(user=request.user)
    error = None
    success = None
    if request.method == 'POST':
        dir_path = request.POST.get('download_directory', '').strip()
        if dir_path:
            try:
                os.makedirs(dir_path, exist_ok=True)
                test_file = os.path.join(dir_path, '.write_test')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                user_settings.download_directory = dir_path
                user_settings.save()
                success = "Settings updated successfully."
            except Exception as e:
                error = f"Invalid or non-writable directory path: {str(e)}"
        else:
            user_settings.download_directory = ''
            user_settings.save()
            success = "Settings updated successfully (using default directory)."
            
    return render(request, 'downloader/settings.html', {
        'settings': user_settings,
        'error': error,
        'success': success
    })

# API Endpoints
@login_required
@require_http_methods(["POST"])
def fetch_info(request):
    try:
        data = json.loads(request.body)
        url = data.get('url')
    except Exception:
        return JsonResponse({'error': 'Invalid request body.'}, status=400)
        
    if not url:
        return JsonResponse({'error': 'YouTube URL is required.'}, status=400)
        
    try:
        import yt_dlp
        ydl_opts = {
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        if not info:
            return JsonResponse({'error': 'Could not extract video information.'}, status=400)
            
        is_playlist = 'entries' in info and info.get('_type') == 'playlist'
        
        if is_playlist:
            entries = info.get('entries', [])
            videos = []
            for entry in entries:
                if entry:
                    videos.append({
                        'title': entry.get('title') or 'Unknown Title',
                        'url': entry.get('url') or entry.get('webpage_url') or f"https://www.youtube.com/watch?v={entry.get('id')}",
                        'id': entry.get('id'),
                    })
            return JsonResponse({
                'is_playlist': True,
                'title': info.get('title') or 'Unnamed Playlist',
                'video_count': len(videos),
                'videos': videos,
                'thumbnail': info.get('thumbnails', [{}])[-1].get('url') if info.get('thumbnails') else None
            })
        else:
            duration_secs = info.get('duration', 0)
            duration_str = ""
            if duration_secs:
                mins, secs = divmod(duration_secs, 60)
                hours, mins = divmod(mins, 60)
                if hours:
                    duration_str = f"{hours}:{mins:02d}:{secs:02d}"
                else:
                    duration_str = f"{mins}:{secs:02d}"
            else:
                duration_str = "Unknown"
                
            return JsonResponse({
                'is_playlist': False,
                'title': info.get('title') or 'Unknown Title',
                'thumbnail': info.get('thumbnail') or (info.get('thumbnails', [{}])[-1].get('url') if info.get('thumbnails') else None),
                'duration': duration_str,
                'duration_seconds': duration_secs,
                'url': url
            })
    except Exception as e:
        return JsonResponse({'error': f'Failed to fetch video details: {str(e)}'}, status=500)

@login_required
@require_http_methods(["POST"])
def start_download(request):
    try:
        data = json.loads(request.body)
        url = data.get('url')
        download_format = data.get('format', 'MP4')
        quality = data.get('quality', 'best')
    except Exception:
        return JsonResponse({'error': 'Invalid request body.'}, status=400)
        
    if not url:
        return JsonResponse({'error': 'YouTube URL is required.'}, status=400)
        
    try:
        import yt_dlp
        
        ydl_opts = {
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        if not info:
            return JsonResponse({'error': 'Failed to retrieve URL details.'}, status=400)
            
        is_playlist = 'entries' in info and info.get('_type') == 'playlist'
        
        download_ids = []
        
        if is_playlist:
            entries = info.get('entries', [])
            playlist_title = info.get('title') or 'Playlist'
            
            for index, entry in enumerate(entries):
                if not entry:
                    continue
                video_url = entry.get('url') or entry.get('webpage_url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                video_title = entry.get('title') or f"{playlist_title} - Video {index+1}"
                
                dl_id = str(uuid.uuid4())
                download_ids.append(dl_id)
                
                DownloadHistory.objects.create(
                    user=request.user,
                    video_title=video_title,
                    youtube_url=video_url,
                    thumbnail_url='',
                    download_format=download_format,
                    video_quality=quality,
                    status='pending',
                    download_id=dl_id,
                    duration=0
                )
            
            thread = threading.Thread(target=download_playlist_task, args=(download_ids,))
            thread.daemon = True
            thread.start()
            
            return JsonResponse({
                'message': 'Playlist download started.',
                'is_playlist': True,
                'download_ids': download_ids
            })
            
        else:
            dl_id = str(uuid.uuid4())
            duration_secs = info.get('duration', 0)
            thumbnail = info.get('thumbnail') or (info.get('thumbnails', [{}])[-1].get('url') if info.get('thumbnails') else '')
            
            db_record = DownloadHistory.objects.create(
                user=request.user,
                video_title=info.get('title') or 'Unknown Title',
                youtube_url=url,
                thumbnail_url=thumbnail,
                download_format=download_format,
                video_quality=quality,
                status='pending',
                download_id=dl_id,
                duration=duration_secs
            )
            
            thread = threading.Thread(target=download_task, args=(db_record.id,))
            thread.daemon = True
            thread.start()
            
            return JsonResponse({
                'message': 'Video download started.',
                'is_playlist': False,
                'download_id': dl_id
            })
            
    except Exception as e:
        return JsonResponse({'error': f'Failed to initiate download: {str(e)}'}, status=500)

@login_required
def download_status(request, download_id):
    try:
        history = DownloadHistory.objects.get(download_id=download_id, user=request.user)
    except DownloadHistory.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
        
    return JsonResponse({
        'download_id': history.download_id,
        'status': history.status,
        'progress': history.progress,
        'speed': history.speed,
        'file_size': history.file_size,
        'video_title': history.video_title,
        'thumbnail_url': history.thumbnail_url,
        'error_message': history.error_message,
        'download_format': history.download_format,
        'video_quality': history.video_quality,
    })

@login_required
def download_file_view(request, download_id):
    try:
        history = DownloadHistory.objects.get(download_id=download_id, user=request.user)
    except DownloadHistory.DoesNotExist:
        raise Http404("Download not found.")
        
    if history.status != 'completed':
        return HttpResponseForbidden("File download is not complete yet.")
        
    file_path = history.file_location
    if not file_path or not os.path.exists(file_path):
        raise Http404("File does not exist on the server.")
        
    try:
        response = FileResponse(open(file_path, 'rb'), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        return response
    except Exception as e:
        raise Http404(f"Error serving file: {str(e)}")
