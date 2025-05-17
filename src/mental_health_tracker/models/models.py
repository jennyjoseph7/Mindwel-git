"""
Core Models
Contains all database models for the application.
"""

from datetime import datetime
from flask_login import UserMixin
from . import db

class User(UserMixin, db.Model):
    """User model for authentication and user data."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(128))
    reset_token = db.Column(db.String(100), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships with fully qualified paths
    mood_entries = db.relationship('mental_health_tracker.models.models.MoodEntry', backref='user', lazy=True)
    journal_entries = db.relationship('mental_health_tracker.models.models.JournalEntry', backref='user', lazy=True)
    activities = db.relationship('mental_health_tracker.models.models.UserActivity', backref='user', lazy=True)
    music_sessions = db.relationship('mental_health_tracker.models.models.MusicTherapySession', backref='user', lazy=True)
    chat_history = db.relationship('mental_health_tracker.models.models.ChatHistory', backref='user', lazy=True)
    breathing_sessions = db.relationship('mental_health_tracker.models.models.BreathingExercise', backref='user', lazy=True)
    
    def set_password(self, password):
        """Set the user's password."""
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches."""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class MoodEntry(db.Model):
    """Model for tracking user mood entries."""
    __tablename__ = 'mood_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    mood_score = db.Column(db.Integer, nullable=False)  # 1-5 scale
    notes = db.Column(db.Text, nullable=True)
    activities = db.Column(db.String(200), nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sentiment_score = db.Column(db.Float, nullable=True)  # -1 to 1
    sentiment_label = db.Column(db.String(20), nullable=True)  # positive, negative, neutral

class JournalEntry(db.Model):
    """Model for storing user journal entries."""
    __tablename__ = 'journal_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    mood_score = db.Column(db.Integer, nullable=True)  # 1-5 scale
    sentiment_score = db.Column(db.Float, nullable=True)  # -1 to 1
    sentiment_label = db.Column(db.String(20), nullable=True)  # positive, negative, neutral

class MusicTherapySession(db.Model):
    """Model for tracking music therapy sessions."""
    __tablename__ = 'music_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    initial_mood = db.Column(db.String(50), nullable=False)
    final_mood = db.Column(db.String(50), nullable=True)
    tracks_played = db.Column(db.Text, nullable=True)  # JSON string of tracks played
    effectiveness_rating = db.Column(db.Integer, nullable=True)  # 1-5 scale
    notes = db.Column(db.Text, nullable=True)

class UserActivity(db.Model):
    """Model for tracking user activities."""
    __tablename__ = 'user_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserActivity {self.activity_type}>'

class ChatHistory(db.Model):
    """Model for storing AI chat history."""
    __tablename__ = 'chat_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sentiment_score = db.Column(db.Float, nullable=True)  # -1 to 1
    sentiment_label = db.Column(db.String(20), nullable=True)  # positive, negative, neutral

class BreathingExercise(db.Model):
    """Model for storing breathing exercise sessions.
    
    Attributes:
        id: Unique identifier
        user_id: Foreign key to User model
        technique: The breathing technique used
        duration: Duration of the exercise in seconds
        created_at: Timestamp of when the exercise was performed
    """
    __tablename__ = 'breathing_exercises'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    technique = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # Duration in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<BreathingExercise {self.technique} by User {self.user_id}>'

class TicTacToeGame(db.Model):
    """Model for storing Tic Tac Toe game statistics.
    
    Attributes:
        id: Unique identifier
        user_id: Foreign key to User model
        winner: The winner of the game ('leaf', 'twig', or 'draw')
        moves: Number of moves made in the game
        duration: Duration of the game in seconds
        created_at: Timestamp of when the game was played
    """
    __tablename__ = 'tictactoe_games'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    winner = db.Column(db.String(10), nullable=False)
    moves = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # Duration in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<TicTacToeGame {self.id} by User {self.user_id}>'

class ColorMatchingGame(db.Model):
    """Model for storing color matching game statistics."""
    __tablename__ = 'color_matching_game'
    __table_args__ = {'extend_existing': True}  # Allow table to be redefined if it exists
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # Duration in seconds
    difficulty = db.Column(db.String(10), nullable=True)  # easy, medium, hard
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Add relationship to User model
    user = db.relationship('User', backref=db.backref('color_matching_games', lazy=True))
    
    def __repr__(self):
        return f'<ColorMatchingGame {self.id} - User {self.user_id}>'
