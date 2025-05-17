"""
AI Chat Integration Module

This module integrates advanced mental health components into the chat flow:
- UserStateManager for tracking user state
- EscalationManager for crisis detection
- ResponseValidator for ensuring quality responses
- ConversationAnalyzer for tracking trends
- SecureDataManager for privacy
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from uuid import uuid4

# Import advanced components
from . import (
    UserStateManager,
    UserProfile,
    ConversationContext,
    EscalationManager,
    EscalationLevel,
    ResponseValidator,
    ResponseQualityIssue,
    ConversationAnalyzer
)

# Import existing utilities
from .ai_utils import analyze_sentiment, analyze_emotions, generate_chat_response

logger = logging.getLogger(__name__)

# Initialize components
user_state_manager = None
escalation_manager = None
response_validator = None
conversation_analyzer = None

# Track previous responses to avoid repetition
previous_responses = {}
repetition_count = {}
# Track conversation history for better context
conversation_history = {}
# Track recognized topics
user_topics = {}

def initialize_components():
    """Initialize all advanced components"""
    global user_state_manager, escalation_manager, response_validator, conversation_analyzer
    
    try:
        # Initialize user state manager
        user_state_manager = UserStateManager()
        
        # Initialize escalation manager
        escalation_manager = EscalationManager(
            default_region=os.getenv("DEFAULT_REGION", "US"),
            api_key=os.getenv("CRISIS_API_KEY"),
            callback_url=os.getenv("CRISIS_CALLBACK_URL")
        )
        
        # Initialize response validator
        response_validator = ResponseValidator()
        
        # Initialize conversation analyzer
        conversation_analyzer = ConversationAnalyzer()
        
        logger.info("Advanced chatbot components initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize components: {str(e)}")
        return False

def extract_topics(message):
    """Extract important topics from the message"""
    topics = []
    
    # Extract family-related topics with more comprehensive patterns
    family_patterns = [
        (r'\b(mom|mother|mum|mama)\b', 'mom'),
        (r'\b(dad|father|papa|daddy)\b', 'dad'),
        (r'\b(sister|sis)\b', 'sister'),
        (r'\b(brother|bro)\b', 'brother'),
        (r'\b(parent|family)\b', 'family'),
        (r'\b(grandma|grandmother|nana)\b', 'grandmother'),
        (r'\b(grandpa|grandfather|grandad)\b', 'grandfather'),
        (r'\b(aunt|auntie)\b', 'aunt'),
        (r'\b(uncle)\b', 'uncle'),
        (r'\b(cousin)\b', 'cousin'),
    ]
    
    for pattern, topic in family_patterns:
        if re.search(pattern, message.lower()):
            topics.append(topic)
    
    # Extract emotion-related topics with more comprehensive patterns
    emotion_patterns = [
        (r'\b(angry|anger|mad|upset|pissed|annoyed|furious)\b', 'anger'),
        (r'\b(sad|depress|down|blue|unhappy|cry|crying|tears)\b', 'sadness'),
        (r'\b(scared|afraid|anxious|anxiety|worried|nervous|stress|stressed)\b', 'anxiety'),
        (r'\b(happy|joy|glad|excited|great|happiness|cheerful)\b', 'happiness'),
        (r'\b(confused|confusion|unsure|uncertain|lost|misunderstand)\b', 'confusion'),
        (r'\b(lonely|alone|isolated|no friends|no one)\b', 'loneliness'),
        (r'\b(tired|exhausted|fatigue|no energy|sleepy)\b', 'tiredness'),
        (r'\b(hate|hatred|despise|can\'t stand)\b', 'hatred'),
        (r'\b(love|adore|care for)\b', 'love'),
        (r'\b(guilty|guilt|shame|ashamed|blame)\b', 'guilt'),
        (r'\b(jealous|envy|envious)\b', 'jealousy'),
        (r'\b(disappointed|letdown|let down)\b', 'disappointment'),
        (r'\b(proud|pride|accomplished|achievement)\b', 'pride'),
    ]
    
    for pattern, topic in emotion_patterns:
        if re.search(pattern, message.lower()):
            topics.append(topic)
    
    # Extract relationship-emotion patterns (e.g., "angry at my mom")
    combined_patterns = []
    
    # Family members
    family_members = ['mom', 'mother', 'dad', 'father', 'sister', 'brother', 'parent', 'family', 'sibling', 'grandma', 'grandpa', 'aunt', 'uncle']
    
    # Emotions with prepositions
    emotion_prepositions = [
        (r'angry at|mad at|upset with|hate', 'anger_toward'),
        (r'sad about|crying over|depressed about', 'sad_about'),
        (r'worried about|anxious about|scared of', 'worried_about'),
        (r'love|miss|adore', 'love_for'),
        (r'disappointed in|let down by', 'disappointed_in')
    ]
    
    # Check for specific combinations
    for member in family_members:
        for pattern, emotion_type in emotion_prepositions:
            relation_pattern = r'(%s)\s+(\w+\s+)*(%s)' % (pattern, member)
            if re.search(relation_pattern, message.lower()):
                topics.append(f"{emotion_type}_{member}")
    
    # Extract life situation topics
    situation_patterns = [
        (r'\b(school|class|study|exam|test|homework|college|university|grade|course)\b', 'school'),
        (r'\b(work|job|boss|career|colleague|office|coworker|salary|workplace)\b', 'work'),
        (r'\b(friend|friendship|bestie|buddy|pal|mate)\b', 'friendship'),
        (r'\b(relationship|girlfriend|boyfriend|partner|dating|marriage|husband|wife|spouse|significant other|ex)\b', 'relationship'),
        (r'\b(sleep|insomnia|awake|dream|nightmare|rest|bed|tired)\b', 'sleep'),
        (r'\b(money|financial|afford|expensive|cost|payment|debt|bills|budget)\b', 'finances'),
        (r'\b(sick|ill|health|doctor|medication|medicine|symptoms|pain|disease|disorder|condition)\b', 'health'),
        (r'\b(therapy|therapist|counseling|counselor|psychologist|psychiatrist|mental health)\b', 'therapy'),
        (r'\b(future|plan|goal|aspiration|dream|ambition|career path)\b', 'future'),
        (r'\b(past|childhood|trauma|memory|memories|remember|when I was)\b', 'past'),
    ]
    
    for pattern, topic in situation_patterns:
        if re.search(pattern, message.lower()):
            topics.append(topic)
    
    return list(set(topics))  # Remove duplicates

def update_conversation_history(session_id, user_message, bot_response=None):
    """Update the conversation history for better context tracking"""
    global conversation_history, user_topics
    
    # Initialize history if needed
    if session_id not in conversation_history:
        conversation_history[session_id] = []
    
    # Add the message to history
    if user_message:
        conversation_history[session_id].append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Extract and update topics
        message_topics = extract_topics(user_message)
        if message_topics:
            if session_id not in user_topics:
                user_topics[session_id] = {}
            
            # Update topic occurrences and timestamps
            for topic in message_topics:
                if topic not in user_topics[session_id]:
                    user_topics[session_id][topic] = {
                        'count': 0,
                        'first_mentioned': datetime.now().isoformat(),
                        'last_mentioned': datetime.now().isoformat()
                    }
                
                user_topics[session_id][topic]['count'] += 1
                user_topics[session_id][topic]['last_mentioned'] = datetime.now().isoformat()
        
        # Special handling for relationship-emotion patterns
        detect_relationship_emotions(session_id, user_message)
    
    # Add bot response to history if provided
    if bot_response:
        conversation_history[session_id].append({
            'role': 'assistant',
            'content': bot_response,
            'timestamp': datetime.now().isoformat()
        })
    
    # Keep history to a reasonable size
    conversation_history[session_id] = conversation_history[session_id][-10:]
    
    return conversation_history[session_id]

def detect_relationship_emotions(session_id, message):
    """Specifically detect relationship-emotion patterns in messages"""
    global user_topics
    
    if session_id not in user_topics:
        user_topics[session_id] = {}
    
    # Pattern matching for "[emotion] at/with/about [person]"
    common_emotions = ['angry', 'mad', 'upset', 'sad', 'happy', 'frustrated', 'annoyed', 'disappointed', 'worried']
    prepositions = ['at', 'with', 'about', 'because of', 'toward', 'for', 'by']
    
    for emotion in common_emotions:
        for prep in prepositions:
            pattern = r'%s\s+%s\s+(\w+\s+)*(\w+)' % (emotion, prep)
            matches = re.finditer(pattern, message.lower())
            
            for match in matches:
                full_match = match.group(0)
                # Extract the target (usually a person) - last word in the match
                target = full_match.split()[-1]
                
                # Remove common articles, possessives, etc.
                if target in ['my', 'the', 'a', 'an', 'his', 'her', 'their']:
                    # If target is a possessive, get the word before the last
                    words = full_match.split()
                    if len(words) >= 2:
                        target = words[-2]
                
                # Create a relationship-emotion topic
                relationship_emotion = f"{emotion}_toward_{target}"
                
                # Add to topics with higher weighting
                if relationship_emotion not in user_topics[session_id]:
                    user_topics[session_id][relationship_emotion] = {
                        'count': 0,
                        'first_mentioned': datetime.now().isoformat(),
                        'last_mentioned': datetime.now().isoformat(),
                        'is_relationship_emotion': True  # Flag this as a special type
                    }
                
                user_topics[session_id][relationship_emotion]['count'] += 2  # Higher weight
                user_topics[session_id][relationship_emotion]['last_mentioned'] = datetime.now().isoformat()

def get_conversation_context(session_id):
    """Get the current conversation context"""
    history = conversation_history.get(session_id, [])
    topics = user_topics.get(session_id, {})
    
    # Find top topics by occurrence count
    top_topics = sorted(
        topics.items(), 
        key=lambda x: x[1]['count'], 
        reverse=True
    )[:3]
    
    # Get most recent user message if available
    last_user_message = None
    for msg in reversed(history):
        if msg['role'] == 'user':
            last_user_message = msg['content']
            break
    
    return {
        'history': history,
        'topics': top_topics,
        'last_message': last_user_message,
        'message_count': len(history)
    }

def detect_user_frustration(session_id, message):
    """Detect signs of user frustration with the conversation"""
    # Check for explicit frustration indicators
    frustration_keywords = [
        'stop', 'annoying', 'irritating', 'understand', 'stupid', 
        'useless', 'not helpful', 'confused', 'confusing', 'wtf',
        'can\'t you', 'cant you', 'don\'t understand', 'dont understand',
        'same thing', 'repeating', 'again', 'listen', 'get it', 'shut up',
        'not listening', 'idiot', 'dumb', 'bro', 'dude'
    ]
    
    # Direct check for frustration keywords
    has_frustration_keywords = any(keyword in message.lower() for keyword in frustration_keywords)
    
    # Check for repetition from the user
    history = conversation_history.get(session_id, [])
    user_messages = [msg['content'] for msg in history if msg['role'] == 'user']
    
    # Check if the user has repeated the same message
    user_repetition = False
    if len(user_messages) >= 2 and message.lower() == user_messages[-2].lower():
        user_repetition = True
    
    # Check if the conversation has gone on for a while with short user responses
    long_conversation_short_responses = (
        len(history) > 6 and
        len(message.split()) <= 3 and
        all(len(user_messages[-3:][i].split()) <= 3 for i in range(min(len(user_messages[-3:]), 3)))
    )
    
    # Check for multiple very short responses, which can indicate frustration
    multiple_short_responses = (
        len(user_messages) >= 3 and
        all(len(msg.split()) <= 2 for msg in user_messages[-3:])
    )
    
    return (
        has_frustration_keywords or 
        user_repetition or 
        long_conversation_short_responses or
        multiple_short_responses
    )

async def process_message(user_id, session_id, message):
    """
    Process an incoming user message with advanced features
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        message: User's message text
        
    Returns:
        Response object with AI response and analysis
    """
    global user_state_manager, escalation_manager, response_validator, conversation_analyzer
    
    # Initialize components if needed
    if user_state_manager is None:
        initialize_components()
    
    # Generate unique message ID
    message_id = str(uuid4())
    
    # Initialize response structure
    response = {
        "message_id": message_id,
        "timestamp": datetime.now().isoformat(),
        "response_text": "",
        "analysis": {},
        "escalation_level": "none",
        "escalation_actions": [],
        "quality_score": 1.0,
        "errors": []
    }
    
    try:
        # Step 1: Get or create user profile
        user_profile = await user_state_manager.get_or_create_profile(user_id)
        
        # Step 2: Get current conversation context
        context = await user_state_manager.get_conversation_context(session_id)
        if not context:
            # Initialize new context for this session
            context = ConversationContext(session_id=session_id, user_id=user_id)
        
        # Step 3: Add message to context
        await user_state_manager.add_message_to_context(
            session_id=session_id,
            role="user",
            content=message
        )
        
        # Step 4: Analyze message sentiment and emotions
        sentiment = analyze_sentiment(message)
        emotions = analyze_emotions(message)
        
        # Step 5: Update context with analysis
        message_analysis = {
            "sentiment": sentiment,
            "emotions": emotions,
            "topics": extract_topics(message)
        }
        
        await user_state_manager.update_context_analysis(
            session_id=session_id,
            message_id=message_id,
            analysis=message_analysis
        )
        
        # Step 6: Check for crisis/escalation scenarios
        escalation_result = await escalation_manager.evaluate_message(
            message=message,
            user_id=user_id,
            session_id=session_id,
            analysis=message_analysis,
            user_profile=user_profile,
            conversation_context=context
        )
        
        response["escalation_level"] = escalation_result["level"].name.lower()
        response["escalation_actions"] = escalation_result["actions"]
        
        # Step 7: Generate AI response
        context_data = await user_state_manager.get_context_for_llm(session_id)
        ai_response = generate_chat_response(
            message=message,
            context=context_data,
            sentiment=sentiment,
            emotions=emotions,
            user_profile=user_profile.to_dict()
        )
        
        # Step 8: Validate response quality
        validation_result = response_validator.validate_response(
            response=ai_response,
            user_message=message,
            conversation_context=context.to_dict(),
            user_profile=user_profile.to_dict()
        )
        
        response["quality_score"] = validation_result["quality_score"]
        
        # Step 9: Handle response based on validation and escalation
        if escalation_result["level"] >= EscalationLevel.MODERATE:
            # Use crisis response from escalation manager
            ai_response = escalation_result["recommended_response"]
        elif not validation_result["valid"]:
            # Improve response if it didn't pass validation
            ai_response = response_validator.improve_response(
                response=ai_response,
                validation_result=validation_result,
                user_message=message,
                context=context.to_dict()
            )
        
        response["response_text"] = ai_response
        
        # Step 10: Add bot response to conversation context
        await user_state_manager.add_message_to_context(
            session_id=session_id,
            role="assistant",
            content=ai_response
        )
        
        # Step 11: Update user profile with insights
        # Analyze the full conversation
        analysis_result = await conversation_analyzer.analyze_conversation(
            session_id=session_id,
            conversation_context=context.to_dict(),
            user_profile=user_profile.to_dict()
        )
        
        # Update user profile with insights
        if analysis_result["potential_insights"]:
            await user_state_manager.update_user_insights(
                user_id=user_id,
                insights=analysis_result["potential_insights"],
                emotional_patterns=analysis_result["emotional_patterns"],
                topic_trends=analysis_result["topic_trends"]
            )
        
        # Step 12: Prepare analysis for response
        response["analysis"] = {
            "sentiment": sentiment,
            "emotions": emotions,
            "topics": message_analysis["topics"],
            "conversation_quality": analysis_result["conversation_quality"],
            "dominant_emotions": analysis_result["emotional_patterns"].get("dominant_emotions", {}),
            "emotional_trajectory": analysis_result["emotional_patterns"].get("emotional_trajectory", ""),
            "recent_topics": analysis_result["topic_trends"].get("recent_topics", []),
            "user_engagement": analysis_result["conversation_dynamics"].get("user_engagement", ""),
            "potential_insights": analysis_result["potential_insights"]
        }
        
        # Step 13: Handle special escalation actions
        if "human_intervention" in escalation_result["actions"]:
            # Take special action for human intervention
            response["requires_human"] = True
            # Additional implementation details would go here
            # This might involve triggering notifications to mental health professionals
        
        # Step 14: Track response in validator history
        response_validator._add_to_history(
            response=ai_response,
            session_id=session_id
        )
        
    except Exception as e:
        # Handle errors gracefully
        logger.error(f"Error processing message: {str(e)}")
        response["errors"].append(str(e))
        
        # Provide generic response if errors occur
        if not response["response_text"]:
            response["response_text"] = "I'm having trouble processing your message right now. Could you try again in a moment?"
    
    return response

def generate_custom_response(message, analysis, session_id, context):
    """
    Generate a custom response based on context and analysis
    
    This function is used when the regular response generation isn't providing good enough results
    or when we need to handle special cases like user frustration.
    """
    # Get conversation history and topics
    history = context['history']
    topics = [topic for topic, data in context['topics']]
    
    # Detect closing intention
    closing_indicators = ['bye', 'goodbye', 'end', 'stop', 'quit', 'exit', 'that\'s all']
    is_closing = any(word in message.lower() for word in closing_indicators)
    
    # Handle closing intention
    if is_closing:
        closing_responses = [
            "Goodbye! I hope our conversation was helpful. Feel free to come back anytime.",
            "Take care! I'm here whenever you want to chat again.",
            "I understand you want to end our conversation. Wishing you well!"
        ]
        return closing_responses[hash(message) % len(closing_responses)]
    
    # Handle user frustration
    if analysis['is_frustrated']:
        frustration_responses = [
            "I'm sorry I haven't been understanding well. Let's try a different approach - what would you like to talk about?",
            "I apologize for not being helpful. Could you tell me more directly what's bothering you so I can better support you?",
            "I can see you're frustrated with me. Let me try to better understand - what's the main thing you want to discuss?",
            "I'm sorry for the confusion. Let's start fresh - what's on your mind right now?",
        ]
        return frustration_responses[hash(message) % len(frustration_responses)]
    
    # Check for relationship-emotion topics in user_topics for this session
    relationship_emotion_topics = []
    if session_id in user_topics:
        relationship_emotion_topics = [
            topic for topic, data in user_topics[session_id].items() 
            if data.get('is_relationship_emotion', False) and 
            (datetime.now() - datetime.fromisoformat(data['last_mentioned'])).total_seconds() < 300  # Within last 5 minutes
        ]
    
    # Enhanced handling for relationship-emotion patterns (e.g., "angry at mom")
    if relationship_emotion_topics:
        # Get the most recently mentioned relationship-emotion
        recent_relationship_emotion = max(
            [(topic, user_topics[session_id][topic]['last_mentioned']) for topic in relationship_emotion_topics],
            key=lambda x: x[1]
        )[0]
        
        # Parse the relationship emotion into components
        parts = recent_relationship_emotion.split('_')
        if len(parts) >= 3:
            emotion = parts[0]
            relation = '_'.join(parts[2:])  # In case the relation has underscores
            
            # Generate responses specific to this relationship-emotion
            if emotion in ['angry', 'mad', 'upset', 'frustrated', 'annoyed']:
                responses = [
                    f"I understand you're feeling {emotion} toward {relation}. That's completely valid. Would you like to share more about what happened between you two?",
                    f"It sounds like there's some tension between you and {relation}. Would you like to talk more about why you're feeling {emotion}?",
                    f"Feeling {emotion} at {relation} is a normal part of relationships. Could you tell me more about what triggered these feelings?"
                ]
                return responses[hash(message + session_id) % len(responses)]
            
            elif emotion in ['sad', 'hurt', 'disappointed']:
                responses = [
                    f"I hear that you're feeling {emotion} about your relationship with {relation}. That can be really difficult. Would you like to share more?",
                    f"When someone close to us like {relation} causes us to feel {emotion}, it can be particularly painful. Would you like to talk about what happened?",
                    f"I'm sorry to hear you're feeling {emotion} regarding {relation}. Would you like to explore these feelings a bit more?"
                ]
                return responses[hash(message + session_id) % len(responses)]
            
            elif emotion in ['worried', 'anxious', 'concerned', 'scared']:
                responses = [
                    f"I understand you're feeling {emotion} about {relation}. What specifically is causing you concern?",
                    f"Being {emotion} about someone like {relation} is natural when we care about them. What's happening that's making you feel this way?",
                    f"It sounds like you're experiencing some {emotion} feelings regarding {relation}. Would you like to talk about what's on your mind?"
                ]
                return responses[hash(message + session_id) % len(responses)]
            
            elif emotion in ['love', 'miss', 'care']:
                responses = [
                    f"It's clear that you have strong positive feelings for {relation}. Would you like to share more about your relationship?",
                    f"The {emotion} you feel for {relation} comes through in your message. How long have you been feeling this way?",
                    f"It's wonderful that you feel such {emotion} for {relation}. Would you like to talk more about your connection with them?"
                ]
                return responses[hash(message + session_id) % len(responses)]
    
    # Handle topic-specific responses
    for family_member in ['mom', 'mother', 'dad', 'father', 'parent', 'sister', 'brother', 'family']:
        if family_member in topics or family_member in message.lower():
            for emotion in ['anger', 'angry', 'mad', 'upset', 'pissed']:
                if emotion in topics or emotion in message.lower() or any(word in message.lower() for word in ['mad', 'upset', 'pissed']):
                    mom_anger_responses = [
                        f"It sounds like you're feeling anger toward your {family_member}. That's completely understandable - family relationships can be complicated. Would you like to share what happened?",
                        f"Being angry at your {family_member} is a common experience. What led to these feelings of anger?",
                        f"I hear that you're upset with your {family_member}. Family conflicts can be really difficult. What's been happening between you two?",
                        f"Feeling angry with family members like your {family_member} is something many people experience. Could you tell me more about the situation?"
                    ]
                    return mom_anger_responses[hash(message + session_id) % len(mom_anger_responses)]
            
            # If family member is mentioned but no specific emotion is detected
            family_responses = [
                f"You mentioned your {family_member}. Would you like to talk more about what's going on between you?",
                f"Family relationships, especially with {family_member}s, can be complex. What's happening with your {family_member}?",
                f"I notice you brought up your {family_member}. How is your relationship with them?"
            ]
            return family_responses[hash(message + session_id) % len(family_responses)]
    
    # Handle emotion-specific responses
    emotions = analysis['emotions']
    dominant_emotion = max(emotions.items(), key=lambda x: x[1])[0] if emotions else None
    
    if dominant_emotion == 'anger' and emotions.get(dominant_emotion, 0) > 0.3:
        anger_responses = [
            "I can tell you're feeling angry. That's a completely valid emotion. Would you like to share more about what's triggering these feelings?",
            "Your anger is understandable. Sometimes talking about what's making you angry can help process those feelings. What's happening?",
            "I hear that you're angry. Would you like to talk more about what's causing this feeling?"
        ]
        return anger_responses[hash(message + session_id) % len(anger_responses)]
    
    elif dominant_emotion == 'sadness' and emotions.get(dominant_emotion, 0) > 0.3:
        sadness_responses = [
            "I can sense that you're feeling sad. I'm here to listen if you want to share what's making you feel this way.",
            "It sounds like you're going through a difficult time. Would you like to talk about what's making you sad?",
            "I'm sorry to hear you're feeling down. Sometimes talking about our sadness can help us process it. What's on your mind?"
        ]
        return sadness_responses[hash(message + session_id) % len(sadness_responses)]
    
    # Enhanced response for confusion expressions (what?, huh?, etc.)
    confusion_expressions = ['what', 'what?', 'huh', 'huh?', 'i don\'t understand', 'i dont understand', 'what do you mean']
    if any(expression == message.lower().strip() for expression in confusion_expressions):
        # Get the last bot message if available
        last_bot_message = None
        for msg in reversed(history):
            if msg['role'] == 'assistant':
                last_bot_message = msg['content']
                break
        
        confusion_responses = [
            "I apologize for the confusion. Let me try to be clearer. What specific part didn't make sense to you?",
            "I'm sorry if I wasn't clear. Let's start fresh - what would you like to talk about?",
            "I understand I might not have been clear. Is there something specific you'd like me to explain better?"
        ]
        return confusion_responses[hash(message + session_id) % len(confusion_responses)]
    
    # Handle very short messages
    if len(message.split()) <= 2:
        short_message_responses = [
            "I'd like to understand better. Could you share a bit more about what's on your mind?",
            "I'm here to listen. Would you like to elaborate on that?",
            "I want to be helpful - could you tell me more about what you're thinking or feeling?"
        ]
        return short_message_responses[hash(message + session_id) % len(short_message_responses)]
    
    # Default responses based on sentiment
    sentiment_label = analysis['sentiment_label']
    
    if sentiment_label == "NEGATIVE":
        negative_responses = [
            "It sounds like you're going through something difficult. I'm here to listen if you want to share more.",
            "I'm sorry to hear that. Would you like to talk more about what's troubling you?",
            "That must be hard to deal with. Would you like to explore these feelings a bit more?"
        ]
        return negative_responses[hash(message + session_id) % len(negative_responses)]
    
    elif sentiment_label == "POSITIVE":
        positive_responses = [
            "I'm glad to hear that! Would you like to share more about what's going well?",
            "That sounds positive. What else has been good lately?",
            "It's great to hear something positive! Would you like to talk more about it?"
        ]
        return positive_responses[hash(message + session_id) % len(positive_responses)]
    
    else:  # NEUTRAL
        neutral_responses = [
            "I'm listening. What else would you like to talk about today?",
            "I'm here to chat about whatever's on your mind. Is there something specific you'd like to discuss?",
            "I'm here to support you. What's been on your mind lately?"
        ]
        return neutral_responses[hash(message + session_id) % len(neutral_responses)] 