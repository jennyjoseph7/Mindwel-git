"""
Test script for enhanced sentiment analysis and chat response functionality.

This script tests the enhanced sentiment analysis system that uses TextBlob and RoBERTa
models for more accurate emotion detection and contextual responses.
"""
import sys
import os
import json
from dotenv import load_dotenv

# Ensure the module path is accessible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

# Load environment variables
load_dotenv()

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Import the enhanced functions
from src.mental_health_tracker.utils.ai_utils import (
    analyze_sentiment,
    analyze_emotions,
    check_crisis_keywords,
    generate_chat_response
)

# Test cases with expected outcomes
TEST_CASES = [
    {
        "text": "I'm feeling really happy today and looking forward to the weekend!",
        "expected_sentiment": "POSITIVE",
        "expected_emotions": ["joy"],
        "expected_crisis": False,
        "description": "Positive sentiment with joy emotion"
    },
    {
        "text": "I'm feeling very sad and depressed lately, nothing seems to help.",
        "expected_sentiment": "NEGATIVE",
        "expected_emotions": ["sadness"],
        "expected_crisis": False,
        "description": "Negative sentiment with sadness emotion"
    },
    {
        "text": "I don't know what to do with my life anymore, there's no point in continuing.",
        "expected_sentiment": "NEGATIVE",
        "expected_emotions": ["sadness", "fear"],
        "expected_crisis": True,
        "description": "Potential crisis content with negative sentiment"
    },
    {
        "text": "I'm really angry at my boss for how they treated me today.",
        "expected_sentiment": "NEGATIVE",
        "expected_emotions": ["anger"],
        "expected_crisis": False,
        "description": "Negative sentiment with anger emotion"
    },
    {
        "text": "I'm not sure how I feel about this situation, it's complicated.",
        "expected_sentiment": "NEUTRAL",
        "expected_emotions": ["neutral"],
        "expected_crisis": False,
        "description": "Neutral sentiment with uncertainty"
    }
]

def run_tests():
    """Run tests on the enhanced sentiment analysis functions"""
    print("=== Enhanced Sentiment Analysis Test ===\n")
    
    print("Initializing models (this may take a moment on first run)...\n")
    
    # Model warm-up to preload transformers
    analyze_sentiment("warm up")
    analyze_emotions("warm up")
    
    # Test each case
    for i, test_case in enumerate(TEST_CASES, 1):
        text = test_case["text"]
        expected_sentiment = test_case["expected_sentiment"]
        expected_emotions = test_case["expected_emotions"]
        expected_crisis = test_case["expected_crisis"]
        
        print(f"Test {i}: {test_case['description']}")
        print(f"Text: \"{text}\"")
        
        # Test sentiment analysis
        score, sentiment = analyze_sentiment(text)
        print(f"Sentiment: {sentiment} (score: {score:.2f})")
        
        # Test emotion detection
        emotions = analyze_emotions(text)
        print(f"Emotions: {json.dumps(emotions, indent=2)}")
        
        # Test crisis detection
        is_crisis = check_crisis_keywords(text)
        print(f"Crisis detection: {is_crisis}")
        
        # Test chat response
        response = generate_chat_response(text)
        print(f"Response: \"{response}\"\n")
        
        # Simple verification
        sentiment_match = sentiment == expected_sentiment
        emotion_match = any(e in emotions for e in expected_emotions)
        crisis_match = is_crisis == expected_crisis
        
        print(f"Verification:")
        print(f"✓ Sentiment match: {sentiment_match}")
        print(f"✓ Emotion detection: {emotion_match}")
        print(f"✓ Crisis detection: {crisis_match}\n")
        
        print("-" * 80 + "\n")
    
    print("=== Test Complete ===")
    print("Note: Slight variations in results are expected due to model probabilistic nature.")

if __name__ == "__main__":
    run_tests() 