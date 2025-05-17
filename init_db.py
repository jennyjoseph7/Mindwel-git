"""
Script to initialize the database.
"""

from src.mental_health_tracker import create_app
from src.mental_health_tracker.models import db

def init_db():
    """Initialize the database."""
    app = create_app()
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Create all tables
        db.create_all()
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_db() 