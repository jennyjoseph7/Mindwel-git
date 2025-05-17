"""
Response Quality Assurance Module: Validates chatbot responses for quality

Features:
- Validates responses for empathy, relevance, and appropriateness
- Detects repetitive patterns and generic responses
- Checks for context sensitivity and user acknowledgment
- Flags low-quality responses for improvement
"""
import re
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import difflib
from enum import Enum, auto

logger = logging.getLogger(__name__)

class ResponseQualityIssue(Enum):
    """Issues that can affect response quality"""
    GENERIC = auto()          # Generic, template-like response
    REPETITIVE = auto()       # Similar to previous responses
    INCONSISTENT = auto()     # Contradicts conversation history
    IRRELEVANT = auto()       # Doesn't address user's message
    INSENSITIVE = auto()      # Lacks empathy or appropriate tone
    DISMISSIVE = auto()       # Minimizes user's concerns
    MISLEADING = auto()       # Contains inaccurate information
    VERBOSE = auto()          # Unnecessarily long
    INCOMPLETE = auto()       # Doesn't fully address the query
    UNNATURAL = auto()        # Sounds robotic or unnatural
    CONTRADICTORY = auto()    # Self-contradicting within the response
    TECHNICAL = auto()        # Too technical or jargon-heavy

class ResponseValidator:
    """
    Validates chatbot responses for quality assurance
    """
    def __init__(self):
        """Initialize the response validator"""
        self.empathy_patterns = [
            r"understand", r"sorry to hear", r"that sounds", r"it seems like",
            r"you feel", r"you're feeling", r"must be", r"can be difficult",
            r"appreciate", r"thank you for", r"sharing", r"I'm here"
        ]
        
        self.generic_responses = [
            "I understand how you feel.",
            "That must be difficult.",
            "I'm here for you.",
            "Thanks for sharing.",
            "Let me know how I can help.",
            "I appreciate you telling me that.",
            "Tell me more about that."
        ]
        
        self.inappropriate_patterns = [
            r"just.*get over it", r"it'?s not that bad", r"other people have it worse",
            r"you should just", r"stop thinking about", r"snap out of it", 
            r"you'?re being dramatic", r"you'?re overreacting"
        ]
        
        # Compile patterns
        self.empathy_regex = re.compile("|".join([f"({pattern})" for pattern in self.empathy_patterns]), re.IGNORECASE)
        self.inappropriate_regex = re.compile("|".join([f"({pattern})" for pattern in self.inappropriate_patterns]), re.IGNORECASE)
        
        # Quality thresholds
        self.min_response_length = 20
        self.max_response_length = 500
        self.min_empathy_matches = 1
        self.max_similarity_score = 0.85  # For repetition detection
        
        # History for tracking
        self.response_history = []
        self.issue_history = []
        
        self.previous_responses = {}  # session_id -> list of previous responses
        logger.info("ResponseValidator initialized")
        
    def validate_response(self, response: str, user_message: str, 
                        conversation_context: Dict = None,
                        user_profile: Dict = None) -> Dict:
        """
        Validate a response for quality issues
        
        Args:
            response: The chatbot's response text
            user_message: The user's message being responded to
            conversation_context: Optional context from prior conversation
            user_profile: Optional user profile information
            
        Returns:
            Dict with validation results
        """
        # Initialize result
        result = {
            "valid": True,
            "issues": [],
            "suggestions": [],
            "quality_score": 1.0  # Start with perfect score
        }
        
        # Track this validation
        self.response_history.append({
            "response": response,
            "user_message": user_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Run all validators
        self._check_length(response, result)
        self._check_empathy(response, user_message, result)
        self._check_repetition(response, result, conversation_context)
        self._check_relevance(response, user_message, result)
        self._check_appropriateness(response, result)
        self._check_tone(response, user_message, user_profile, result)
        
        # Update quality score based on issues
        result["quality_score"] -= len(result["issues"]) * 0.1
        result["quality_score"] = max(0.0, min(1.0, result["quality_score"]))
        
        # Overall validity threshold
        result["valid"] = result["quality_score"] >= 0.7
        
        # Record issues for history
        if result["issues"]:
            self.issue_history.append({
                "timestamp": datetime.now().isoformat(),
                "issues": result["issues"],
                "quality_score": result["quality_score"]
            })
        
        return result
    
    def _check_length(self, response: str, result: Dict):
        """Check if response length is appropriate"""
        if len(response) < self.min_response_length:
            result["issues"].append(ResponseQualityIssue.INCOMPLETE)
            result["suggestions"].append(f"Response is too short (< {self.min_response_length} chars). Add more detail or context.")
            
        if len(response) > self.max_response_length:
            result["issues"].append(ResponseQualityIssue.VERBOSE)
            result["suggestions"].append(f"Response is too long (> {self.max_response_length} chars). Consider being more concise.")
    
    def _check_empathy(self, response: str, user_message: str, result: Dict):
        """Check if response shows empathy"""
        # Skip empathy check for very short user messages or questions
        if len(user_message) < 10 or user_message.strip().endswith("?"):
            return
            
        empathy_matches = self.empathy_regex.findall(response)
        if len(empathy_matches) < self.min_empathy_matches:
            result["issues"].append(ResponseQualityIssue.INSENSITIVE)
            result["suggestions"].append(
                "Response lacks empathetic language. Consider acknowledging feelings or using phrases "
                "like 'I understand' or 'That sounds difficult'."
            )
    
    def _check_repetition(self, response: str, result: Dict, context: Dict = None):
        """Check if response is repetitive compared to recent responses"""
        # Check for generic template-like responses
        for generic in self.generic_responses:
            if generic.lower() in response.lower():
                result["issues"].append(ResponseQualityIssue.GENERIC)
                result["suggestions"].append(
                    f"Response contains generic phrases like '{generic}'. "
                    "Consider personalizing your response more."
                )
                break
        
        # Check for repetition in conversation history
        if context and "messages" in context:
            recent_responses = [
                msg["content"] for msg in context["messages"][-5:] 
                if msg.get("role") == "assistant"
            ]
            
            for prev_response in recent_responses:
                similarity = self._calculate_similarity(response, prev_response)
                if similarity > self.max_similarity_score:
                    result["issues"].append(ResponseQualityIssue.REPETITIVE)
                    result["suggestions"].append(
                        "Response is too similar to a recent message. "
                        "Avoid repetition by varying your phrasing."
                    )
                    break
        
        # Check internal history if context not available
        if not context and len(self.response_history) > 1:
            recent_responses = [r["response"] for r in self.response_history[-5:-1]]
            
            for prev_response in recent_responses:
                similarity = self._calculate_similarity(response, prev_response)
                if similarity > self.max_similarity_score:
                    result["issues"].append(ResponseQualityIssue.REPETITIVE)
                    result["suggestions"].append(
                        "Response is too similar to a recent message. "
                        "Avoid repetition by varying your phrasing."
                    )
                    break
    
    def _check_relevance(self, response: str, user_message: str, result: Dict):
        """Check if response is relevant to the user's message"""
        # Extract key terms from user message (basic approach)
        user_words = set(re.findall(r'\b\w{4,}\b', user_message.lower()))
        response_words = set(re.findall(r'\b\w{4,}\b', response.lower()))
        
        # Simple overlap check - could be improved with semantic analysis
        if len(user_words) >= 3:
            overlap = user_words.intersection(response_words)
            if len(overlap) < min(2, len(user_words) // 3):
                result["issues"].append(ResponseQualityIssue.IRRELEVANT)
                result["suggestions"].append(
                    "Response may not be relevant to the user's message. "
                    "Try to address the specific topics they mentioned."
                )
    
    def _check_appropriateness(self, response: str, result: Dict):
        """Check if response contains inappropriate language"""
        inappropriate_matches = self.inappropriate_regex.findall(response)
        if inappropriate_matches:
            result["issues"].append(ResponseQualityIssue.DISMISSIVE)
            result["suggestions"].append(
                "Response contains potentially dismissive or inappropriate language. "
                "Use more supportive phrasing."
            )
    
    def _check_tone(self, response: str, user_message: str, 
                   user_profile: Dict = None, result: Dict = None):
        """Check if response tone matches user preferences and message tone"""
        if not user_profile:
            return
            
        # Check for tone alignment with user preferences
        if "preferences" in user_profile:
            prefs = user_profile["preferences"]
            
            # Check formality alignment
            if prefs.get("communication_style") == "formal":
                informal_markers = re.findall(r'\b(yeah|nah|cool|awesome|gonna|wanna|dunno)\b', response, re.IGNORECASE)
                if informal_markers:
                    result["issues"].append(ResponseQualityIssue.INSENSITIVE)
                    result["suggestions"].append(
                        "User prefers formal communication, but response contains informal language. "
                        "Consider a more professional tone."
                    )
            
            elif prefs.get("communication_style") == "casual":
                if len(response) > 100 and not re.search(r'\b(hey|hi|thanks|ok|sure|great)\b', response, re.IGNORECASE):
                    result["issues"].append(ResponseQualityIssue.INSENSITIVE)
                    result["suggestions"].append(
                        "User prefers casual communication, but response is quite formal. "
                        "Consider a more conversational tone."
                    )
            
            # Check response length alignment
            if prefs.get("response_length") == "short" and len(response) > 120:
                result["issues"].append(ResponseQualityIssue.INSENSITIVE)
                result["suggestions"].append(
                    "User seems to prefer shorter responses. Consider being more concise."
                )
            
            elif prefs.get("response_length") == "long" and len(response) < 80:
                result["issues"].append(ResponseQualityIssue.INSENSITIVE)
                result["suggestions"].append(
                    "User seems to prefer detailed responses. Consider providing more information."
                )
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two strings"""
        if not text1 or not text2:
            return 0.0
            
        # Normalize text
        text1 = text1.lower()
        text2 = text2.lower()
        
        # Use difflib's sequence matcher for similarity
        return difflib.SequenceMatcher(None, text1, text2).ratio()
    
    def get_quality_metrics(self) -> Dict:
        """Get quality metrics based on historical validation"""
        total_validations = len(self.response_history)
        if total_validations == 0:
            return {
                "total_validations": 0,
                "issue_rate": 0.0,
                "quality_avg": 1.0,
                "common_issues": {}
            }
        
        # Calculate issue rate
        issues_count = len(self.issue_history)
        issue_rate = issues_count / total_validations
        
        # Calculate average quality score
        quality_scores = [issue["quality_score"] for issue in self.issue_history] if self.issue_history else [1.0]
        quality_avg = sum(quality_scores) / len(quality_scores)
        
        # Count issue types
        issue_types = {}
        for issue_record in self.issue_history:
            for issue_type in issue_record["issues"]:
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
        
        # Sort by frequency
        common_issues = {k: v for k, v in sorted(issue_types.items(), key=lambda x: x[1], reverse=True)}
        
        return {
            "total_validations": total_validations,
            "issue_rate": issue_rate,
            "quality_avg": quality_avg,
            "common_issues": common_issues
        }
    
    def improve_response(self, response: str, validation_result: Dict, 
                       user_message: str, context: Dict = None) -> str:
        """
        Attempt to improve a response based on validation issues
        
        Args:
            response: Original response text
            validation_result: Validation results
            user_message: User message being responded to
            context: Optional conversation context
            
        Returns:
            Improved response text
        """
        # If valid, return original
        if validation_result["valid"]:
            return response
            
        improved = response
        issues = validation_result["issues"]
        
        # Fix length issues
        if ResponseQualityIssue.INCOMPLETE in issues:
            # Expand the response
            if "I'm here for you" not in improved:
                improved += " I'm here for you and ready to listen whenever you want to talk more."
            
        elif ResponseQualityIssue.VERBOSE in issues:
            # Shorten the response - split into sentences and take first 3-4
            sentences = re.split(r'(?<=[.!?])\s+', improved)
            if len(sentences) > 4:
                improved = " ".join(sentences[:4])
        
        # Fix empathy issues
        if ResponseQualityIssue.INSENSITIVE in issues:
            # Add empathetic opener if not present
            empathy_openers = [
                "I understand how you feel. ",
                "That sounds really challenging. ",
                "I appreciate you sharing that with me. ",
                "I hear what you're saying. "
            ]
            
            # Check if already starts with empathy
            has_empathy_opener = any(improved.lower().startswith(opener.lower()) for opener in empathy_openers)
            
            if not has_empathy_opener:
                # Choose an appropriate opener
                if "difficult" in user_message.lower() or "hard" in user_message.lower():
                    improved = f"That does sound difficult. {improved}"
                elif "sad" in user_message.lower() or "upset" in user_message.lower():
                    improved = f"I'm sorry you're feeling this way. {improved}"
                else:
                    improved = f"I appreciate you sharing that with me. {improved}"
        
        # Fix generic responses
        if ResponseQualityIssue.GENERIC in issues:
            # Check if the entire response is generic or just contains generic phrases
            is_entirely_generic = any(improved.lower().strip() == generic.lower().strip() 
                                    for generic in self.generic_responses)
            
            if is_entirely_generic:
                # Replace with more specific response using user message content
                user_words = set(re.findall(r'\b\w{4,}\b', user_message.lower()))
                if user_words:
                    topic = next(iter(user_words))
                    improved = f"I hear that {topic} is important to you. Can you tell me more about how it's affecting you?"
            else:
                # Just try to personalize slightly
                improved = improved.replace("I understand how you feel", 
                                          "I understand that this situation is uniquely challenging for you")
                improved = improved.replace("That must be difficult", 
                                          "What you're describing sounds genuinely difficult")
        
        # Fix inappropriate responses - these should be completely replaced
        if ResponseQualityIssue.DISMISSIVE in issues:
            improved = (
                "I want to support you through this difficult time. Everyone's experience is unique, "
                "and I'm here to listen without judgment. Would you like to talk more about what you're going through?"
            )
        
        return improved
        
    def reset_history(self):
        """Reset validation history"""
        self.response_history = []
        self.issue_history = []
        self.previous_responses = {}
    
    def _check_repetition(self, response: str, session_id: str) -> str:
        """Check for repetition with previous responses"""
        if session_id not in self.previous_responses:
            return None
        
        previous = self.previous_responses[session_id]
        if not previous:
            return None
        
        # Check for exact matches first
        for prev_response in previous:
            if response == prev_response:
                return "Response is identical to a previous response"
        
        # Check for high similarity
        response_lower = response.lower()
        for prev_response in previous[-3:]:  # Check last 3 responses
            prev_lower = prev_response.lower()
            
            # Check for substantial overlap
            if len(response_lower) > 20 and len(prev_lower) > 20:
                # Simple check for shared phrases
                if response_lower in prev_lower or prev_lower in response_lower:
                    return "Response is too similar to a recent response"
                
                # Count shared phrases of 5+ words
                response_phrases = self._get_phrases(response_lower, 5)
                prev_phrases = self._get_phrases(prev_lower, 5)
                shared_phrases = set(response_phrases).intersection(set(prev_phrases))
                
                if shared_phrases and len(shared_phrases) >= 3:
                    return "Response contains multiple phrases identical to a recent response"
        
        return None
    
    def _get_phrases(self, text: str, min_words: int) -> List[str]:
        """Extract phrases of at least min_words length from text"""
        words = text.split()
        if len(words) < min_words:
            return []
        
        phrases = []
        for i in range(len(words) - min_words + 1):
            phrase = " ".join(words[i:i+min_words])
            if len(phrase) > 10:  # Only include substantive phrases
                phrases.append(phrase)
        
        return phrases
    
    def _check_generic(self, response: str) -> str:
        """Check for generic, template-like responses"""
        # List of generic phrases commonly used in chatbots
        generic_phrases = [
            r"I'm here to help",
            r"I'm sorry you're feeling that way",
            r"that must be (difficult|hard|challenging)",
            r"I understand (how you feel|that you're)",
            r"tell me more about",
            r"I'm here to listen",
            r"I appreciate you sharing that",
            r"thank you for sharing",
            r"I'm sorry to hear that"
        ]
        
        # Count matches
        generic_count = 0
        for phrase in generic_phrases:
            if re.search(phrase, response, re.IGNORECASE):
                generic_count += 1
        
        # Generic responses often contain multiple generic phrases
        if generic_count >= 3:
            return "Response contains multiple generic phrases and lacks specificity"
        
        # Check for completely generic responses with no specificity
        if generic_count >= 1 and len(response) < 60:
            return "Response is short and generic without specific content"
        
        return None
    
    def _check_empathy(self, response: str, user_message: str, 
                      conversation_context: Dict[str, Any] = None) -> str:
        """Check for appropriate empathy and tone"""
        # Check for negative sentiment or emotions in user message
        negative_indicators = [
            "sad", "depress", "anxious", "anxiety", "stress", "worried", 
            "upset", "hurt", "angry", "mad", "suffering", "struggle", "pain",
            "lost", "alone", "lonely", "hopeless", "suicidal", "kill", "die",
            "hate", "trauma", "abuse", "crisis"
        ]
        
        # Count negative indicators in user message
        negative_count = sum(1 for word in negative_indicators 
                           if word in user_message.lower())
        
        # Get sentiment from context if available
        sentiment = None
        if conversation_context and "sentiment_history" in conversation_context:
            sentiment_history = conversation_context.get("sentiment_history", [])
            if sentiment_history:
                # Get most recent sentiment
                sentiment = sentiment_history[-1].get("value", 0.5)
        
        # Check for clear negative sentiment
        has_negative_sentiment = (negative_count >= 2 or 
                                (sentiment is not None and sentiment < 0.3))
        
        if has_negative_sentiment:
            # Check if response shows appropriate empathy
            empathy_indicators = [
                r"I('m| am) sorry",
                r"that (sounds|seems|must be) (difficult|hard|challenging|tough)",
                r"I understand",
                r"you('re| are) feeling",
                r"it('s| is) (okay|valid|natural|normal)",
                r"I can (imagine|understand|see)"
            ]
            
            # Check for at least one empathy indicator
            has_empathy = any(re.search(pattern, response, re.IGNORECASE) 
                            for pattern in empathy_indicators)
            
            if not has_empathy:
                return "Response lacks empathy for user's negative emotions"
        
        # Check for inappropriate positivity in response to negative messages
        if has_negative_sentiment:
            positive_phrases = [
                r"cheer up",
                r"look on the bright side",
                r"be happy",
                r"think positive",
                r"don't worry",
                r"it could be worse",
                r"everything happens for a reason",
                r"every cloud has a silver lining"
            ]
            
            for phrase in positive_phrases:
                if re.search(phrase, response, re.IGNORECASE):
                    return "Response contains inappropriate positivity for negative sentiment"
        
        return None
    
    def _check_dismissive(self, response: str) -> str:
        """Check for dismissive language"""
        dismissive_phrases = [
            r"you('re| are) overreacting",
            r"it's not that (bad|serious|important)",
            r"get over it",
            r"move on",
            r"everyone (feels|goes through) that",
            r"you should just",
            r"you'll be fine",
            r"stop (worrying|thinking about it)",
            r"it's all in your head",
            r"you're being (dramatic|too sensitive)",
            r"that's just how life is"
        ]
        
        # Check for dismissive phrases
        for phrase in dismissive_phrases:
            if re.search(phrase, response, re.IGNORECASE):
                return f"Response contains dismissive language: '{re.search(phrase, response, re.IGNORECASE).group(0)}'"
        
        return None
    
    def _check_relevance(self, response: str, user_message: str,
                        conversation_context: Dict[str, Any] = None) -> str:
        """Check if response is relevant to user's message"""
        # Extract potential topics from user message (simple version)
        user_words = set(user_message.lower().split())
        
        # Check for context topics
        context_topics = []
        if conversation_context and "topics" in conversation_context:
            context_topics = list(conversation_context.get("topics", {}).keys())
        
        # Extract key nouns from user message (simplified)
        potential_topics = [word for word in user_words if len(word) > 3 and not self._is_common_word(word)]
        
        # Add context topics
        all_topics = set(potential_topics + context_topics)
        
        # Consider message as "important" if it's a question
        is_question = "?" in user_message or any(q in user_message.lower() for q in [
            "what", "why", "how", "when", "where", "who", "which", "can you", "could you"
        ])
        
        # For questions or messages with clear topics, check if response addresses them
        if (is_question or all_topics) and len(user_message) > 15:
            response_words = set(response.lower().split())
            
            # Check if important topics are reflected in response
            topic_overlap = all_topics.intersection(response_words)
            
            # For questions, response should address the question
            if is_question and not topic_overlap and len(all_topics) > 0:
                return "Response doesn't appear to address the user's question"
            
            # For statements with clear topics, response should reflect topics
            if not is_question and all_topics and not topic_overlap and len(all_topics) >= 2:
                return "Response doesn't reflect any topics from user's message"
        
        return None
    
    def _is_common_word(self, word: str) -> bool:
        """Check if a word is a common function word"""
        common_words = {
            "the", "and", "but", "for", "or", "yet", "so", "nor", "about",
            "above", "after", "along", "amid", "among", "around", "before",
            "behind", "below", "beneath", "beside", "between", "beyond",
            "with", "without", "within", "this", "that", "these", "those",
            "than", "then", "they", "them", "their", "there", "here", "where",
            "when", "what", "who", "which", "whose", "whom", "have", "has",
            "had", "will", "would", "should", "could", "can", "may", "might",
            "must", "shall", "being", "been", "were", "your", "you're", "youre",
            "yours", "myself", "yourself", "himself", "herself", "itself",
            "ourselves", "themselves", "something", "anything", "everything",
            "nothing", "become", "became", "very", "really", "just", "like"
        }
        return word.lower() in common_words
    
    def _check_natural_language(self, response: str) -> str:
        """Check for unnatural/robotic language patterns"""
        # Check for overly repetitive phrasing
        words = response.lower().split()
        if len(words) >= 10:
            # Check for repeated phrases
            for i in range(len(words) - 3):
                phrase = " ".join(words[i:i+3])
                if phrase in " ".join(words[i+3:]):
                    return "Response contains repetitive phrasing"
        
        # Check for awkward transitions
        awkward_transitions = [
            r"speaking of",
            r"on another note",
            r"changing topics",
            r"to address your point",
            r"moving on to",
            r"with regards to your",
            r"to respond to your"
        ]
        
        for phrase in awkward_transitions:
            if re.search(phrase, response, re.IGNORECASE):
                return "Response contains awkward transitions"
        
        # Check for robotic patterns
        robotic_patterns = [
            r"as an AI",
            r"I don't have (emotions|feelings|personal)",
            r"I'm not capable of",
            r"I cannot",
            r"I do not have the ability",
            r"I am a (chatbot|bot|assistant|AI)"
        ]
        
        for pattern in robotic_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return "Response contains robotic self-references"
        
        return None
    
    def _check_contradictions(self, response: str) -> str:
        """Check for contradictory statements within the response"""
        # Check for simple contradictions
        contradictory_pairs = [
            (r"you should", r"you shouldn't"),
            (r"is important", r"isn't important"),
            (r"I recommend", r"I don't recommend"),
            (r"it's helpful", r"it's not helpful"),
            (r"you need to", r"you don't need to"),
            (r"it's good", r"it's bad"),
            (r"always", r"never")
        ]
        
        for pattern1, pattern2 in contradictory_pairs:
            if (re.search(pattern1, response, re.IGNORECASE) and 
                re.search(pattern2, response, re.IGNORECASE)):
                return "Response contains contradictory statements"
        
        # Check for yes/no contradictions
        if (("yes" in response.lower() and "no" in response.lower()) and
            not re.search(r"(yes and no|both yes and no|yes or no)", response, re.IGNORECASE)):
            return "Response contains potentially contradictory yes/no statements"
        
        return None
    
    def _check_jargon(self, response: str) -> str:
        """Check for overly technical jargon"""
        technical_terms = [
            r"neurotransmitter", r"serotonin", r"dopamine", r"psychopathology",
            r"neurochemical", r"neurological", r"cognitive restructuring",
            r"behavioral activation", r"psychodynamic", r"psychoanalytic",
            r"metacognitive", r"cognitive distortion", r"catastrophizing",
            r"desensitization", r"maladaptive", r"psychoeducation",
            r"comorbidity", r"symptomatology", r"dissociation", r"schema",
            r"psychotropic", r"benzodiazepine", r"antidepressant", r"limbic system"
        ]
        
        # Count technical terms
        jargon_count = sum(1 for term in technical_terms 
                         if re.search(term, response, re.IGNORECASE))
        
        if jargon_count >= 2:
            return "Response contains too much technical jargon"
        
        return None
    
    def _add_to_history(self, response: str, session_id: str, max_history: int = 10) -> None:
        """Add response to history for the session"""
        if session_id not in self.previous_responses:
            self.previous_responses[session_id] = []
        
        self.previous_responses[session_id].append(response)
        
        # Keep history to a reasonable size
        if len(self.previous_responses[session_id]) > max_history:
            self.previous_responses[session_id] = self.previous_responses[session_id][-max_history:]
    
    def clear_history(self, session_id: str = None) -> None:
        """Clear response history for a session or all sessions"""
        if session_id:
            if session_id in self.previous_responses:
                del self.previous_responses[session_id]
        else:
            self.previous_responses = {} 