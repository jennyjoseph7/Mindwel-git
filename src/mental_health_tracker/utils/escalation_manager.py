"""
Escalation Manager: Handles crisis detection, risk assessment, and human handoff

Features:
- Multi-factor crisis detection (sentiment, emotions, keywords, patterns)
- Graduated escalation levels with appropriate responses
- Optional human-in-the-loop integration
- Location-based crisis resources
"""
import re
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import httpx
import asyncio
from uuid import uuid4
import os
from enum import IntEnum

logger = logging.getLogger(__name__)

class EscalationLevel(IntEnum):
    """Enumeration of escalation severity levels"""
    NONE = 0
    MILD = 1
    MODERATE = 2
    SEVERE = 3
    EMERGENCY = 4

# Define crisis detection patterns
CRISIS_PATTERNS = [
    r"\bkill myself\b", r"\bsuicid(e|al)\b", r"\bwant(ing)? to die\b",
    r"\bend (my|this) life\b", r"\bno reason to live\b",
    r"\bharm (myself|me)\b", r"\bi'?m going to die\b", 
    r"\btake my (own )?life\b", r"\bdon'?t want to (be here|live|exist)",
    r"\b(can'?t|cannot) go on\b", r"\bgive(ing)? up\b", r"\bno (hope|future)\b",
    r"\bdeath\b", r"\bhopeless\b"
]

# Additional concerning patterns that may indicate rising risk
CONCERNING_PATTERNS = [
    r"\balone\b", r"\bisolat(ed|ion)\b", r"\bworthless\b", r"\btrapped\b",
    r"\bburden\b", r"\bnobody cares\b", r"\bempty\b", r"\bno point\b",
    r"\bpain(ful)?\b", r"\btoo much\b", r"\bcan'?t (take|handle|bear) it\b",
    r"\bdon'?t know (what|how) to\b"
]

# Compile regex patterns for efficiency
CRISIS_REGEX = re.compile('|'.join(CRISIS_PATTERNS), re.IGNORECASE)
CONCERNING_REGEX = re.compile('|'.join(CONCERNING_PATTERNS), re.IGNORECASE)

# Default crisis resources by region
DEFAULT_CRISIS_RESOURCES = {
    "US": {
        "phone": "988",
        "text": "Text HOME to 741741",
        "chat": "https://988lifeline.org/chat/",
        "name": "988 Suicide & Crisis Lifeline"
    },
    "UK": {
        "phone": "116 123",
        "text": "Text SHOUT to 85258",
        "chat": "https://www.samaritans.org/",
        "name": "Samaritans"
    },
    "CA": {
        "phone": "1-833-456-4566",
        "text": "Text HOME to 686868",
        "chat": "https://talksuicide.ca/",
        "name": "Talk Suicide Canada"
    },
    "AU": {
        "phone": "13 11 14",
        "text": "Text 0477 13 11 14",
        "chat": "https://www.lifeline.org.au/crisis-chat/",
        "name": "Lifeline Australia"
    },
    "IN": {
        "phone": "9152987821",
        "chat": "https://www.aasra.info/",
        "name": "AASRA"
    },
    "GLOBAL": {
        "resources": "https://findahelpline.com/",
        "name": "Find A Helpline"
    }
}

