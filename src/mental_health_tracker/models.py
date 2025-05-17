"""Database models for the mental health tracker application."""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_login import UserMixin
import sys

# Create a database instance
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for storing user account information.
    
    Attributes:
        id: Unique identifier
        username: User's username
        email: User's email address
        password: Hashed password
        created_at: Account creation timestamp
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships to other models
    journal_entries = db.relationship('JournalEntry', backref='user', lazy=True)
    mood_entries = db.relationship('mental_health_tracker.features.mood.models.mood_entry.MoodEntry', backref='user', lazy=True)
    chat_history = db.relationship('ChatHistory', backref='user', lazy=True)
    music_sessions = db.relationship('MusicTherapySession', backref='user', lazy=True)
    breathing_sessions = db.relationship('BreathingExercise', backref='user', lazy=True)
    
    def set_password(self, password):
        """Hash and set the user's password"""
        self.password = generate_password_hash(password)
        
    def check_password(self, password):
        """Check if the provided password matches the hashed password"""
        return check_password_hash(self.password, password)

# Only import models from feature-specific modules if they haven't been imported yet
# This prevents duplicate model definitions
if 'JournalEntry' not in globals():
    from .features.journal.models.journal_entry import JournalEntry
if 'MoodEntry' not in globals():
    from .features.mood.models.mood_entry import MoodEntry
if 'ChatHistory' not in globals():
    from .features.ai_chat.models.chat_history import ChatHistory
if 'MusicTherapySession' not in globals():
    from .features.music_therapy.models.music_therapy_session import MusicTherapySession

class BreathingExercise(db.Model):
    """Model for storing breathing exercise sessions.
    
    Attributes:
        id: Unique identifier
        user_id: Foreign key to User model
        technique: The breathing technique used
        duration: Duration of the exercise in seconds
        created_at: Timestamp of when the exercise was performed
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    technique = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # Duration in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<BreathingExercise {self.technique} by User {self.user_id}>' 