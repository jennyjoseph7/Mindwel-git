"""
UserStateManager Module

This module provides comprehensive user state tracking for mental health conversations:
- Maintains user profiles with preferences and patterns
- Tracks conversation context and history
- Identifies recurring topics and emotional patterns
- Provides rich context for improved AI responses
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import re

# Configure logging
logger = logging.getLogger(__name__)

class UserProfile:
    """User profile containing preferences, patterns, and metadata"""
    
    def __init__(self, user_id: str, data: Dict[str, Any] = None):
        self.user_id = user_id
        self.created_at = datetime.now().isoformat()
        self.last_active = datetime.now().isoformat()
        self.interaction_count = 0
        self.preferences = {}
        self.emotional_patterns = {
            "common_emotions": {},
            "triggers": {},
            "trend": "neutral"
        }
        self.demographics = {}
        self.topics_of_interest = []
        self.conversation_style = "standard"
        self.crisis_history = []
        
        # Initialize with provided data if available
        if data:
            self.update(data)
    
    def update(self, data: Dict[str, Any]) -> None:
        """Update profile with new data"""
        for key, value in data.items():
            if hasattr(self, key) and key != "user_id":
                setattr(self, key, value)
        
        self.last_active = datetime.now().isoformat()
        self.interaction_count += 1
    
    def update_emotional_patterns(self, emotion_data: Dict[str, float]) -> None:
        """Update emotional patterns based on new data"""
        # Track emotion frequencies
        for emotion, score in emotion_data.items():
            if score > 0.3:  # Only track significant emotions
                if emotion not in self.emotional_patterns["common_emotions"]:
                    self.emotional_patterns["common_emotions"][emotion] = {
                        "count": 0,
                        "avg_intensity": 0.0,
                        "first_observed": datetime.now().isoformat()
                    }
                
                # Update count and intensity
                current = self.emotional_patterns["common_emotions"][emotion]
                current["count"] += 1
                current["avg_intensity"] = (
                    (current["avg_intensity"] * (current["count"] - 1) + score) / 
                    current["count"]
                )
                current["last_observed"] = datetime.now().isoformat()
        
        # Determine emotional trend
        emotions = self.emotional_patterns["common_emotions"]
        if emotions:
            sorted_emotions = sorted(
                emotions.items(), 
                key=lambda x: (x[1]["count"], x[1]["avg_intensity"]), 
                reverse=True
            )
            
            # Set the trend based on most frequent emotions
            if sorted_emotions:
                self.emotional_patterns["trend"] = sorted_emotions[0][0]
    
    def add_topic(self, topic: str) -> None:
        """Add topic of interest"""
        if topic and topic not in self.topics_of_interest:
            self.topics_of_interest.append(topic)
            # Keep the list to a reasonable size
            self.topics_of_interest = self.topics_of_interest[:10]
    
    def record_crisis(self, severity: str, topic: str) -> None:
        """Record a crisis event"""
        self.crisis_history.append({
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "topic": topic
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "user_id": self.user_id,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "interaction_count": self.interaction_count,
            "preferences": self.preferences,
            "emotional_patterns": self.emotional_patterns,
            "demographics": self.demographics,
            "topics_of_interest": self.topics_of_interest,
            "conversation_style": self.conversation_style,
            "crisis_history": self.crisis_history
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Create profile from dictionary"""
        profile = cls(data.get("user_id", "unknown"))
        profile.update(data)
        return profile


