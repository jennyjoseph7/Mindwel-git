"""
Test script to verify the integration of the enhanced SentimentAnalyzer with our chatbot.
This script tests the sample conversation shown in the problem example.
"""

print("Starting test script...")

# Import the SentimentAnalyzer class
print("Importing SentimentAnalyzer...")
from src.mental_health_tracker.utils.sentiment_analyzer import SentimentAnalyzer

def test_conversation():
    """Test the conversation example from the problem description"""
    
    # Initialize the analyzer
    print("Initializing SentimentAnalyzer...")
    analyzer = SentimentAnalyzer()
    print("Initialization complete!\n")
    
    # Example conversation from the problem description
    example_conversation = [
        "Hello! How are you feeling today? I'm here to chat and help track your mental wellbeing.",
        "im sad",
        "my scolded me im very angry at her",
        "ok but why did she scold me",
        "ok",
        "is my wrong or me"
    ]
    
    print("=" * 80)
    print("TESTING SAMPLE CONVERSATION")
    print("=" * 80)
    
    # Process each message in the conversation
    for i, message in enumerate(example_conversation):
        print(f"\nMESSAGE {i+1}: '{message}'")
        
        # Analyze sentiment
        result = analyzer.analyze_sentiment(message)
        
        # Print the analysis details
        print(f"  Sentiment: {result['sentiment']} (score: {result['score']:.2f})")
        
        if result['detected_emotions']:
            print(f"  Emotions: {', '.join(result['detected_emotions'])}")
            
        if result['detected_context']:
            print(f"  Context: {result['detected_context']}")
        
        # Get response
        response = analyzer.get_response(result)
        print(f"\n  BOT RESPONSE: '{response['response_text']}'")
        
        if response.get('additional_info'):
            print(f"  ADDITIONAL INFO: {response['additional_info']}")
        
        print("-" * 80)
    
    # Test some edge cases
    print("\n\n")
    print("=" * 80)
    print("TESTING EDGE CASES")
    print("=" * 80)
    
    edge_cases = [
        ("", "Testing empty message"),
        ("yes", "Testing single word response"),
        ("I want to die", "Testing crisis detection"),
        ("My mom and dad are always fighting", "Testing relationship detection"),
        ("I'm so anxious about my exam tomorrow", "Testing emotion detection")
    ]
    
    for message, description in edge_cases:
        print(f"\n{description}: '{message}'")
        
        # Skip processing for empty message test
        if not message:
            print("  Empty message - showing raw result:")
            print(analyzer.analyze_sentiment(message))
            print("-" * 80)
            continue
            
        # Analyze sentiment
        result = analyzer.analyze_sentiment(message)
        
        # Print the analysis details
        print(f"  Sentiment: {result['sentiment']} (score: {result['score']:.2f})")
        
        if result['detected_emotions']:
            print(f"  Emotions: {', '.join(result['detected_emotions'])}")
            
        if result['detected_context']:
            print(f"  Context: {result['detected_context']}")
        
        # Get response
        response = analyzer.get_response(result)
        print(f"\n  BOT RESPONSE: '{response['response_text']}'")
        
        if response.get('additional_info'):
            print(f"  ADDITIONAL INFO: {response['additional_info']}")
        
        print("-" * 80)
    
    print("\nTesting complete!")

print("Running test conversation...")
test_conversation()
print("Tests completed successfully!") 