import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask_wtf.csrf import CSRFProtect
# Add CORS support
from flask_cors import CORS
# Update import to use the consolidated models
from .models import (
    db,
    User,
    MoodEntry,
    JournalEntry,
    ChatHistory,
    MusicTherapySession,
    UserActivity
)
from .utils.ai_utils import analyze_sentiment, analyze_emotions, get_mood_patterns, generate_chat_response, logger
from .config import SECRET_KEY, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
import json
import random
import re
import asyncio

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['WTF_CSRF_ENABLED'] = False

# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": "*"}})

# Load configuration from config.py
app.config.from_object('src.mental_health_tracker.config')

# Initialize extensions with app
db.init_app(app)
csrf = CSRFProtect(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Context processor to provide current year to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

# Create database tables
with app.app_context():
    # db.drop_all()  # Drop all existing tables - REMOVED to preserve user data between sessions
    db.create_all()  # Create tables with new schema

# Simple user database (replace with a real database in production)
users = {}

# Create a WTForm for mood entry
class MoodEntryForm(FlaskForm):
    mood_score = SelectField('Mood Score', choices=[(1, 'Very Sad'), (2, 'Sad'), (3, 'Neutral'), (4, 'Happy'), (5, 'Very Happy')], coerce=int)
    activities = StringField('Activities')
    notes = TextAreaField('Notes')
    submit = SubmitField('Save Entry')

# Create a WTForm for journal entry
class JournalEntryForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Your Thoughts', validators=[DataRequired()])
    submit = SubmitField('Save Entry')

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Check if username or email already exists
    if User.query.filter_by(username=username).first():
        flash('Username already exists', 'error')
        return redirect(url_for('auth.login'))
    
    if User.query.filter_by(email=email).first():
        flash('Email already exists', 'error')
        return redirect(url_for('auth.login'))
    
    # Create new user with hashed password
    user = User(
        username=username,
        email=email,
        password=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.commit()
    
    flash('Registration successful! Please login.', 'success')
    return redirect(url_for('auth.login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))

@app.route('/reset-password')
def reset_password():
    return render_template('reset_password.html')

@app.route('/music-therapy')
def music_therapy():
    # Check if user is logged in
    user_id = session.get('user_id')
    recommended_mood = None
    
    # If user is logged in, analyze their mood patterns and track activity
    if user_id:
        track_activity(user_id, 'music', 'Started a music therapy session')
        user = User.query.get(user_id)
        if user:
            try:
                # Get the latest mood entry
                latest_mood = MoodEntry.query.filter_by(user_id=user_id).order_by(MoodEntry.date_created.desc()).first()
                if latest_mood:
                    # Simple mapping from mood score to therapy moods
                    mood_mapping = {
                        1: 'sad',
                        2: 'anxious',
                        3: 'calm',
                        4: 'happy',
                        5: 'energetic'
                    }
                    recommended_mood = mood_mapping.get(latest_mood.mood_score, 'calm')
            except Exception as e:
                print(f"Error getting mood recommendation: {str(e)}")
                recommended_mood = 'calm'
    
    return render_template('music_therapy.html', recommended_mood=recommended_mood)

@app.route('/api/music-recommendations', methods=['POST'])
def music_recommendations():
    """Get music recommendations based on mood"""
    try:
        if not request.is_json:
            app.logger.error("Request is not JSON format")
            return jsonify({"status": "error", "error": "Request must be JSON"}), 400
            
        data = request.json
        mood = data.get('mood', 'calm')
        create_session = data.get('create_session', False)
        session_id = None
        
        app.logger.info(f"Received music recommendations request for mood: {mood}")
        
        # If user is logged in and wants to create a session, record it
        if session.get('user_id') and create_session:
            user_id = session.get('user_id')
            app.logger.info(f"Creating music session for user_id: {user_id}, mood: {mood}")
            new_session = MusicTherapySession(
                user_id=user_id,
                initial_mood=mood,
                start_time=datetime.utcnow()
            )
            
            db.session.add(new_session)
            db.session.commit()
            session_id = new_session.id
            app.logger.info(f"Created session with ID: {session_id}")
        
        # Scan the audio directory for actual files
        app.logger.info(f"Scanning audio files for mood: {mood}")
        mood_tracks = scan_audio_files(mood)
        
        # Check if we're using real files or demo files
        is_demo_mode = True
        if mood_tracks and 'demo' not in mood_tracks[0].get('id', '').lower():
            is_demo_mode = False
        
        app.logger.info(f"Found {len(mood_tracks)} tracks. Demo mode: {is_demo_mode}")
        
        # Get therapy tip for this mood
        therapy_tip = get_therapy_tip(mood)
        
        response_data = {
            "status": "success",
            "mood": mood,
            "recommendations": mood_tracks,
            "therapy_tip": therapy_tip,
            "is_demo_mode": is_demo_mode
        }
        
        # If user is logged in, include session ID
        if session_id:
            response_data["session_id"] = session_id
            
        response = jsonify(response_data)
        # Add CORS headers to ensure browser can access the response
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        
        app.logger.info(f"Successfully responded with {len(mood_tracks)} recommendations")
        return response
    except Exception as e:
        app.logger.error(f"Error processing music recommendations: {str(e)}")
        error_response = jsonify({
            "status": "error",
            "error": f"An error occurred while processing music recommendations: {str(e)}"
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        error_response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return error_response, 500

# Function to scan audio directory for files by mood
def scan_audio_files(mood):
    """Scan the audio directory for files matching the mood"""
    try:
        # Path to the main audio folder - use absolute path to ensure correct resolution
        audio_dir = os.path.join(app.static_folder, 'audio')
        app.logger.info(f"Looking for audio files in: {audio_dir}")
        
        # Fallback to hardcoded music library if directory doesn't exist or mood is invalid
        if not os.path.exists(audio_dir):
            app.logger.error(f"Audio directory does not exist: {audio_dir}")
            return music_library.get(mood, music_library['calm'])
        
        # Path to the specific mood folder (e.g., /static/audio/calm/)
        mood_dir = os.path.join(audio_dir, mood)
        app.logger.info(f"Looking for {mood} audio files in: {mood_dir}")
        
        # Get list of all audio files for the specified mood
        mood_files = []
        
        # First try to find files in the mood-specific directory
        if os.path.exists(mood_dir):
            app.logger.info(f"Mood directory exists: {mood_dir}")
            files_in_dir = os.listdir(mood_dir)
            app.logger.info(f"Found {len(files_in_dir)} files in directory: {files_in_dir}")
            
            # List all MP3 files in the mood directory
            for filename in files_in_dir:
                if filename.lower().endswith('.mp3'):
                    file_id = os.path.splitext(filename)[0]  # Remove extension
                    
                    # Create track info - ensure path starts with / for browser
                    track = {
                        'id': file_id,
                        'title': generate_title(file_id),
                        'artist': generate_artist(mood),
                        'duration': '3:30',  # Default duration
                        'file': f'/static/audio/{mood}/{filename}'
                    }
                    mood_files.append(track)
        else:
            app.logger.warning(f"Mood-specific directory not found: {mood_dir}")
        
        # If no mood-specific directory, try the original approach of finding files named with the mood prefix
        if not mood_files:
            app.logger.info(f"Checking main audio directory for files with prefix {mood}*.mp3")
            # Pattern to match files starting with the mood name (e.g., calm1.mp3)
            pattern = f"{mood}*.mp3"
            
            # List all files in the main audio directory matching the pattern
            for filename in os.listdir(audio_dir):
                if filename.lower().startswith(mood.lower()) and filename.lower().endswith('.mp3'):
                    file_id = os.path.splitext(filename)[0]  # Remove extension
                    
                    # Create track info - ensure path starts with / for browser
                    track = {
                        'id': file_id,
                        'title': generate_title(file_id),
                        'artist': generate_artist(mood),
                        'duration': '3:30',  # Default duration
                        'file': f'/static/audio/{filename}'
                    }
                    mood_files.append(track)
        
        # If no files found for this mood, return default library entries
        if not mood_files:
            app.logger.warning(f"No music files found for mood: {mood}. Using fallback library.")
            return music_library.get(mood, music_library['calm'])
        
        app.logger.info(f"Successfully found {len(mood_files)} tracks for mood: {mood}")
        
        # Sort the files by name for a predictable order
        mood_files.sort(key=lambda x: x['id'])
        
        return mood_files
    except Exception as e:
        app.logger.error(f"Error in scan_audio_files: {str(e)}")
        # Return fallback library in case of error
        return music_library.get(mood, music_library['calm'])

# Helper function to generate a title from file ID
def generate_title(file_id):
    """Generate a user-friendly title from the file ID"""
    # Remove numbers and special chars
    base_name = ''.join(c for c in file_id if not c.isdigit())
    
    # Convert to title case and add some variety
    mood_titles = {
        'happy': ['Joyful Moment', 'Sunny Day', 'Celebration', 'Uplifting Spirits', 'Cheerful Melody'],
        'sad': ['Reflective Moment', 'Rainy Day', 'Melancholy', 'Emotional Journey', 'Heartfelt'],
        'calm': ['Peaceful Moment', 'Tranquil Waters', 'Serenity', 'Gentle Breeze', 'Mindfulness'],
        'focus': ['Concentration', 'Deep Work', 'Mind Clarity', 'Flow State', 'Productivity Zone'],
        'energetic': ['Power Up', 'Dynamic Move', 'Energy Flow', 'Motivation Boost', 'Active Beat'],
        'sleep': ['Dreamy Night', 'Gentle Lullaby', 'Bedtime Story', 'Night Whispers', 'Starry Sky']
    }
    
    # Extract mood from file_id
    for mood in mood_titles:
        if mood in file_id.lower():
            # Get a random title based on the hash of the file_id for consistency
            import hashlib
            hash_val = int(hashlib.md5(file_id.encode()).hexdigest(), 16)
            return mood_titles[mood][hash_val % len(mood_titles[mood])]
    
    # Default title if no mood matched
    return f"Track {file_id}"

# Helper function to generate an artist name
def generate_artist(mood):
    """Generate an artist name based on the mood"""
    mood_artists = {
        'happy': ['Joy Makers', 'Sunshine Band', 'Happy Vibes', 'Uplift'],
        'sad': ['Melancholy', 'Deep Feelings', 'Reflection', 'Soul Journey'],
        'calm': ['Serenity Now', 'Peace Makers', 'Tranquil Sounds', 'Zen Masters'],
        'focus': ['Concentration', 'Mind Shapers', 'Focus Flow', 'Brain Waves'],
        'energetic': ['Energy Boost', 'Power Up', 'Active Minds', 'Momentum'],
        'sleep': ['Dream Weavers', 'Night Whisperers', 'Slumber', 'Sleep Well']
    }
    
    # Get artist for mood or default
    artists = mood_artists.get(mood, ['Unknown Artist'])
    
    # Use a random artist
    return random.choice(artists)

# Music library (fallback if directory doesn't exist)
music_library = {
    'happy': [
        {'id': 'happy1', 'title': 'Good Vibes', 'artist': 'Positive Energy', 'duration': '3:45', 'file': 'static/audio/happy1.mp3'},
        {'id': 'happy2', 'title': 'Sunshine Day', 'artist': 'Mood Lifters', 'duration': '4:20', 'file': 'static/audio/happy2.mp3'},
        {'id': 'happy3', 'title': 'Joyful Morning', 'artist': 'Spirit Raisers', 'duration': '3:15', 'file': 'static/audio/happy3.mp3'},
    ],
    'sad': [
        {'id': 'sad1', 'title': 'Gentle Comfort', 'artist': 'Emotion Healers', 'duration': '5:10', 'file': 'static/audio/sad1.mp3'},
        {'id': 'sad2', 'title': 'Rainy Day', 'artist': 'Soul Soothers', 'duration': '4:55', 'file': 'static/audio/sad2.mp3'},
        {'id': 'sad3', 'title': 'Reflection Time', 'artist': 'Inner Peace', 'duration': '5:30', 'file': 'static/audio/sad3.mp3'},
    ],
    'calm': [
        {'id': 'calm1', 'title': 'Ocean Waves', 'artist': 'Nature Sounds', 'duration': '6:15', 'file': 'static/audio/calm1.mp3'},
        {'id': 'calm2', 'title': 'Peaceful Garden', 'artist': 'Serenity', 'duration': '5:45', 'file': 'static/audio/calm2.mp3'},
        {'id': 'calm3', 'title': 'Gentle Breeze', 'artist': 'Relaxation', 'duration': '4:50', 'file': 'static/audio/calm3.mp3'},
    ],
    'focus': [
        {'id': 'focus1', 'title': 'Deep Focus', 'artist': 'Concentration', 'duration': '7:25', 'file': 'static/audio/focus1.mp3'},
        {'id': 'focus2', 'title': 'Flow State', 'artist': 'Mind Shapers', 'duration': '6:40', 'file': 'static/audio/focus2.mp3'},
        {'id': 'focus3', 'title': 'Productivity Zone', 'artist': 'Brain Waves', 'duration': '5:55', 'file': 'static/audio/focus3.mp3'},
    ],
    'energetic': [
        {'id': 'energetic1', 'title': 'Morning Boost', 'artist': 'Energy Flow', 'duration': '3:30', 'file': 'static/audio/energetic1.mp3'},
        {'id': 'energetic2', 'title': 'Power Up', 'artist': 'Motivators', 'duration': '4:15', 'file': 'static/audio/energetic2.mp3'},
        {'id': 'energetic3', 'title': 'Dynamic Day', 'artist': 'Momentum', 'duration': '3:45', 'file': 'static/audio/energetic3.mp3'},
    ],
    'sleep': [
        {'id': 'sleep1', 'title': 'Starry Night', 'artist': 'Dream Weavers', 'duration': '8:30', 'file': 'static/audio/sleep1.mp3'},
        {'id': 'sleep2', 'title': 'Gentle Lullaby', 'artist': 'Sleep Therapy', 'duration': '7:45', 'file': 'static/audio/sleep2.mp3'},
        {'id': 'sleep3', 'title': 'Night Rain', 'artist': 'Slumber', 'duration': '9:10', 'file': 'static/audio/sleep3.mp3'},
    ]
}

def get_therapy_tip(mood):
    """Provide therapy tips based on mood"""
    tips = {
        'happy': "Enhance your positive mood with upbeat music and try to be mindful of what's contributing to your happiness.",
        'sad': "Sad music can help validate your feelings. Start with music matching your mood, then gradually shift to more uplifting tunes.",
        'calm': "Focus on slow, rhythmic music to maintain your peaceful state. This is perfect for meditation and mindfulness practices.",
        'focus': "Instrumental music without lyrics helps maintain concentration and enhances mental performance.",
        'energetic': "Channel your energy with dynamic beats. These tracks can help motivate you for exercise or productive tasks.",
        'sleep': "These gentle melodies can help calm your mind and prepare your body for restful sleep."
    }
    return tips.get(mood, "Listen to music that resonates with how you're feeling right now.")

@app.route('/api/save-music-session', methods=['POST'])
def save_music_session():
    """Save a user's music therapy session data"""
    if not session.get('user_id'):
        return jsonify({"error": "You must be logged in"}), 401
        
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
        
    data = request.json
    session_id = data.get('session_id')
    final_mood = data.get('final_mood')
    tracks_played = data.get('tracks_played', [])
    duration_seconds = data.get('duration_seconds', 0)
    effectiveness_rating = data.get('effectiveness_rating')
    notes = data.get('notes', '')
    
    # Validate the session_id
    if not session_id:
        return jsonify({"error": "Session ID is required"}), 400
    
    try:
        # Find the music therapy session
        music_session = MusicTherapySession.query.get(session_id)
        
        if not music_session:
            return jsonify({"error": "Session not found"}), 404
            
        # Check if the session belongs to the logged-in user
        if music_session.user_id != session.get('user_id'):
            return jsonify({"error": "Unauthorized access to this session"}), 403
            
        # Update the session
        music_session.end_time = datetime.utcnow()
        music_session.final_mood = final_mood
        music_session.tracks_played = json.dumps(tracks_played)
        music_session.duration_seconds = duration_seconds
        music_session.effectiveness_rating = effectiveness_rating
        music_session.notes = notes
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Session data saved successfully",
            "session_id": session_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/music-history', methods=['GET'])
def music_history():
    """Get user's music therapy session history"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({"error": "You must be logged in"}), 401
    
    try:
        # Get the user's music therapy sessions
        sessions = MusicTherapySession.query.filter_by(user_id=user_id)\
            .order_by(MusicTherapySession.start_time.desc())\
            .limit(10)\
            .all()
        
        session_list = []
        for s in sessions:
            # Parse tracks_played if it's not None
            tracks = []
            if s.tracks_played:
                try:
                    tracks = json.loads(s.tracks_played)
                except:
                    tracks = []
            
            session_list.append({
                "id": s.id,
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "duration_seconds": s.duration_seconds,
                "initial_mood": s.initial_mood,
                "final_mood": s.final_mood,
                "tracks_played": tracks,
                "effectiveness_rating": s.effectiveness_rating,
                "notes": s.notes
            })
        
        return jsonify({
            "status": "success",
            "sessions": session_list
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/focus-mode')
def focus_mode():
    if 'user_id' not in session:
        return render_template('focus/dashboard.html', sessions=None, requires_login=True)
    
    sessions = FocusSession.query.filter_by(user_id=session['user_id']).order_by(FocusSession.start_time.desc()).limit(10).all()
    return render_template('focus/dashboard.html', sessions=sessions, requires_login=False)

@app.route('/games')
def games():
    return render_template('games.html')

@app.route('/games-dashboard')
def games_dashboard():
    return render_template('games_dashboard.html')

@app.route('/honor-score')
def honor_score():
    return render_template('honor_score.html')

@app.route('/profile')
def profile():
    # Check if user is logged in
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    
    user_id = session.get('user_id')
    
    # Get recent mood entries
    recent_moods = MoodEntry.query.filter_by(user_id=user_id).order_by(MoodEntry.date_created.desc()).limit(7).all()
    
    # Get recent journal entries
    recent_journals = JournalEntry.query.filter_by(user_id=user_id).order_by(JournalEntry.date_created.desc()).limit(3).all()
    
    # Calculate overall mood average if there are entries
    mood_avg = None
    if recent_moods:
        mood_sum = sum(entry.mood_score for entry in recent_moods)
        mood_avg = round(mood_sum / len(recent_moods), 1)
    
    return render_template('profile.html', 
                          recent_moods=recent_moods, 
                          recent_journals=recent_journals,
                          mood_avg=mood_avg)

def track_activity(user_id, activity_type, description):
    """
    Helper function to track user activities
    
    Args:
        user_id (int): The ID of the user
        activity_type (str): Type of activity ('music', 'mood', 'journal', 'focus')
        description (str): Description of the activity
    """
    activity = UserActivity(
        user_id=user_id,
        activity_type=activity_type,
        description=description
    )
    db.session.add(activity)
    db.session.commit()

@app.route('/dashboard')
@login_required
def dashboard():
    # Get recent mood entries
    recent_moods = MoodEntry.query.filter_by(user_id=current_user.id).order_by(MoodEntry.date_created.desc()).limit(10).all()
    
    # Get recent activities
    recent_activities = UserActivity.query.filter_by(user_id=current_user.id).order_by(UserActivity.created_at.desc()).limit(5).all()
    
    # Get recent journal entries
    journal_entries = JournalEntry.query.filter_by(user_id=current_user.id).order_by(JournalEntry.created_at.desc()).limit(2).all()
    
    # Calculate mood trend
    mood_trend = None
    if recent_moods:
        latest_mood = sum(mood.mood_score for mood in recent_moods[:3]) / min(len(recent_moods), 3)
        older_mood = sum(mood.mood_score for mood in recent_moods[-3:]) / min(len(recent_moods), 3)
        mood_trend = "improving" if latest_mood > older_mood else "steady" if latest_mood == older_mood else "declining"

    # Prepare chart data for the last 10 moods (reverse for chronological order)
    if recent_moods:
        chart_dates = [mood.date_created.strftime('%a') for mood in reversed(recent_moods)]
        chart_scores = [mood.mood_score for mood in reversed(recent_moods)]
    else:
        chart_dates = []
        chart_scores = []

    return render_template('dashboard.html',
                         recent_moods=recent_moods,
                         recent_activities=recent_activities,
                         journal_entries=journal_entries,
                         mood_trend=mood_trend,
                         chart_dates=chart_dates,
                         chart_scores=chart_scores)

# Journal routes
@app.route('/journal')
def journal():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    
    return redirect(url_for('journal.index'))

@app.route('/journal/new', methods=['GET', 'POST'])
def journal_new():
    form = JournalEntryForm()
    
    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data
        user_id = session.get('user_id')
        
        if not user_id:
            flash('Please log in to create a journal entry', 'error')
            return redirect(url_for('auth.login'))
            
        # Analyze sentiment and emotions using AI
        sentiment_score, sentiment_label = analyze_sentiment(content)
        emotions_json = analyze_emotions(content)
        
        # Generate AI recommendations based on emotions
        emotions = json.loads(emotions_json)
        recommendations = generate_recommendations(emotions)
        
        # Create new journal entry with AI analysis
        new_entry = JournalEntry(
            title=title,
            content=content,
            user_id=user_id,
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            key_emotions=emotions_json
        )
        
        db.session.add(new_entry)
        db.session.commit()
        
        # Track journal entry
        track_activity(user_id, 'journal', f'Added journal entry: {title}')
        
        flash('Journal entry created successfully!', 'success')
        return redirect(url_for('journal.index'))
        
    return render_template('journal_new.html', form=form)

def generate_recommendations(emotions):
    """Generate personalized recommendations based on emotional analysis"""
    recommendations = []
    
    # Analyze dominant emotions
    dominant_emotion = max(emotions.items(), key=lambda x: x[1])[0]
    
    # Generate recommendations based on emotions
    if dominant_emotion == 'sadness' and emotions['sadness'] > 0.7:
        recommendations.append({
            'type': 'activity',
            'title': 'Try a Mood-Boosting Activity',
            'description': 'Consider going for a walk, practicing gratitude, or engaging in a hobby you enjoy.'
        })
    elif dominant_emotion == 'anger' and emotions['anger'] > 0.7:
        recommendations.append({
            'type': 'technique',
            'title': 'Practice Anger Management',
            'description': 'Try deep breathing exercises or progressive muscle relaxation to calm down.'
        })
    elif dominant_emotion == 'anxiety' and emotions['anxiety'] > 0.7:
        recommendations.append({
            'type': 'meditation',
            'title': 'Mindfulness Meditation',
            'description': 'Try a 5-minute mindfulness meditation to reduce anxiety and stress.'
        })
    
    # Add general wellness recommendations
    recommendations.append({
        'type': 'general',
        'title': 'General Wellness',
        'description': 'Remember to stay hydrated, get enough sleep, and maintain a balanced diet.'
    })
    
    return recommendations

@app.route('/journal/view/<int:entry_id>')
def journal_view(entry_id):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    
    entry = JournalEntry.query.get_or_404(entry_id)
    
    # Ensure the entry belongs to the current user
    if entry.user_id != session['user_id']:
        abort(403)
    
    # Clean up any encryption tokens in the title and content for display
    if entry.title:
        entry.title = re.sub(r'[A-Za-z0-9+/]{20,}={0,2}', '', entry.title)
        entry.title = re.sub(r'[A-Za-z0-9]{10,}\.[A-Za-z0-9]{10,}', '', entry.title)
    
    if entry.content:
        entry.content = re.sub(r'[A-Za-z0-9+/]{20,}={0,2}', '', entry.content)
        entry.content = re.sub(r'[A-Za-z0-9]{10,}\.[A-Za-z0-9]{10,}', '', entry.content)
    
    # Add a template filter to parse JSON
    @app.template_filter('fromjson')
    def fromjson_filter(value):
        try:
            return json.loads(value)
        except:
            return {}
    
    return render_template('journal/view.html', 
                          entry=entry, 
                          generate_recommendations=generate_recommendations)

@app.route('/journal/edit/<int:entry_id>', methods=['GET', 'POST'])
def journal_edit(entry_id):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    
    entry = JournalEntry.query.get_or_404(entry_id)
    
    # Ensure the entry belongs to the current user
    if entry.user_id != session['user_id']:
        abort(403)
    
    # Clean up any encryption tokens in the title and content for display
    if entry.title:
        entry.title = re.sub(r'[A-Za-z0-9+/]{20,}={0,2}', '', entry.title)
        entry.title = re.sub(r'[A-Za-z0-9]{10,}\.[A-Za-z0-9]{10,}', '', entry.title)
    
    if entry.content:
        entry.content = re.sub(r'[A-Za-z0-9+/]{20,}={0,2}', '', entry.content)
        entry.content = re.sub(r'[A-Za-z0-9]{10,}\.[A-Za-z0-9]{10,}', '', entry.content)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            flash('Title and content are required', 'error')
            return redirect(url_for('journal_edit', entry_id=entry.id))
        
        try:
            # Clean up any potential tokens in the submitted content
            title = re.sub(r'[A-Za-z0-9+/]{20,}={0,2}', '', title)
            title = re.sub(r'[A-Za-z0-9]{10,}\.[A-Za-z0-9]{10,}', '', title)
            content = re.sub(r'[A-Za-z0-9+/]{20,}={0,2}', '', content)
            content = re.sub(r'[A-Za-z0-9]{10,}\.[A-Za-z0-9]{10,}', '', content)
            
            entry.title = title
            entry.content = content
            
            # Update sentiment and emotion analysis
            sentiment_score, sentiment_label = analyze_sentiment(content)
            emotions_json = analyze_emotions(content)
            
            entry.sentiment_score = sentiment_score
            entry.sentiment_label = sentiment_label
            entry.key_emotions = emotions_json
            
            db.session.commit()
            flash('Journal entry updated successfully', 'success')
            return redirect(url_for('journal_view', entry_id=entry.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating journal entry: {str(e)}', 'error')
            return redirect(url_for('journal_edit', entry_id=entry.id))
    
    return render_template('journal/form.html', entry=entry)

@app.route('/journal/delete/<int:entry_id>', methods=['POST'])
def journal_delete(entry_id):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    
    entry = JournalEntry.query.get_or_404(entry_id)
    
    # Ensure the entry belongs to the current user
    if entry.user_id != session['user_id']:
        abort(403)
    
    try:
        db.session.delete(entry)
        db.session.commit()
        flash('Journal entry deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting journal entry: {str(e)}', 'error')
    
    return redirect(url_for('journal'))

# API endpoint for real-time journal analysis
@app.route('/api/analyze-journal', methods=['POST'])
def analyze_journal():
    if not session.get('user_id'):
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({'error': 'No content provided'}), 400
    
    content = data['content']
    
    try:
        # Analyze sentiment and emotions
        sentiment_score, sentiment_label = analyze_sentiment(content)
        emotions_json = analyze_emotions(content)
        
        # Generate recommendations based on emotions
        emotions = json.loads(emotions_json)
        recommendations = generate_recommendations(emotions)
        
        return jsonify({
            'sentiment_score': sentiment_score,
            'sentiment_label': sentiment_label,
            'emotions': emotions,
            'recommendations': recommendations
        })
    except Exception as e:
        logger.error(f"Error in journal analysis API: {str(e)}")
        return jsonify({'error': 'Analysis failed'}), 500

# Mood Tracker routes
@app.route('/mood-tracker')
def mood_tracker():
    # Check if user is logged in
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access the mood tracker', 'error')
        return redirect(url_for('auth.login'))
    
    # Get the mood entries for the user, ordered by date
    entries = MoodEntry.query.filter_by(user_id=user_id).order_by(MoodEntry.date_created.desc()).all()
    
    # Analyze emotional patterns
    pattern_data = analyze_emotional_patterns(user_id)
    
    return render_template('mood_tracker.html', entries=entries, pattern_data=pattern_data)

def analyze_emotional_patterns(user_id):
    """Analyze emotional patterns over time"""
    try:
        # Get recent journal entries
        recent_entries = JournalEntry.query.filter_by(user_id=user_id).order_by(JournalEntry.date_created.desc()).limit(10).all()
        
        if not recent_entries:
            return None
            
        # Aggregate emotions over time
        emotional_data = []
        for entry in recent_entries:
            emotions = json.loads(entry.key_emotions)
            emotional_data.append({
                'date': entry.date_created.strftime('%Y-%m-%d'),
                'emotions': emotions,
                'sentiment': entry.sentiment_score
            })
            
        # Calculate emotional trends
        trends = {
            'overall_sentiment': sum(d['sentiment'] for d in emotional_data) / len(emotional_data),
            'dominant_emotions': {},
            'emotional_stability': calculate_emotional_stability(emotional_data)
        }
        
        # Find dominant emotions
        all_emotions = {}
        for entry in emotional_data:
            for emotion, score in entry['emotions'].items():
                if emotion not in all_emotions:
                    all_emotions[emotion] = []
                all_emotions[emotion].append(score)
                
        for emotion, scores in all_emotions.items():
            trends['dominant_emotions'][emotion] = sum(scores) / len(scores)
            
        return trends
    except Exception as e:
        logger.error(f"Error analyzing emotional patterns: {str(e)}")
        return None

def calculate_emotional_stability(emotional_data):
    """Calculate emotional stability based on sentiment variance"""
    try:
        sentiments = [d['sentiment'] for d in emotional_data]
        if len(sentiments) < 2:
            return 0.5  # Neutral stability if not enough data
            
        # Calculate variance in sentiment
        mean = sum(sentiments) / len(sentiments)
        variance = sum((s - mean) ** 2 for s in sentiments) / len(sentiments)
        
        # Convert variance to stability score (0-1)
        # Lower variance = higher stability
        max_variance = 1.0
        stability = max(0, 1 - (variance / max_variance))
        
        return stability
    except Exception as e:
        logger.error(f"Error calculating emotional stability: {str(e)}")
        return 0.5

@app.route('/mood-tracker/new', methods=['GET', 'POST'])
def mood_new():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    
    form = MoodEntryForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            mood_score = form.mood_score.data
            notes = form.notes.data
            activities = form.activities.data
            
            # Analyze sentiment of notes if provided
            sentiment_score = None
            sentiment_label = None
            if notes:
                sentiment_score, sentiment_label = analyze_sentiment(notes)
            
            new_entry = MoodEntry(
                mood_score=mood_score,
                notes=notes,
                activities=activities,
                user_id=session['user_id'],
                sentiment_score=sentiment_score,
                sentiment_label=sentiment_label
            )
            
            db.session.add(new_entry)
            db.session.commit()
            
            # Track mood entry
            mood_label = ['Very Sad', 'Sad', 'Neutral', 'Happy', 'Very Happy'][mood_score - 1]
            track_activity(session['user_id'], 'mood', f'Logged mood: {mood_label}')
            
            flash('Mood entry created successfully!', 'success')
            return redirect(url_for('mood_tracker'))
    
    return render_template('mood/form.html', form=form)

@app.route('/mood-tracker/delete/<int:entry_id>', methods=['POST'])
def mood_delete(entry_id):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    
    entry = MoodEntry.query.get_or_404(entry_id)
    
    # Ensure the entry belongs to the current user
    if entry.user_id != session['user_id']:
        abort(403)
    
    try:
        db.session.delete(entry)
        db.session.commit()
        flash('Mood entry deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting mood entry: {str(e)}', 'error')
    
    return redirect(url_for('mood_tracker'))

@app.route('/chat')
def chat():
    if not session.get('user_id'):
        flash('Please login to access the chat', 'error')
        return redirect(url_for('auth.login'))
    return render_template('chat.html')

@app.route('/ai-chat')
def ai_chat():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
        
    user_id = session.get('user_id')
    
    # Get user's emotional patterns and mood patterns
    patterns = get_mood_patterns(user_id, db)
    emotional_patterns = analyze_emotional_patterns(user_id)
    
    # Get recent chat history
    chat_history = ChatHistory.query.filter_by(user_id=user_id).order_by(ChatHistory.timestamp.desc()).limit(10).all()
    
    return render_template('ai_chat.html', 
                         chat_history=chat_history,
                         patterns=patterns,
                         emotional_patterns=emotional_patterns)

@app.route('/api/chat', methods=['POST'])
def chat_api():
    try:
        # Get user ID from session
        user_id = session.get('user_id')
        print(f"Processing message from user ID: {user_id}")
        
        # Get request data
        data = request.get_json()
        if not data:
            print("No data received in request")
            return jsonify({'error': 'No data provided'}), 400
        
        # Extract the message and session ID
        message = data.get('message', '').strip()
        session_id = data.get('session_id', None)
        
        if not message:
            print("Empty message received")
            return jsonify({'error': 'Message is required'}), 400
        
        print(f"Processing message: {message[:30]}{'...' if len(message) > 30 else ''}")
        
        # Use our enhanced AI chat integration
        from .utils.ai_chat_integration import process_message
        
        # Helper function to run async code
        def run_async(coro):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
                
        # Process with advanced components
        try:
            result = run_async(process_message(
                user_id=str(user_id) if user_id else "anonymous",
                session_id=session_id,
                message=message
            ))
            
            response = result.get('response', "I'm sorry, I couldn't process your message.")
            sentiment_label = result.get('sentiment_label', 'NEUTRAL')
            emotions = result.get('emotions', {"neutral": 1.0})
            session_id = result.get('session_id')
            
            print(f"Advanced processing complete for '{message}'. Response: '{response[:30]}...'")
            except Exception as e:
            print(f"Error in advanced processing: {str(e)}")
            # Fallback to basic sentiment analysis
            sentiment_score, sentiment_label = analyze_sentiment(message)
            emotions = analyze_emotions(message)
            response = "I'm having trouble with advanced processing right now. Could you try expressing that in a different way?"

        # Store the chat in history if user is logged in
        if user_id:
            try:
                # Store the chat exchange as a single entry
                chat_entry = ChatHistory(
                    user_id=user_id,
                    message=message,
                    response=response,
                    sentiment_score=0.5,  # Default value since we now use advanced analysis
                    sentiment_label=sentiment_label,
                    timestamp=datetime.utcnow()
                )
                db.session.add(chat_entry)
                db.session.commit()
                print("Successfully stored chat history")
            except Exception as db_error:
                print(f"Database error in chat history: {str(db_error)}")
                db.session.rollback()

        result = {
            'response': response,
            'sentiment_label': sentiment_label,
            'emotions': emotions,
            'session_id': session_id
        }
        print("API response:", result)
        print("Successfully prepared response")
        return jsonify(result)
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({
            'error': 'An error occurred while processing your message',
            'response': "I'm having trouble processing your request right now. Please try again."
        }), 500

# Helper function for response generation
def generate_personalized_response(message, sentiment_label, emotions, user_context=None):
    """Generate a personalized response using the AI utility functions"""
    try:
        # Use the main generate_chat_response function from ai_utils
        from .utils.ai_utils import generate_chat_response
        return generate_chat_response(message, user_context)
    except Exception as e:
        print(f"Error in generate_personalized_response: {str(e)}")
        # Fallback to a simpler response if something goes wrong
        if sentiment_label == "NEGATIVE":
            return "I can tell you're going through a difficult time. I'm here to listen and support you. Would you like to tell me more about what's happening?"
        elif sentiment_label == "POSITIVE":
            return "I'm glad to hear that! It's wonderful that you're having positive experiences. Would you like to explore more about what's working well for you?"
        else:
            return "Thank you for sharing. I'm here to support you. Would you like to explore your feelings a bit more?"

@app.route('/api/analyze-mood-patterns', methods=['GET'])
def analyze_mood_patterns():
    if not session.get('user_id'):
        return jsonify({"error": "You must be logged in"}), 401
    
    days = request.args.get('days', default=7, type=int)
    patterns = get_mood_patterns(session['user_id'], db, days)
    
    if not patterns:
        return jsonify({"error": "No mood data available"}), 404
    
    return jsonify(patterns)

# Custom template filter for converting newlines to <br> tags
@app.template_filter('nl2br')
def nl2br(value):
    if not value:
        return ''
    return value.replace('\n', '<br>')

@app.template_filter('timeago')
def timeago_filter(date):
    now = datetime.utcnow()
    diff = now - date

    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token='')

@app.route('/api/moods/latest')
@login_required
def api_moods_latest():
    moods = (
        MoodEntry.query
        .filter_by(user_id=current_user.id)
        .order_by(MoodEntry.date_created.desc())
        .limit(10)
        .all()
    )
    return jsonify([
        {
            "timestamp": mood.date_created.isoformat(),
            "mood": mood.mood_score
        }
        for mood in reversed(moods)
    ])

if __name__ == '__main__':
    app.run(debug=True)
