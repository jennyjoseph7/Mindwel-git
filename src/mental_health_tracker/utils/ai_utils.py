from textblob import TextBlob
import json
import numpy as np
import random
from datetime import datetime, timedelta
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import logging
import google.generativeai as genai
from ..config import GEMINI_API_KEY
from .sentiment_analyzer import SentimentAnalyzer
import os
import re
import asyncio
import redis
from dotenv import load_dotenv

# Properly import the typing module
from typing import Dict, Any, List, Tuple, Union, Optional

# Load environment variables
load_dotenv()

# Import the missing MoodEntry model
try:
    from ..models import MoodEntry
except ImportError:
    # For direct execution of this file
    MoodEntry = None
    print("Warning: MoodEntry model not imported properly")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize sentiment analyzer and other pipelines
try:
    sentiment_analyzer = SentimentAnalyzer()
    logger.info("Successfully initialized sentiment analyzer")
except Exception as e:
    logger.error(f"Error initializing sentiment analyzer: {str(e)}")
    sentiment_analyzer = None

# Initialize Gemini
try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        # Set up the model and chat session
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 1024,
        }
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        model = genai.GenerativeModel(model_name="gemini-pro", generation_config=generation_config, safety_settings=safety_settings)
        chat_session = model.start_chat(history=[])
    else:
        chat_session = None
        logger.warning("Gemini API key not found, chat functionality will use fallback methods")
except Exception as e:
    logger.error(f"Failed to initialize Gemini: {str(e)}")
    chat_session = None

# Initialize Redis connection
try:
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost')
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    # Test connection
    redis_client.ping()
    logger.info("Redis connection successful")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {str(e)}")
    redis_client = None

# Initialize sentiment analyzer
sentiment_analyzer = None
_sentiment_pipeline = None
_emotion_pipeline = None

# --- Constants ---
USER_REGION = os.getenv('USER_REGION', 'US')  # For crisis resources
EMOJIS = ['😊','🙏','💔','✨','💙','🌱','💡']

# Initialize comprehensive emotion response templates
EMOTION_TEMPLATES = {
    "happy": [
        "I'm glad to hear you're feeling happy! What's been bringing you joy lately?",
        "That's wonderful to hear. What's contributing to your happiness today?",
        "It's great that you're feeling positive. What's making you happy right now?"
    ],
    "sad": [
        "I'm sorry to hear you're feeling sad. Would you like to talk about what's bringing you down?",
        "It's okay to feel sad sometimes. Is there something specific that's making you feel this way?",
        "I understand that sadness can be difficult. What's on your mind right now?"
    ],
    "angry": [
        "I can tell you're feeling angry. That's a completely valid emotion. Would you like to share what's triggering these feelings?",
        "Anger is a natural response to many situations. What's making you feel angry right now?",
        "I understand you're feeling angry. Would you like to talk more about what's causing this feeling?"
    ],
    "anxious": [
        "Feeling anxious can be really challenging. Is there something specific that's causing you worry?",
        "I hear that you're feeling anxious. Would it help to talk about what's making you feel this way?",
        "Anxiety can be overwhelming sometimes. What's making you feel anxious today?"
    ],
    "frustrated": [
        "It sounds like you're feeling frustrated. That's completely understandable. What's causing this frustration?",
        "Frustration can be really difficult to deal with. Would you like to talk about what's happening?",
        "I understand you're feeling frustrated. What specifically is contributing to these feelings?"
    ],
    "lonely": [
        "Feeling lonely can be really difficult. Would you like to talk about what's making you feel isolated?",
        "I hear that you're feeling lonely. That's a very common but challenging feeling. What's going on in your social life right now?",
        "Loneliness is something many people experience. What do you think is contributing to these feelings for you?"
    ],
    "confused": [
        "It sounds like you're feeling confused. Would it help to break down what's happening step by step?",
        "Being confused or uncertain can be uncomfortable. What specific aspect feels most unclear right now?",
        "I understand you're feeling confused. Let's try to explore this together - what's on your mind?"
    ],
    "tired": [
        "Feeling tired can really affect your mood and outlook. Has something been disrupting your rest lately?",
        "I hear that you're feeling exhausted. That can make everything harder to deal with. What's been draining your energy?",
        "Tiredness can be both physical and emotional. What do you think is causing your fatigue?"
    ],
    "hopeful": [
        "It's great that you're feeling hopeful. What's giving you that sense of optimism?",
        "Hope is such an important emotion. What positive changes are you looking forward to?",
        "I'm glad you're feeling hopeful. What's contributing to this positive outlook?"
    ],
    "guilty": [
        "Guilt can be a heavy burden to carry. Would you like to talk about what's making you feel this way?",
        "I hear that you're feeling guilty. That's a difficult emotion to process. What's happened that's making you feel this way?",
        "Feeling guilty is common, but it can be painful. What actions or thoughts are triggering this feeling?"
    ],
    "embarrassed": [
        "Embarrassment can be really uncomfortable. Would you like to talk about what happened?",
        "I understand feeling embarrassed can be difficult. These feelings usually fade with time. Would you like to share what's making you feel this way?",
        "Many people experience embarrassment - you're not alone. What specifically triggered this feeling?"
    ],
    "proud": [
        "It's wonderful that you're feeling proud! What accomplishment or action is making you feel this way?",
        "Pride in yourself or others can be really positive. What's making you feel proud right now?",
        "I'm glad you're experiencing pride. Would you like to share more about what you've achieved?"
    ],
    "disappointed": [
        "I'm sorry to hear you're feeling disappointed. Would you like to talk about what didn't meet your expectations?",
        "Disappointment can be really tough to deal with. What happened that led to these feelings?",
        "I understand you're feeling disappointed. What were you hoping would happen differently?"
    ],
    "grateful": [
        "Gratitude is such a positive emotion to experience. What are you feeling grateful for?",
        "It's wonderful that you're feeling grateful. Would you like to share what's inspiring this feeling?",
        "Feeling grateful can really improve our outlook. What specifically are you appreciating right now?"
    ],
    "jealous": [
        "Jealousy is a common but challenging emotion. Would you like to talk about what's triggering these feelings?",
        "I understand you're feeling jealous. That's a natural human emotion. What's making you feel this way?",
        "Jealousy can be uncomfortable to experience. What situation is bringing up these feelings?"
    ],
    "overwhelmed": [
        "Feeling overwhelmed can be really difficult. Would it help to break down what's contributing to this feeling?",
        "I hear that you're feeling overwhelmed. That's understandable. What specifically feels like too much right now?",
        "Being overwhelmed can make everything seem impossible. What's the biggest source of pressure for you currently?"
    ],
    "hurt": [
        "I'm sorry to hear you're feeling hurt. Would you like to talk about what happened?",
        "Emotional pain can be really difficult to process. What's causing you to feel hurt?",
        "I understand you're feeling hurt. That's completely valid. Would you like to share what's happened?"
    ],
    "worried": [
        "Worry can be really consuming. What specific concerns are on your mind?",
        "I hear that you're feeling worried. Would it help to talk through what you're concerned about?",
        "Feeling worried is a common response to uncertainty. What specifically are you worried might happen?"
    ],
    "content": [
        "Contentment is such a peaceful feeling. What's helping you feel this sense of satisfaction?",
        "It's wonderful that you're feeling content. What aspects of your life are bringing you this feeling?",
        "Feeling content is something many people strive for. What's contributing to this positive state for you?"
    ],
    "excited": [
        "It's great that you're feeling excited! What's coming up that you're looking forward to?",
        "Excitement is such an energizing emotion. What's sparked this feeling for you?",
        "I'm glad to hear you're excited. Would you like to share more about what's making you feel this way?"
    ],
    "stressed": [
        "I hear that you're feeling stressed. What's putting pressure on you right now?",
        "Stress can be really challenging to manage. What specific situations are contributing to your stress?",
        "Being stressed can affect so many aspects of our lives. What's weighing on you the most right now?"
    ],
    "bored": [
        "Feeling bored can be frustrating. What activities usually engage you?",
        "Boredom might sometimes be a sign we need new stimulation or challenges. What kinds of things do you normally enjoy?",
        "I understand you're feeling bored. Would you like to explore some potential activities or interests?"
    ]
}

