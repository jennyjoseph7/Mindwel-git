// Music Therapy JavaScript Implementation

// Map moods to static audio files
const moodAudioFiles = {
  calm: [
    '/static/audio/calm/calm1.mp3', '/static/audio/calm/calm2.mp3', '/static/audio/calm/calm3.mp3', '/static/audio/calm/calm4.mp3', '/static/audio/calm/calm5.mp3', '/static/audio/calm/calm6.mp3', '/static/audio/calm/calm7.mp3'
  ],
  happy: [
    '/static/audio/happy/happy1.mp3', '/static/audio/happy/happy2.mp3', '/static/audio/happy/happy3.mp3', '/static/audio/happy/happy4.mp3', '/static/audio/happy/happy5.mp3', '/static/audio/happy/happy6.mp3'
  ],
  sad: [
    '/static/audio/sad/sad1.mp3', '/static/audio/sad/sad2.mp3', '/static/audio/sad/sad3.mp3', '/static/audio/sad/sad4.mp3', '/static/audio/sad/sad5.mp3', '/static/audio/sad/sad6.mp3'
  ],
  focus: [
    '/static/audio/focus/focus1.mp3', '/static/audio/focus/focus2.mp3', '/static/audio/focus/focus3.mp3', '/static/audio/focus/focus4.mp3', '/static/audio/focus/focus5.mp3', '/static/audio/focus/focus6.mp3', '/static/audio/focus/focus7.mp3', '/static/audio/focus/focus8.mp3'
  ],
  energetic: [
    '/static/audio/energetic/energetic1.mp3', '/static/audio/energetic/energetic2.mp3', '/static/audio/energetic/energetic3.mp3', '/static/audio/energetic/energetic4.mp3', '/static/audio/energetic/energetic5.mp3', '/static/audio/energetic/energetic6.mp3', '/static/audio/energetic/energetic7.mp3', '/static/audio/energetic/energetic8.mp3'
  ],
  sleep: [
    '/static/audio/sleep/sleep1.mp3', '/static/audio/sleep/sleep2.mp3', '/static/audio/sleep/sleep3.mp3', '/static/audio/sleep/sleep4.mp3', '/static/audio/sleep/sleep5.mp3', '/static/audio/sleep/sleep6.mp3', '/static/audio/sleep/sleep7.mp3', '/static/audio/sleep/sleep8.mp3', '/static/audio/sleep/sleep9.mp3'
  ]
};

class MusicPlayer {
    constructor() {
        this.audio = new Audio();
        this.isPlaying = false;
        this.currentTrack = null;
        this.playlist = [];
        this.queue = [];
        this.currentIndex = 0;
        this.isRepeat = false;
        this.isShuffle = false;
        this.currentMood = null;
        this.sessionId = null;
        this.sessionStartTime = null;
        this.tracksPlayed = [];
        
        // Initialize playlists - these are only fallbacks if API fails
        // Actual playlists will be loaded from the server
        this.playlists = {};

        this.initializeElements();
        this.bindEvents();
        this.setupAudioEvents();
        
        // Set initial volume
        this.audio.volume = 0.8;
        
        // Handle recommended mood if provided
        const recommendedMood = document.getElementById('recommended-mood');
        if (recommendedMood && recommendedMood.value) {
            this.changeMood(recommendedMood.value);
        }
    }

    initializeElements() {
        // Player controls
        this.playButton = document.getElementById('btn-play');
        this.prevButton = document.getElementById('btn-prev');
        this.nextButton = document.getElementById('btn-next');
        this.forwardButton = document.getElementById('btn-forward');
        this.backwardButton = document.getElementById('btn-backward');
        this.repeatButton = document.getElementById('btn-repeat');
        this.shuffleButton = document.getElementById('btn-shuffle');
        
        // Progress elements
        this.progressBar = document.querySelector('.progress-bar-fill');
        this.currentTimeDisplay = document.getElementById('current-time');
        this.totalTimeDisplay = document.getElementById('total-time');
        
        // Track info
        this.trackTitle = document.getElementById('current-track-name');
        this.trackArtist = document.getElementById('current-track-artist');
        
        // Volume control
        this.volumeSlider = document.getElementById('volume-slider');
        
        // Track list and queue
        this.trackList = document.getElementById('track-list');
        this.queueTracks = document.getElementById('queue-tracks');
        
        // Mood buttons
        this.moodButtons = document.querySelectorAll('.mood-button');
        
        // Feedback elements
        this.feedbackArea = document.getElementById('mood-feedback-area');
        this.feedbackForm = document.getElementById('mood-feedback-form');
        this.closeFeedbackButton = document.getElementById('btn-close-feedback');
        this.closeFeedbackXButton = document.getElementById('btn-close-feedback-x');
        this.showFeedbackButton = document.getElementById('btn-show-feedback');
        this.endSessionButton = document.getElementById('btn-end-session');
        
        // Therapy tip elements
        this.therapyTip = document.getElementById('therapy-tip');
        this.refreshTipButton = document.getElementById('btn-refresh-tip');
        
        // Queue management
        this.clearQueueButton = document.getElementById('btn-clear-queue');
    }