class ConversationContext:
    """Maintains conversation context with memory and pattern recognition"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now().isoformat()
        self.last_updated = datetime.now().isoformat()
        self.messages = []
        self.topics = {}  # Topic frequency tracking
        self.sentiment_history = []
        self.emotion_history = []
        self.detected_patterns = {
            "repetition": False,
            "topic_switching": False,
            "emotional_escalation": False,
            "engagement_level": "normal"
        }
        self.summary = ""
        self.important_mentions = {
            "people": {},
            "events": {},
            "concerns": {}
        }
    
    def add_message(self, role: str, content: str, 
                    analysis: Dict[str, Any] = None) -> None:
        """Add a message to the conversation history"""
        self.last_updated = datetime.now().isoformat()
        
        # Create message object
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add analysis if provided
        if analysis:
            message["analysis"] = analysis
            
            # Update sentiment and emotion history
            if "sentiment" in analysis:
                self.sentiment_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "value": analysis["sentiment"]
                })
            
            if "emotions" in analysis:
                self.emotion_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "values": analysis["emotions"]
                })
            
            # Update topics based on analysis
            if "topics" in analysis and isinstance(analysis["topics"], list):
                for topic in analysis["topics"]:
                    if topic in self.topics:
                        self.topics[topic]["count"] += 1
                        self.topics[topic]["last_mentioned"] = datetime.now().isoformat()
                    else:
                        self.topics[topic] = {
                            "count": 1,
                            "first_mentioned": datetime.now().isoformat(),
                            "last_mentioned": datetime.now().isoformat()
                        }
            
            # Extract important mentions
            if role == "user" and content:
                self._extract_important_mentions(content)
        
        # Add message to history
        self.messages.append(message)
        
        # Keep history to a reasonable size
        if len(self.messages) > 20:
            self.messages = self.messages[-20:]
        
        # Detect patterns after user messages
        if role == "user":
            self._detect_patterns(content, analysis)
    
    def _extract_important_mentions(self, content: str) -> None:
        """Extract important entities mentioned in the message"""
        # Extract people mentions (family, friends, etc.)
        people_patterns = {
            "mom": r'\b(mom|mother|mum|mama)\b',
            "dad": r'\b(dad|father|papa)\b',
            "partner": r'\b(husband|wife|boyfriend|girlfriend|partner|spouse)\b',
            "friend": r'\b(friend|bestie|buddy)\b',
            "therapist": r'\b(therapist|counselor|psychologist|psychiatrist)\b',
            "doctor": r'\b(doctor|physician|nurse|specialist)\b',
            "boss": r'\b(boss|manager|supervisor)\b',
            "colleague": r'\b(colleague|coworker|workmate)\b'
        }
        
        for person_type, pattern in people_patterns.items():
            if re.search(pattern, content.lower()):
                if person_type not in self.important_mentions["people"]:
                    self.important_mentions["people"][person_type] = {
                        "count": 0,
                        "first_mentioned": datetime.now().isoformat()
                    }
                
                self.important_mentions["people"][person_type]["count"] += 1
                self.important_mentions["people"][person_type]["last_mentioned"] = datetime.now().isoformat()
        
        # Extract significant life events
        event_patterns = {
            "job_change": r'\b(new job|fired|laid off|quit|started job|promotion|career change)\b',
            "relationship_change": r'\b(broke up|breakup|divorce|separated|new relationship|dating|married|engaged)\b',
            "health_issue": r'\b(diagnosed|sick|ill|injury|hospital|surgery|condition|symptoms)\b',
            "moving": r'\b(moved|moving|new home|new apartment|relocation|new city)\b',
            "education": r'\b(school|college|university|class|course|degree|graduated|studying)\b',
            "financial": r'\b(money|debt|bills|financial|afford|expensive|payment|salary|budget)\b'
        }
        
        for event_type, pattern in event_patterns.items():
            if re.search(pattern, content.lower()):
                if event_type not in self.important_mentions["events"]:
                    self.important_mentions["events"][event_type] = {
                        "count": 0,
                        "first_mentioned": datetime.now().isoformat()
                    }
                
                self.important_mentions["events"][event_type]["count"] += 1
                self.important_mentions["events"][event_type]["last_mentioned"] = datetime.now().isoformat()
        
        # Extract key concerns/worries
        concern_patterns = {
            "sleep": r'\b(insomnia|sleep|cant sleep|trouble sleeping|nightmares)\b',
            "anxiety": r'\b(anxiety|anxious|panic|worry|worried|stress|stressed)\b',
            "depression": r'\b(depression|depressed|hopeless|sad|down|blue|unhappy)\b',
            "social": r'\b(lonely|alone|isolated|no friends|social anxiety)\b',
            "work": r'\b(work stress|workload|job pressure|workplace|deadlines)\b',
            "future": r'\b(future|planning|goals|purpose|meaning|direction)\b'
        }
        
        for concern_type, pattern in concern_patterns.items():
            if re.search(pattern, content.lower()):
                if concern_type not in self.important_mentions["concerns"]:
                    self.important_mentions["concerns"][concern_type] = {
                        "count": 0,
                        "first_mentioned": datetime.now().isoformat()
                    }
                
                self.important_mentions["concerns"][concern_type]["count"] += 1
                self.important_mentions["concerns"][concern_type]["last_mentioned"] = datetime.now().isoformat()
    
    def _detect_patterns(self, content: str, analysis: Dict[str, Any] = None) -> None:
        """Detect conversation patterns"""
        # Check for message repetition
        if len(self.messages) >= 3:
            user_messages = [m for m in self.messages if m["role"] == "user"]
            if len(user_messages) >= 2:
                last_message = user_messages[-1]["content"].lower()
                previous_message = user_messages[-2]["content"].lower()
                
                # Check for exact repetition or high similarity
                if last_message == previous_message or (
                    len(last_message) > 5 and 
                    (last_message in previous_message or previous_message in last_message)
                ):
                    self.detected_patterns["repetition"] = True
        
        # Check for topic switching
        if analysis and "topics" in analysis and self.topics:
            current_topics = set(analysis["topics"])
            
            # Get recent topics from last few messages
            recent_topics = set()
            for message in reversed(self.messages[:-1]):
                if "analysis" in message and "topics" in message["analysis"]:
                    recent_topics.update(message["analysis"]["topics"])
                if len(recent_topics) >= 3:  # Consider up to 3 recent topics
                    break
            
            # If no overlap between current and recent topics, might be topic switching
            if current_topics and recent_topics and not current_topics.intersection(recent_topics):
                self.detected_patterns["topic_switching"] = True
        
        # Check for emotional escalation
        if len(self.emotion_history) >= 3:
            # Look at negative emotions (anger, sadness, anxiety)
            negative_emotions = ["anger", "sadness", "anxiety", "fear", "disgust"]
            
            # Calculate negative emotion intensity for recent messages
            recent_intensities = []
            for emotion_data in self.emotion_history[-3:]:
                intensity = sum(
                    emotion_data["values"].get(emotion, 0) 
                    for emotion in negative_emotions
                )
                recent_intensities.append(intensity)
            
            # Check if there's an upward trend in negative emotions
            if (len(recent_intensities) >= 3 and
                recent_intensities[-1] > recent_intensities[-2] > recent_intensities[-3] and
                recent_intensities[-1] > 0.5):  # Significant intensity in latest message
                self.detected_patterns["emotional_escalation"] = True
        
        # Determine engagement level
        if len(self.messages) >= 5:
            user_messages = [m for m in self.messages[-5:] if m["role"] == "user"]
            avg_length = sum(len(m["content"].split()) for m in user_messages) / max(len(user_messages), 1)
            
            if avg_length < 3:
                self.detected_patterns["engagement_level"] = "low"
            elif avg_length > 15:
                self.detected_patterns["engagement_level"] = "high"
            else:
                self.detected_patterns["engagement_level"] = "normal"
    
    def generate_summary(self) -> str:
        """Generate a concise summary of the conversation"""
        # Start with basic stats
        num_messages = len([m for m in self.messages if m["role"] == "user"])
        
        # Get top topics
        top_topics = sorted(
            self.topics.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:3]
        
        top_topics_text = ", ".join([t[0] for t in top_topics]) if top_topics else "None"
        
        # Get sentiment trend
        sentiment_trend = "neutral"
        if len(self.sentiment_history) >= 3:
            recent_avg = sum(s["value"] for s in self.sentiment_history[-3:]) / 3
            if recent_avg < 0.3:
                sentiment_trend = "negative"
            elif recent_avg > 0.7:
                sentiment_trend = "positive"
        
        # Get important mentions
        people = sorted(
            self.important_mentions["people"].items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:2]
        
        concerns = sorted(
            self.important_mentions["concerns"].items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:2]
        
        people_text = ", ".join([p[0] for p in people]) if people else "None"
        concerns_text = ", ".join([c[0] for c in concerns]) if concerns else "None"
        
        # Create the summary
        summary = (
            f"Conversation with {num_messages} user messages. "
            f"Main topics: {top_topics_text}. "
            f"Sentiment: {sentiment_trend}. "
            f"Key people: {people_text}. "
            f"Main concerns: {concerns_text}."
        )
        
        self.summary = summary
        return summary
    
    def get_recent_messages(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get the most recent messages"""
        return self.messages[-count:] if len(self.messages) >= count else self.messages
    
    def get_context_for_response(self) -> Dict[str, Any]:
        """Get rich context for generating the next response"""
        # Update summary
        self.generate_summary()
        
        # Get top topics
        top_topics = sorted(
            self.topics.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:5]
        
        # Get recent messages
        recent_messages = self.get_recent_messages(5)
        
        # Get important entities
        important_people = sorted(
            self.important_mentions["people"].items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        important_concerns = sorted(
            self.important_mentions["concerns"].items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        # Prepare message context
        context = {
            "summary": self.summary,
            "topics": {name: data["count"] for name, data in top_topics},
            "recent_messages": recent_messages,
            "patterns": self.detected_patterns,
            "important_people": {name: data["count"] for name, data in important_people},
            "important_concerns": {name: data["count"] for name, data in important_concerns}
        }
        
        return context
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "messages": self.messages,
            "topics": self.topics,
            "sentiment_history": self.sentiment_history,
            "emotion_history": self.emotion_history,
            "detected_patterns": self.detected_patterns,
            "summary": self.summary,
            "important_mentions": self.important_mentions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        """Create context from dictionary"""
        context = cls(data.get("session_id", "unknown"))
        
        # Set properties from the data
        context.created_at = data.get("created_at", context.created_at)
        context.last_updated = data.get("last_updated", context.last_updated)
        context.messages = data.get("messages", [])
        context.topics = data.get("topics", {})
        context.sentiment_history = data.get("sentiment_history", [])
        context.emotion_history = data.get("emotion_history", [])
        context.detected_patterns = data.get("detected_patterns", context.detected_patterns)
        context.summary = data.get("summary", "")
        context.important_mentions = data.get("important_mentions", context.important_mentions)
        
        return context


class UserStateManager:
    """Manages user state across conversations"""
    
    def __init__(self, storage_backend=None):
        self.profiles = {}  # In-memory cache of user profiles
        self.contexts = {}  # In-memory cache of conversation contexts
        self.storage = storage_backend  # External storage provider (optional)
        logger.info("UserStateManager initialized")
    
    async def get_user_profile(self, user_id: str) -> UserProfile:
        """Get user profile, loading from storage if needed"""
        if user_id in self.profiles:
            return self.profiles[user_id]
        
        profile = None
        
        # Try to load from storage
        if self.storage:
            try:
                profile_data = await self.storage.get_user_profile(user_id)
                if profile_data:
                    profile = UserProfile.from_dict(profile_data)
            except Exception as e:
                logger.error(f"Error loading user profile from storage: {str(e)}")
        
        # Create new profile if not found
        if not profile:
            profile = UserProfile(user_id)
        
        # Cache the profile
        self.profiles[user_id] = profile
        return profile
    
    async def get_conversation_context(self, session_id: str) -> ConversationContext:
        """Get conversation context, loading from storage if needed"""
        if session_id in self.contexts:
            return self.contexts[session_id]
        
        context = None
        
        # Try to load from storage
        if self.storage:
            try:
                context_data = await self.storage.get_conversation_context(session_id)
                if context_data:
                    context = ConversationContext.from_dict(context_data)
            except Exception as e:
                logger.error(f"Error loading conversation context from storage: {str(e)}")
        
        # Create new context if not found
        if not context:
            context = ConversationContext(session_id)
        
        # Cache the context
        self.contexts[session_id] = context
        return context
    
    async def save_user_profile(self, profile: UserProfile) -> bool:
        """Save user profile to storage"""
        # Update cache
        self.profiles[profile.user_id] = profile
        
        # Save to storage if available
        if self.storage:
            try:
                await self.storage.save_user_profile(profile.to_dict())
                return True
            except Exception as e:
                logger.error(f"Error saving user profile to storage: {str(e)}")
                return False
        
        return True
    
    async def save_conversation_context(self, context: ConversationContext) -> bool:
        """Save conversation context to storage"""
        # Update cache
        self.contexts[context.session_id] = context
        
        # Save to storage if available
        if self.storage:
            try:
                await self.storage.save_conversation_context(context.to_dict())
                return True
            except Exception as e:
                logger.error(f"Error saving conversation context to storage: {str(e)}")
                return False
        
        return True
    
    async def process_message(self, user_id: str, session_id: str, 
                             message: str, analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a user message and update state
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            message: User message text
            analysis: Pre-analyzed message data (sentiment, emotions, etc.)
            
        Returns:
            Dict containing updated profile and context
        """
        # Get user profile and conversation context
        profile = await self.get_user_profile(user_id)
        context = await self.get_conversation_context(session_id)
        
        # Update conversation context with the message
        context.add_message("user", message, analysis)
        
        # Extract topics from message via context
        topics = []
        if analysis and "topics" in analysis:
            topics = analysis["topics"]
        
        # Update profile with topics
        for topic in topics:
            profile.add_topic(topic)
        
        # Update emotional patterns in profile
        if analysis and "emotions" in analysis:
            profile.update_emotional_patterns(analysis["emotions"])
        
        # Save updates
        await self.save_user_profile(profile)
        await self.save_conversation_context(context)
        
        # Return the updated profile and context
        return {
            "profile": profile.to_dict(),
            "context": context.get_context_for_response()
        }
    
    async def add_assistant_response(self, session_id: str, response: str, 
                                    analysis: Dict[str, Any] = None) -> bool:
        """Add an assistant response to the conversation context"""
        try:
            # Get conversation context
            context = await self.get_conversation_context(session_id)
            
            # Add the message
            context.add_message("assistant", response, analysis)
            
            # Save the updated context
            await self.save_conversation_context(context)
            
            return True
        except Exception as e:
            logger.error(f"Error adding assistant response: {str(e)}")
            return False
    
    async def get_user_state(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Get current user state (profile and context)"""
        profile = await self.get_user_profile(user_id)
        context = await self.get_conversation_context(session_id)
        
        return {
            "profile": profile.to_dict(),
            "context": context.get_context_for_response()
        }
    
    async def update_user_preferences(self, user_id: str, 
                                     preferences: Dict[str, Any]) -> bool:
        """Update user preferences"""
        try:
            profile = await self.get_user_profile(user_id)
            
            # Update preferences
            profile.preferences.update(preferences)
            
            # Save changes
            await self.save_user_profile(profile)
            
            return True
        except Exception as e:
            logger.error(f"Error updating user preferences: {str(e)}")
            return False
    
    async def record_crisis_event(self, user_id: str, session_id: str,
                                 severity: str, topic: str) -> bool:
        """Record a crisis event for a user"""
        try:
            profile = await self.get_user_profile(user_id)
            context = await self.get_conversation_context(session_id)
            
            # Record the event in the user profile
            profile.record_crisis(severity, topic)
            
            # Add a note to the conversation context
            context.add_message(
                "system",
                f"Crisis event detected: {severity} regarding {topic}",
                {"event_type": "crisis", "severity": severity, "topic": topic}
            )
            
            # Save changes
            await self.save_user_profile(profile)
            await self.save_conversation_context(context)
            
            return True
        except Exception as e:
            logger.error(f"Error recording crisis event: {str(e)}")
            return False
    
    def clear_cache(self) -> None:
        """Clear in-memory caches"""
        self.profiles = {}
        self.contexts = {}
        logger.info("UserStateManager cache cleared") 