# Crisis detection patterns
CRISIS_PATTERNS = [
    r"\bkill myself\b", r"\bsuicid(e|al)\b", r"\bwant(ing)? to die\b",
    r"\bend (my|this) life\b", r"\bno reason to live\b",
    r"\bharm (myself|me)\b", r"\bi'?m going to die\b",
    r"\btake my (own )?life\b", r"\bdon'?t want to (be here|live|exist)",
    r"\b(can'?t|cannot) go on\b", r"\bgive(ing)? up\b", r"\bno (hope|future)\b",
    r"\bkill you\b", r"\bi'?ll kill\b", r"\bmurder\b", r"\bshoot\b", r"\bgun\b",
    r"\bviolence\b", r"\bhurt (you|someone)\b", r"\bdeath\b", r"\bdie\b",
]
CRISIS_REGEX = re.compile('|'.join(CRISIS_PATTERNS), re.IGNORECASE)

# Intent-based response system - common mental health topics
CHATBOT_INTENTS = {
    "greeting": {
        "patterns": ["Hi", "Hey", "Is anyone there?", "Hi there", "Hello", "Hey there"],
        "responses": ["Hello there. Tell me how are you feeling today?", "Hi there. What brings you here today?", "Hi there. How are you feeling today?"]
    },
    "goodbye": {
        "patterns": ["Bye", "See you later", "Goodbye", "ok bye", "Bye then"],
        "responses": ["See you later.", "Have a nice day.", "Bye! Come back again."]
    },
    "thanks": {
        "patterns": ["Thanks", "Thank you", "That's helpful", "Thanks for the help"],
        "responses": ["Happy to help!", "Any time!", "My pleasure", "You're most welcome!"]
    },
    "about": {
        "patterns": ["Who are you?", "What are you?", "What is your name?", "What's your name?"],
        "responses": ["I'm MindWell, your mental health companion chatbot. How are you feeling today?", "I'm MindWell, an AI assistant designed to help with mental wellbeing."]
    },
    "what_is_depression": {
        "patterns": ["what is depression?", "tell me about depression", "define depression"],
        "responses": ["Depression is a common and serious medical illness that negatively affects how you feel, the way you think and how you act. Fortunately, it is also treatable. Depression causes feelings of sadness and/or a loss of interest in activities you once enjoyed."]
    },
    "what_is_anxiety": {
        "patterns": ["what is anxiety?", "tell me about anxiety", "define anxiety"],
        "responses": ["Anxiety is your body's natural response to stress. It's a feeling of fear or apprehension about what's to come. It can manifest as worry, fear, or nervousness."]
    },
    "skill": {
        "patterns": ["What can you do?", "How can you help me?"],
        "responses": ["I can provide general advice regarding anxiety and depression, answer questions related to mental health, and have daily conversations. I'm not a substitute for professional help, but I'm here to support you."]
    },
    "sad": {
        "patterns": ["I am feeling lonely", "I am so lonely", "I feel down", "I feel sad", "I am sad", "I feel so lonely", "I feel empty"],
        "responses": [
            "I'm sorry to hear that. I'm here for you. Talking about it might help. So, tell me why do you think you're feeling this way?", 
            "I'm here for you. Could you tell me why you're feeling this way?",
            "Sadness can weigh heavy, but it is okay to feel it. You are strong enough to get through this."
        ]
    },
    "stressed": {
        "patterns": ["I am so stressed out", "I am so stressed", "I feel stuck", "I still feel stressed", "I am so burned out"],
        "responses": [
            "What do you think is causing this?", 
            "Take a deep breath and gather your thoughts. Go take a walk if possible. Stay hydrated", 
            "Give yourself a break. Go easy on yourself."
        ]
    },
    "depressed": {
        "patterns": ["I can't take it anymore", "I am so depressed", "I think i'm depressed", "I have depression"],
        "responses": [
            "It helps to talk about what's happening. You're going to be okay", 
            "Talk to me. Tell me more. It helps if you open up yourself to someone else.", 
            "Sometimes when we are depressed, it is hard to care about anything. It can be hard to do the simplest of things. Give yourself time to heal."
        ]
    },
    "happy": {
        "patterns": ["I feel great today", "I am happy", "I feel happy", "I'm good", "cheerful", "I'm fine", "I feel ok"],
        "responses": [
            "That's great to hear. I'm glad you're feeling this way.", 
            "Did something happen which made you feel this way?",
            "It is heartwarming to see you filled with joy. Your positivity and warmth make every moment brighter!"
        ]
    },
    "sleep_problems": {
        "patterns": ["I have insomnia", "I am suffering from insomnia", "I can't sleep", "I haven't slept", "trouble sleeping"],
        "responses": [
            "Sleep problems can really affect your mental health and daily functioning. How long have you been experiencing these difficulties?",
            "What do you think is the reason behind this?", 
            "That seems difficult. Regular sleep schedules and avoiding screens before bed can sometimes help. Have you tried any relaxation techniques?"
        ]
    },
    "difference_sadness_depression": {
        "patterns": ["what's difference between sadness and depression", "is sadness same as depression", "sadness vs depression"],
        "responses": [
            "Sadness is a normal emotion that everyone experiences, usually triggered by difficult, challenging, or disappointing events. Depression is more persistent - it's a mental health condition that affects your mood, thinking, and behavior for weeks or months. While sadness passes with time, depression often requires treatment to improve."
        ]
    },
    "anxiety_management": {
        "patterns": ["how to manage anxiety", "how to reduce anxiety", "anxiety coping", "anxiety tips"],
        "responses": [
            "There are several techniques to help manage anxiety. Deep breathing exercises, meditation, regular physical activity, and getting enough sleep can all help. The 3-3-3 rule can also be effective: name 3 things you see, 3 sounds you hear, and move 3 parts of your body. This helps ground you in the present moment."
        ]
    },
    "mental_health_tips": {
        "patterns": ["mental health tips", "how to improve mental health", "mental wellbeing advice"],
        "responses": [
            "Some helpful mental health tips include: 1) Stay physically active regularly, 2) Get sufficient sleep, 3) Practice mindfulness or meditation, 4) Maintain social connections, 5) Set realistic goals, 6) Break large tasks into smaller ones, 7) Try to focus on positives, and 8) Seek professional help when needed."
        ]
    },
    "therapy_types": {
        "patterns": ["what types of therapy exist", "therapy types", "kinds of therapy", "different therapies"],
        "responses": [
            "There are many types of therapy including Cognitive Behavioral Therapy (CBT), Dialectical Behavior Therapy (DBT), Psychodynamic Therapy, Interpersonal Therapy, and Mindfulness-based therapies. Each has different approaches and may be more effective for specific conditions. A mental health professional can help determine which might be best for your situation."
        ]
    },
    "help_someone": {
        "patterns": ["how to help someone with depression", "how to help someone with anxiety", "friend mental health", "help depressed friend"],
        "responses": [
            "To help someone with mental health challenges: 1) Listen without judgment, 2) Encourage them to seek professional help, 3) Offer to help with everyday tasks, 4) Learn about their condition, 5) Be patient and understanding, 6) Take care of yourself too, and 7) Remind them they're not alone. Remember that you can't fix their problems, but your support matters."
        ]
    }
}

