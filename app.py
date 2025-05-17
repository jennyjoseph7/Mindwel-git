from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory, abort
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, current_user, login_user, logout_user, login_required, UserMixin
from transformers import pipeline
import google.generativeai as genai
from datetime import datetime
import json
import jinja2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up template folder path - Use absolute paths
template_dir = os.path.abspath('src/mental_health_tracker/templates')
static_dir = os.path.abspath('src/mental_health_tracker/static')

# Create app with custom template folder
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')  # Use environment variable for secret key

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Create a simple User model for testing
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    # Return a mock user for now
    return User(user_id)

# Add current_user to all templates
@app.context_processor
def inject_user():
    return {'current_user': current_user}

# Add a simple login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = 1  # Mock user ID
        user = User(user_id)
        login_user(user)
        return redirect(url_for('index'))
    return render_template('auth/login.html')

# Add placeholder dashboard route
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# Add placeholder journal list route
@app.route('/journal')
@login_required
def journal_list():
    return render_template('journal/list.html')

# Add logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Initialize models
emotion_classifier = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    top_k=None
)

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
gemini_available = False

if not GEMINI_API_KEY:
    app.logger.warning("GEMINI_API_KEY environment variable is not set - AI chat functionality will be disabled")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-pro")
        chat_session = gemini_model.start_chat()
        gemini_available = True
        app.logger.info("Gemini API configured successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize Gemini API: {str(e)}")

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        # Fallback to a simple HTML response if there's a template error
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>MindWell - Mental Health Tracker</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        </head>
        <body>
            <div class="container mt-5">
                <div class="row">
                    <div class="col-lg-8 mx-auto text-center">
                        <h1>Welcome to MindWell</h1>
                        <p class="lead">Your mental health tracker and companion for well-being</p>
                        <div class="mt-4">
                            <a href="/login" class="btn btn-primary me-2">Login</a>
                            <a href="/ai-chat" class="btn btn-success">Try AI Chat</a>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

@app.route('/ai-chat')
def ai_chat():
    if not gemini_available:
        return render_template('ai/chat_unavailable.html', reason="API key not configured")
    
    if 'chat_history' not in session:
        session['chat_history'] = []
    
    try:
        return render_template('ai/chat.html', messages=session['chat_history'])
    except jinja2.exceptions.TemplateNotFound:
        # First fallback - try the attached template
        try:
            return render_template('chat.html', messages=session['chat_history'])
        except:
            # Second fallback - a simple message
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>AI Chat | Mental Health Tracker</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            </head>
            <body>
                <div class="container mt-5">
                    <div class="row">
                        <div class="col-lg-8 mx-auto">
                            <div class="card shadow">
                                <div class="card-header bg-primary text-white">
                                    <h2 class="mb-0">AI Chat Assistant</h2>
                                </div>
                                <div class="card-body">
                                    <p>AI Chat feature is under development.</p>
                                    <p>Please try again later or <a href="/">return to the home page</a>.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """

@app.route('/new_chat')
def new_chat():
    session['chat_history'] = []
    return redirect(url_for('ai_chat'))

@app.route('/send_message', methods=['POST'])
def send_message():
    if not gemini_available:
        return jsonify({'error': 'AI chat functionality is currently unavailable'}), 503
    
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    user_input = request.json.get('message')
    
    if not user_input:
        return jsonify({'error': 'Empty message'}), 400
    
    try:
        # Emotion detection
        emotion_results = emotion_classifier(user_input)
        emotions = {res['label']: res['score'] for res in emotion_results[0]}
        dominant_emotion = max(emotions.items(), key=lambda x: x[1])[0]
        
        # Construct prompt for Gemini
        prompt = f"The user seems to be feeling {dominant_emotion}. Here's their message: '{user_input}'. Respond appropriately with empathy and support, focusing on mental health and wellbeing. Keep the response concise and helpful."
        
        # Get response from Gemini
        response = chat_session.send_message(prompt)
        
        # Determine sentiment based on dominant emotion
        sentiment = 'POSITIVE' if dominant_emotion in ['joy', 'love'] else 'NEGATIVE'
        if dominant_emotion in ['neutral']:
            sentiment = 'NEUTRAL'
        
        # Save to session
        message_data = {
            'message': user_input,
            'response': response.text,
            'timestamp': datetime.now().isoformat(),
            'sentiment_label': sentiment,
            'emotions': emotions
        }
        
        if 'chat_history' not in session:
            session['chat_history'] = []
        
        session['chat_history'].append(message_data)
        session.modified = True
        
        return jsonify({
            'response': response.text,
            'sentiment_label': sentiment,
            'emotions': emotions
        })
        
    except Exception as e:
        app.logger.error(f"Error in send_message: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your message. Please try again.'}), 500

@app.route('/music/<mood>')
def redirect_to_audio(mood):
    # Redirect to the static audio directory for the given mood
    return redirect(f'/static/audio/{mood}/')

# Add a simple, direct favicon route with better error handling
@app.route('/favicon.ico')
def favicon():
    try:
        # Serve the icon directly from the images directory
        return app.send_static_file('images/generated-icon.png')
    except Exception as e:
        app.logger.error(f"Error serving favicon: {str(e)}")
        # Return empty response with 204 status if the file isn't found
        return '', 204

# Add a catch-all route for 404 errors
@app.errorhandler(404)
def page_not_found(e):
    app.logger.warning(f"404 error: {request.path}")
    return "Page not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 