    bindEvents() {
        // Player control events
        if (this.playButton) this.playButton.addEventListener('click', () => this.togglePlay());
        if (this.prevButton) this.prevButton.addEventListener('click', () => this.playPrevious());
        if (this.nextButton) this.nextButton.addEventListener('click', () => this.playNext());
        if (this.forwardButton) this.forwardButton.addEventListener('click', () => this.forward(10));
        if (this.backwardButton) this.backwardButton.addEventListener('click', () => this.backward(10));
        if (this.repeatButton) this.repeatButton.addEventListener('click', () => this.toggleRepeat());
        if (this.shuffleButton) this.shuffleButton.addEventListener('click', () => this.toggleShuffle());
        
        // Progress bar click
        const progressElement = document.querySelector('.progress');
        if (progressElement) {
            progressElement.addEventListener('click', (e) => {
                const progressBar = e.currentTarget;
                const clickPosition = e.offsetX / progressBar.offsetWidth;
                this.audio.currentTime = clickPosition * this.audio.duration;
            });
        }
        
        // Volume control
        if (this.volumeSlider) {
            this.volumeSlider.addEventListener('input', (e) => {
                this.audio.volume = e.target.value / 100;
            });
        }
        
        // Mood button events
        if (this.moodButtons) {
            this.moodButtons.forEach(button => {
                button.addEventListener('click', () => {
                    const mood = button.dataset.mood;
                    this.changeMood(mood);
                });
            });
        }
        
        // Feedback form events
        if (this.showFeedbackButton) this.showFeedbackButton.addEventListener('click', () => this.showFeedback());
        if (this.closeFeedbackButton) this.closeFeedbackButton.addEventListener('click', () => this.hideFeedback());
        if (this.closeFeedbackXButton) this.closeFeedbackXButton.addEventListener('click', () => this.hideFeedback());
        if (this.feedbackForm) this.feedbackForm.addEventListener('submit', (e) => this.handleFeedbackSubmit(e));
        if (this.endSessionButton) this.endSessionButton.addEventListener('click', () => this.showFeedback());
        
        // Queue management
        if (this.clearQueueButton) this.clearQueueButton.addEventListener('click', () => this.clearQueue());
        
        // Therapy tip refresh
        if (this.refreshTipButton) this.refreshTipButton.addEventListener('click', () => this.refreshTherapyTip());
    }

    setupAudioEvents() {
        this.audio.addEventListener('timeupdate', () => this.updateProgress());
        this.audio.addEventListener('loadedmetadata', () => this.updateTotalTime());
        this.audio.addEventListener('ended', () => this.handleTrackEnd());
        this.audio.addEventListener('error', (e) => this.handleAudioError(e));
        
        // Add play event to track played tracks
        this.audio.addEventListener('play', () => {
            if (this.currentTrack && !this.tracksPlayed.some(t => t.id === this.currentTrack.id)) {
                this.tracksPlayed.push({
                    id: this.currentTrack.id,
                    title: this.currentTrack.title,
                    artist: this.currentTrack.artist,
                    timestamp: new Date().toISOString()
                });
            }
        });
    }