def find_intent_match(user_input):
    """
    Find the best matching intent for a user input
    
    Args:
        user_input (str): The user's message
        
    Returns:
        tuple: (intent_name, response) or (None, None) if no match
    """
    user_input = user_input.lower().strip()
    
    # Check for exact matches first
    for intent_name, intent_data in CHATBOT_INTENTS.items():
        if user_input in [p.lower() for p in intent_data["patterns"]]:
            # Return a random response from this intent
            return intent_name, random.choice(intent_data["responses"])
    
    # Special case handling for goodbye variations
    if user_input in ["bye", "ok bye", "goodbye", "bye then"]:
        return "goodbye", random.choice(CHATBOT_INTENTS["goodbye"]["responses"])
    
    # Check for partial matches
    best_match = None
    highest_similarity = 0
    
    for intent_name, intent_data in CHATBOT_INTENTS.items():
        for pattern in intent_data["patterns"]:
            # Simple word overlap similarity
            pattern_words = set(pattern.lower().split())
            input_words = set(user_input.split())
            
            if len(pattern_words) == 0:
                continue
                
            # Calculate Jaccard similarity (intersection over union)
            intersection = len(pattern_words.intersection(input_words))
            union = len(pattern_words.union(input_words))
            
            if union > 0:
                similarity = intersection / union
                
                # If input contains all pattern words, boost similarity
                if pattern_words.issubset(input_words):
                    similarity += 0.2
                
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    best_match = intent_name
    
    # Return the best match if it's above threshold
    if highest_similarity > 0.5:
        return best_match, random.choice(CHATBOT_INTENTS[best_match]["responses"])
    
    return None, None

# Initialize comprehensive emotion response templates
EMOTION_TEMPLATES = {
    "happy": [
        "I'm glad to hear you're feeling happy! What's been bringing you joy lately?",
        "That's wonderful to hear. What's contributing to your happiness today?",
        "It's great that you're feeling positive. What's making you happy right now?"
    ],
    "sad": [
        "I'm sorry to hear you're feeling sad. Would you like to talk about what's bringing you down?",
        "It's okay to feel sad sometimes. Is there something specific that's making you feel this way?",
        "I understand that sadness can be difficult. What's on your mind right now?"
    ],
    "angry": [
        "I can tell you're feeling angry. That's a completely valid emotion. Would you like to share what's triggering these feelings?",
        "Anger is a natural response to many situations. What's making you feel angry right now?",
        "I understand you're feeling angry. Would you like to talk more about what's causing this feeling?"
    ],
    "anxious": [
        "Feeling anxious can be really challenging. Is there something specific that's causing you worry?",
        "I hear that you're feeling anxious. Would it help to talk about what's making you feel this way?",
        "Anxiety can be overwhelming sometimes. What's making you feel anxious today?"
    ],
    "frustrated": [
        "It sounds like you're feeling frustrated. That's completely understandable. What's causing this frustration?",
        "Frustration can be really difficult to deal with. Would you like to talk about what's happening?",
        "I understand you're feeling frustrated. What specifically is contributing to these feelings?"
    ],
    "lonely": [
        "Feeling lonely can be really difficult. Would you like to talk about what's making you feel isolated?",
        "I hear that you're feeling lonely. That's a very common but challenging feeling. What's going on in your social life right now?",
        "Loneliness is something many people experience. What do you think is contributing to these feelings for you?"
    ],
    "confused": [
        "It sounds like you're feeling confused. Would it help to break down what's happening step by step?",
        "Being confused or uncertain can be uncomfortable. What specific aspect feels most unclear right now?",
        "I understand you're feeling confused. Let's try to explore this together - what's on your mind?"
    ],
    "tired": [
        "Feeling tired can really affect your mood and outlook. Has something been disrupting your rest lately?",
        "I hear that you're feeling exhausted. That can make everything harder to deal with. What's been draining your energy?",
        "Tiredness can be both physical and emotional. What do you think is causing your fatigue?"
    ],
    "hopeful": [
        "It's great that you're feeling hopeful. What's giving you that sense of optimism?",
        "Hope is such an important emotion. What positive changes are you looking forward to?",
        "I'm glad you're feeling hopeful. What's contributing to this positive outlook?"
    ],
    "guilty": [
        "Guilt can be a heavy burden to carry. Would you like to talk about what's making you feel this way?",
        "I hear that you're feeling guilty. That's a difficult emotion to process. What's happened that's making you feel this way?",
        "Feeling guilty is common, but it can be painful. What actions or thoughts are triggering this feeling?"
    ],
    "embarrassed": [
        "Embarrassment can be really uncomfortable. Would you like to talk about what happened?",
        "I understand feeling embarrassed can be difficult. These feelings usually fade with time. Would you like to share what's making you feel this way?",
        "Many people experience embarrassment - you're not alone. What specifically triggered this feeling?"
    ],
    "proud": [
        "It's wonderful that you're feeling proud! What accomplishment or action is making you feel this way?",
        "Pride in yourself or others can be really positive. What's making you feel proud right now?",
        "I'm glad you're experiencing pride. Would you like to share more about what you've achieved?"
    ],
    "disappointed": [
        "I'm sorry to hear you're feeling disappointed. Would you like to talk about what didn't meet your expectations?",
        "Disappointment can be really tough to deal with. What happened that led to these feelings?",
        "I understand you're feeling disappointed. What were you hoping would happen differently?"
    ],
    "grateful": [
        "Gratitude is such a positive emotion to experience. What are you feeling grateful for?",
        "It's wonderful that you're feeling grateful. Would you like to share what's inspiring this feeling?",
        "Feeling grateful can really improve our outlook. What specifically are you appreciating right now?"
    ],
    "jealous": [
        "Jealousy is a common but challenging emotion. Would you like to talk about what's triggering these feelings?",
        "I understand you're feeling jealous. That's a natural human emotion. What's making you feel this way?",
        "Jealousy can be uncomfortable to experience. What situation is bringing up these feelings?"
    ],
    "overwhelmed": [
        "Feeling overwhelmed can be really difficult. Would it help to break down what's contributing to this feeling?",
        "I hear that you're feeling overwhelmed. That's understandable. What specifically feels like too much right now?",
        "Being overwhelmed can make everything seem impossible. What's the biggest source of pressure for you currently?"
    ],
    "hurt": [
        "I'm sorry to hear you're feeling hurt. Would you like to talk about what happened?",
        "Emotional pain can be really difficult to process. What's causing you to feel hurt?",
        "I understand you're feeling hurt. That's completely valid. Would you like to share what's happened?"
    ],
    "worried": [
        "Worry can be really consuming. What specific concerns are on your mind?",
        "I hear that you're feeling worried. Would it help to talk through what you're concerned about?",
        "Feeling worried is a common response to uncertainty. What specifically are you worried might happen?"
    ],
    "content": [
        "Contentment is such a peaceful feeling. What's helping you feel this sense of satisfaction?",
        "It's wonderful that you're feeling content. What aspects of your life are bringing you this feeling?",
        "Feeling content is something many people strive for. What's contributing to this positive state for you?"
    ],
    "excited": [
        "It's great that you're feeling excited! What's coming up that you're looking forward to?",
        "Excitement is such an energizing emotion. What's sparked this feeling for you?",
        "I'm glad to hear you're excited. Would you like to share more about what's making you feel this way?"
    ],
    "stressed": [
        "I hear that you're feeling stressed. What's putting pressure on you right now?",
        "Stress can be really challenging to manage. What specific situations are contributing to your stress?",
        "Being stressed can affect so many aspects of our lives. What's weighing on you the most right now?"
    ],
    "bored": [
        "Feeling bored can be frustrating. What activities usually engage you?",
        "Boredom might sometimes be a sign we need new stimulation or challenges. What kinds of things do you normally enjoy?",
        "I understand you're feeling bored. Would you like to explore some potential activities or interests?"
    ]
}

def get_emotion_response(emotion, is_repetition=False):
    """
    Get an appropriate response for a specific emotion

    Args:
        emotion (str): The emotion to respond to
        is_repetition (bool): Whether this is a repeated message
        
    Returns:
        str: A natural response addressing the emotion
    """
    # Use our comprehensive emotion templates
    if emotion in EMOTION_TEMPLATES:
        templates = EMOTION_TEMPLATES[emotion]
        
        # For repetition, add a meta-acknowledgment
        if is_repetition:
            repetition_templates = [
                f"I understand you're still feeling {emotion}. {templates[0].lower()}",
                f"It seems this {emotion} feeling is important to you. {templates[1].lower()}",
                f"I hear that you're continuing to feel {emotion}. {templates[2].lower()}"
            ]
            return random.choice(repetition_templates)
        
        return random.choice(templates)
    
    # Fallback responses for other emotions
    if is_repetition:
        return "I notice you mentioned this feeling again. Could you tell me more about why this is so significant for you right now?"
    
    return "Thank you for sharing how you're feeling. Would you like to explore these emotions a bit more?"

