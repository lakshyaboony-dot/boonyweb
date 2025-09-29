#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real-time Chatbot Service for Boony English Learning
Provides AI-powered conversation with topic selection and live corrections
"""

import openai
import json
import random
from datetime import datetime
from typing import List, Dict, Optional
from models import Progress, User
from core.openai_helper import client as openai_client

class BoonyChat:
    def __init__(self):
        self.client = openai_client
        self.conversation_topics = {
            'beginner': [
                {'topic': 'Daily Routine', 'description': 'Talk about your daily activities and habits'},
                {'topic': 'Family & Friends', 'description': 'Discuss your family members and friendships'},
                {'topic': 'Food & Cooking', 'description': 'Share about your favorite foods and cooking experiences'}
            ],
            'intermediate': [
                {'topic': 'Travel & Adventure', 'description': 'Discuss travel experiences and dream destinations'},
                {'topic': 'Career & Goals', 'description': 'Talk about your career aspirations and life goals'},
                {'topic': 'Technology & Innovation', 'description': 'Explore how technology impacts our daily lives'}
            ],
            'advanced': [
                {'topic': 'Global Issues', 'description': 'Discuss current world events and social issues'},
                {'topic': 'Philosophy & Ethics', 'description': 'Explore deep philosophical questions and moral dilemmas'},
                {'topic': 'Science & Future', 'description': 'Talk about scientific discoveries and future possibilities'}
            ]
        }
        
        self.conversation_history = {}
        self.user_corrections = {}
    
    def get_user_level(self, user_id: str) -> str:
        """Determine user's English level based on progress and performance"""
        try:
            progress = Progress.query.filter_by(user_id=user_id).order_by(Progress.day.desc()).first()
            if not progress:
                return 'beginner'
            
            # Extract day number from progress
            day_num = int(progress.day.replace('Day-', ''))
            
            # Enhanced level determination with performance metrics
            try:
                # Get user's recent performance data
                recent_progress = Progress.query.filter_by(user_id=user_id).order_by(Progress.day.desc()).limit(10).all()
                
                if len(recent_progress) >= 3:
                    # Calculate average performance score
                    total_score = 0
                    score_count = 0
                    
                    for prog in recent_progress:
                        if hasattr(prog, 'score') and prog.score is not None:
                            total_score += prog.score
                            score_count += 1
                    
                    avg_score = total_score / score_count if score_count > 0 else 0
                    
                    # Enhanced level logic combining days and performance
                    if day_num >= 100 and avg_score >= 85:
                        return 'advanced'
                    elif day_num >= 80 and avg_score >= 80:
                        return 'advanced'
                    elif day_num >= 50 and avg_score >= 75:
                        return 'intermediate'
                    elif day_num >= 30 and avg_score >= 70:
                        return 'intermediate'
                    elif day_num >= 20 and avg_score >= 60:
                        return 'intermediate'
                    else:
                        return 'beginner'
                else:
                    # Fallback to day-based logic
                    if day_num <= 30:
                        return 'beginner'
                    elif day_num <= 80:
                        return 'intermediate'
                    else:
                        return 'advanced'
                        
            except Exception as perf_error:
                print(f"Performance calculation error: {perf_error}")
                # Fallback to simple day-based logic
                if day_num <= 30:
                    return 'beginner'
                elif day_num <= 80:
                    return 'intermediate'
                else:
                    return 'advanced'
                    
        except Exception as e:
            print(f"Error determining user level: {e}")
            return 'beginner'
    
    def get_topic_options(self, user_id: str) -> List[Dict]:
        """Get AI-powered conversation topic options based on user level"""
        level = self.get_user_level(user_id)
        
        try:
            # Enhanced topic database with more variety
            topic_database = {
                'beginner': [
                    {'topic': 'Daily Routine', 'description': 'Talk about your daily activities, morning routine, and schedule'},
                    {'topic': 'Food & Cooking', 'description': 'Discuss favorite foods, cooking experiences, and recipes'},
                    {'topic': 'Weather & Seasons', 'description': 'Chat about weather, seasons, and outdoor activities'},
                    {'topic': 'Family & Friends', 'description': 'Share stories about family members and friendships'},
                    {'topic': 'Hobbies & Interests', 'description': 'Talk about your hobbies, sports, and free time activities'},
                    {'topic': 'Shopping & Money', 'description': 'Discuss shopping experiences and managing money'},
                    {'topic': 'Health & Exercise', 'description': 'Talk about staying healthy and exercise routines'},
                    {'topic': 'Transportation', 'description': 'Discuss different ways of traveling and commuting'}
                ],
                'intermediate': [
                    {'topic': 'Travel & Culture', 'description': 'Share travel experiences and explore cultural differences'},
                    {'topic': 'Work & Career', 'description': 'Discuss job experiences, career goals, and workplace challenges'},
                    {'topic': 'Technology & Social Media', 'description': 'Talk about technology trends and social media impact'},
                    {'topic': 'Education & Learning', 'description': 'Discuss learning experiences and educational systems'},
                    {'topic': 'Entertainment & Media', 'description': 'Talk about movies, music, books, and entertainment preferences'},
                    {'topic': 'Environment & Nature', 'description': 'Discuss environmental issues and nature conservation'},
                    {'topic': 'Relationships & Communication', 'description': 'Explore interpersonal relationships and communication skills'},
                    {'topic': 'Future Plans & Dreams', 'description': 'Share your future aspirations and life goals'}
                ],
                'advanced': [
                    {'topic': 'Current Events & Politics', 'description': 'Analyze recent news, political developments, and global issues'},
                    {'topic': 'Philosophy & Ethics', 'description': 'Explore philosophical questions and ethical dilemmas'},
                    {'topic': 'Science & Innovation', 'description': 'Discuss scientific breakthroughs and technological innovations'},
                    {'topic': 'Economics & Business', 'description': 'Analyze economic trends and business strategies'},
                    {'topic': 'Art & Literature', 'description': 'Discuss artistic movements, literature, and creative expression'},
                    {'topic': 'Psychology & Human Behavior', 'description': 'Explore human psychology and behavioral patterns'},
                    {'topic': 'Global Challenges', 'description': 'Discuss climate change, poverty, and global solutions'},
                    {'topic': 'Innovation & Entrepreneurship', 'description': 'Talk about startups, innovation, and business creation'}
                ]
            }
            
            available_topics = topic_database.get(level, topic_database['beginner'])
            
            # Use AI to select 3 most relevant topics based on current trends and user engagement
            try:
                current_hour = datetime.now().hour
                current_day = datetime.now().weekday()  # 0=Monday, 6=Sunday
                
                # Weight topics based on time and context
                weighted_topics = []
                for topic in available_topics:
                    weight = 1.0
                    
                    # Time-based weighting
                    if current_hour < 12 and 'Daily Routine' in topic['topic']:
                        weight += 0.3
                    elif 12 <= current_hour < 18 and 'Work' in topic['topic']:
                        weight += 0.3
                    elif current_hour >= 18 and ('Entertainment' in topic['topic'] or 'Food' in topic['topic']):
                        weight += 0.3
                    
                    # Day-based weighting
                    if current_day < 5:  # Weekday
                        if 'Work' in topic['topic'] or 'Career' in topic['topic']:
                            weight += 0.2
                    else:  # Weekend
                        if 'Hobbies' in topic['topic'] or 'Travel' in topic['topic'] or 'Entertainment' in topic['topic']:
                            weight += 0.2
                    
                    weighted_topics.append((topic, weight))
                
                # Sort by weight and select top 3
                weighted_topics.sort(key=lambda x: x[1], reverse=True)
                selected_topics = [topic[0] for topic in weighted_topics[:3]]
                
                # Add some randomness to avoid repetition
                if len(available_topics) > 3:
                    random.shuffle(selected_topics)
                    # Replace one topic with a random one occasionally
                    if random.random() < 0.3:
                        remaining_topics = [t for t in available_topics if t not in selected_topics]
                        if remaining_topics:
                            selected_topics[-1] = random.choice(remaining_topics)
                
                return selected_topics
                
            except Exception as e:
                print(f"Error in AI topic selection: {e}")
                # Fallback to random selection
                return random.sample(available_topics, min(3, len(available_topics)))
                
        except Exception as e:
            print(f"Error getting conversation topics: {e}")
            # Ultimate fallback
            return [
                {'topic': 'Daily Life', 'description': 'Talk about your daily activities and experiences'},
                {'topic': 'Interests', 'description': 'Share your hobbies and things you enjoy'},
                {'topic': 'Future Plans', 'description': 'Discuss your goals and future aspirations'}
            ]
    
    def start_conversation(self, user_id: str, selected_topic: str) -> Dict:
        """Start a new conversation with selected topic"""
        level = self.get_user_level(user_id)
        
        # Initialize conversation history
        self.conversation_history[user_id] = {
            'topic': selected_topic,
            'level': level,
            'messages': [],
            'corrections': [],
            'start_time': datetime.now().isoformat()
        }
        
        # Generate opening message from Boony
        opening_prompt = f"""
You are Boony, a friendly English learning assistant. Start a natural conversation about "{selected_topic}" with a {level} level English learner.

Guidelines:
- Be encouraging and supportive
- Ask engaging questions to keep conversation flowing
- Use vocabulary appropriate for {level} level
- Keep responses conversational and natural (2-3 sentences max)
- Show genuine interest in the user's responses

Start the conversation with a warm greeting and introduce the topic naturally.
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": opening_prompt},
                    {"role": "user", "content": f"Let's talk about {selected_topic}"}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            boony_message = response.choices[0].message.content.strip()
            
            # Store in conversation history
            self.conversation_history[user_id]['messages'].append({
                'role': 'assistant',
                'content': boony_message,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                'success': True,
                'message': boony_message,
                'topic': selected_topic,
                'level': level
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to start conversation: {str(e)}",
                'message': f"Hi! I'm Boony, and I'm excited to talk with you about {selected_topic}! How are you doing today?"
            }
    
    def process_user_message(self, user_id: str, message: str) -> Dict:
        """Process user message and generate AI response with corrections"""
        if user_id not in self.conversation_history:
            return {
                'success': False,
                'error': 'No active conversation found. Please start a new conversation.'
            }
        
        conversation = self.conversation_history[user_id]
        topic = conversation['topic']
        level = conversation['level']
        
        # Add user message to history
        conversation['messages'].append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Analyze message for corrections
        corrections = self.analyze_grammar(message, level)
        
        # Generate Boony's response
        response_data = self.generate_response(user_id, message, topic, level)
        
        # Add corrections to response if any
        if corrections:
            conversation['corrections'].extend(corrections)
            response_data['corrections'] = corrections
        
        return response_data
    
    def analyze_grammar(self, message: str, level: str) -> List[Dict]:
        """Enhanced grammar analysis with better error detection"""
        correction_prompt = f"""