    loadTrack(track) {
        if (!track) return;
        
        this.currentTrack = track;
        let filePath = track.file;
        if (!filePath.startsWith('/')) filePath = '/' + filePath;
        this.audio.src = filePath;
        this.audio.load();

        this.updateTrackInfo();
        this.highlightCurrentTrack();
        this.progressBar.style.width = '0%';
        document.title = `${track.title} - Music Therapy`;

        // Update total time and playlist duration when metadata is loaded
        this.audio.onloadedmetadata = () => {
            if (this.totalTimeDisplay && !isNaN(this.audio.duration)) {
                this.totalTimeDisplay.textContent = this.formatTime(this.audio.duration);
            }
            // Also update the duration in the playlist UI for the current track
            const trackItems = document.querySelectorAll('.track-item');
            if (trackItems && trackItems.length > this.currentIndex) {
                const durationElem = trackItems[this.currentIndex].querySelector('.track-duration');
                if (durationElem) {
                    durationElem.textContent = this.formatTime(this.audio.duration);
                }
            }
        };
    }

    togglePlay() {
        if (this.isPlaying) {
            this.audio.pause();
            this.playButton.innerHTML = '<i class="fas fa-play"></i>';
        } else {
            // If we have a track, play it
            if (this.currentTrack) {
                const playPromise = this.audio.play();
                
                if (playPromise !== undefined) {
                    playPromise.then(_ => {
                        // Playback started successfully
                        this.playButton.innerHTML = '<i class="fas fa-pause"></i>';
                    })
                    .catch(error => {
                        // Auto-play was prevented
                        this.showNotification("Playback blocked by browser. Please interact with the page first.", "warning");
                        this.isPlaying = false;
                    });
                }
            } else if (this.playlist.length > 0) {
                // If no track is loaded but we have a playlist, load the first track
                this.loadTrack(this.playlist[0]);
                this.togglePlay();
                return;
            } else {
                // No track and no playlist, show notification
                this.showNotification("Please select a mood first to load tracks", "info");
                return;
            }
        }
        this.isPlaying = !this.isPlaying;
    }

    playNext() {
        if (this.queue.length > 0) {
            const nextTrack = this.queue.shift();
            this.loadTrack(nextTrack);
            this.updateQueueDisplay();
            if (this.isPlaying) this.audio.play();
        } else if (this.playlist.length > 0) {
            if (this.isShuffle) {
                const randomIndex = Math.floor(Math.random() * this.playlist.length);
                this.currentIndex = randomIndex;
            } else {
                this.currentIndex = (this.currentIndex + 1) % this.playlist.length;
            }
            this.loadTrack(this.playlist[this.currentIndex]);
            if (this.isPlaying) this.audio.play();
        }
    }

    playPrevious() {
        if (this.playlist.length > 0) {
            if (this.audio.currentTime > 3) {
                // If we're more than 3 seconds into the song, restart it
                this.audio.currentTime = 0;
            } else {
                // Otherwise go to previous track
                if (this.isShuffle) {
                    const randomIndex = Math.floor(Math.random() * this.playlist.length);
                    this.currentIndex = randomIndex;
                } else {
                    this.currentIndex = (this.currentIndex - 1 + this.playlist.length) % this.playlist.length;
                }
                this.loadTrack(this.playlist[this.currentIndex]);
            }
            if (this.isPlaying) this.audio.play();
        }
    }

    forward(seconds = 10) {
        this.audio.currentTime = Math.min(this.audio.currentTime + seconds, this.audio.duration);
    }

    backward(seconds = 10) {
        this.audio.currentTime = Math.max(this.audio.currentTime - seconds, 0);
    }

    toggleRepeat() {
        this.isRepeat = !this.isRepeat;
        this.repeatButton.classList.toggle('active');
        this.audio.loop = this.isRepeat;
    }

    toggleShuffle() {
        this.isShuffle = !this.isShuffle;
        this.shuffleButton.classList.toggle('active');
    }

