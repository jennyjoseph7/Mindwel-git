"""
MindfulMate: A mental health support companion with:
  • Real-time sentiment & emotion analysis (TextBlob + RoBERTa + regex patterns)
  • Enhanced context management and memory persistence
  • Emotionally intelligent, empathetic responses with template and model fallback
  • Robust safety & crisis escalation with location-specific resources
  • REST API with FastAPI, async pipeline loading, rate limiting, Redis caching
  • Config-driven model selection, structured logging, and error handling
  • Secure JSON serialization, input validation, and stubbed feedback analytics
"""
import os
import re
import random
import logging
import datetime
import asyncio
import json
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel, Field, validator
from textblob import TextBlob
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import openai
import aioredis
from dotenv import load_dotenv

# --- Load config ---
load_dotenv()
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')
openai.api_key = os.getenv('OPENAI_API_KEY')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost')
USER_REGION = os.getenv('USER_REGION', 'US')  # For crisis resources

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger('mindfulmate')

# --- FastAPI setup ---
app = FastAPI(title='MindfulMate API', version='2.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.on_event('startup')
async def startup():
    # Initialize Redis and rate limiter
    app.state.redis = await aioredis.from_url(REDIS_URL, encoding='utf-8', decode_responses=True)
    await FastAPILimiter.init(app.state.redis)

# --- Constants & Globals ---
EMOJIS = ['😊','🙏','💔','✨','💙','🌱','💡']
CRISIS_PATTERNS = [
    r"\bkill myself\b", r"\bsuicid(e|al)\b", r"\bwant(ing)? to die\b",
    r"\bend (my|this) life\b", r"\bno reason to live\b",
    r"\bharm (myself|me)\b", r"\bi'?m going to die\b",
    r"\btake my (own )?life\b", r"\bdon'?t want to (be here|live|exist)",
    r"\b(can'?t|cannot) go on\b", r"\bgive(ing)? up\b", r"\bno (hope|future)\b",
]
CRISIS_REGEX = re.compile('|'.join(CRISIS_PATTERNS), re.IGNORECASE)
_sentiment_pipeline: Any = None
_emotion_pipeline: Any = None

# --- Pydantic Models with Input Validation ---
class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    message: str = Field(..., min_length=1, max_length=500)

    @validator('message')
    def sanitize_message(cls, v):
        # Basic sanitization: strip control chars
        return re.sub(r'[\x00-\x1f]+', ' ', v).strip()

class ChatResponse(BaseModel):
    response: str

# --- Pipeline Initialization (async singleton) ---
async def get_sentiment_pipeline():
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        try:
            _sentiment_pipeline = pipeline(
                'sentiment-analysis',
                model='cardiffnlp/twitter-roberta-base-sentiment'
            )
        except Exception as e:
            logger.error(f"Sentiment pipeline load failed: {e}")
            _sentiment_pipeline = lambda x: [{'label':'neutral','score':1.0}]
    return _sentiment_pipeline

async def get_emotion_pipeline():
    global _emotion_pipeline
    if _emotion_pipeline is None:
        try:
            tok = AutoTokenizer.from_pretrained('j-hartmann/emotion-english-distilroberta-base')
            mod = AutoModelForSequenceClassification.from_pretrained('j-hartmann/emotion-english-distilroberta-base')
            _emotion_pipeline = pipeline(
                'text-classification', model=mod, tokenizer=tok,
                return_all_scores=True
            )
        except Exception as e:
            logger.error(f"Emotion pipeline load failed: {e}")
            _emotion_pipeline = lambda x: [{'label':'neutral','score':1.0}]
    return _emotion_pipeline

# --- Analyzer ---
class SentimentAnalyzer:
    """Combines TextBlob, HF sentiment, and regex-based emotion detection."""
    patterns = {
        'anger': r'(?i)(angry|mad|furious|irritated|hate)',
        'sadness': r'(?i)(sad|depress|heartbroken|miserable|grief)',
        'joy': r'(?i)(happy|excited|joyful|proud)',
        'fear': r'(?i)(afraid|scared|terrified|anxious)',
        'surprise': r'(?i)(surpris|shocked|wow)',
        'disgust': r'(?i)(disgust|gross|revolting)'
    }

    async def analyze(self, text: str) -> Dict:
        polarity = round(TextBlob(text).sentiment.polarity, 2)
        primary = 'positive' if polarity>0.1 else 'negative' if polarity<-0.1 else 'neutral'
        # HF sentiment
        pipe = await get_sentiment_pipeline()
        hf = pipe(text)[0]
        label, score = hf['label'].lower(), round(hf['score'], 2)
        # Regex emotions
        emotions = {}
        for emo, pat in self.patterns.items():
            cnt = len(re.findall(pat, text))
            if cnt: emotions[emo] = min(0.5 + cnt*0.2, 0.95)
        if not emotions: emotions['neutral'] = 0.5
        # Urgency
        urgency = 1
        if polarity < -0.6 or (label=='negative' and score>0.7): urgency += 1
        if re.search(r'(?i)(urgent|help|now)', text): urgency += 1
        if CRISIS_REGEX.search(text): urgency = 5
        # Risk
        is_risk = bool(CRISIS_REGEX.search(text))
        return {'polarity':polarity,'primary':primary,'label':label,'score':score,
                'emotions':emotions,'urgency':urgency,'is_risk':is_risk}

# --- Context Manager with JSON Serialization ---
class ConversationManager:
    """Manages session context in Redis with JSON serialization and expiry"""
    @staticmethod
    async def update(redis, session_id: str, message: str, analysis: Dict) -> Dict:
        key = f"ctx:{session_id}"
        raw = await redis.get(key)
        ctx = json.loads(raw) if raw else {
            'count':0, 'topics':[], 'patterns':{}, 'last_emoji':0, 'prev':None
        }
        ctx['count'] += 1
        # topics
        found = re.findall(r"\b(job|breakup|family|health|lonely|anxiety|depress)\b", message, re.I)
        for t in found:
            t = t.lower()
            if t not in ctx['topics']: ctx['topics'].insert(0, t)
        ctx['topics'] = ctx['topics'][:3]
        # patterns frequency
        for w in re.findall(r"\w+", message.lower()): ctx['patterns'][w] = ctx['patterns'].get(w,0) + 1
        # sentiment shift
        prev = ctx.get('prev')
        shift = bool(prev and prev.get('primary') != analysis['primary'])
        ctx['prev'] = {'primary':analysis['primary'], 'ts':datetime.datetime.utcnow().isoformat()}
        # persist JSON
        await redis.set(key, json.dumps(ctx), ex=3600)
        ctx['shift'] = shift
        return ctx

# --- Safety Manager ---
class SafetyManager:
    @staticmethod
    def escalation_message(region: str) -> str:
        resources = {
            'US': 'Call 988 (US Suicide & Crisis Lifeline).',
            'UK': 'Call Samaritans at 116 123.',
            'IN': 'Call AASRA at +91-22-27546669.'
        }
        contact = resources.get(region.upper(), 'Please seek local emergency services.')
        return (
            "I'm concerned about your safety. "
            f"{contact} You're not alone—help is available."
        )

# --- Responder ---
class Responder:
    def __init__(self): self.analyzer = SentimentAnalyzer()

    async def respond(self, redis, session_id: str, message: str) -> str:
        analysis = await self.analyzer.analyze(message)
        # crisis
        if analysis['is_risk'] or analysis['urgency']==5:
            return SafetyManager.escalation_message(USER_REGION)
        # update context
        ctx = await ConversationManager.update(redis, session_id, message, analysis)
        # build prompt
        prompt = (
            f"[User]: {message}\n"
            f"[Sent]: {analysis['label']}({analysis['score']})\n"
            f"[Emo]: {analysis['emotions']}\n"
            f"[Urg]: {analysis['urgency']}\n"
            f"[Ctx]: phase={'opening' if ctx['count']<=3 else 'middle' if ctx['count']<=10 else 'closing'},"
            f" topics={ctx['topics']}\n\nCraft an empathetic response."
        )
        # call OpenAI with fallback
        try:
            resp = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=[{'role':'user','content':prompt}],
                temperature=0.7,
                max_tokens=120
            )
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI error: {e}")
            reply = "I'm here for you—please feel free to share more."
        else:
            reply = resp.choices[0].message.content.strip()
        # emoji pacing
        if ctx['count'] - ctx['last_emoji'] >= 2 and analysis['urgency']<4:
            reply += f" {random.choice(EMOJIS)}"
            ctx['last_emoji'] = ctx['count']
            await redis.set(f"ctx:{session_id}", json.dumps(ctx), ex=3600)
        # enforce length
        words = reply.split()
        if len(words) < 12:
            reply += " Let's talk more—I'm here."
        elif len(words) > 45:
            reply = ' '.join(words[:45]) + '...'
        return reply

# --- API Endpoints ---
@app.post('/chat', response_model=ChatResponse, dependencies=[Depends(RateLimiter(times=5, seconds=10))])
async def chat(req: ChatRequest, request: Request):
    try:
        res = await Responder().respond(request.app.state.redis, req.session_id, req.message)
        return ChatResponse(response=res)
    except Exception as e:
        logger.error(f"chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail='Internal error')

@app.post('/feedback')
async def feedback(session_id: str = Field(...), rating: int = Field(..., ge=1, le=5), comments: str = Field('', max_length=300)):
    # TODO: store feedback in separate Redis stream or database
    logger.info(f"Feedback received: session={session_id} rating={rating}")
    return {'status': 'thank you for your feedback'}

@app.get('/health')
async def health():
    return {'status': 'ok'}

if __name__=='__main__':
    import uvicorn
    uvicorn.run('mindfulmate:app', host='0.0.0.0', port=8000, reload=True) 