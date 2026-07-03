// CSRF Helper
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
const csrftoken = getCookie('csrftoken');

// Active downloads tracking
const activePollers = {};

document.addEventListener('DOMContentLoaded', () => {
    // Select elements
    const urlForm = document.getElementById('url-form');
    const urlInput = document.getElementById('url-input');
    const analyzeBtn = document.getElementById('analyze-btn');
    const analysisLoading = document.getElementById('analysis-loading');
    const previewContainer = document.getElementById('preview-container');
    const previewContent = document.getElementById('preview-content');
    const errorAlert = document.getElementById('error-alert');
    const errorText = document.getElementById('error-text');
    const historySearch = document.getElementById('history-search');
    
    // Initialize polling for existing active downloads loaded from backend
    const initialActiveItems = document.querySelectorAll('.active-download-item');
    initialActiveItems.forEach(item => {
        const downloadId = item.dataset.downloadId;
        if (downloadId) {
            startPolling(downloadId);
        }
    });

    // History Search - Realtime client-side filter
    if (historySearch) {
        historySearch.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().strip ? e.target.value.toLowerCase().trim() : e.target.value.toLowerCase();
            const historyItems = document.querySelectorAll('.history-download-item');
            
            historyItems.forEach(item => {
                const title = item.querySelector('.video-title').textContent.toLowerCase();
                const url = item.querySelector('.video-url').textContent.toLowerCase();
                if (title.includes(query) || url.includes(query)) {
                    item.style.setProperty('display', 'flex', 'important');
                } else {
                    item.style.setProperty('display', 'none', 'important');
                }
            });
        });
    }

    // Submit URL for analysis
    if (urlForm) {
        urlForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const url = urlInput.value.trim();
            if (!url) return;

            // Reset UI states
            errorAlert.classList.add('d-none');
            previewContainer.classList.add('d-none');
            analysisLoading.classList.remove('d-none');
            analyzeBtn.disabled = true;

            fetch('/api/fetch-info/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({ url: url })
            })
            .then(response => response.json().then(data => ({ status: response.status, data })))
            .then(({ status, data }) => {
                analysisLoading.classList.add('d-none');
                analyzeBtn.disabled = false;

                if (status !== 200) {
                    showError(data.error || 'Failed to analyze video URL.');
                    return;
                }

                renderPreview(data, url);
            })
            .catch(err => {
                analysisLoading.classList.add('d-none');
                analyzeBtn.disabled = false;
                showError('A network error occurred. Please try again.');
                console.error(err);
            });
        });
    }

    // Format selection cards event delegation
    document.addEventListener('click', (e) => {
        const formatCard = e.target.closest('.format-card');
        if (formatCard) {
            const container = formatCard.closest('.format-selection-container');
            const formatValue = formatCard.dataset.format;
            
            // Toggle active card
            container.querySelectorAll('.format-card').forEach(c => c.classList.remove('active'));
            formatCard.classList.add('active');

            // Show or hide quality selector based on format selection
            const qualityWrapper = container.nextElementSibling; // the quality-select-wrapper
            if (formatValue === 'MP4') {
                qualityWrapper.classList.add('show');
            } else {
                qualityWrapper.classList.remove('show');
            }
        }
    });

    // Start download button action
    document.addEventListener('click', (e) => {
        const downloadBtn = e.target.closest('.start-download-btn');
        if (downloadBtn) {
            const url = downloadBtn.dataset.url;
            const previewCard = downloadBtn.closest('.glass-card');
            const formatCard = previewCard.querySelector('.format-card.active');
            const formatValue = formatCard ? formatCard.dataset.format : 'MP4';
            const qualitySelect = previewCard.querySelector('.quality-select');
            const qualityValue = formatValue === 'MP4' && qualitySelect ? qualitySelect.value : 'best';

            downloadBtn.disabled = true;
            downloadBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Starting...';

            fetch('/api/start-download/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({
                    url: url,
                    format: formatValue,
                    quality: qualityValue
                })
            })
            .then(response => response.json().then(data => ({ status: response.status, data })))
            .then(({ status, data }) => {
                if (status !== 200) {
                    showError(data.error || 'Failed to start download.');
                    downloadBtn.disabled = false;
                    downloadBtn.innerHTML = 'Download Now';
                    return;
                }

                // Success! Close preview container and reset url input
                previewContainer.classList.add('d-none');
                urlInput.value = '';

                // Handle single video vs playlist response
                if (data.is_playlist) {
                    data.download_ids.forEach(id => {
                        createActiveDownloadRow(id);
                        startPolling(id);
                    });
                } else {
                    createActiveDownloadRow(data.download_id);
                    startPolling(data.download_id);
                }
            })
            .catch(err => {
                showError('Failed to start download due to connection issues.');
                downloadBtn.disabled = false;
                downloadBtn.innerHTML = 'Download Now';
                console.error(err);
            });
        }
    });
});

