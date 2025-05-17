"""
Test script to verify the integration of the new SentimentAnalyzer with our chatbot.
Run this script to test both the sentiment analysis and crisis detection.
"""

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from src.mental_health_tracker.utils.sentiment_analyzer import SentimentAnalyzer
from src.mental_health_tracker.utils.ai_utils import analyze_sentiment, check_crisis_keywords, generate_chat_response

# Test examples with different sentiments and scenarios
test_inputs = [
    "I had a great day today, everything is going well.",
    "I'm feeling a bit down today, but I'll be okay.",
    "I'm so angry at my boss for how they treated me yesterday!",
    "I'm worried about my upcoming presentation.",
    "I don't see any point in living anymore, I feel so worthless.",
    "yes",
    "no",
    "I'm having issues with my family, they don't understand me."
]

def test_sentiment_analyzer():
    """Test the standalone SentimentAnalyzer class"""
    print("\n===== Testing SentimentAnalyzer directly =====")
    analyzer = SentimentAnalyzer()
    
    for text in test_inputs:
        print(f"\nInput: '{text}'")
        result = analyzer.analyze_sentiment(text)
        print(f"Sentiment: {result['sentiment']} (Score: {result['score']:.2f})")
        
        # If highly negative, show the response with resources
        if result['sentiment'] == 'highly_negative':
            response = analyzer.get_response(result)
            print(f"Response: '{response['response_text']}'")
            print(f"Crisis Resource: '{response['additional_info']}'")

def test_integrated_sentiment():
    """Test the integrated sentiment analysis in ai_utils"""
    print("\n===== Testing integrated sentiment analysis =====")
    for text in test_inputs:
        print(f"\nInput: '{text}'")
        score, label = analyze_sentiment(text)
        print(f"Sentiment: {label} (Score: {score:.2f})")
        
        # Check for crisis keywords
        is_crisis, resource = check_crisis_keywords(text)
        if is_crisis:
            print(f"Crisis detected! Resource: {resource}")

def test_chat_response():
    """Test the full chat response generation with crisis handling"""
    print("\n===== Testing chat response generation =====")
    for text in test_inputs:
        print(f"\nUser: '{text}'")
        response = generate_chat_response(text)
        print(f"MindWell: {response}")
        print("-" * 70)

if __name__ == "__main__":
    print("Starting sentiment analysis tests...\n")
    test_sentiment_analyzer()
    test_integrated_sentiment()
    test_chat_response()
    print("\nTests completed!") 