"""
Simple test script to verify the sentiment analyzer can be imported correctly.
"""

print("Starting simple test...")

try:
    print("Attempting to import SentimentAnalyzer...")
    from src.mental_health_tracker.utils.sentiment_analyzer import SentimentAnalyzer
    print("SentimentAnalyzer imported successfully!")
    
    print("Creating SentimentAnalyzer instance...")
    analyzer = SentimentAnalyzer()
    print("SentimentAnalyzer instance created successfully!")
    
    print("Testing sentiment analysis...")
    test_text = "I feel sad today"
    print(f"Test text: '{test_text}'")
    
    result = analyzer.analyze_sentiment(test_text)
    print(f"Analysis result: {result}")
    
    response = analyzer.get_response(result)
    print(f"Bot response: {response}")
    
    print("All tests passed!")
except Exception as e:
    print(f"Error occurred: {str(e)}")
    import traceback
    traceback.print_exc()

print("Test complete.") 