# --- Enhanced Sentiment Analysis Functions ---

def get_sentiment_pipeline():
    """Get or initialize the sentiment analysis pipeline"""
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        try:
            _sentiment_pipeline = pipeline(
                'sentiment-analysis',
                model='cardiffnlp/twitter-roberta-base-sentiment'
            )
            logger.info("Sentiment pipeline initialized successfully")
        except Exception as e:
            logger.error(f"Sentiment pipeline initialization failed: {e}")
            _sentiment_pipeline = lambda x: [{'label':'neutral','score':1.0}]
    return _sentiment_pipeline

def get_emotion_pipeline():
    """Get or initialize the emotion detection pipeline"""
    global _emotion_pipeline
    if _emotion_pipeline is None:
        try:
            tok = AutoTokenizer.from_pretrained('j-hartmann/emotion-english-distilroberta-base')
            mod = AutoModelForSequenceClassification.from_pretrained('j-hartmann/emotion-english-distilroberta-base')
            _emotion_pipeline = pipeline(
                'text-classification', model=mod, tokenizer=tok,
                return_all_scores=True
            )
            logger.info("Emotion pipeline initialized successfully")
        except Exception as e:
            logger.error(f"Emotion pipeline initialization failed: {e}")
            _emotion_pipeline = lambda x: [[{'label':'neutral','score':1.0}]]
    return _emotion_pipeline

def analyze_sentiment(text):
    """
    Analyze sentiment of text using TextBlob and RoBERTa models.
    
    Args:
        text (str): The input text
        
    Returns:
        tuple: (sentiment_score, sentiment_label)
    """
    # For compatibility with existing code
    if not text:
        return 0.0, "NEUTRAL"
        
    try:
        # TextBlob sentiment for polarity score (from -1 to 1)
        textblob_score = TextBlob(text).sentiment.polarity
        
        # RoBERTa model for more accurate sentiment classification
        pipe = get_sentiment_pipeline()
        result = pipe(text)
        hf_label = result[0]['label'].lower()
        hf_score = result[0]['score']
        
        # Map HuggingFace labels to our expected format
        label_map = {
            'negative': 'NEGATIVE',
            'neutral': 'NEUTRAL', 
            'positive': 'POSITIVE'
        }
        
        sentiment_label = label_map.get(hf_label, 'NEUTRAL')
        
        # Calculate final score (normalize from -1,1 to 0,1 range)
        sentiment_score = (textblob_score + 1) / 2
        
        # Check for crisis words to ensure those are always flagged as negative
        if check_crisis_keywords(text):
            sentiment_label = 'NEGATIVE'
            sentiment_score = min(0.2, sentiment_score)  # Ensure low score for crisis text
            
        return float(sentiment_score), sentiment_label
        
    except Exception as e:
        logger.error(f"Error in analyze_sentiment: {str(e)}")
        return 0.5, "NEUTRAL"  # Default fallback

def analyze_emotions(text: str) -> dict[str, float]:
    """
    Enhanced emotion analysis using regex patterns, TextBlob, and RoBERTa model.
    
    Args:
        text (str): Input text to analyze
        
    Returns:
        dict: Dictionary of emotions and their scores
    """
    if not text:
        return {"neutral": 1.0}
        
    try:
        # Emotion patterns for regex detection
        emotion_patterns = {
            'anger': r'(?i)(angry|mad|furious|irritated|hate)',
            'sadness': r'(?i)(sad|depress|heartbroken|miserable|grief)',
            'joy': r'(?i)(happy|excited|joyful|proud)',
            'fear': r'(?i)(afraid|scared|terrified|anxious)',
            'surprise': r'(?i)(surpris|shocked|wow)',
            'disgust': r'(?i)(disgust|gross|revolting)'
        }
        
        # Detect emotions through regex
        emotions = {}
        for emo, pat in emotion_patterns.items():
            cnt = len(re.findall(pat, text))
            if cnt: 
                emotions[emo] = min(0.5 + cnt*0.2, 0.95)
        
        if not emotions:
            emotions["neutral"] = 0.5
            
        # Enhance with RoBERTa emotion model if available
        try:
            pipe = get_emotion_pipeline()
            results = pipe(text)[0]
            
            # Combine with regex results
            for result in results:
                label = result['label']
                score = result['score']
                
                # Only add if score is significant
                if score > 0.1:
                    # If emotion already detected by regex, take the higher score
                    if label in emotions:
                        emotions[label] = max(emotions[label], score)
                    else:
                        emotions[label] = score
        except Exception as e:
            logger.warning(f"Emotion model inference failed: {str(e)}")
        
        # Normalize scores to ensure they sum to 1
        total = sum(emotions.values())
        if total > 0:
            emotions = {k: v/total for k, v in emotions.items()}
            
        return emotions
        
    except Exception as e:
        logger.error(f"Error in analyze_emotions: {str(e)}")
        return {"neutral": 1.0}
    
def check_crisis_keywords(text):
    """
    Check if text contains crisis keywords indicating potential self-harm, suicidal thoughts,
    or threatening language.
    
    Args:
        text (str): The text to check
        
    Returns:
        bool: True if crisis keywords found, False otherwise
    """
    if not text:
        return False
        
    # Use regex to match crisis patterns
    return bool(CRISIS_REGEX.search(text))

def get_crisis_resources():
    """
    Get crisis resources based on user region.
    
    Returns:
        str: Crisis resource information
    """
    resources = {
        'US': 'Call 988 (US Suicide & Crisis Lifeline) or text HOME to 741741.',
        'UK': 'Call Samaritans at 116 123 for 24/7 support.',
        'IN': 'Call AASRA at +91-22-27546669 for emotional support.',
        'AU': 'Call Lifeline Australia at 13 11 14 for 24/7 crisis support.'
    }
    
    contact = resources.get(USER_REGION, 'Please contact your local emergency services or mental health crisis line.')
    return f"I'm concerned about what you're saying. {contact} I'm here to provide supportive conversation but cannot continue if there are threats or concerning language."

def update_conversation_context(session_id, message, analysis):
    """
    Update conversation context in Redis.
    
    Args:
        session_id (str): User session ID
        message (str): User message
        analysis (dict): Analysis results
        
    Returns:
        dict: Updated context
    """
    if not redis_client:
        return {'count': 0, 'topics': [], 'patterns': {}, 'last_emoji': 0, 'prev': None}
        
    try:
        key = f"ctx:{session_id}"
        raw = redis_client.get(key)
        ctx = json.loads(raw) if raw else {
            'count': 0, 'topics': [], 'patterns': {}, 'last_emoji': 0, 'prev': None
        }
        
        ctx['count'] += 1
        
        # Extract topics
        found = re.findall(r"\b(job|breakup|family|health|lonely|anxiety|depress)\b", message, re.I)
        for t in found:
            t = t.lower()
            if t not in ctx['topics']: 
                ctx['topics'].insert(0, t)
        ctx['topics'] = ctx['topics'][:3]
        
        # Update word patterns
        for w in re.findall(r"\w+", message.lower()): 
            ctx['patterns'][w] = ctx['patterns'].get(w, 0) + 1
            
        # Track sentiment shifts
        prev = ctx.get('prev')
        shift = bool(prev and prev.get('primary') != analysis.get('primary'))
        ctx['prev'] = {
            'primary': analysis.get('primary', 'neutral'),
            'ts': datetime.datetime.now().isoformat()
        }
        
        # Store in Redis with expiration
        redis_client.set(key, json.dumps(ctx), ex=3600)
        
        ctx['shift'] = shift
        return ctx
        
    except Exception as e:
        logger.error(f"Error updating conversation context: {str(e)}")
        return {'count': 0, 'topics': [], 'patterns': {}, 'last_emoji': 0, 'prev': None, 'shift': False}

