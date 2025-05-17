# AI Mental Health Tracker

A web application that helps users track their mental health through journaling, mood tracking, and interactive relaxation games.

## Features

- Guided breathing exercises
- Interactive games (Tic Tac Toe, Snake, Color Matching)
- Mood tracking and analysis
- Journal entries with sentiment analysis
- AI-powered chat support with crisis detection
- Focus mode
- Music therapy recommendations

## Enhanced AI Features

- **Advanced Sentiment Analysis**: Uses RoBERTa model to detect emotions with higher accuracy
- **Emotion Recognition**: Detects specific emotions (anger, sadness, anxiety, fear, confusion) and responds appropriately
- **Context Awareness**: Recognizes topics like family, relationships, work stress and tailors responses
- **Conversation Memory**: Tracks conversation history to avoid repetitive responses
- **Crisis Detection**: Identifies potentially concerning messages and provides appropriate resources
- **Adaptive Responses**: Provides varied, natural responses that fit the user's emotional state
- **Special Handling for Brief Replies**: Properly handles short user messages like "yes", "no", or "ok" without asking redundant questions

## MindfulMate: Advanced Mental Health Chatbot

The MindfulMate component provides a highly accurate mental health support chatbot with these features:

- **Multi-model Sentiment Analysis**: Combines TextBlob, RoBERTa, and regex pattern detection
- **Enhanced Context Management**: Persistent conversation memory with Redis
- **Emotionally Intelligent Responses**: Tailored responses based on sentiment, emotions, and context
- **Crisis Detection & Escalation**: Region-specific crisis resources when concerning content detected
- **FastAPI Backend**: High-performance async API with rate limiting and validation
- **Production-Ready**: Structured logging, error handling, and health checks

## System Requirements

- Windows 10 or later
- Python 3.8 or later
- Minimum 4GB RAM
- At least 10GB free disk space
- Internet connection for AI features
- Redis server (for MindfulMate)

## Installation

1. Clone this repository or download the source code
2. Create a .env file from the example:
   ```bash
   cp env.example .env
   ```
   Then edit .env to add your API keys

3. Run the setup script as administrator:
   ```bash
   python setup.py
   ```
   This will:
   - Check system requirements
   - Increase page file size for AI model support
   - Install required Python packages

4. Restart your computer for the changes to take effect

## API Keys

For full functionality, you'll need to obtain:
- A Google AI API key (Gemini) from https://ai.google.dev/
  - Add it to your .env file as GEMINI_API_KEY=your-key-here
- An OpenAI API key from https://platform.openai.com/ (for MindfulMate)
  - Add it to your .env file as OPENAI_API_KEY=your-key-here

## Running the Application

1. After restarting, open a terminal in the project directory
2. Run the main application:
   ```bash
   python main.py
   ```
3. Open your web browser and navigate to `http://localhost:5000`

## Running MindfulMate (Advanced Chatbot API)

1. Make sure Redis is installed and running locally
2. Start the MindfulMate API server:
   ```bash
   python mindfulmate.py
   ```
3. The API will be available at `http://localhost:8000`
4. Test the API health check at `http://localhost:8000/health`
5. Interact with the chatbot via POST requests to `/chat` with:
   ```json
   {
     "session_id": "user123",
     "message": "I'm feeling a bit down today"
   }
   ```

## Testing the Sentiment Analysis

To test the RoBERTa sentiment analyzer functionality:
```bash
python test_sentiment.py
```
This will demonstrate the advanced sentiment analysis and crisis detection features.

## Troubleshooting

If you encounter the "paging file is too small" error:

1. Run the setup script as administrator
2. If the setup script fails, manually increase your page file size:
   - Open System Properties (Win + Pause/Break)
   - Click "Advanced system settings"
   - Under Performance, click "Settings"
   - Go to "Advanced" tab
   - Under Virtual Memory, click "Change"
   - Uncheck "Automatically manage paging file size"
   - Set initial and maximum size to 1.5x your RAM size
   - Click "Set" and "OK"
   - Restart your computer

## MindfulMate API Troubleshooting

- **Redis Connection Issue**: Make sure Redis is running on localhost or update the REDIS_URL in .env
- **API Key Error**: Verify your OpenAI API key is correct and has sufficient credits
- **Model Loading Error**: First-time startup may be slow as models are downloaded
- **Rate Limiting**: By default, API is limited to 5 requests per 10 seconds per client

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 