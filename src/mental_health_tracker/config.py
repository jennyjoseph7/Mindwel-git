import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    # Try to load from .env file
    load_dotenv(encoding='utf-8')
    logger.info("Successfully loaded .env file")
except Exception as e:
    logger.warning(f"Could not load .env file: {str(e)}")

# API Keys
# For development, you can set your Gemini API key here
# For production, set it as an environment variable: export GEMINI_API_KEY='your-api-key'
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Get a Google API key from: https://ai.google.dev/ (Gemini API)
# Development fallback - DO NOT USE IN PRODUCTION
if not GEMINI_API_KEY or GEMINI_API_KEY == 'YOUR_API_KEY_HERE':
    logger.warning("Using development API key. Please set GEMINI_API_KEY for production use.")
    # This is a placeholder key and won't work in production
    GEMINI_API_KEY = "AIzaSyDaUJr7_CYqGC-nD-M8oVVS4Ey_BgXyBKE"
    logger.warning("To use Gemini features, get an API key from https://ai.google.dev/ and set it as GEMINI_API_KEY in .env")

# Flask Configuration
SECRET_KEY = os.getenv('FLASK_SECRET_KEY', os.urandom(24))
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///mental_health.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# CSRF Protection - DISABLED FOR DEVELOPMENT ONLY
# WARNING: Don't use these settings in production!
WTF_CSRF_ENABLED = False  # Disabled for development
WTF_CSRF_SECRET_KEY = os.getenv('CSRF_SECRET_KEY', os.urandom(24))
WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
WTF_CSRF_SSL_STRICT = False
WTF_CSRF_CHECK_DEFAULT = False  # Disabled for development
WTF_CSRF_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
WTF_CSRF_FIELD_NAME = "csrf_token"
WTF_CSRF_HEADERS = ['X-CSRFToken', 'X-CSRF-Token'] 