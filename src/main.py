"""Main entry point for the Mental Health Tracker application."""

from mental_health_tracker import create_app
from mental_health_tracker.models import db

# Create the Flask application
app = create_app()

# Create the database tables when running directly
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 