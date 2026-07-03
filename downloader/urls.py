from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('settings/', views.settings_view, name='settings'),
    path('api/fetch-info/', views.fetch_info, name='fetch_info'),
    path('api/start-download/', views.start_download, name='start_download'),
    path('api/download-status/<str:download_id>/', views.download_status, name='download_status'),
    path('api/download-file/<str:download_id>/', views.download_file_view, name='download_file'),
]
