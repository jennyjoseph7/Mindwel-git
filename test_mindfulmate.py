"""
Test script for MindfulMate API

This script sends test messages to the MindfulMate API to verify its functionality.
It includes tests for general responses, sentiment detection, and crisis detection.
"""
import requests
import json
import os
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API endpoint
API_URL = "http://localhost:8000"
SESSION_ID = str(uuid.uuid4())  # Generate a random session ID for testing

def test_health():
    """Test the health endpoint"""
    response = requests.get(f"{API_URL}/health")
    print(f"\n[Health Check] Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.status_code == 200

def test_chat(message, test_name):
    """Send a message to the chat endpoint and print the response"""
    print(f"\n[Test: {test_name}]")
    print(f"Message: '{message}'")
    
    try:
        response = requests.post(
            f"{API_URL}/chat",
            json={"session_id": SESSION_ID, "message": message}
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: '{response.json().get('response')}'")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

def run_tests():
    """Run a series of tests to verify API functionality"""
    # Test the health endpoint
    if not test_health():
        print("Health check failed. Make sure the API is running.")
        return

    # Test normal conversation
    tests = [
        ("Hello, how are you today?", "Greeting"),
        ("I've been feeling a bit tired lately", "Neutral statement"),
        ("I'm really happy about my new job!", "Positive statement"),
        ("I'm feeling sad and disappointed", "Negative statement"),
        ("I'm really angry at my friend", "Anger emotion"),
        ("I'm super excited about the upcoming vacation", "Joy emotion"),
        ("I don't know what to do with my life", "Existential question"),
        ("Thanks for the chat", "Closing statement")
    ]
    
    # Run the standard tests
    for message, test_name in tests:
        test_chat(message, test_name)
    
    # Crisis detection test (uncomment to test - will trigger crisis detection)
    print("\n[Crisis Detection Test]")
    print("Note: This test is commented out by default to avoid triggering crisis detection unnecessarily.")
    print("To test crisis detection, uncomment the line in the code.")
    
    # test_chat("I feel like there's no hope and I want to end it all", "Crisis detection")

if __name__ == "__main__":
    print("== MindfulMate API Test ==")
    print(f"Using API at {API_URL}")
    print(f"Session ID: {SESSION_ID}")
    
    run_tests()
    
    print("\n== Test Complete ==")
    print("Note: For the first run, responses might be slow as models are loaded.")
    print("For full testing, make sure Redis is running and the appropriate API keys are set in .env") 