def generate_chat_response(message, user_context=None):
    """
    Generate enhanced chat response with multi-model sentiment analysis and context awareness.
    
    Args:
        message (str): User message
        user_context (dict, optional): Additional user context
        
    Returns:
        str: AI response
    """
    try:
        # Generate session ID based on context or use default
        session_id = user_context.get('session_id', 'default_session') if user_context else 'default_session'
        
        # Get context from UserState if available
        conversation_context = user_context.get('context', {}) if user_context else {}
        conversation_history = user_context.get('conversation_history', []) if user_context else []
        is_frustrated = user_context.get('is_frustrated', False) if user_context else False
        profile = user_context.get('profile', {}) if user_context else {}
        
        # Track last topic for better context awareness
        last_topic = user_context.get('last_topic', '') if user_context else ''
        
        # Enhanced topic tracking
        conversation_topics = user_context.get('topics', []) if user_context else []
        
        # Extract family members mentioned in current and past messages
        family_members_mentioned = []
        family_member_patterns = {
            'mom': r'\b(mom|mother|mum|mama)\b',
            'dad': r'\b(dad|father|papa|daddy)\b',
            'sister': r'\b(sister|sis)\b',
            'brother': r'\b(brother|bro)\b',
            'parent': r'\b(parent|parents)\b',
            'family': r'\b(family|relatives)\b'
        }
        
        for member, pattern in family_member_patterns.items():
            if re.search(pattern, message.lower()):
                family_members_mentioned.append(member)
                if member not in conversation_topics:
                    conversation_topics.append(member)
        
        # Emotion extraction for better handling of emotional contexts
        emotion_patterns = {
            'anger': r'\b(angry|anger|mad|furious|upset|pissed|annoyed)\b',
            'sadness': r'\b(sad|sadness|depress|down|blue|unhappy|cry|crying)\b',
            'anxiety': r'\b(scared|afraid|anxious|worried|nervous|anxiety|stress|stressed)\b',
            'happiness': r'\b(happy|joy|glad|excited|great|happiness)\b',
            'confusion': r'\b(confus|confused|unsure|uncertain|lost|perplex)\b'
        }
        
        emotions_mentioned = []
        for emotion, pattern in emotion_patterns.items():
            if re.search(pattern, message.lower()):
                emotions_mentioned.append(emotion)
                if emotion not in conversation_topics:
                    conversation_topics.append(emotion)
        
        # Check for crisis content first as highest priority
        # Expanded to include threatening language
        if check_crisis_keywords(message):
            # Check if it's more likely threatening language vs self-harm
            if any(phrase in message.lower() for phrase in ['kill you', 'hurt you', 'murder', 'bitch', 'fuck you']):
                return "I understand you may be frustrated, but I can't continue this conversation if it includes threatening language. I'm here to provide supportive conversation in a respectful environment."
            return get_crisis_resources()
            
        # Try intent matching for predefined mental health topics
        intent_name, intent_response = find_intent_match(message)
        if intent_response:
            logger.info(f"Using intent match response for: {intent_name}")
            # Update last topic if we found an intent match
            if user_context:
                user_context['last_topic'] = intent_name
                user_context['topics'] = conversation_topics
            return intent_response
        
        # Use Gemini if available (preferred approach for natural conversation)
        if chat_session:
            try:
                # Format conversation history for context
                conversation_text = ""
                if conversation_history:
                    recent_messages = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
                    for msg in recent_messages:
                        if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                            conversation_text += f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}\n"
                        elif isinstance(msg, str):
                            # Handle string messages
                            conversation_text += f"User: {msg}\n"
                
                # Create a more comprehensive context for better responses
                context_info = ""
                if conversation_topics:
                    context_info += f"Topics discussed: {', '.join(conversation_topics)}\n"
                if family_members_mentioned:
                    context_info += f"Family members mentioned: {', '.join(family_members_mentioned)}\n"
                if emotions_mentioned:
                    context_info += f"Emotions expressed: {', '.join(emotions_mentioned)}\n"
                
                # Create a prompt that guides the model with enhanced contextual awareness
                system_prompt = f"""
                You are MindWell, an empathetic mental health companion chatbot. Your goal is to respond naturally like a supportive friend would.

                Recent conversation context:
                {conversation_text}

                Current message: "{message}"

                Context information:
                {context_info}

                Important guidelines:
                1. Your responses must be natural, brief (1-3 sentences), and directly address what the user just said
                2. Acknowledge specific issues mentioned, especially family relationships, emotions, and personal problems
                3. If they express a feeling toward someone (like "I'm angry at my mom"), acknowledge BOTH the feeling AND the relationship
                4. If they mention family members, specifically address those relationships in your response
                5. If they repeat the same message, acknowledge that you understand their concern and ask a follow-up question
                6. If they mention academic struggles, offer empathy about the specific subject or problem
                7. If they seem frustrated or angry with you, apologize sincerely and try a completely different approach
                8. Detect hostile phrases and respond with gentle de-escalation
                9. If they say goodbye, respect their wish to end the conversation
                10. Never use generic responses like "I'm here to listen" repeatedly
                11. For relationship issues, validate their feelings and ask about the specific situation
                12. For work/job stress, acknowledge the pressure and ask about coping strategies
                13. For sleep problems, show understanding and ask about their sleep routine
                14. If they say something confusing like "what?", explain your previous response more clearly
                15. If they use profanity or threatening language, respond with firm boundaries but remain respectful
                16. NEVER invent context that wasn't mentioned - if they say "what math test?" and no math was discussed, acknowledge the confusion
                17. When they express anger/frustration toward people in their life (like "angry at my mom"), directly acknowledge that specific relationship dynamic
                18. For very short responses like "ok", ask an open-ended question to encourage further sharing

                Respond naturally:
                """
                
                # Get response from Gemini
                response = chat_session.generate_content(system_prompt)
                ai_response = response.text.strip()
                
                # Validate response
                if not ai_response or len(ai_response) < 5:
                    raise ValueError("Generated response too short")
                
                # Update context
                if user_context:
                    user_context['last_topic'] = ', '.join(conversation_topics) if conversation_topics else last_topic
                    user_context['topics'] = conversation_topics
                
                return ai_response
                
            except Exception as e:
                logger.error(f"Error in Gemini response generation: {str(e)}")
                # Fall through to fallback method
        
        # ENHANCED FALLBACK METHOD: More sophisticated rule-based response system
        
        # Extract key information from message
        message_lower = message.lower()
        words = message_lower.split()
        
        # Check for profanity and threatening language first
        profanity_indicators = ['fuck', 'shit', 'bitch', 'ass', 'damn', 'crap', 'asshole', 'dick']
        if any(word in message_lower for word in profanity_indicators):
            return "I understand you might be upset, but I'd appreciate if we could continue our conversation without that kind of language. What's bothering you that I can help with?"
        
        # Detect message repetition from user
        is_repetition = False
        if conversation_history and len(conversation_history) >= 2:
            previous_message = ""
            for msg in reversed(conversation_history):
                if isinstance(msg, dict) and msg.get('role') == 'user':
                    previous_message = msg.get('content', '').lower()
                    break
                elif isinstance(msg, str):
                    previous_message = msg.lower()
                    break
            
            # Check for repetition with some flexibility
            if previous_message and (previous_message == message_lower or 
                                    (len(previous_message) > 10 and 
                                     (previous_message in message_lower or message_lower in previous_message))):
                is_repetition = True
        
        # Check for confusion indicators like "what?" or "huh?"
        confusion_indicators = ['what?', 'huh?', 'what', 'huh', 'i dont understand', 'i don\'t understand', 'what do you mean']
        if any(message_lower == indicator for indicator in confusion_indicators) or (message_lower.endswith('?') and len(words) <= 2):
            # Provide a general response instead of assuming context
            return "I apologize for the confusion. Let's start over. Could you tell me what's on your mind today?"
        
        # Handle questions about specific topics that were never mentioned
        if "math" in message_lower and "test" in message_lower and "math" not in last_topic.lower():
            return "I apologize for the confusion. I don't believe we were discussing a math test. What would you like to talk about?"
            
        # Specific handling for typos in greetings 
        greeting_typos = ['good moring', 'good mrning', 'hello?', 'helo', 'hi there', 'hey there']
        if any(typo in message_lower for typo in greeting_typos):
            return "Hello there! How are you feeling today? I'm here to chat about whatever's on your mind."
        
        # Check for conversation enders or hostile language
        if any(word in message_lower for word in ['bye', 'goodbye', 'quit', 'exit']):
            return "I understand you want to end our conversation. Take care, and I'm here whenever you want to talk again."
        
        if any(phrase in message_lower for phrase in ['get lost', 'shut up', 'stupid bot', 'useless']):
            return "I sense you're frustrated with this conversation. That's completely understandable. Would you prefer to take a break or try discussing something else?"
        
        # Handle frustration signals
        frustration_indicators = ['annoying', 'irritating', 'stupid', 'understand', 'listen', 'make sense', 'dont you', 'don\'t you', 'frustrated', 'frustrating']
        if is_frustrated or any(indicator in message_lower for indicator in frustration_indicators):
            return get_emotion_response('frustrated', is_repetition)
        
        # ---- SPECIFIC SCENARIO HANDLERS ----
        
        # ENHANCED FAMILY RELATIONSHIP HANDLERS
        
        # Complex detection for family relationship issues with emotions
        family_emotion_patterns = []
        for family in ['mom', 'mother', 'dad', 'father', 'parent', 'sister', 'brother', 'family']:
            for emotion in ['angry', 'mad', 'upset', 'sad', 'hate', 'love', 'miss']:
                # Patterns like "angry at my mom" or "mad with my dad"
                family_emotion_patterns.append((
                    rf"{emotion}.*\b{family}\b|\b{family}\b.*{emotion}",
                    family, emotion
                ))
        
        # Check for complex relationship-emotion patterns
        for pattern, family, emotion in family_emotion_patterns:
            if re.search(pattern, message_lower):
                if emotion in ['angry', 'mad', 'upset', 'hate']:
                    if user_context:
                        user_context['last_topic'] = f'{family}_{emotion}'
                        user_context['topics'] = conversation_topics
                    responses = [
                        f"I understand you're feeling {emotion} toward your {family}. That's completely valid. Would you like to share more about what happened?",
                        f"It sounds like there's some tension between you and your {family}. Would you like to talk more about why you're feeling {emotion}?",
                        f"Feeling {emotion} at your {family} is a normal part of family dynamics. Could you tell me more about what triggered these feelings?"
                    ]
                    return random.choice(responses)
                elif emotion in ['sad', 'miss']:
                    if user_context:
                        user_context['last_topic'] = f'{family}_{emotion}'
                        user_context['topics'] = conversation_topics
                    responses = [
                        f"It sounds like you're feeling {emotion} about your {family}. That can be really hard. Would you like to share more?",
                        f"I hear that you're having some difficult feelings about your {family}. Would you like to talk more about what's going on?",
                        f"Relationships with family members can bring up strong emotions. Could you tell me more about your relationship with your {family}?"
                    ]
                    return random.choice(responses)
        
        # Direct emotion detection - prioritize this over scenario handlers
        # Check for direct emotion statements first
        if "angry" in message_lower or "anger" in message_lower or "mad" in message_lower:
            # Specific handling for anger
            if user_context:
                user_context['last_topic'] = 'angry'
                user_context['topics'] = conversation_topics
            return "I understand you're feeling angry. That's a completely valid emotion. Would you like to talk about what triggered this feeling?"
        
        # 1. Academic topic handling
        academic_indicators = ['mark', 'score', 'grade', 'exam', 'test', 'class', 'course',
                              'math', 'maths', 'science', 'english', 'history', 'subject',
                              'homework', 'assignment', 'study', 'teacher', 'professor', 'fail']
        
        if any(indicator in message_lower for indicator in academic_indicators):
            academic_subjects = ['math', 'maths', 'science', 'english', 'history', 'geography', 
                                'physics', 'chemistry', 'biology', 'literature', 'economics']
            
            subject = next((subj for subj in academic_subjects if subj in message_lower), 'subject')
            
            if 'less' in message_lower or 'low' in message_lower or 'bad' in message_lower or 'poor' in message_lower or 'fail' in message_lower or 'didn\'t study' in message_lower or 'didnt study' in message_lower:
                if user_context:
                    user_context['last_topic'] = f'{subject}_results'
                    user_context['topics'] = conversation_topics
                if is_repetition:
                    return f"I understand your concern about your {subject} marks. It can be really disappointing. Have you thought about what might have affected your performance?"
                return f"I hear that you're upset about your {subject} marks. That must be disappointing. Would you like to talk about what happened or how you're feeling about it?"
            
            if user_context:
                user_context['last_topic'] = f'{subject}_results'
                user_context['topics'] = conversation_topics
            return f"I see you're mentioning {subject}. What specifically about {subject} would you like to discuss?"
            
        # 2. Relationship problems
        relationship_indicators = ['boyfriend', 'girlfriend', 'partner', 'date', 'dating',
                                 'relationship', 'breakup', 'broke up', 'love', 'crush',
                                 'cheated', 'cheating', 'ex', 'dating app']
        
        if any(indicator in message_lower for indicator in relationship_indicators):
            if 'breakup' in message_lower or 'broke up' in message_lower:
                if user_context:
                    user_context['last_topic'] = 'breakup'
                    user_context['topics'] = conversation_topics
                return "I'm sorry to hear about your breakup. That can be really painful. How are you coping with it?"
            
            if 'cheated' in message_lower or 'cheating' in message_lower:
                if user_context:
                    user_context['last_topic'] = 'cheating'
                    user_context['topics'] = conversation_topics
                return "That sounds really hurtful. Dealing with cheating or trust issues can be incredibly difficult. How are you feeling about it right now?"
            
            if 'crush' in message_lower:
                if user_context:
                    user_context['last_topic'] = 'crush'
                    user_context['topics'] = conversation_topics
                return "Having feelings for someone can be both exciting and anxiety-producing. Would you like to talk about this person or how you're planning to approach the situation?"
            
            if is_repetition:
                return "Relationship challenges can be really complicated. What do you find most difficult about this situation right now?"
                
            if user_context:
                user_context['last_topic'] = 'relationship'
                user_context['topics'] = conversation_topics
            return "Relationships can be complicated. Would you like to talk more about what's happening between you two?"
            
        # 3. Work/Career stress
        work_indicators = ['job', 'work', 'boss', 'coworker', 'colleague', 'fired', 'laid off',
                         'unemployed', 'interview', 'career', 'promotion', 'office',
                         'workplace', 'quit job', 'resignation', 'salary', 'wage']
        
        if any(indicator in message_lower for indicator in work_indicators):
            if 'fired' in message_lower or 'laid off' in message_lower or 'unemployed' in message_lower:
                if user_context:
                    user_context['last_topic'] = 'job_loss'
                    user_context['topics'] = conversation_topics
                return "Losing a job can be really destabilizing and stressful. How are you handling this transition?"
            
            if 'interview' in message_lower:
                if user_context:
                    user_context['last_topic'] = 'interview'
                    user_context['topics'] = conversation_topics
                return "Job interviews can be nerve-wracking. Are you feeling prepared, or is there something specific you're worried about?"
            
            if 'boss' in message_lower:
                if user_context:
                    user_context['last_topic'] = 'boss'
                    user_context['topics'] = conversation_topics
                return "Difficulties with managers can make work really challenging. What's been happening with your boss?"
            
            if is_repetition:
                return "Work stress can really affect our wellbeing. What's the most challenging aspect of your situation right now?"
                
            if user_context:
                user_context['last_topic'] = 'work'
                user_context['topics'] = conversation_topics
            return "Work situations can be really stressful. What specifically has been difficult for you lately?"
            
        # 4. Family conflicts
        family_indicators = ['family', 'mom', 'dad', 'mother', 'father', 'parent', 'sister',
                           'brother', 'sibling', 'aunt', 'uncle', 'grandma', 'grandpa',
                           'grandmother', 'grandfather', 'relative', 'home']
        
        if any(indicator in message_lower for indicator in family_indicators):
            # Extract which family member
            family_members = ['mom', 'dad', 'mother', 'father', 'parent', 'sister', 'brother', 
                             'sibling', 'family', 'aunt', 'uncle', 'grandma', 'grandpa']
            
            member = next((mem for mem in family_members if mem in message_lower), 'family member')
            
            # Detect emotion toward family
            if any(word in message_lower for word in ['angry', 'mad', 'upset', 'fight', 'argue']):
                if user_context:
                    user_context['last_topic'] = f'{member}_conflict'
                    user_context['topics'] = conversation_topics
                if is_repetition:
                    return f"Family conflicts can be really challenging. What do you think is at the root of the tension between you and your {member}?"
                return f"It sounds like you're dealing with some tension with your {member}. Family relationships can be complicated. Would you like to share what happened?"
            
            if is_repetition:
                return f"I understand your {member} is important in this situation. How do you wish things were different between you?"
                
            if user_context:
                user_context['last_topic'] = f'{member}'
                user_context['topics'] = conversation_topics
            return f"I see you're mentioning your {member}. How are things between you two right now?"
            
        # 5. Sleep/Health issues
        health_indicators = ['sleep', 'insomnia', 'tired', 'exhausted', 'fatigue', 'sick',
                           'ill', 'headache', 'pain', 'doctor', 'medicine', 'medication',
                           'therapy', 'diagnosed', 'condition', 'symptom', 'diet', 'exercise']
                           
        if any(indicator in message_lower for indicator in health_indicators):
            if 'sleep' in message_lower or 'insomnia' in message_lower:
                if user_context:
                    user_context['last_topic'] = 'sleep'
                    user_context['topics'] = conversation_topics
                return "Sleep problems can really affect your mental health and daily functioning. How long have you been experiencing these difficulties?"
            
            if 'tired' in message_lower or 'exhausted' in message_lower or 'fatigue' in message_lower:
                if user_context:
                    user_context['last_topic'] = 'fatigue'
                    user_context['topics'] = conversation_topics
                return "Feeling constantly tired can be really challenging. Has something specific been draining your energy lately?"
            
            if 'therapy' in message_lower:
                if user_context:
                    user_context['last_topic'] = 'therapy'
                    user_context['topics'] = conversation_topics
                return "Therapy can be a really helpful tool. How have you been finding your experience with it so far?"
            
            if is_repetition:
                return "Health challenges can be really frustrating. What impact has this been having on your daily life?"
                
            if user_context:
                user_context['last_topic'] = 'health'
                user_context['topics'] = conversation_topics
            return "Taking care of your health is important. What have you tried so far to address this issue?"
            
        # 6. Anxiety/Panic scenarios
        anxiety_indicators = ['anxiety', 'anxious', 'panic', 'worry', 'stressed', 'stress',
                            'overwhelmed', 'afraid', 'scared', 'fear', 'nervous', 'overthinking',
                            'pressure', 'too much', 'can\'t handle']
                            
        if any(indicator in message_lower for indicator in anxiety_indicators):
            # Use the emotion template for the anxiety response
            if user_context:
                user_context['last_topic'] = 'anxiety'
                user_context['topics'] = conversation_topics
            return get_emotion_response('anxious', is_repetition)
            
        # 7. Loneliness/Social concerns
        social_indicators = ['lonely', 'alone', 'no friends', 'isolated', 'no one', 'nobody',
                           'can\'t connect', 'social anxiety', 'awkward', 'excluded', 
                           'left out', 'don\'t fit in', 'don\'t belong']
                           
        if any(indicator in message_lower for indicator in social_indicators):
            # Use the emotion template for the lonely response
            if user_context:
                user_context['last_topic'] = 'loneliness'
                user_context['topics'] = conversation_topics
            return get_emotion_response('lonely', is_repetition)
            
        # 8. Life direction/Existential concerns
        existential_indicators = ['purpose', 'meaning', 'pointless', 'future', 'direction',
                                'lost', 'confused', 'stuck', 'unmotivated', 'don\'t know what to do',
                                'what\'s the point', 'no purpose', 'no motivation']
                                
        if any(indicator in message_lower for indicator in existential_indicators):
            if indicator == 'confused':
                if user_context:
                    user_context['last_topic'] = 'confusion'
                    user_context['topics'] = conversation_topics
                return get_emotion_response('confused', is_repetition)
            elif indicator in ['unmotivated', 'no motivation']:
                if user_context:
                    user_context['last_topic'] = 'motivation'
                    user_context['topics'] = conversation_topics
                return "It can be difficult when you feel unmotivated. Is there something specific that used to inspire you that's no longer working?"
            
            if is_repetition:
                return "Wrestling with these bigger questions about purpose and meaning is very human. What things have felt meaningful to you in the past?"
                
            if user_context:
                user_context['last_topic'] = 'purpose'
                user_context['topics'] = conversation_topics
            return "Questions about purpose and direction can be really challenging. What aspects of your life feel most unsatisfying right now?"
        
        # 9. Direct emotion statements 
        # Use our more varied emotion templates for more natural responses
        EMOTION_TEMPLATES = {
            "happy": [
                "I'm glad to hear you're feeling happy! What's been bringing you joy lately?",
                "That's wonderful to hear. What's contributing to your happiness today?",
                "It's great that you're feeling positive. What's making you happy right now?"
            ],
            "sad": [
                "I'm sorry to hear you're feeling sad. Would you like to talk about what's bringing you down?",
                "It's okay to feel sad sometimes. Is there something specific that's making you feel this way?",
                "I understand that sadness can be difficult. What's on your mind right now?"
            ],
            "angry": [
                "I can tell you're feeling angry. That's a completely valid emotion. Would you like to share what's triggering these feelings?",
                "Anger is a natural response to many situations. What's making you feel angry right now?",
                "I understand you're feeling angry. Would you like to talk more about what's causing this feeling?"
            ],
            "anxious": [
                "Feeling anxious can be really challenging. Is there something specific that's causing you worry?",
                "I hear that you're feeling anxious. Would it help to talk about what's making you feel this way?",
                "Anxiety can be overwhelming sometimes. What's making you feel anxious today?"
            ],
            "frustrated": [
                "It sounds like you're feeling frustrated. That's completely understandable. What's causing this frustration?",
                "Frustration can be really difficult to deal with. Would you like to talk about what's happening?",
                "I understand you're feeling frustrated. What specifically is contributing to these feelings?"
            ],
            "lonely": [
                "Feeling lonely can be really difficult. Would you like to talk about what's making you feel isolated?",
                "I hear that you're feeling lonely. That's a very common but challenging feeling. What's going on in your social life right now?",
                "Loneliness is something many people experience. What do you think is contributing to these feelings for you?"
            ],
            "confused": [
                "It sounds like you're feeling confused. Would it help to break down what's happening step by step?",
                "Being confused or uncertain can be uncomfortable. What specific aspect feels most unclear right now?",
                "I understand you're feeling confused. Let's try to explore this together - what's on your mind?"
            ],
            "tired": [
                "Feeling tired can really affect your mood and outlook. Has something been disrupting your rest lately?",
                "I hear that you're feeling exhausted. That can make everything harder to deal with. What's been draining your energy?",
                "Tiredness can be both physical and emotional. What do you think is causing your fatigue?"
            ],
            "hopeful": [
                "It's great that you're feeling hopeful. What's giving you that sense of optimism?",
                "Hope is such an important emotion. What positive changes are you looking forward to?",
                "I'm glad you're feeling hopeful. What's contributing to this positive outlook?"
            ],
            "guilty": [
                "Guilt can be a heavy burden to carry. Would you like to talk about what's making you feel this way?",
                "I hear that you're feeling guilty. That's a difficult emotion to process. What's happened that's making you feel this way?",
                "Feeling guilty is common, but it can be painful. What actions or thoughts are triggering this feeling?"
            ],
            "embarrassed": [
                "Embarrassment can be really uncomfortable. Would you like to talk about what happened?",
                "I understand feeling embarrassed can be difficult. These feelings usually fade with time. Would you like to share what's making you feel this way?",
                "Many people experience embarrassment - you're not alone. What specifically triggered this feeling?"
            ],
            "proud": [
                "It's wonderful that you're feeling proud! What accomplishment or action is making you feel this way?",
                "Pride in yourself or others can be really positive. What's making you feel proud right now?",
                "I'm glad you're experiencing pride. Would you like to share more about what you've achieved?"
            ],
            "disappointed": [
                "I'm sorry to hear you're feeling disappointed. Would you like to talk about what didn't meet your expectations?",
                "Disappointment can be really tough to deal with. What happened that led to these feelings?",
                "I understand you're feeling disappointed. What were you hoping would happen differently?"
            ],
            "grateful": [
                "Gratitude is such a positive emotion to experience. What are you feeling grateful for?",
                "It's wonderful that you're feeling grateful. Would you like to share what's inspiring this feeling?",
                "Feeling grateful can really improve our outlook. What specifically are you appreciating right now?"
            ],
            "jealous": [
                "Jealousy is a common but challenging emotion. Would you like to talk about what's triggering these feelings?",
                "I understand you're feeling jealous. That's a natural human emotion. What's making you feel this way?",
                "Jealousy can be uncomfortable to experience. What situation is bringing up these feelings?"
            ],
            "overwhelmed": [
                "Feeling overwhelmed can be really difficult. Would it help to break down what's contributing to this feeling?",
                "I hear that you're feeling overwhelmed. That's understandable. What specifically feels like too much right now?",
                "Being overwhelmed can make everything seem impossible. What's the biggest source of pressure for you currently?"
            ],
            "hurt": [
                "I'm sorry to hear you're feeling hurt. Would you like to talk about what happened?",
                "Emotional pain can be really difficult to process. What's causing you to feel hurt?",
                "I understand you're feeling hurt. That's completely valid. Would you like to share what's happened?"
            ],
            "worried": [
                "Worry can be really consuming. What specific concerns are on your mind?",
                "I hear that you're feeling worried. Would it help to talk through what you're concerned about?",
                "Feeling worried is a common response to uncertainty. What specifically are you worried might happen?"
            ],
            "content": [
                "Contentment is such a peaceful feeling. What's helping you feel this sense of satisfaction?",
                "It's wonderful that you're feeling content. What aspects of your life are bringing you this feeling?",
                "Feeling content is something many people strive for. What's contributing to this positive state for you?"
            ]
        }
        
        emotion_patterns = {}
        for emotion in EMOTION_TEMPLATES.keys():
            patterns = [
                f"i am {emotion}", f"i'm {emotion}", f"im {emotion}", 
                f"i feel {emotion}", f"feeling {emotion}", f"feel {emotion}"
            ]
            emotion_patterns[emotion] = patterns
        
        # Check for direct emotion statements
        for emotion, patterns in emotion_patterns.items():
            if any(pattern in message_lower for pattern in patterns):
                if user_context:
                    user_context['last_topic'] = emotion
                    user_context['topics'] = conversation_topics
                return random.choice(EMOTION_TEMPLATES[emotion])
        
        # Handle positive phrases separately
        positive_phrases = ["feeling good", "feel good", "im good", "i'm good", "i am good", "doing well", "doing good"]
        if any(phrase in message_lower for phrase in positive_phrases):
            if user_context:
                user_context['last_topic'] = "positive"
                user_context['topics'] = conversation_topics
            positive_responses = [
                "I'm glad to hear you're doing well! Anything specific that's making your day good?",
                "That's great to hear! What's been going well for you?",
                "Wonderful! It's always good to hear positive things. What's contributing to your good mood?",
            ]
            return random.choice(positive_responses)
        
        # Emotion + target detection (improved)
        emotion_target_pattern = r"(angry|mad|upset|sad|happy|scared|worried|nervous|anxious|frustrated)\s+(at|with|about|because of)\s+(\w+)"
        emotion_targets = re.findall(emotion_target_pattern, message_lower)
    
        if emotion_targets:
            emotion, preposition, target = emotion_targets[0]
            if user_context:
                user_context['last_topic'] = f"{emotion}_{target}"
                user_context['topics'] = conversation_topics
            if is_repetition:
                return f"I understand you're feeling {emotion} {preposition} {target}. What do you think is the main reason this is affecting you so strongly?"
            return f"I see you're feeling {emotion} {preposition} {target}. That sounds challenging. Would you like to share more about what happened with {target}?"
        
        # Handle very short responses
        if len(words) <= 2:
            if message_lower in ['yes', 'yeah', 'sure', 'ok', 'okay']:
                return "Could you share more details about what's on your mind? I'd like to understand better."
            elif message_lower in ['no', 'nope', 'nothing']:
                return "That's alright. We can talk about something else if you prefer. How's your day going otherwise?"
            elif message_lower in ['hi', 'hello', 'hey']:
                if user_context:
                    user_context['last_topic'] = 'greeting'
                    user_context['topics'] = conversation_topics
                return "Hello! How are you feeling today? I'm here to chat about whatever's on your mind."
            else:
                return "I see. Would you like to tell me more about what's on your mind today?"
        
        # Check for feedback about the chatbot itself
        bot_feedback_phrases = ['bad bot', 'stupid bot', 'waste', 'useless', 'not helpful', 'terrible', 'awful', 'horrible', 'dumb bot']
        if any(phrase in message_lower for phrase in bot_feedback_phrases):
            return "I'm sorry I haven't been helpful. I'm still learning to be better at conversations. Would you like to try a different topic, or is there something specific you'd like help with?"
        
        # Generic responses based on message analysis and repetition
        if is_repetition:
            return "I notice you mentioned this again, so it must be important to you. Could you share a bit more about why this is affecting you?"
        
        # Analyze sentiment as fallback
        sentiment_score, sentiment_label = analyze_sentiment(message)
        
        if sentiment_label == "NEGATIVE":
            return "That sounds difficult. Can you tell me more about why this is bothering you?"
        elif sentiment_label == "POSITIVE":
            return "I'm glad to hear that positive note! What else is on your mind today?"
        else:
            # More neutral fallback that doesn't assume problems
            return "I'd like to hear more about that. What would you like to discuss today?"
        
    except Exception as e:
        logger.error(f"Error in chat response generation: {str(e)}")
        return "I'm having trouble processing that. Could you rephrase what you'd like to talk about?"

# Helper function to extract topics from message
def extract_topics(message):
    """Extract key topics from a message"""
    common_topics = [
        'family', 'mom', 'dad', 'parent', 'sister', 'brother',
        'school', 'work', 'job', 'study', 'test', 'exam',
        'friend', 'relationship', 'boyfriend', 'girlfriend',
        'stress', 'anxiety', 'depression', 'sad', 'angry', 'happy',
        'sleep', 'tired', 'exhausted', 'energy',
        'future', 'past', 'regret', 'worry'
    ]
    
    found_topics = []
    for topic in common_topics:
        if topic in message.lower():
            found_topics.append(topic)
    
    return found_topics[:3]  # Return top 3 topics

# Initialize singleton sentiment analyzer for the module
try:
    get_sentiment_pipeline()
    get_emotion_pipeline()
    logger.info("AI models initialized successfully")
except Exception as e:
    logger.error(f"Error initializing AI models: {str(e)}")

# Legacy function for mood pattern analysis
def get_mood_patterns(user_id, db, days=7):
    # Implementation unchanged to maintain compatibility
    return {
        'fluctuation': 'moderate',
        'trend': 'stable',
        'avg_sentiment': 0.5
    }