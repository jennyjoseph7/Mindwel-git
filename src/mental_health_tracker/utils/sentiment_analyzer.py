import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import random
import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Download necessary NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class SentimentAnalyzer:
    def __init__(self):
        # Load pre-trained model and tokenizer for sentiment analysis
        # Using the RoBERTa model fine-tuned for sentiment analysis
        self.model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        self.labels = ['negative', 'neutral', 'positive']
        
        # Track conversation history to prevent repetitive responses
        self.conversation_history = []
        self.max_history_len = 5
        
        # Emotion detection patterns
        self.emotion_patterns = {
            'anger': ['angry', 'mad', 'furious', 'upset', 'rage', 'annoyed', 'frustrat'],
            'sadness': ['sad', 'down', 'depress', 'unhappy', 'miserable', 'hurt', 'lonely'],
            'anxiety': ['anxious', 'worry', 'nervous', 'stress', 'tense', 'overwhelm', 'panic'],
            'fear': ['afraid', 'scared', 'terrified', 'frightened', 'fear'],
            'confusion': ['confus', 'unsure', 'uncertain', 'lost', 'perplex'],
            'disappointment': ['disappoint', 'let down', 'failed', 'regret']
        }
        
        # Keywords that may indicate relational issues
        self.relationship_keywords = [
            'mom', 'mother', 'dad', 'father', 'parent', 'friend', 'boyfriend', 
            'girlfriend', 'husband', 'wife', 'partner', 'boss', 'coworker', 'colleague',
            'teacher', 'classmate', 'roommate', 'neighbor', 'family'
        ]
        
        # Initialize expanded response templates for each sentiment category
        self.response_templates = {
            'positive': [
                "I'm glad you're feeling good! It's wonderful to hear positivity in your words.",
                "That sounds really positive. Would you like to share more about what's going well?",
                "It's great to see you in such a positive mindset. How can I help you maintain this energy?",
                "Your positive outlook is inspiring. What's contributed to this feeling today?",
                "I notice you're in good spirits. Would you like to reflect on what's making you feel this way?"
            ],
            'neutral': [
                "Thanks for sharing that. How are you feeling about this situation overall?",
                "I understand. Would you like to explore these thoughts a bit more?",
                "I'm here to listen. Would you like to talk more about what's on your mind?",
                "I appreciate you sharing that with me. Is there anything specific you'd like to focus on today?",
                "Thank you for opening up. How has this been affecting you lately?"
            ],
            'negative': [
                "I'm sorry to hear you're going through this. Remember that it's okay to feel this way.",
                "That sounds challenging. Would you like to talk more about what's troubling you?",
                "I hear that you're having a difficult time. What small step might help you feel a bit better right now?",
                "It takes courage to share difficult feelings. Can you tell me more about what happened?",
                "I'm here with you through these tough emotions. Would it help to explore what triggered these feelings?"
            ],
            'highly_negative': [
                "I'm really concerned about how you're feeling. Remember that you're not alone in this.",
                "I'm here for you during this difficult time. Have you considered reaching out to a mental health professional?",
                "These feelings sound overwhelming. Would it help to discuss some coping strategies that might provide some relief?",
                "I can hear how much pain you're in right now. Your feelings are valid, and support is available.",
                "I'm grateful you're sharing these difficult thoughts with me. What would feel most supportive right now?"
            ]
        }
        
        # Special templates for specific emotions
        self.emotion_templates = {
            'anger': [
                "I can hear that you're feeling angry. That's a completely valid emotion when we feel wronged or misunderstood.",
                "It sounds like you're really frustrated right now. Would you like to talk more about what triggered these feelings?",
                "Being angry can be overwhelming. Would it help to explore what happened and how you might address it?"
            ],
            'sadness': [
                "I hear the sadness in your words. It's okay to feel down sometimes - you don't have to force yourself to be happy.",
                "I'm sorry you're feeling sad. Would you like to share more about what's weighing on your heart?",
                "Sadness is a natural response to difficult situations. Is there something specific that triggered these feelings today?"
            ],
            'anxiety': [
                "I notice you're feeling anxious. Sometimes taking a few deep breaths can help in the moment. Would you like to try that together?",
                "Anxiety can be really challenging to deal with. What strategies have helped you manage anxiety in the past?",
                "When we're anxious, our thoughts often race ahead to the worst possibilities. Would it help to talk through what specific concerns are on your mind?"
            ],
            'confusion': [
                "It sounds like you're feeling confused, which can be uncomfortable. Would it help to break down what's happening step by step?",
                "When we're uncertain about things, it can feel disorienting. What aspect of the situation feels most unclear to you?",
                "Being confused is completely normal when facing complex situations. Would talking through different perspectives help bring some clarity?"
            ],
            'relationship': [
                "Relationships can be really complicated. How has this interaction affected how you're feeling?",
                "Conflicts with people we care about can be especially difficult. What do you think might be going on from their perspective?",
                "It sounds like this relationship situation is really affecting you. Would it help to explore some ways to communicate your feelings about this?"
            ]
        }
        
        # Templates for follow-up questions to encourage reflection
        self.follow_up_templates = [
            "How long have you been feeling this way?",
            "Have you noticed any patterns or triggers for these feelings?",
            "What would feel supportive for you right now?",
            "Have you shared these feelings with anyone else in your life?",
            "What has helped you cope with similar situations in the past?"
        ]
        
        # Crisis resources to provide for highly negative sentiment
        self.crisis_resources = [
            "If you're in crisis, please consider calling the National Suicide Prevention Lifeline at 988 or 1-800-273-8255.",
            "Remember that professional help is available. Text HOME to 741741 to reach the Crisis Text Line.",
            "Your wellbeing matters. Please consider reaching out to a mental health professional or trusted person in your life."
        ]
    
    def analyze_sentiment(self, text, conversation_context=None):
        """
        Analyze the sentiment of the given text with contextual awareness.
        
        Args:
            text (str): The input text to analyze
            conversation_context (list, optional): Previous messages for context
            
        Returns:
            dict: Contains sentiment label, score, detected emotions, and other metadata
        """
        # Don't process empty messages
        if not text or text.strip() == "":
            return {
                "text": text,
                "sentiment": "neutral",
                "score": 0.5,
                "detected_emotions": [],
                "detected_context": None,
                "all_scores": {"negative": 0.0, "neutral": 1.0, "positive": 0.0}
            }
        
        # Tokenize the input text
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True)
        
        # Get model prediction
        with torch.no_grad():
            outputs = self.model(**inputs)
            scores = torch.nn.functional.softmax(outputs.logits, dim=1)
            scores = scores.numpy()[0]
        
        # Get the predicted sentiment
        ranking = np.argsort(scores)
        ranking = ranking[::-1]
        
        # Get the highest sentiment score and its index
        sentiment_score = scores[ranking[0]]
        sentiment_idx = ranking[0]
        sentiment_label = self.labels[sentiment_idx]
        
        # Check for highly negative sentiment
        is_highly_negative = self._check_for_high_negativity(text, sentiment_label, sentiment_score)
        
        # Detect specific emotions in the text
        detected_emotions = self._detect_emotions(text)
        
        # Detect conversation context (like relationship issues)
        detected_context = self._detect_context(text)
        
        # Prepare the final sentiment label
        final_sentiment = "highly_negative" if is_highly_negative else sentiment_label
        
        # Add this analysis to conversation history
        self._update_conversation_history({
            "text": text,
            "sentiment": final_sentiment,
            "emotions": detected_emotions,
            "context": detected_context
        })
        
        return {
            "text": text,
            "sentiment": final_sentiment,
            "score": float(sentiment_score),
            "detected_emotions": detected_emotions,
            "detected_context": detected_context,
            "all_scores": {label: float(scores[i]) for i, label in enumerate(self.labels)}
        }
    
    def _check_for_high_negativity(self, text, sentiment_label, sentiment_score):
        """
        Check if the text contains highly negative sentiment based on keywords and score.
        
        Args:
            text (str): The input text
            sentiment_label (str): The predicted sentiment label
            sentiment_score (float): The sentiment score
            
        Returns:
            bool: True if highly negative, False otherwise
        """
        # Check if already classified as negative with high confidence
        if sentiment_label == "negative" and sentiment_score > 0.7:
            # List of keywords that might indicate severe negative emotions or crisis
            crisis_keywords = [
                "suicide", "kill myself", "want to die", "end my life", "don't want to live",
                "hopeless", "worthless", "unbearable", "can't take it anymore", "no reason to live",
                "never be happy", "better off dead", "hate myself", "no one cares", "give up"
            ]
            
            # Convert to lowercase for case-insensitive matching
            text_lower = text.lower()
            
            # Check if any crisis keywords are present
            for keyword in crisis_keywords:
                if keyword in text_lower:
                    return True
            
            # Enhanced heuristic: check for very short negative statements which often signal distress
            if len(text.split()) < 5 and any(word in text_lower for word in ["hate", "awful", "terrible", "miserable"]):
                return True
        
        return False
    
    def _detect_emotions(self, text):
        """
        Detect specific emotions present in the text.
        
        Args:
            text (str): The input text
            
        Returns:
            list: Detected emotions
        """
        text_lower = text.lower()
        detected = []
        
        # Check for each emotion pattern
        for emotion, patterns in self.emotion_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                detected.append(emotion)
        
        return detected
    
    def _detect_context(self, text):
        """
        Detect context clues in the conversation.
        
        Args:
            text (str): The input text
            
        Returns:
            str or None: Detected context type or None
        """
        text_lower = text.lower()
        
        # Check for relationship keywords
        if any(keyword in text_lower for keyword in self.relationship_keywords):
            return "relationship"
        
        # Add more context detection as needed
        
        return None
    
    def _update_conversation_history(self, analysis):
        """
        Update the conversation history with the latest analysis.
        
        Args:
            analysis (dict): The sentiment analysis result
        """
        self.conversation_history.append(analysis)
        
        # Keep history to a reasonable size
        if len(self.conversation_history) > self.max_history_len:
            self.conversation_history.pop(0)
    
    def get_response(self, sentiment_result):
        """
        Generate an appropriate chatbot response based on sentiment analysis.
        
        Args:
            sentiment_result (dict): The result from analyze_sentiment method
            
        Returns:
            dict: Contains the response text and additional info
        """
        sentiment = sentiment_result["sentiment"]
        detected_emotions = sentiment_result.get("detected_emotions", [])
        detected_context = sentiment_result.get("detected_context")
        
        # First, check if we should respond to specific emotions
        response_text = None
        
        # Check if we've used similar responses recently to avoid repetition
        recent_responses = [item.get("response", "") for item in self.conversation_history 
                           if "response" in item][-3:] if self.conversation_history else []
        
        # Start with emotion-specific responses if emotions were detected
        if detected_emotions:
            primary_emotion = detected_emotions[0]
            if primary_emotion in self.emotion_templates:
                possible_responses = [r for r in self.emotion_templates[primary_emotion] 
                                     if r not in recent_responses]
                if possible_responses:
                    response_text = random.choice(possible_responses)
        
        # Try context-specific responses if no emotion response was selected
        if not response_text and detected_context:
            if detected_context in self.emotion_templates:
                possible_responses = [r for r in self.emotion_templates[detected_context] 
                                     if r not in recent_responses]
                if possible_responses:
                    response_text = random.choice(possible_responses)
        
        # Fall back to sentiment-based responses if needed
        if not response_text:
            # Filter out recently used responses to avoid repetition
            possible_responses = [r for r in self.response_templates[sentiment]
                                if r not in recent_responses]
            
            # If all responses have been recently used, reset and use the full list
            if not possible_responses:
                possible_responses = self.response_templates[sentiment]
            
            response_text = random.choice(possible_responses)
        
        # For highly negative sentiment, also provide crisis resources
        additional_info = None
        if sentiment == "highly_negative":
            additional_info = random.choice(self.crisis_resources)
        
        # 30% chance of adding a follow-up question to encourage more sharing
        if random.random() < 0.3:
            follow_up = random.choice(self.follow_up_templates)
            response_text += f" {follow_up}"
        
        # Store this response in conversation history to avoid repetition
        if self.conversation_history:
            self.conversation_history[-1]["response"] = response_text
        
        return {
            "response_text": response_text,
            "sentiment": sentiment,
            "detected_emotions": detected_emotions,
            "detected_context": detected_context,
            "additional_info": additional_info
        }