    changeMood(mood) {
        if (!mood) return;
        this.currentMood = mood;
        this.tracksPlayed = [];
        this.sessionStartTime = new Date();

        // Update active state of mood buttons
        this.moodButtons.forEach(button => {
            button.classList.toggle('active', button.dataset.mood === mood);
        });

        // Show loading state
        this.trackList.innerHTML = '<p class="text-muted">Loading tracks...</p>';

        // Build playlist from static files
        const files = moodAudioFiles[mood] || [];
        this.playlist = files.map((file, idx) => ({
            id: `${mood}_${idx+1}`,
            title: `${mood.charAt(0).toUpperCase() + mood.slice(1)} Track ${idx+1}`,
            artist: mood.charAt(0).toUpperCase() + mood.slice(1),
            file: file,
            duration: '' // leave blank for now
        }));
        this.currentIndex = 0;

        // Update track list
        this.updateTrackList();

        // Load first track if playlist has tracks
        if (this.playlist.length > 0) {
            this.loadTrack(this.playlist[0]);
            this.showNotification(`Loaded ${this.playlist.length} tracks for ${mood} mood`, 'success');
        } else {
            this.showNotification(`No tracks found for ${mood} mood`, 'warning');
            this.trackList.innerHTML = '<p class="text-muted">No tracks available for this mood</p>';
        }
    }

    updateProgress() {
        if (this.audio.duration) {
            const progressPercent = (this.audio.currentTime / this.audio.duration) * 100;
            this.progressBar.style.width = progressPercent + '%';
            
            // Update current time display
            if (this.currentTimeDisplay) {
                this.currentTimeDisplay.textContent = this.formatTime(this.audio.currentTime);
            }
        }
    }