// Render the preview card
function renderPreview(data, url) {
    const previewContainer = document.getElementById('preview-container');
    const previewContent = document.getElementById('preview-content');

    let html = '';
    const thumbnailSrc = data.thumbnail || 'https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=360';

    if (data.is_playlist) {
        // Playlist preview
        html = `
            <div class="dynamic-media-wrapper">
                <div class="dynamic-media-blur-bg" style="background-image: url('${thumbnailSrc}');"></div>
                <div class="dynamic-media-content">
                    <div class="row align-items-center g-4">
                        <div class="col-md-3 text-center">
                            <div class="thumbnail-preview" style="height: 120px; width: 100%;">
                                <img src="${thumbnailSrc}" alt="Playlist Thumbnail" class="img-fluid rounded">
                            </div>
                        </div>
                        <div class="col-md-9">
                            <h5 class="fw-bold mb-1">${escapeHtml(data.title)}</h5>
                            <p class="text-secondary mb-3"><i class="bi bi-music-note-list me-1"></i> Playlist &bull; ${data.video_count} videos</p>
                            
                            <div class="mb-3 format-selection-container d-flex gap-3">
                                <div class="format-card p-3 flex-fill text-center active" data-format="MP4">
                                    <i class="bi bi-file-earmark-play fs-4 d-block mb-1 text-primary"></i>
                                    <span class="fw-bold">MP4 Video</span>
                                </div>
                                <div class="format-card p-3 flex-fill text-center" data-format="MP3">
                                    <i class="bi bi-file-earmark-music fs-4 d-block mb-1 text-purple"></i>
                                    <span class="fw-bold">MP3 Audio</span>
                                </div>
                            </div>
                            
                            <div class="quality-select-wrapper show mb-3">
                                <label class="form-label text-secondary small">Select Max Video Quality</label>
                                <select class="form-select glass-input quality-select">
                                    <option value="best">Best Available Quality</option>
                                    <option value="1080p">1080p Full HD</option>
                                    <option value="720p">720p HD</option>
                                    <option value="360p">360p Standard</option>
                                </select>
                            </div>

                            <div class="playlist-videos-list mb-3 p-2 bg-dark rounded" style="max-height: 150px; overflow-y: auto; font-size: 0.85rem;">
                                <div class="text-secondary px-2 py-1 border-bottom border-secondary mb-1">Videos in Playlist:</div>
                                ${data.videos.slice(0, 10).map((v, i) => `<div class="text-truncate px-2 py-1 text-light">${i+1}. ${escapeHtml(v.title)}</div>`).join('')}
                                ${data.videos.length > 10 ? `<div class="text-secondary px-2 py-1 text-center font-italic">+ ${data.video_count - 10} more videos</div>` : ''}
                            </div>

                            <button class="btn btn-primary-gradient w-100 start-download-btn" data-url="${escapeHtml(url)}">Download Playlist</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    } else {
        // Single video preview
        html = `
            <div class="dynamic-media-wrapper">
                <div class="dynamic-media-blur-bg" style="background-image: url('${thumbnailSrc}');"></div>
                <div class="dynamic-media-content">
                    <div class="row align-items-center g-4">
                        <div class="col-md-4 text-center">
                            <div class="thumbnail-preview" style="width: 100%; aspect-ratio: 16/9;">
                                <img src="${thumbnailSrc}" alt="Video Thumbnail" class="img-fluid w-100 rounded">
                                <span class="duration-tag">${data.duration}</span>
                            </div>
                        </div>
                        <div class="col-md-8">
                            <h5 class="fw-bold mb-1">${escapeHtml(data.title)}</h5>
                            <p class="text-secondary mb-3 small"><i class="bi bi-youtube me-1"></i> YouTube Video</p>
                            
                            <div class="mb-3 format-selection-container d-flex gap-3">
                                <div class="format-card p-3 flex-fill text-center active" data-format="MP4">
                                    <i class="bi bi-file-earmark-play fs-4 d-block mb-1 text-primary"></i>
                                    <span class="fw-bold">MP4 Video</span>
                                </div>
                                <div class="format-card p-3 flex-fill text-center" data-format="MP3">
                                    <i class="bi bi-file-earmark-music fs-4 d-block mb-1 text-purple"></i>
                                    <span class="fw-bold">MP3 Audio</span>
                                </div>
                            </div>
                            
                            <div class="quality-select-wrapper show mb-3">
                                <label class="form-label text-secondary small">Select Video Quality</label>
                                <select class="form-select glass-input quality-select">
                                    <option value="best">Best Available</option>
                                    <option value="1080p">1080p Full HD</option>
                                    <option value="720p">720p HD</option>
                                    <option value="360p">360p Standard</option>
                                </select>
                            </div>

                            <button class="btn btn-primary-gradient w-100 start-download-btn" data-url="${escapeHtml(url)}">Download Now</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    previewContent.innerHTML = html;
    previewContainer.classList.remove('d-none');
    previewContainer.scrollIntoView({ behavior: 'smooth' });
}

// Dynamically create a placeholder row for active downloads
function createActiveDownloadRow(downloadId) {
    const activeDownloadsList = document.getElementById('active-downloads-list');
    const noActiveDownloads = document.getElementById('no-active-downloads');

    if (noActiveDownloads) {
        noActiveDownloads.remove();
    }

    // Check if item already exists to avoid duplicates
    if (document.getElementById(`dl-item-${downloadId}`)) {
        return;
    }

    const rowHtml = `
        <div class="download-item active-download-item d-flex align-items-center gap-3 py-3" id="dl-item-${downloadId}" data-download-id="${downloadId}">
            <div class="thumbnail-preview flex-shrink-0 bg-dark rounded" style="width: 80px; height: 50px;">
                <img src="" id="dl-thumb-${downloadId}" alt="Pending Thumbnail" class="d-none w-100 h-100 object-fit-cover rounded">
                <div class="w-100 h-100 d-flex align-items-center justify-content-center text-secondary" id="dl-placeholder-thumb-${downloadId}">
                    <i class="bi bi-hourglass-split spinner-border spinner-border-sm text-secondary" style="border: none;"></i>
                </div>
            </div>
            <div class="flex-grow-1 min-w-0">
                <div class="d-flex justify-content-between align-items-start gap-2 mb-1">
                    <h6 class="fw-bold mb-0 text-truncate video-title text-light" id="dl-title-${downloadId}">Processing request...</h6>
                    <span class="badge badge-pending flex-shrink-0" id="dl-badge-${downloadId}">Pending</span>
                </div>
                <div class="progress mb-1">
                    <div class="progress-bar progress-bar-animated progress-bar-striped" id="dl-progress-bar-${downloadId}" role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
                <div class="d-flex justify-content-between text-secondary small">
                    <span id="dl-progress-text-${downloadId}">0%</span>
                    <span id="dl-speed-${downloadId}">--</span>
                </div>
            </div>
        </div>
    `;

    activeDownloadsList.insertAdjacentHTML('afterbegin', rowHtml);
}

// Start polling API for details
function startPolling(downloadId) {
    if (activePollers[downloadId]) return;

    activePollers[downloadId] = setInterval(() => {
        fetch(`/api/download-status/${downloadId}/`)
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    clearInterval(activePollers[downloadId]);
                    delete activePollers[downloadId];
                    return;
                }

                updateDownloadItemUI(data);

                // Stop conditions
                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(activePollers[downloadId]);
                    delete activePollers[downloadId];
                    
                    // Delay slightly to show 100% completion before moving to history
                    setTimeout(() => {
                        moveItemToHistory(data);
                    }, 1000);
                }
            })
            .catch(err => {
                console.error('Polling error:', err);
            });
    }, 1500);
}