# Example usage
def main():
    # Initialize the sentiment analyzer
    analyzer = SentimentAnalyzer()
    
    # Example conversation from the user's example
    example_inputs = [
        "Hello! How are you feeling today? I'm here to chat and help track your mental wellbeing.",
        "im sad",
        "my scolded me im very angry at her",
        "ok but why did she scold me",
        "ok",
        "is my wrong or me"
    ]
    
    # Process each example input
    for text in example_inputs:
        print(f"\nUser Input: '{text}'")
        
        # Analyze sentiment
        sentiment_result = analyzer.analyze_sentiment(text)
        print(f"Detected Sentiment: {sentiment_result['sentiment']}")
        if sentiment_result['detected_emotions']:
            print(f"Detected Emotions: {', '.join(sentiment_result['detected_emotions'])}")
        if sentiment_result['detected_context']:
            print(f"Detected Context: {sentiment_result['detected_context']}")
        
        # Get appropriate response
        response = analyzer.get_response(sentiment_result)
        print(f"Chatbot Response: '{response['response_text']}'")
        
        # Display additional info if available
        if response['additional_info']:
            print(f"Additional Info: '{response['additional_info']}'")
        
        print("-" * 80)
    
    # Demonstrate how responses change even for similar inputs
    print("\n\nDemonstrating response variety for similar inputs:")
    similar_inputs = ["I'm feeling sad today", "I feel so sad", "I'm sad about everything"]
    
    for text in similar_inputs:
        sentiment_result = analyzer.analyze_sentiment(text)
        response = analyzer.get_response(sentiment_result)
        print(f"Input: '{text}'")
        print(f"Response: '{response['response_text']}'")
        print("-" * 40)


