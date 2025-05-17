"""
Database Models
Contains all database models for the application.
"""

from flask_sqlalchemy import SQLAlchemy

# Create a db instance without initializing it
db = SQLAlchemy()

# Import all models after db is created to avoid circular imports
from .models import (
    User,  # Import User first as other models depend on it
    UserActivity,
    MusicTherapySession,
    MoodEntry,
    JournalEntry,
    ChatHistory,
    BreathingExercise,
    TicTacToeGame,
    ColorMatchingGame
)

__all__ = [
    'db',
    'User',
    'UserActivity',
    'MusicTherapySession',
    'MoodEntry',
    'JournalEntry',
    'ChatHistory',
    'BreathingExercise',
    'TicTacToeGame',
    'ColorMatchingGame'
]