// Update the UI state of a downloading item
function updateDownloadItemUI(data) {
    const id = data.download_id;
    const titleEl = document.getElementById(`dl-title-${id}`);
    const badgeEl = document.getElementById(`dl-badge-${id}`);
    const progressBar = document.getElementById(`dl-progress-bar-${id}`);
    const progressText = document.getElementById(`dl-progress-text-${id}`);
    const speedEl = document.getElementById(`dl-speed-${id}`);
    const imgEl = document.getElementById(`dl-thumb-${id}`);
    const placeholderEl = document.getElementById(`dl-placeholder-thumb-${id}`);

    if (titleEl) titleEl.textContent = data.video_title || 'Downloading video...';

    // Update Image
    if (data.thumbnail_url && imgEl && placeholderEl) {
        imgEl.src = data.thumbnail_url;
        imgEl.classList.remove('d-none');
        placeholderEl.classList.add('d-none');
    }

    // Update status badge classes
    if (badgeEl) {
        badgeEl.textContent = capitalizeFirstLetter(data.status);
        badgeEl.className = 'badge flex-shrink-0'; // Reset classes
        if (data.status === 'pending') badgeEl.classList.add('badge-pending');
        else if (data.status === 'downloading') badgeEl.classList.add('badge-downloading');
        else if (data.status === 'processing') badgeEl.classList.add('badge-processing');
        else if (data.status === 'completed') badgeEl.classList.add('badge-completed');
        else if (data.status === 'failed') badgeEl.classList.add('badge-failed');
    }

    // Update progress elements
    if (progressBar) {
        progressBar.style.width = `${data.progress}%`;
        progressBar.setAttribute('aria-valuenow', data.progress);
    }
    if (progressText) {
        if (data.status === 'processing') {
            progressText.textContent = 'Processing files...';
        } else {
            progressText.textContent = `${data.progress}%`;
        }
    }

    // Update speed
    if (speedEl) {
        if (data.status === 'downloading' && data.speed) {
            speedEl.textContent = data.speed;
        } else if (data.status === 'processing') {
            speedEl.textContent = 'FFmpeg processing';
        } else {
            speedEl.textContent = '--';
        }
    }
}