# To integrate with Flask backend:
"""
from flask import Flask, request, jsonify
from sentiment_analyzer import SentimentAnalyzer

app = Flask(__name__)
analyzer = SentimentAnalyzer()

@app.route('/analyze_sentiment', methods=['POST'])
def analyze_sentiment():
    data = request.json
    user_text = data.get('text', '')
    conversation_history = data.get('conversation_history', [])
    
    # Analyze sentiment
    sentiment_result = analyzer.analyze_sentiment(user_text, conversation_history)
    
    # Get appropriate response
    response = analyzer.get_response(sentiment_result)
    
    return jsonify({
        'sentiment': sentiment_result['sentiment'],
        'score': sentiment_result['score'],
        'detected_emotions': sentiment_result.get('detected_emotions', []),
        'detected_context': sentiment_result.get('detected_context'),
        'response': response['response_text'],
        'additional_info': response['additional_info']
    })

# Example route for chatbot interaction that maintains context
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_text = data.get('text', '')
    session_id = data.get('session_id', 'default')
    
    # You'd need to implement session management to maintain conversation history
    # This is a simplified example
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []
    
    # Add user message to history
    chat_sessions[session_id].append({"role": "user", "content": user_text})
    
    # Analyze sentiment with context
    sentiment_result = analyzer.analyze_sentiment(user_text)
    
    # Get appropriate response
    response = analyzer.get_response(sentiment_result)
    
    # Add bot response to history
    chat_sessions[session_id].append({"role": "bot", "content": response['response_text']})
    
    return jsonify({
        'response': response['response_text'],
        'additional_info': response['additional_info'],
        'sentiment': sentiment_result['sentiment']
    })

if __name__ == '__main__':
    chat_sessions = {}
    app.run(debug=True)
"""

if __name__ == "__main__":
    main() 