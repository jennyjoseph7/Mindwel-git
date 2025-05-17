from datetime import datetime
from .. import db

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