// Move item from active list to history list upon completion
function moveItemToHistory(data) {
    const id = data.download_id;
    const activeRow = document.getElementById(`dl-item-${id}`);
    if (activeRow) {
        activeRow.remove();
    }

    // Check if we need to show "No active downloads" placeholder
    const activeDownloadsList = document.getElementById('active-downloads-list');
    if (activeDownloadsList && activeDownloadsList.children.length === 0) {
        activeDownloadsList.innerHTML = `
            <div class="text-center py-4 text-secondary" id="no-active-downloads">
                <i class="bi bi-cloud-arrow-down fs-1 d-block mb-2"></i>
                No active downloads.
            </div>
        `;
    }

    // Add to history list (prepend to the top of the history list)
    const historyList = document.getElementById('history-list');
    const noHistory = document.getElementById('no-history');
    if (noHistory) {
        noHistory.remove();
    }

    // Format file size nicely
    let sizeStr = '--';
    if (data.file_size) {
        const sizeBytes = data.file_size;
        if (sizeBytes > 1024 * 1024 * 1024) {
            sizeStr = `${(sizeBytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
        } else if (sizeBytes > 1024 * 1024) {
            sizeStr = `${(sizeBytes / (1024 * 1024)).toFixed(2)} MB`;
        } else {
            sizeStr = `${(sizeBytes / 1024).toFixed(2)} KB`;
        }
    }

    // Action button
    let actionBtn = '';
    if (data.status === 'completed') {
        actionBtn = `
            <a href="/api/download-file/${data.download_id}/" class="btn btn-sm btn-primary-gradient px-3 py-2 rounded-pill">
                <i class="bi bi-download me-1"></i> Download
            </a>
        `;
    } else {
        actionBtn = `
            <button class="btn btn-sm btn-secondary-glass text-danger border-danger px-3 py-2 rounded-pill" disabled title="${escapeHtml(data.error_message || '')}">
                <i class="bi bi-exclamation-triangle-fill me-1"></i> Failed
            </button>
        `;
    }

    const historyRowHtml = `
        <div class="download-item history-download-item d-flex align-items-center justify-content-between gap-3 py-3" id="history-item-${id}">
            <div class="d-flex align-items-center gap-3 min-w-0">
                <div class="thumbnail-preview flex-shrink-0 bg-dark rounded" style="width: 80px; height: 50px;">
                    <img src="${data.thumbnail_url || 'https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=100'}" alt="Thumbnail" class="w-100 h-100 object-fit-cover rounded">
                </div>
                <div class="min-w-0">
                    <h6 class="fw-bold mb-1 text-truncate video-title text-light" style="max-width: 350px;">${escapeHtml(data.video_title)}</h6>
                    <div class="d-flex flex-wrap gap-2 align-items-center text-secondary small">
                        <span class="badge text-uppercase bg-secondary text-light">${escapeHtml(data.download_format)} ${data.download_format === 'MP4' ? escapeHtml(data.video_quality) : ''}</span>
                        <span>&bull;</span>
                        <span>${sizeStr}</span>
                        <span>&bull;</span>
                        <span class="text-truncate video-url" style="max-width: 180px;">Just now</span>
                    </div>
                </div>
            </div>
            <div class="flex-shrink-0">
                ${actionBtn}
            </div>
        </div>
    `;

    if (historyList) {
        historyList.insertAdjacentHTML('afterbegin', historyRowHtml);
    }
}

// Helpers
function showError(msg) {
    const errorAlert = document.getElementById('error-alert');
    const errorText = document.getElementById('error-text');
    if (errorAlert && errorText) {
        errorText.textContent = msg;
        errorAlert.classList.remove('d-none');
        errorAlert.scrollIntoView({ behavior: 'smooth' });
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function capitalizeFirstLetter(string) {
    if (!string) return '';
    return string.charAt(0).toUpperCase() + string.slice(1);
}
