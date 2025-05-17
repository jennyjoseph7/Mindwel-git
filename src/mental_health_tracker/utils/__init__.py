"""
Mental Health Tracker Utilities

This package provides advanced components for mental health conversation analysis and support:
- UserStateManager: Tracks user profiles, preferences, and conversation context
- EscalationManager: Handles crisis detection and graduated response protocols
- ResponseValidator: Ensures high-quality, empathetic responses
- ConversationAnalyzer: Identifies patterns and generates insights from conversations
- SecureDataManager: Provides encryption and privacy-compliant data management
"""

# Import and re-export components for easy access
from .user_state_manager import UserStateManager, UserProfile, ConversationContext
from .escalation_manager import EscalationManager, EscalationLevel
from .response_validator import ResponseValidator, ResponseQualityIssue
from .conversation_analyzer import ConversationAnalyzer
from .secure_data_manager import SecureDataManager

# Import basic utilities
from .ai_utils import (
    analyze_sentiment,
    analyze_emotions,
    generate_chat_response
)

# Export all components
__all__ = [
    # Advanced components
    'UserStateManager',
    'UserProfile',
    'ConversationContext',
    'EscalationManager',
    'EscalationLevel',
    'ResponseValidator',
    'ResponseQualityIssue',
    'ConversationAnalyzer',
    'SecureDataManager',
    
    # Basic utilities
    'analyze_sentiment',
    'analyze_emotions',
    'generate_chat_response'
] 