    updateTotalTime() {
        if (this.totalTimeDisplay && !isNaN(this.audio.duration)) {
            this.totalTimeDisplay.textContent = this.formatTime(this.audio.duration);
        }
    }

    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`;
    }

    handleTrackEnd() {
        if (this.isRepeat) {
            this.audio.play();
        } else {
            this.playNext();
        }
    }

    handleAudioError(e) {
        console.error('Audio error:', e);
        this.showNotification('Error playing track. Trying next track...', 'error');
        
        // Try to play the next track after a short delay
        setTimeout(() => this.playNext(), 1000);
    }

    updateTrackInfo() {
        if (this.currentTrack) {
            if (this.trackTitle) this.trackTitle.textContent = this.currentTrack.title || 'Unknown Track';
            if (this.trackArtist) this.trackArtist.textContent = this.currentTrack.artist || 'Unknown Artist';
        }
    }

    highlightCurrentTrack() {
        // Remove active class from all tracks
        const trackItems = document.querySelectorAll('.track-item');
        trackItems.forEach(item => item.classList.remove('active'));
        
        // Add active class to current track
        if (this.currentTrack) {
            const currentTrackItem = document.querySelector(`.track-item[data-id="${this.currentTrack.id}"]`);
            if (currentTrackItem) {
                currentTrackItem.classList.add('active');
                // Scroll to the track in the list
                currentTrackItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
    }

    updateTrackList() {
        if (!this.trackList) return;
        
        if (this.playlist.length === 0) {
            this.trackList.innerHTML = '<p class="text-muted">No tracks available for this mood</p>';
            return;
        }
        
        let html = '';
        
        this.playlist.forEach((track, index) => {
            html += `
                <div class="track-item ${this.currentIndex === index ? 'active' : ''}" data-id="${track.id}">
                    <div class="track-info">
                        <div class="track-title">${track.title || 'Unknown Track'}</div>
                        <div class="track-artist">${track.artist || 'Unknown Artist'}</div>
                    </div>
                    <div class="track-duration">${track.duration || '--:--'}</div>
                    <div class="track-actions">
                        <button class="track-play" data-index="${index}"><i class="fas fa-play"></i></button>
                        <button class="track-queue" data-index="${index}"><i class="fas fa-plus"></i></button>
                    </div>
                </div>
            `;
        });
        
        this.trackList.innerHTML = html;
        
        // Add event listeners for track actions
        document.querySelectorAll('.track-play').forEach(button => {
            button.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.index);
                this.currentIndex = index;
                this.loadTrack(this.playlist[index]);
                this.audio.play();
                this.isPlaying = true;
                this.playButton.innerHTML = '<i class="fas fa-pause"></i>';
            });
        });
        
        document.querySelectorAll('.track-queue').forEach(button => {
            button.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.index);
                this.queue.push(this.playlist[index]);
                this.updateQueueDisplay();
                this.showNotification(`Added "${this.playlist[index].title}" to queue`, 'success');
            });
        });
    }

    showFeedback() {
        if (this.feedbackArea) {
            this.feedbackArea.style.display = 'flex';
        }
    }

    hideFeedback() {
        if (this.feedbackArea) {
            this.feedbackArea.style.display = 'none';
        }
    }

    async handleFeedbackSubmit(e) {
        e.preventDefault();
        
        // Only proceed if we have a session ID
        if (!this.sessionId) {
            this.showNotification('Cannot save feedback without an active session', 'error');
            this.hideFeedback();
            return;
        }
        
        const finalMood = document.getElementById('final-mood').value;
        const effectivenessRating = document.getElementById('effectiveness-rating').value;
        const sessionNotes = document.getElementById('session-notes').value;
        
        // Calculate session duration in seconds
        const durationSeconds = Math.floor((new Date() - this.sessionStartTime) / 1000);
        
        try {
            const response = await fetch('/api/save-music-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    final_mood: finalMood,
                    tracks_played: this.tracksPlayed,
                    duration_seconds: durationSeconds,
                    effectiveness_rating: parseInt(effectivenessRating),
                    notes: sessionNotes
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to save session feedback');
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showNotification('Feedback saved successfully', 'success');
            } else {
                throw new Error(data.error || 'Unknown error occurred');
            }
            
            // Reset form and hide it
            this.feedbackForm.reset();
            this.hideFeedback();
            
        } catch (error) {
            console.error('Error saving session feedback:', error);
            this.showNotification('Failed to save feedback: ' + error.message, 'error');
        }
    }

    clearQueue() {
        this.queue = [];
        this.updateQueueDisplay();
        this.showNotification('Queue cleared', 'info');
    }

    updateQueueDisplay() {
        if (!this.queueTracks) return;
        
        if (this.queue.length === 0) {
            this.queueTracks.innerHTML = '<p class="text-muted">No tracks in queue</p>';
            return;
        }
        
        let html = '';
        
        this.queue.forEach((track, index) => {
            html += `
                <div class="track-item" data-id="${track.id}">
                    <div class="track-info">
                        <div class="track-title">${track.title || 'Unknown Track'}</div>
                        <div class="track-artist">${track.artist || 'Unknown Artist'}</div>
                    </div>
                    <div class="track-actions">
                        <button class="queue-remove" data-index="${index}"><i class="fas fa-times"></i></button>
                    </div>
                </div>
            `;
        });
        
        this.queueTracks.innerHTML = html;
        
        // Add event listeners for queue removal
        document.querySelectorAll('.queue-remove').forEach(button => {
            button.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.index);
                this.queue.splice(index, 1);
                this.updateQueueDisplay();
            });
        });
    }

    refreshTherapyTip() {
        // Only proceed if we have a current mood
        if (!this.currentMood) return;
        
        fetch('/api/music-recommendations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ mood: this.currentMood, create_session: false })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success' && data.therapy_tip && this.therapyTip) {
                this.therapyTip.textContent = data.therapy_tip;
            }
        })
        .catch(error => {
            console.error('Error refreshing therapy tip:', error);
        });
    }

    showNotification(message, type = 'info') {
        const notificationArea = document.getElementById('notification-area');
        if (!notificationArea) return;
        
        const notificationId = 'notification-' + Date.now();
        
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.id = notificationId;
        
        notification.innerHTML = `
            <i class="${this.getNotificationIcon(type)}"></i>
            <span>${message}</span>
            <button class="notification-close" data-id="${notificationId}">×</button>
        `;
        
        notificationArea.appendChild(notification);
        
        // Add close event
        notification.querySelector('.notification-close').addEventListener('click', () => {
            this.hideNotification(notificationId);
        });
        
        // Auto hide after 5 seconds
        setTimeout(() => {
            this.hideNotification(notificationId);
        }, 5000);
    }

    hideNotification(id) {
        const notification = document.getElementById(id);
        if (notification) {
            notification.classList.add('notification-hiding');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    }

    getNotificationIcon(type) {
        switch (type) {
            case 'success': return 'fas fa-check-circle';
            case 'error': return 'fas fa-exclamation-circle';
            case 'warning': return 'fas fa-exclamation-triangle';
            case 'info': 
            default: return 'fas fa-info-circle';
        }
    }
}

// Initialize player when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.musicPlayer = new MusicPlayer();
});
