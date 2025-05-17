from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
from flask_login import current_user, login_required
from ..models import db, ChatHistory, MoodEntry, JournalEntry
from ..utils.ai_utils import analyze_sentiment, analyze_emotions
from ..utils.ai_chat_integration import process_message
from datetime import datetime
import json
import logging
import asyncio

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
ai_chat_bp = Blueprint('ai_chat', __name__, url_prefix='/ai-chat')

@ai_chat_bp.route('/')
@login_required
def index():
    """Display the AI chat interface."""
    # Get recent chat history
    chat_history = ChatHistory.query.filter_by(user_id=current_user.id).order_by(ChatHistory.timestamp.desc()).limit(10).all()
    
    return render_template('ai/chat.html', messages=chat_history)

def run_async(coro):
    """Run an async coroutine in a synchronous context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@ai_chat_bp.route('/send', methods=['POST'])
@login_required
# We're running with CSRF disabled in config instead of using decorators
def send_message():
    """Process an incoming message and generate a response using advanced components."""
    try:
        # Log the request 
        logger.info(f"Received message request from user {current_user.id}")
        logger.debug(f"Headers: {request.headers}")
        
        data = request.get_json()
        if not data:
            logger.error("No JSON data received in request")
            return jsonify({'error': 'No data provided'}), 400
        
        # Extract the message
        message = data.get('message', '').strip()
        if not message:
            logger.error("Empty message received")
            return jsonify({'error': 'Message is required'}), 400
        
        logger.info(f"Processing message from user {current_user.id}: {message[:30]}{'...' if len(message) > 30 else ''}")
        
        # Get session ID from request or generate new one
        session_id = data.get('session_id', None)
        
        # Process message using advanced components
        try:
            # Process the message through our advanced components
            result = run_async(process_message(
                user_id=str(current_user.id),
                session_id=session_id,
                message=message
            ))
            
            logger.info(f"Advanced processing complete. Escalation level: {result.get('escalation_level', 0)}")
            
            response = result.get('response', "I'm sorry, I couldn't process your message.")
            sentiment_label = result.get('sentiment_label', 'NEUTRAL')
            emotions = result.get('emotions', {"neutral": 1.0})
            
            # Update session_id for frontend to maintain conversation state
            session_id = result.get('session_id')
        except Exception as e:
            logger.error(f"Error in advanced processing: {str(e)}")
            # Fallback to basic sentiment analysis
            sentiment_score, sentiment_label = analyze_sentiment(message)
            emotions = analyze_emotions(message)
            response = "I'm having trouble with advanced processing right now. How else can I help you?"
        
        # Save the conversation to the database
        try:
            chat_entry = ChatHistory(
                user_id=current_user.id,
                message=message,
                response=response,
                sentiment_score=0.5,  # Default value
                sentiment_label=sentiment_label,
                timestamp=datetime.utcnow()
            )
            db.session.add(chat_entry)
            db.session.commit()
            logger.info(f"Chat entry saved successfully for user {current_user.id}")
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            db.session.rollback()
        
        # Create response with session ID to maintain conversation state
        return jsonify({
            'response': response,
            'sentiment_label': sentiment_label,
            'emotions': emotions,
            'session_id': session_id
        })
    
    except Exception as e:
        logger.exception(f"Error in send_message: {str(e)}")
        return jsonify({
            'error': 'An error occurred while processing your message',
            'response': "I'm having trouble right now. Please try again later."
        }), 500

def get_user_context(user_id):
    """Gather context about the user for personalized responses."""
    context = {}
    
    # Get recent mood entries
    moods = MoodEntry.query.filter_by(user_id=user_id).order_by(MoodEntry.date_created.desc()).limit(5).all()
    if moods:
        avg_mood = sum(m.mood_score for m in moods) / len(moods)
        context['recent_mood_avg'] = avg_mood
        context['current_mood'] = moods[0].mood_score
    
    # Get recent journal entries
    journals = JournalEntry.query.filter_by(user_id=user_id).order_by(JournalEntry.date_created.desc()).limit(3).all()
    if journals:
        context['has_journal'] = True
        context['recent_journal_topic'] = journals[0].title
    
    return context 