Analyze this English message from a {level} level learner for grammar, vocabulary, and structure improvements.

Message: "{message}"

Analyze for:
1. Grammar errors (verb tenses, subject-verb agreement, etc.)
2. Word choice and vocabulary improvements
3. Sentence structure issues
4. Common ESL mistakes

Provide corrections in this exact JSON format:
{{
    "corrections": [
        {{
            "original": "incorrect phrase",
            "corrected": "correct phrase",
            "explanation": "brief explanation of the error",
            "type": "grammar|vocabulary|structure"
        }}
    ]
}}

Only include actual errors. If the text is correct, return empty corrections array.
Keep explanations simple and encouraging for language learners.
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert English teacher providing grammar corrections for language learners. Focus on helpful, encouraging feedback."},
                    {"role": "user", "content": correction_prompt}
                ],
                max_tokens=400,
                temperature=0.2
            )
            
            correction_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                correction_data = json.loads(correction_text)
                corrections = correction_data.get('corrections', [])
                
                # Validate and clean corrections
                valid_corrections = []
                for correction in corrections:
                    if all(key in correction for key in ['original', 'corrected', 'explanation']):
                        # Ensure corrections are meaningful
                        if correction['original'].strip() != correction['corrected'].strip():
                            valid_corrections.append({
                                'original': correction['original'].strip(),
                                'corrected': correction['corrected'].strip(),
                                'explanation': correction['explanation'].strip(),
                                'type': correction.get('type', 'grammar')
                            })
                
                return valid_corrections[:3]  # Limit to 3 corrections to avoid overwhelming
                
            except json.JSONDecodeError as json_error:
                print(f"JSON parsing error: {json_error}")
                # Try to extract corrections using regex as fallback
                import re
                corrections = []
                
                # Look for common correction patterns
                patterns = [
                    r'"([^"]+)"\s*→\s*"([^"]+)"',
                    r'"([^"]+)"\s*should\s+be\s*"([^"]+)"',
                    r'Change\s*"([^"]+)"\s*to\s*"([^"]+)"'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, correction_text, re.IGNORECASE)
                    for match in matches:
                        if len(match) == 2:
                            corrections.append({
                                'original': match[0],
                                'corrected': match[1],
                                'explanation': 'Grammar correction suggested',
                                'type': 'grammar'
                            })
                
                return corrections[:2]  # Limit fallback corrections
                
        except Exception as e:
            print(f"Error analyzing grammar: {e}")
            return []
    
    def generate_response(self, user_id: str, user_message: str, topic: str, level: str) -> Dict:
        """Generate Boony's conversational response"""
        conversation = self.conversation_history[user_id]
        recent_messages = conversation['messages'][-6:]  # Last 6 messages for context
        
        # Build conversation context
        context_messages = [
            {
                "role": "system",
                "content": f"""
You are Boony, a friendly English learning assistant having a natural conversation about "{topic}" with a {level} level English learner.

Guidelines:
- Keep the conversation flowing naturally
- Ask follow-up questions to maintain engagement
- Use vocabulary appropriate for {level} level
- Be encouraging and supportive
- Keep responses conversational (2-3 sentences max)
- Show genuine interest in their responses
- Don't mention grammar corrections directly in conversation
"""
            }
        ]
        
        # Add recent conversation history
        for msg in recent_messages[:-1]:  # Exclude the current message
            context_messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
        
        # Add current user message
        context_messages.append({
            "role": "user",
            "content": user_message
        })
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=context_messages,
                max_tokens=150,
                temperature=0.7
            )
            
            boony_response = response.choices[0].message.content.strip()
            
            # Add to conversation history
            conversation['messages'].append({
                'role': 'assistant',
                'content': boony_response,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                'success': True,
                'message': boony_response,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            fallback_responses = [
                "That's interesting! Can you tell me more about that?",
                "I'd love to hear more about your thoughts on this!",
                "That sounds fascinating! What do you think about it?",
                "Great point! How do you feel about that?"
            ]
            
            fallback_message = random.choice(fallback_responses)
            
            conversation['messages'].append({
                'role': 'assistant',
                'content': fallback_message,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                'success': True,
                'message': fallback_message,
                'timestamp': datetime.now().isoformat(),
                'fallback': True
            }
    
    def get_conversation_summary(self, user_id: str) -> Dict:
        """Generate an enhanced conversation summary with learning insights"""
        if user_id not in self.conversation_history:
            return {'success': False, 'error': 'No conversation found'}
        
        conversation = self.conversation_history[user_id]
        user_messages = [msg for msg in conversation['messages'] if msg['role'] == 'user']
        total_corrections = len(conversation.get('corrections', []))
        
        try:
            # Get recent conversation for AI summary
            recent_messages = conversation['messages'][-12:]  # Last 12 messages
            messages_text = "\n".join([
                f"{msg['role'].title()}: {msg['content']}"
                for msg in recent_messages
            ])
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an English teacher providing a conversation summary for a language learner.
                        
Analyze the conversation and provide:
1. Main topics discussed
2. Key vocabulary used
3. Grammar patterns practiced
4. Areas for improvement
5. Positive aspects of the learner's English

Keep the summary encouraging and constructive. Focus on learning achievements.
Format as a friendly, motivating summary in 3-4 sentences."""
                    },
                    {
                        "role": "user",
                        "content": f"Topic: {conversation['topic']}\n\nConversation ({len(user_messages)} user messages):\n{messages_text}"
                    }
                ],
                max_tokens=250,
                temperature=0.6
            )
            
            ai_summary = response.choices[0].message.content
            
            return {
                'success': True,
                'topic': conversation['topic'],
                'level': conversation['level'],
                'total_messages': len(user_messages),
                'total_corrections': total_corrections,
                'duration': conversation.get('start_time'),
                'corrections': conversation.get('corrections', []),
                'ai_summary': ai_summary,
                'stats': {
                    'words_practiced': sum(len(msg['content'].split()) for msg in user_messages),
                    'avg_message_length': round(sum(len(msg['content'].split()) for msg in user_messages) / len(user_messages), 1) if user_messages else 0
                }
            }
            
        except Exception as e:
            print(f"Error generating AI summary: {e}")
            # Fallback summary
            return {
                'success': True,
                'topic': conversation['topic'],
                'level': conversation['level'],
                'total_messages': len(user_messages),
                'total_corrections': total_corrections,
                'duration': conversation.get('start_time'),
                'corrections': conversation.get('corrections', []),
                'summary': f"Great conversation practice about {conversation['topic']}! You exchanged {len(user_messages)} messages and practiced your English skills. Keep up the good work!"
            }
    
    def end_conversation(self, user_id: str) -> Dict:
        """End conversation and provide summary"""
        summary = self.get_conversation_summary(user_id)
        
        # Clear conversation history
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
        
        return summary

# Global chatbot instance
chatbot = BoonyChat()