class EscalationManager:
    """
    Manages crisis detection and escalation workflow with human handoff
    """
    def __init__(self, default_region="US", api_key=None, callback_url=None):
        """
        Initialize the escalation manager
        
        Args:
            default_region: Default region code for crisis resources
            api_key: API key for crisis resources service (if applicable)
            callback_url: URL for human handoff webhook (if applicable)
        """
        self.default_region = default_region
        self.api_key = api_key
        self.callback_url = callback_url
        self.escalation_history = {}  # user_id -> list of escalation events
        self.active_escalations = {}  # user_id -> escalation details
        self.crisis_patterns = self._init_crisis_patterns()
        logger.info("EscalationManager initialized")
        
    def _init_crisis_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for crisis detection"""
        return {
            # Self-harm and suicide indicators
            "suicidal": [
                r"\b(kill myself|suicide|end my life|take my life)\b",
                r"\b(don'?t want to (live|be alive|exist))\b",
                r"\b(want(ing)? to die)\b",
                r"\b(no (point|reason) (in|to) liv(e|ing))\b",
                r"\b(better off dead|better off without me)\b",
                r"\b(can'?t (go on|take (it|this) anymore))\b"
            ],
            
            # Self-harm indicators
            "self_harm": [
                r"\b(cut(ting)? myself|hurt(ing)? myself|harm(ing)? myself)\b",
                r"\b(injure|injuring)\b.{0,20}\b(myself|me)\b",
                r"\b(burn(ing)? myself)\b",
                r"\bself[- ]harm\b",
                r"\b(starve|starving) (myself|myself to)\b"
            ],
            
            # Violence toward others
            "violence": [
                r"\b(kill|hurt|harm|shoot)\b.{0,20}\b(you|someone|people|them|him|her)\b",
                r"\b(murder|attack|assault)\b",
                r"\b(gun|knife|weapon)\b.{0,30}\b(use|shoot|stab|kill)\b",
                r"\b(want(ing)? to|going to)\b.{0,20}\b(attack|hurt|kill)\b"
            ],
            
            # Plan-specific indicators
            "plan": [
                r"\b(plan(ning)? to)\b.{0,30}\b(suicide|kill|end|take my life)\b",
                r"\b(prepared|preparing|ready|set up)\b.{0,30}\b(suicide|die|end it)\b",
                r"\b(wrote|writing|have|leave|left)\b.{0,20}\b(note|letter|message|will)\b",
                r"\b(found|get|have|got|bought)\b.{0,20}\b(pills|medication|gun|knife|rope)\b",
                r"\b(this is|my)\b.{0,20}\b(last|final|goodbye|farewell)\b"
            ],
            
            # Immediate timing indicators
            "immediate": [
                r"\b(now|immediately|tonight|today)\b.{0,30}\b(die|suicide|kill|end)\b",
                r"\b(going to)\b.{0,20}\b(do it|end it|kill|suicide)\b.{0,20}\b(now|after this|when|once)\b",
                r"\b(saying|telling you|wanted you to know|last message)\b.{0,30}\b(goodbye|farewell)\b",
                r"\badios\b"
            ],
            
            # Hopelessness indicators
            "hopelessness": [
                r"\b(no (hope|future|point|reason))\b",
                r"\b(can'?t see|no way|never get better)\b",
                r"\b(tired of|exhausted from|can'?t stand)\b.{0,20}\b(life|living|everything|this)\b",
                r"\b(nothing (will|can|could) help)\b",
                r"\b(tried everything|nothing works|beyond help)\b"
            ],
            
            # Previous attempts
            "previous_attempt": [
                r"\b(tried|attempt(ed)?)\b.{0,30}\b((to )?(kill|harm) myself|suicide)\b",
                r"\b(last time)\b.{0,30}\b(tried|attempt|kill|harm)\b",
                r"\b(before|previously|already)\b.{0,30}\b(tried|attempt|kill|harm)\b"
            ]
        }
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for efficient matching"""
        compiled = {}
        for category, patterns in self.crisis_patterns.items():
            compiled[category] = re.compile('|'.join(patterns), re.IGNORECASE)
        return compiled
    
    async def assess_message(self, message: str, analysis: Dict, 
                           conversation_context: Dict = None,
                           user_profile: Dict = None) -> Dict:
        """
        Assess a message for crisis indicators and determine escalation level
        
        Args:
            message: The user's message text
            analysis: Sentiment analysis results
            conversation_context: Optional context from prior conversation
            user_profile: Optional user profile information
            
        Returns:
            Dict with escalation assessment results
        """
        # Initialize result
        result = {
            "escalation_level": EscalationLevel.NONE,
            "crisis_detected": False,
            "concerning_patterns": [],
            "triggers": [],
            "escalation_required": False,
            "recommended_action": None,
            "response_guidelines": None
        }
        
        # Check for direct crisis language
        crisis_matches = CRISIS_REGEX.findall(message.lower())
        if crisis_matches:
            result["crisis_detected"] = True
            result["triggers"].extend(crisis_matches)
            result["escalation_level"] = EscalationLevel.SEVERE
        
        # Check for concerning patterns
        concerning_matches = CONCERNING_REGEX.findall(message.lower())
        if concerning_matches:
            result["concerning_patterns"].extend(concerning_matches)
            
            # If no crisis detected yet, set escalation level based on concerning patterns
            if not result["crisis_detected"]:
                if len(concerning_matches) >= 3:
                    result["escalation_level"] = EscalationLevel.MODERATE
                else:
                    result["escalation_level"] = EscalationLevel.LOW
        
        # Factor in sentiment analysis
        if "sentiment" in analysis:
            sentiment_score = analysis["sentiment"]
            # Very negative sentiment increases escalation level
            if sentiment_score < 0.2 and result["escalation_level"] < EscalationLevel.HIGH:
                result["escalation_level"] = EscalationLevel.HIGH
            elif sentiment_score < 0.3 and result["escalation_level"] < EscalationLevel.MODERATE:
                result["escalation_level"] = EscalationLevel.MODERATE
        
        # Factor in emotion analysis
        if "emotions" in analysis:
            emotions = analysis["emotions"]
            # High levels of negative emotions increase escalation
            if emotions.get("sadness", 0) > 0.7 or emotions.get("fear", 0) > 0.7:
                result["escalation_level"] = max(result["escalation_level"], EscalationLevel.HIGH)
                result["triggers"].append(f"High {'sadness' if emotions.get('sadness', 0) > 0.7 else 'fear'}")
            
            # Anger can be concerning
            if emotions.get("anger", 0) > 0.6:
                result["escalation_level"] = max(result["escalation_level"], EscalationLevel.MODERATE)
                result["triggers"].append("High anger")
                
        # Check conversation context for escalation risk
        if conversation_context and "escalation_risk" in conversation_context:
            escalation_risk = conversation_context["escalation_risk"]
            
            # If conversation shows high escalation risk
            if escalation_risk > 0.7:
                result["escalation_level"] = max(result["escalation_level"], EscalationLevel.HIGH)
                result["triggers"].append("Conversation pattern escalation")
            elif escalation_risk > 0.4:
                result["escalation_level"] = max(result["escalation_level"], EscalationLevel.MODERATE)
                result["triggers"].append("Rising conversation risk")
        
        # Check for repetition of concerning messages
        if conversation_context and "repetition_counters" in conversation_context:
            repetition = conversation_context["repetition_counters"]
            if any(count >= 3 for count in repetition.values()):
                result["escalation_level"] = max(result["escalation_level"], EscalationLevel.HIGH)
                result["triggers"].append("Repeated concerning messages")
        
        # Set recommended actions based on escalation level
        self._set_recommended_actions(result)
        
        return result
    
    def _set_recommended_actions(self, result: Dict):
        """Set recommended actions based on escalation level"""
        level = result["escalation_level"]
        
        if level == EscalationLevel.NONE:
            result["recommended_action"] = "continue"
            result["response_guidelines"] = "Respond normally with empathy."
            
        elif level == EscalationLevel.LOW:
            result["recommended_action"] = "monitor"
            result["response_guidelines"] = "Acknowledge feelings and offer supportive response."
            
        elif level == EscalationLevel.MODERATE:
            result["recommended_action"] = "support"
            result["escalation_required"] = True
            result["response_guidelines"] = "Express concern, validate feelings, suggest resources."
            
        elif level == EscalationLevel.HIGH:
            result["recommended_action"] = "resources"
            result["escalation_required"] = True
            result["response_guidelines"] = "Express concern directly, provide support resources, encourage professional help."
            
        elif level >= EscalationLevel.SEVERE:
            result["recommended_action"] = "crisis_protocol"
            result["escalation_required"] = True
            result["response_guidelines"] = "Initiate crisis protocol, provide direct crisis resources, offer human handoff."
    
    async def get_crisis_resources(self, region_code=None, user_location=None) -> Dict:
        """
        Get crisis resources based on region or location
        
        Args:
            region_code: ISO country code (e.g., 'US', 'UK')
            user_location: Optional detailed location info
            
        Returns:
            Dict of crisis resources
        """
        region = region_code or self.default_region or "GLOBAL"
        
        # Try to get location-specific resources if we have API access
        if self.api_key and user_location:
            try:
                resources = await self._fetch_location_resources(user_location)
                if resources:
                    return resources
            except Exception as e:
                logger.error(f"Error fetching location resources: {str(e)}")
        
        # Fallback to default resources
        return DEFAULT_CRISIS_RESOURCES.get(region, DEFAULT_CRISIS_RESOURCES["GLOBAL"])
    
    async def _fetch_location_resources(self, location_info: Dict) -> Optional[Dict]:
        """
        Fetch location-specific crisis resources from external API
        
        Args:
            location_info: Location information (city, region, country, etc.)
            
        Returns:
            Dict of location-specific crisis resources or None if not found
        """
        # This is a stub for actual API implementation
        # In a real implementation, this would call a service like OpenCrisisAPI
        await asyncio.sleep(0.1)  # Simulate API call
        
        # Return None to fall back to default resources
        return None
    
    async def initiate_human_handoff(self, user_id: str, session_id: str, 
                                   context: Dict, urgency: str = "standard") -> Dict:
        """
        Initiate handoff to human support staff
        
        Args:
            user_id: User identifier
            session_id: Current session identifier
            context: Conversation context
            urgency: Urgency level ('standard', 'urgent', 'emergency')
            
        Returns:
            Dict with handoff information
        """
        handoff_id = str(uuid4())
        
        # Prepare handoff data
        handoff_data = {
            "handoff_id": handoff_id,
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "urgency": urgency,
            "context_summary": self._prepare_context_summary(context),
            "status": "pending"
        }
        
        # Track this escalation
        self.active_escalations[user_id] = handoff_data
        
        if user_id not in self.escalation_history:
            self.escalation_history[user_id] = []
        self.escalation_history[user_id].append({
            "handoff_id": handoff_id,
            "timestamp": handoff_data["timestamp"],
            "urgency": urgency
        })
        
        # If we have a callback URL, send the handoff request
        if self.callback_url:
            try:
                await self._send_handoff_webhook(handoff_data)
                handoff_data["status"] = "requested"
            except Exception as e:
                logger.error(f"Error sending handoff webhook: {str(e)}")
                handoff_data["status"] = "failed"
                handoff_data["error"] = str(e)
        
        return handoff_data
    
    async def _send_handoff_webhook(self, handoff_data: Dict) -> bool:
        """
        Send handoff webhook to callback URL
        
        Args:
            handoff_data: Handoff information
            
        Returns:
            True if successful, False otherwise
        """
        if not self.callback_url:
            return False
            
        try:
            # Send webhook
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.callback_url,
                    json=handoff_data,
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Handoff webhook failed: {response.status_code} {response.text}")
                    return False
                    
                return True
        except Exception as e:
            logger.error(f"Error sending handoff webhook: {str(e)}")
            return False
    
    def _prepare_context_summary(self, context: Dict) -> Dict:
        """
        Prepare a summary of conversation context for handoff
        
        Args:
            context: Full conversation context
            
        Returns:
            Dict with summarized context
        """
        # Extract relevant information for handoff
        summary = {
            "recent_messages": [],
            "sentiment_trend": None,
            "escalation_triggers": [],
            "user_topics": []
        }
        
        # Get recent messages
        if "messages" in context:
            # Get last 5 messages
            for msg in context["messages"][-5:]:
                summary["recent_messages"].append({
                    "role": msg.get("role", "unknown"),
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("timestamp", "")
                })
        
        # Get sentiment trend
        if "sentiment_history" in context:
            sentiment_history = context["sentiment_history"]
            if len(sentiment_history) >= 3:
                last_scores = [item["score"] for item in sentiment_history[-3:]]
                if last_scores[2] < last_scores[1] < last_scores[0]:
                    summary["sentiment_trend"] = "declining"
                elif last_scores[2] > last_scores[1] > last_scores[0]:
                    summary["sentiment_trend"] = "improving"
                else:
                    summary["sentiment_trend"] = "fluctuating"
                
                # Add the actual scores
                summary["sentiment_scores"] = last_scores
        
        # Get user topics
        if "topic_history" in context:
            summary["user_topics"] = context["topic_history"][:5]  # Top 5 topics
            
        return summary
    
    def get_escalation_response(self, assessment: Dict, resources: Dict, 
                              include_feedback: bool = True) -> str:
        """
        Generate an appropriate response based on escalation level
        
        Args:
            assessment: Escalation assessment
            resources: Crisis resources
            include_feedback: Whether to include feedback options
            
        Returns:
            Response text
        """
        level = assessment["escalation_level"]
        
        if level <= EscalationLevel.LOW:
            # Low concern - supportive response
            return (
                "I notice you seem to be having a difficult time. Remember that it's okay to "
                "feel this way, and sharing your feelings is a positive step. Is there something "
                "specific that's troubling you that you'd like to discuss more?"
            )
            
        elif level == EscalationLevel.MODERATE:
            # Moderate concern - supportive with gentle resources
            return (
                "I'm concerned about what you're sharing. These feelings can be overwhelming, "
                "but please know you don't have to face them alone. Many people find it helpful "
                "to talk to someone. Would it be helpful to explore some support options or "
                "coping strategies together?"
            )
            
        elif level == EscalationLevel.HIGH:
            # High concern - direct resources
            resource_name = resources.get("name", "a crisis helpline")
            resource_contact = resources.get("phone", resources.get("text", "a crisis service"))
            
            return (
                f"I'm genuinely concerned about you right now. What you're experiencing sounds "
                f"really difficult, and it's important you get the support you need. "
                f"{resource_name} ({resource_contact}) has trained counselors available 24/7 "
                f"who can provide immediate support. Would you like me to provide more information "
                f"about resources that might help?"
            )
            
        elif level >= EscalationLevel.SEVERE:
            # Severe concern - crisis protocol
            resource_name = resources.get("name", "a crisis helpline")
            resource_phone = resources.get("phone", "")
            resource_text = resources.get("text", "")
            resource_chat = resources.get("chat", "")
            
            response = (
                f"I'm very concerned about your safety right now. Please know that you're not alone, "
                f"and immediate help is available. {resource_name} can provide immediate support:\n\n"
            )
            
            if resource_phone:
                response += f"• Call: {resource_phone}\n"
                
            if resource_text:
                response += f"• Text: {resource_text}\n"
                
            if resource_chat:
                response += f"• Chat online: {resource_chat}\n"
                
            response += (
                f"\nThese services are confidential and available 24/7. Would you like me to connect "
                f"you with a human counselor who can continue this conversation with you?"
            )
            
            return response
        
        # Default response for any other case
        return (
            "I want to make sure you're getting the support you need. How are you feeling right now, "
            "and is there something specific I can help you with?"
        )
        
    async def check_handoff_status(self, handoff_id: str) -> Dict:
        """
        Check status of a human handoff request
        
        Args:
            handoff_id: Handoff identifier
            
        Returns:
            Dict with handoff status information
        """
        # Find the handoff in active escalations
        for user_id, handoff_data in self.active_escalations.items():
            if handoff_data["handoff_id"] == handoff_id:
                # If we have a callback URL, check status from service
                if self.callback_url:
                    try:
                        status = await self._fetch_handoff_status(handoff_id)
                        handoff_data["status"] = status.get("status", handoff_data["status"])
                        return status
                    except Exception as e:
                        logger.error(f"Error checking handoff status: {str(e)}")
                
                # Return current status
                return {
                    "handoff_id": handoff_id,
                    "status": handoff_data["status"],
                    "user_id": user_id,
                    "timestamp": handoff_data["timestamp"]
                }
        
        # Handoff not found
        return {
            "handoff_id": handoff_id,
            "status": "not_found",
            "error": "Handoff request not found"
        }
    
    async def _fetch_handoff_status(self, handoff_id: str) -> Dict:
        """
        Fetch handoff status from external service
        
        Args:
            handoff_id: Handoff identifier
            
        Returns:
            Dict with handoff status information
        """
        # This is a stub for actual API implementation
        # In a real implementation, this would call a service endpoint
        await asyncio.sleep(0.1)  # Simulate API call
        
        # Return dummy status
        return {
            "handoff_id": handoff_id,
            "status": "pending",
            "estimated_wait_time": "5 minutes"
        }
    
    async def complete_handoff(self, handoff_id: str, outcome: str, notes: str = None) -> Dict:
        """
        Mark a handoff as complete
        
        Args:
            handoff_id: Handoff identifier
            outcome: Outcome of the handoff ('completed', 'rejected', 'timeout', etc.)
            notes: Optional notes about the handoff
            
        Returns:
            Dict with updated handoff information
        """
        # Find the handoff in active escalations
        for user_id, handoff_data in self.active_escalations.items():
            if handoff_data["handoff_id"] == handoff_id:
                # Update handoff data
                handoff_data["status"] = "completed"
                handoff_data["outcome"] = outcome
                handoff_data["completion_time"] = datetime.now().isoformat()
                if notes:
                    handoff_data["notes"] = notes
                
                # Update escalation history
                for escalation in self.escalation_history.get(user_id, []):
                    if escalation["handoff_id"] == handoff_id:
                        escalation["outcome"] = outcome
                        escalation["completion_time"] = handoff_data["completion_time"]
                        break
                
                # If we have a callback URL, update status in service
                if self.callback_url:
                    try:
                        await self._update_handoff_status(handoff_data)
                    except Exception as e:
                        logger.error(f"Error updating handoff status: {str(e)}")
                
                return handoff_data
        
        # Handoff not found
        return {
            "handoff_id": handoff_id,
            "status": "not_found",
            "error": "Handoff request not found"
        }
    
    async def _update_handoff_status(self, handoff_data: Dict) -> bool:
        """
        Update handoff status in external service
        
        Args:
            handoff_data: Handoff information
            
        Returns:
            True if successful, False otherwise
        """
        if not self.callback_url:
            return False
            
        try:
            # Send update request
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.callback_url}/{handoff_data['handoff_id']}",
                    json=handoff_data,
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Handoff status update failed: {response.status_code} {response.text}")
                    return False
                    
                return True
        except Exception as e:
            logger.error(f"Error updating handoff status: {str(e)}")
            return False
    
    def get_user_escalation_history(self, user_id: str) -> List[Dict]:
        """
        Get escalation history for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            List of escalation events
        """
        return self.escalation_history.get(user_id, []) 