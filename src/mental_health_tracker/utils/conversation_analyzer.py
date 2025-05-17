"""
Conversation Analyzer: Analyzes conversation patterns and trends over time

Features:
- Identifies emotional trends and sentiment patterns
- Detects recurring topics and concerns
- Generates conversation insights for users and therapists
- Tracks mood improvements and regressions
"""
import re
import logging
import json
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from collections import Counter
import statistics
import math

logger = logging.getLogger(__name__)

class ConversationAnalyzer:
    """
    Analyzes conversation patterns and trends across multiple sessions
    """
    def __init__(self):
        """Initialize the conversation analyzer"""
        # Topic and keyword dictionary for categorization
        self.topic_keywords = {
            "work": ["job", "career", "boss", "coworker", "office", "workplace", "workload", "promotion", "fired"],
            "relationships": ["partner", "husband", "wife", "boyfriend", "girlfriend", "date", "relationship", "marriage", "divorce"],
            "family": ["parent", "mother", "father", "sister", "brother", "child", "kid", "baby", "family", "son", "daughter"],
            "health": ["health", "sick", "doctor", "hospital", "medication", "pain", "treatment", "diagnosis", "symptom"],
            "anxiety": ["anxious", "worry", "panic", "stress", "tense", "nervous", "overwhelmed", "anxiety"],
            "depression": ["depressed", "sad", "hopeless", "empty", "worthless", "tired", "depression", "unmotivated"],
            "sleep": ["sleep", "insomnia", "nightmare", "tired", "exhausted", "fatigue", "rest", "bed"],
            "social": ["friend", "social", "party", "gathering", "lonely", "alone", "isolated", "connection"],
            "finance": ["money", "debt", "financial", "bill", "afford", "payment", "budget", "income", "expense"],
            "self_esteem": ["confidence", "self-esteem", "worthless", "failure", "succeed", "inadequate", "proud"]
        }
        
        # Initialize insight generators
        self.insight_generators = [
            self._generate_topic_insights,
            self._generate_emotion_insights,
            self._generate_sentiment_insights,
            self._generate_pattern_insights
        ]
    
    def analyze_conversation_history(self, conversation_history: List[Dict], 
                                   timeframe_days: int = 7) -> Dict:
        """
        Analyze conversation history to identify patterns and trends
        
        Args:
            conversation_history: List of conversation entries with message, response, timestamp, analysis
            timeframe_days: Number of days to analyze (default: 7)
            
        Returns:
            Dict with analysis results
        """
        # Filter conversations by timeframe
        cutoff_date = datetime.now() - timedelta(days=timeframe_days)
        recent_history = [
            entry for entry in conversation_history 
            if self._parse_timestamp(entry.get("timestamp", "")) >= cutoff_date
        ]
        
        if not recent_history:
            return {
                "error": "No conversation history available in the specified timeframe",
                "message_count": 0,
                "insights": []
            }
        
        # Initialize analysis result
        result = {
            "message_count": len(recent_history),
            "timeframe_days": timeframe_days,
            "analyzed_at": datetime.now().isoformat(),
            "topics": {},
            "emotions": {},
            "sentiment_trend": {},
            "patterns": {},
            "insights": []
        }
        
        # Extract topics
        all_topics = []
        for entry in recent_history:
            message = entry.get("message", "")
            if not message:
                continue
                
            # Look for topics in messages
            found_topics = self._extract_topics(message)
            all_topics.extend(found_topics)
        
        # Count topics
        topic_counter = Counter(all_topics)
        result["topics"] = {topic: count for topic, count in topic_counter.most_common()}
        
        # Extract emotions
        all_emotions = []
        for entry in recent_history:
            analysis = entry.get("analysis", {})
            emotions = analysis.get("emotions", {})
            if not emotions:
                continue
                
            # Get dominant emotion
            if emotions:
                dominant_emotion = max(emotions.items(), key=lambda x: x[1])
                if dominant_emotion[1] > 0.3:  # Only count significant emotions
                    all_emotions.append(dominant_emotion[0])
        
        # Count emotions
        emotion_counter = Counter(all_emotions)
        result["emotions"] = {emotion: count for emotion, count in emotion_counter.most_common()}
        
        # Analyze sentiment trend
        sentiment_scores = []
        sentiment_dates = []
        for entry in recent_history:
            sentiment = entry.get("analysis", {}).get("sentiment", None)
            timestamp = entry.get("timestamp")
            if sentiment is not None and timestamp:
                sentiment_scores.append(sentiment)
                sentiment_dates.append(self._parse_timestamp(timestamp))
        
        # Calculate sentiment trend
        if sentiment_scores:
            result["sentiment_trend"] = self._calculate_sentiment_trend(sentiment_scores, sentiment_dates)
        
        # Identify patterns (repeated themes, questions, etc.)
        result["patterns"] = self._identify_patterns(recent_history)
        
        # Generate insights
        for generator in self.insight_generators:
            insights = generator(result, recent_history)
            if insights:
                result["insights"].extend(insights)
        
        # Sort insights by priority
        result["insights"] = sorted(result["insights"], key=lambda x: x.get("priority", 5))
        
        return result
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text based on keyword matching"""
        text_lower = text.lower()
        found_topics = []
        
        for topic, keywords in self.topic_keywords.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                    found_topics.append(topic)
                    break
        
        return found_topics
    
    def _calculate_sentiment_trend(self, scores: List[float], dates: List[datetime]) -> Dict:
        """Calculate sentiment trend from a series of sentiment scores"""
        if not scores or len(scores) < 2:
            return {"trend": "insufficient_data"}
            
        # Basic statistics
        average = sum(scores) / len(scores)
        try:
            stdev = statistics.stdev(scores)
        except statistics.StatisticsError:
            stdev = 0
            
        # Check if scores are mostly consistent
        if stdev < 0.15:
            if average > 0.6:
                trend = "consistently_positive"
            elif average < 0.4:
                trend = "consistently_negative"
            else:
                trend = "consistently_neutral"
        else:
            # Calculate trend line (simple linear regression)
            x = list(range(len(scores)))
            x_mean = sum(x) / len(x)
            y_mean = sum(scores) / len(scores)
            
            numerator = sum((x[i] - x_mean) * (scores[i] - y_mean) for i in range(len(scores)))
            denominator = sum((x[i] - x_mean) ** 2 for i in range(len(scores)))
            
            slope = numerator / denominator if denominator != 0 else 0
            
            if abs(slope) < 0.03:
                trend = "fluctuating"
            elif slope > 0:
                trend = "improving"
            else:
                trend = "declining"
        
        # Calculate volatility
        volatility = stdev / (max(scores) - min(scores)) if max(scores) != min(scores) else 0
        
        # Check for recent dramatic shifts
        recent_shift = False
        if len(scores) >= 3:
            last_diff = abs(scores[-1] - scores[-2])
            avg_diff = sum(abs(scores[i] - scores[i-1]) for i in range(1, len(scores))) / (len(scores) - 1)
            if last_diff > 2 * avg_diff:
                recent_shift = True
        
        return {
            "trend": trend,
            "average": average,
            "volatility": volatility,
            "recent_shift": recent_shift,
            "improvement_chance": 0.5 + slope * 5  # Simple heuristic
        }
    
    def _identify_patterns(self, history: List[Dict]) -> Dict:
        """Identify recurring patterns in conversation history"""
        patterns = {}
        
        # Extract user messages
        user_messages = [entry.get("message", "") for entry in history]
        
        # Check for repetitive questions
        question_counter = Counter()
        for message in user_messages:
            if message.endswith("?"):
                # Normalize question
                normalized = re.sub(r'[^\w\s]', '', message.lower())
                question_counter[normalized] += 1
        
        # Filter for questions asked multiple times
        repeated_questions = {q: count for q, count in question_counter.items() if count > 1}
        if repeated_questions:
            patterns["repeated_questions"] = repeated_questions
        
        # Check for abandonment patterns (user stops responding after bot says something)
        response_gaps = []
        for i in range(len(history) - 1):
            current_time = self._parse_timestamp(history[i].get("timestamp", ""))
            next_time = self._parse_timestamp(history[i+1].get("timestamp", ""))
            gap_hours = (next_time - current_time).total_seconds() / 3600
            
            if gap_hours > 12:
                response_gaps.append({
                    "gap_hours": gap_hours,
                    "last_response": history[i].get("response", ""),
                    "sentiment": history[i].get("analysis", {}).get("sentiment_label", "unknown")
                })
        
        if response_gaps:
            patterns["response_gaps"] = response_gaps
        
        # Check for late night messages (potential sleep issues)
        late_night_messages = []
        for entry in history:
            timestamp = self._parse_timestamp(entry.get("timestamp", ""))
            hour = timestamp.hour
            if hour >= 23 or hour <= 4:
                late_night_messages.append({
                    "time": timestamp.strftime("%H:%M"),
                    "date": timestamp.strftime("%Y-%m-%d"),
                    "sentiment": entry.get("analysis", {}).get("sentiment_label", "unknown")
                })
        
        if late_night_messages:
            patterns["late_night_messages"] = late_night_messages
        
        return patterns
    
    def _generate_topic_insights(self, analysis_result: Dict, history: List[Dict]) -> List[Dict]:
        """Generate insights about conversation topics"""
        insights = []
        
        # Get top topics
        topics = analysis_result.get("topics", {})
        if not topics:
            return []
            
        top_topics = list(topics.items())[:3]
        
        # Insight about most discussed topic
        if top_topics:
            top_topic, count = top_topics[0]
            if count >= 3:
                insights.append({
                    "type": "topic_frequency",
                    "priority": 1,
                    "text": f"You've discussed {top_topic} {count} times in the past {analysis_result['timeframe_days']} days.",
                    "topic": top_topic,
                    "frequency": count
                })
        
        # Insight about topic combination
        if len(top_topics) >= 2:
            topic1 = top_topics[0][0]
            topic2 = top_topics[1][0]
            insights.append({
                "type": "topic_combination",
                "priority": 3,
                "text": f"You frequently discuss both {topic1} and {topic2}, suggesting they might be connected for you.",
                "topics": [topic1, topic2]
            })
        
        # Check if any known negative topics are prominent
        negative_topics = ["anxiety", "depression", "health"]
        for topic in negative_topics:
            if topic in topics and topics[topic] >= 2:
                insights.append({
                    "type": "concern_topic",
                    "priority": 2,
                    "text": f"Your conversations about {topic} appear {topics[topic]} times recently. Would you like to explore resources related to this?",
                    "topic": topic,
                    "frequency": topics[topic]
                })
                break
        
        return insights
    
    def _generate_emotion_insights(self, analysis_result: Dict, history: List[Dict]) -> List[Dict]:
        """Generate insights about emotional patterns"""
        insights = []
        
        emotions = analysis_result.get("emotions", {})
        if not emotions:
            return []
        
        # Get dominant emotion
        dominant_emotion = next(iter(emotions.items()), (None, 0))
        if dominant_emotion[0] and dominant_emotion[1] >= 2:
            insights.append({
                "type": "dominant_emotion",
                "priority": 2,
                "text": f"The emotion of {dominant_emotion[0]} appears frequently in your conversations.",
                "emotion": dominant_emotion[0],
                "frequency": dominant_emotion[1]
            })
        
        # Check for emotional variety/balance
        if len(emotions) >= 3:
            insights.append({
                "type": "emotional_variety",
                "priority": 4,
                "text": f"You've expressed a healthy range of emotions in our conversations.",
                "emotions": list(emotions.keys())[:3]
            })
        elif len(emotions) == 1:
            emotion = next(iter(emotions.keys()))
            insights.append({
                "type": "emotional_fixation",
                "priority": 3,
                "text": f"Your conversations have primarily expressed {emotion}. It may help to explore other feelings too.",
                "emotion": emotion
            })
        
        # Check for problematic emotions
        negative_emotions = ["sadness", "anger", "fear"]
        for emotion in negative_emotions:
            if emotion in emotions and emotions[emotion] >= 2:
                insights.append({
                    "type": "concerning_emotion",
                    "priority": 2,
                    "text": f"You've expressed {emotion} multiple times recently. Would you like to discuss ways to manage this feeling?",
                    "emotion": emotion,
                    "frequency": emotions[emotion]
                })
                break
        
        return insights
    
    def _generate_sentiment_insights(self, analysis_result: Dict, history: List[Dict]) -> List[Dict]:
        """Generate insights about sentiment trends"""
        insights = []
        
        sentiment_trend = analysis_result.get("sentiment_trend", {})
        if not sentiment_trend or sentiment_trend.get("trend") == "insufficient_data":
            return []
        
        trend = sentiment_trend.get("trend")
        
        # Generate insight based on trend
        if trend == "improving":
            insights.append({
                "type": "sentiment_improvement",
                "priority": 1,
                "text": "Your mood appears to be improving over our recent conversations. What positive changes have you noticed?",
                "trend": "improving",
                "improvement_chance": sentiment_trend.get("improvement_chance", 0.5)
            })
        elif trend == "declining":
            insights.append({
                "type": "sentiment_decline",
                "priority": 1,
                "text": "Your mood seems to have been declining in our recent conversations. Is there something specific that's been challenging?",
                "trend": "declining",
                "improvement_chance": sentiment_trend.get("improvement_chance", 0.5)
            })
        elif trend == "consistently_negative":
            insights.append({
                "type": "persistent_negative",
                "priority": 1,
                "text": "You've been consistently expressing negative feelings. Would it be helpful to discuss strategies for improving your mood?",
                "trend": "consistently_negative"
            })
        elif trend == "consistently_positive":
            insights.append({
                "type": "persistent_positive",
                "priority": 3,
                "text": "You've been maintaining a positive outlook in our conversations. What strategies have been working well for you?",
                "trend": "consistently_positive"
            })
        elif trend == "fluctuating":
            insights.append({
                "type": "mood_fluctuation",
                "priority": 2,
                "text": "Your mood seems to fluctuate significantly between conversations. Have you noticed particular triggers for these changes?",
                "trend": "fluctuating",
                "volatility": sentiment_trend.get("volatility", 0)
            })
        
        # Check for recent dramatic shifts
        if sentiment_trend.get("recent_shift"):
            insights.append({
                "type": "mood_shift",
                "priority": 1,
                "text": "There's been a noticeable shift in your mood recently. Would you like to talk about what might have caused this change?",
                "recent_shift": True
            })
        
        return insights
    
    def _generate_pattern_insights(self, analysis_result: Dict, history: List[Dict]) -> List[Dict]:
        """Generate insights about behavioral patterns"""
        insights = []
        
        patterns = analysis_result.get("patterns", {})
        if not patterns:
            return []
        
        # Insight about repeated questions
        repeated_questions = patterns.get("repeated_questions", {})
        if repeated_questions:
            insights.append({
                "type": "repeated_questions",
                "priority": 2,
                "text": "You've asked some questions multiple times. Is there a particular concern that hasn't been addressed fully?",
                "questions": list(repeated_questions.keys())[:2]
            })
        
        # Insight about response gaps
        response_gaps = patterns.get("response_gaps", [])
        if response_gaps and len(response_gaps) >= 2:
            insights.append({
                "type": "conversation_gaps",
                "priority": 4,
                "text": "There have been some gaps in our conversation. Feel free to reach out anytime you need support.",
                "gap_count": len(response_gaps)
            })
        
        # Insight about late night messages
        late_night_messages = patterns.get("late_night_messages", [])
        if late_night_messages and len(late_night_messages) >= 2:
            insights.append({
                "type": "late_night_activity",
                "priority": 3,
                "text": "I've noticed you often message late at night. Have you been experiencing sleep difficulties?",
                "occurrences": len(late_night_messages)
            })
        
        return insights
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string to datetime object"""
        if not timestamp_str:
            return datetime.now()
            
        try:
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError):
            logger.error(f"Invalid timestamp format: {timestamp_str}")
            return datetime.now()
    
    def generate_weekly_report(self, user_id: str, conversation_history: List[Dict]) -> Dict:
        """
        Generate a comprehensive weekly report for a user
        
        Args:
            user_id: User identifier
            conversation_history: List of conversation entries
            
        Returns:
            Dict with weekly report data
        """
        # Analyze conversation history
        analysis = self.analyze_conversation_history(conversation_history, timeframe_days=7)
        
        # Initialize report
        report = {
            "user_id": user_id,
            "generated_at": datetime.now().isoformat(),
            "period": {
                "start": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                "end": datetime.now().strftime("%Y-%m-%d")
            },
            "summary": self._generate_summary(analysis),
            "mood_trend": self._format_mood_trend(analysis),
            "top_topics": [],
            "key_insights": [],
            "recommendations": []
        }
        
        # Add top topics
        topics = analysis.get("topics", {})
        report["top_topics"] = [{"topic": t, "count": c} for t, c in list(topics.items())[:5]]
        
        # Add key insights
        insights = analysis.get("insights", [])
        report["key_insights"] = insights[:5]  # Top 5 insights
        
        # Generate recommendations
        report["recommendations"] = self._generate_recommendations(analysis)
        
        return report
    
    def _generate_summary(self, analysis: Dict) -> str:
        """Generate a text summary of the analysis"""
        message_count = analysis.get("message_count", 0)
        if message_count == 0:
            return "No conversation data available for this period."
            
        # Get top topics and emotions
        top_topics = list(analysis.get("topics", {}).keys())[:3]
        top_emotions = list(analysis.get("emotions", {}).keys())[:3]
        
        # Get sentiment trend
        sentiment_trend = analysis.get("sentiment_trend", {}).get("trend", "undetermined")
        
        # Build summary
        summary = f"Based on {message_count} messages over the past week, "
        
        # Add topics
        if top_topics:
            topics_text = ", ".join(top_topics[:-1]) + (" and " + top_topics[-1] if len(top_topics) > 1 else top_topics[0])
            summary += f"you primarily discussed {topics_text}. "
        
        # Add emotions
        if top_emotions:
            emotions_text = ", ".join(top_emotions[:-1]) + (" and " + top_emotions[-1] if len(top_emotions) > 1 else top_emotions[0])
            summary += f"You frequently expressed feelings of {emotions_text}. "
        
        # Add sentiment trend
        if sentiment_trend == "improving":
            summary += "Your overall mood appears to be improving. "
        elif sentiment_trend == "declining":
            summary += "Your overall mood has been declining. "
        elif sentiment_trend == "consistently_positive":
            summary += "You've maintained a consistently positive outlook. "
        elif sentiment_trend == "consistently_negative":
            summary += "You've expressed primarily negative feelings. "
        elif sentiment_trend == "fluctuating":
            summary += "Your mood has fluctuated considerably. "
        
        return summary.strip()
    
    def _format_mood_trend(self, analysis: Dict) -> Dict:
        """Format mood trend data for reporting"""
        sentiment_trend = analysis.get("sentiment_trend", {})
        
        result = {
            "trend": sentiment_trend.get("trend", "undetermined"),
            "average": sentiment_trend.get("average", 0.5),
            "description": ""
        }
        
        # Add descriptive text
        trend = result["trend"]
        if trend == "improving":
            result["description"] = "Your mood has been gradually improving"
        elif trend == "declining":
            result["description"] = "Your mood has been declining recently"
        elif trend == "consistently_positive":
            result["description"] = "You've maintained a positive outlook"
        elif trend == "consistently_negative":
            result["description"] = "You've experienced persistent negative feelings"
        elif trend == "fluctuating":
            result["description"] = "Your mood has had significant ups and downs"
        else:
            result["description"] = "Not enough data to determine mood trend"
        
        return result
    
    def _generate_recommendations(self, analysis: Dict) -> List[Dict]:
        """Generate personalized recommendations based on analysis"""
        recommendations = []
        
        # Check sentiment trend
        sentiment_trend = analysis.get("sentiment_trend", {}).get("trend", "")
        
        if sentiment_trend == "declining" or sentiment_trend == "consistently_negative":
            recommendations.append({
                "type": "mood_improvement",
                "text": "Consider practicing daily gratitude exercises or mindfulness meditation to improve mood.",
                "action": "Try listing three things you're grateful for each morning for one week."
            })
            
            recommendations.append({
                "type": "professional_support",
                "text": "Your consistent mood patterns might benefit from professional support.",
                "action": "Would you like information about connecting with a therapist?"
            })
            
        # Check for anxiety topic
        topics = analysis.get("topics", {})
        if "anxiety" in topics and topics["anxiety"] >= 2:
            recommendations.append({
                "type": "anxiety_management",
                "text": "You've mentioned anxiety frequently. Deep breathing exercises can help manage anxiety symptoms.",
                "action": "Try the 4-7-8 breathing technique when feeling anxious: inhale for 4 seconds, hold for 7, exhale for 8."
            })
            
        # Check for sleep issues
        patterns = analysis.get("patterns", {})
        if patterns.get("late_night_messages"):
            recommendations.append({
                "type": "sleep_hygiene",
                "text": "Your late-night activity suggests possible sleep difficulties.",
                "action": "Consider establishing a regular sleep schedule and avoiding screens an hour before bedtime."
            })
            
        # Check for social isolation indications
        if "loneliness" in topics or "social" in topics:
            recommendations.append({
                "type": "social_connection",
                "text": "Increasing social connections can significantly improve mood and wellbeing.",
                "action": "Consider reaching out to one friend or family member this week for a brief check-in."
            })
            
        # General wellbeing recommendation (always include at least one)
        if not recommendations:
            recommendations.append({
                "type": "general_wellbeing",
                "text": "Regular physical activity is one of the most effective ways to maintain mental wellbeing.",
                "action": "Try incorporating a 10-minute walk into your daily routine."
            })
            
        return recommendations
    
    def get_topics_over_time(self, conversation_history: List[Dict], 
                          timeframe_days: int = 30,
                          interval_days: int = 7) -> Dict:
        """
        Analyze how topics change over time in conversation history
        
        Args:
            conversation_history: List of conversation entries
            timeframe_days: Total time period to analyze in days
            interval_days: Size of each interval in days
            
        Returns:
            Dict with topic trends over time
        """
        # Filter conversations by timeframe
        end_date = datetime.now()
        start_date = end_date - timedelta(days=timeframe_days)
        
        filtered_history = [
            entry for entry in conversation_history 
            if self._parse_timestamp(entry.get("timestamp", "")) >= start_date
        ]
        
        if not filtered_history:
            return {
                "error": "No conversation history available in the specified timeframe",
                "intervals": []
            }
        
        # Create time intervals
        intervals = []
        for i in range(0, timeframe_days, interval_days):
            interval_start = end_date - timedelta(days=timeframe_days - i)
            interval_end = interval_start + timedelta(days=interval_days)
            if interval_end > end_date:
                interval_end = end_date
                
            interval = {
                "start": interval_start.strftime("%Y-%m-%d"),
                "end": interval_end.strftime("%Y-%m-%d"),
                "topics": {},
                "message_count": 0
            }
            
            # Find conversations in this interval
            interval_messages = [
                entry for entry in filtered_history
                if interval_start <= self._parse_timestamp(entry.get("timestamp", "")) < interval_end
            ]
            
            interval["message_count"] = len(interval_messages)
            
            # Extract topics for this interval
            all_topics = []
            for entry in interval_messages:
                message = entry.get("message", "")
                if message:
                    found_topics = self._extract_topics(message)
                    all_topics.extend(found_topics)
            
            # Count topics
            topic_counter = Counter(all_topics)
            interval["topics"] = {topic: count for topic, count in topic_counter.most_common()}
            
            intervals.append(interval)
        
        # Calculate topic trends
        all_topics = set()
        for interval in intervals:
            all_topics.update(interval["topics"].keys())
        
        topic_trends = {}
        for topic in all_topics:
            trend = []
            for interval in intervals:
                trend.append({
                    "interval": f"{interval['start']} to {interval['end']}",
                    "count": interval["topics"].get(topic, 0)
                })
            topic_trends[topic] = trend
        
        return {
            "intervals": intervals,
            "topic_trends": topic_trends
        } 