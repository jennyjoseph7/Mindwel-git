"""
Test script specifically for the problem scenario described by the user.
This tests how the new SentimentAnalyzer handles the previously problematic conversation.
"""

print("Testing the original problem conversation...")

from src.mental_health_tracker.utils.sentiment_analyzer import SentimentAnalyzer

# Create a single analyzer instance to maintain conversation context
analyzer = SentimentAnalyzer()

# The problematic conversation example from the user, correctly formatted as [user, bot, user, bot, ...]
conversation = [
    # First message from the bot (greeting)
    "Hello! How are you feeling today? I'm here to chat and help track your mental wellbeing.",
    
    # User's first reply
    "im sad",
    
    # Original bot response
    "I'm here with you. There's no rush to share more - I'm here to support you at your own pace.",
    
    # User's second message
    "my scolded me im very angry at her",
    
    # Original bot response
    "I hear that you're feeling down. Those emotions are completely valid, and it takes courage to acknowledge them. Try to be gentle with yourself right now.",
    
    # User's third message
    "ok but why did she scold me",
    
    # Original bot response (notice it's the same as before - this was part of the problem)
    "I hear that you're feeling down. Those emotions are completely valid, and it takes courage to acknowledge them. Try to be gentle with yourself right now.",
    
    # User's fourth message
    "ok",
    
    # Original bot response
    "Thanks for letting me know. I'm here to support you through whatever you're experiencing.",
    
    # User's fifth message
    "is my wrong or me",
    
    # Original bot response (generic and repetitive)
    "Thank you for sharing that with me. I'm here to support you through whatever you're experiencing."
]

# Test our new analyzer with this conversation
print("\nINPUT/OUTPUT WITH NEW ANALYZER:\n")

# Simulate the conversation properly
current_turn = 1  # Skip the initial greeting from the bot

while current_turn < len(conversation):
    # User message
    user_message = conversation[current_turn]
    print(f"USER: {user_message}")
    current_turn += 1
    
    # Skip if we've reached the end
    if current_turn >= len(conversation):
        break
    
    # Original bot response
    original_response = conversation[current_turn]
    print(f"OLD BOT: {original_response}")
    
    # Generate new response with our improved analyzer
    result = analyzer.analyze_sentiment(user_message)
    response = analyzer.get_response(result)
    
    print(f"NEW BOT: {response['response_text']}")
    if response.get('additional_info'):
        print(f"ADDITIONAL INFO: {response['additional_info']}")
    
    # Add extra info about the analysis
    if result['detected_emotions']:
        print(f"(Detected emotions: {', '.join(result['detected_emotions'])})")
    if result['detected_context']:
        print(f"(Detected context: {result['detected_context']})")
    
    print("-" * 80)
    
    # Move to next turn
    current_turn += 1

print("\nTest complete!") 