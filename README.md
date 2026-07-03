# YouTube Video & Playlist Downloader

A premium, web-based automation application developed using the **Django Framework** and **Python**. It allows users to download single YouTube videos or entire playlists as high-quality MP4 video streams or MP3 audio extractions. 

Styled with a **sleek dark-mode theme** and **glassmorphism layout design**, it features real-time progress polling, download history logs, query search filters, and custom user settings to specify download directory pathways on the host machine.

---

## 🚀 Features

* 🔐 **User Authentication**: Secure user registration and login management.
* 🎥 **Single Video Download**: Fetch details (thumbnail, duration, titles) and download videos.
* 🎶 **Playlist Downloader**: Fast extraction of playlist index items, allowing sequential downloading of entire playlists in the background.
* 🛠️ **Format & Quality Control**: Choose between MP4 video or MP3 audio. Supports quality selections: 360p, 720p, 1080p Full HD, or Best Available.
* 📈 **Real-time Progress Indicator**: Dynamic progress percentage update and speed rate calculations polled asynchronously.
* ⚙️ **Custom Download Directory**: Configure custom paths on the local computer to save downloaded files directly.
* 📜 **Download History**: Searchable history cards showing file sizes, download dates, formats, and click-to-download browser links.

---

## 🛠️ Technology Stack

* **Frontend**: HTML5, CSS3 (Glassmorphic Stylesheet), JavaScript (ES6 AJAX & Poller), Bootstrap 5.
* **Backend**: Django 5.0 (Python 3.14).
* **Database**: MySQL / MariaDB (XAMPP).
* **Core Libraries**: `yt-dlp` (Stream retrieval), `FFmpeg` (Audio/Video merging & MP3 conversion), `PyMySQL` (Database connector), `Pillow`, `Requests`.

---

## ⚙️ Prerequisites

1. **Python 3.10+**: Ensure Python is installed.
2. **XAMPP**: Running Apache and MySQL modules.
3. **FFmpeg**: Required by `yt-dlp` for merging streams and post-processing files.

---

## 📦 Installation & Setup

Follow these steps to run the application locally:

### 1. Configure the Database
* Start XAMPP Control Panel and start **Apache** and **MySQL**.
* Open your browser and head to `http://localhost/phpmyadmin/` (or run a SQL command) to create a database named:
  ```sql
  CREATE DATABASE yt_downloader CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  ```

### 2. Install Project Dependencies
Run the following commands in your command shell to install the required libraries:
```bash
pip install django<5.1 yt-dlp pymysql pillow requests
```

### 3. Run Database Migrations
Create and execute the database schemas:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Launch the Application
Run the local development server:
```bash
python manage.py runserver
```

Open **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your web browser.

---

## 📂 Project Structure

```text
├── downloader/
│   ├── migrations/          # DB migration schemas
│   ├── static/              # CSS layouts & JavaScript AJAX polling
│   ├── templates/           # Login, Register, Settings, and Dashboard views
│   ├── models.py            # UserSettings and DownloadHistory schemas
│   ├── views.py             # User handlers, download thread worker logic, APIs
│   ├── urls.py              # Application routes
│   └── tests.py             # Unit tests checking signal/DB/API endpoints
├── yt_downloader_project/
│   ├── settings.py          # Database credentials and apps registration
│   ├── urls.py              # Root router configuration
│   └── __init__.py          # PyMySQL DB patch activation
├── manage.py                # Django administrative utility script
└── README.md                # Project documentation
```

---

## 🧪 Running Unit Tests
You can verify application routes and model handlers by executing the unit tests:
```bash
python manage.py test
```
