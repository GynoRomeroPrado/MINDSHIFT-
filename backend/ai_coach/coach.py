"""
AI Coach System - Core conversational AI for mental health coaching
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import openai
import anthropic
from enum import Enum
import json
import re

from config import settings


class CoachPersona(str, Enum):
    """Available coach personas"""
    COACH = "coach"  # Professional, structured, goal-oriented
    FRIEND = "friend"  # Warm, conversational, supportive
    EXPERT = "expert"  # Clinical, educational, informative


class InterventionType(str, Enum):
    """Types of therapeutic interventions"""
    BREATHING = "breathing"
    GROUNDING = "grounding"
    COGNITIVE_REFRAME = "cognitive_reframe"
    MINDFULNESS = "mindfulness"
    JOURNALING = "journaling"
    PROGRESSIVE_RELAXATION = "progressive_relaxation"


class CrisisLevel(str, Enum):
    """Crisis severity levels"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AICoach:
    """Main AI Coach class handling conversations and interventions"""

    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Crisis keywords for detection
        self.crisis_keywords = {
            'critical': ['suicide', 'kill myself', 'end my life', 'not worth living',
                         'better off dead', 'want to die'],
            'high': ['self harm', 'hurt myself', 'cutting', 'harm', 'hopeless'],
            'medium': ['can\'t go on', 'give up', 'no point', 'worthless'],
            'low': ['stressed', 'overwhelmed', 'anxious', 'depressed']
        }

    def get_system_prompt(self, persona: CoachPersona, user_context: Dict) -> str:
        """Generate system prompt based on persona and user context"""

        base_prompts = {
            CoachPersona.COACH: """You are a professional mental health coach trained in CBT and DBT techniques.
Your role is to:
- Help users identify and reframe negative thought patterns
- Guide them through evidence-based coping strategies
- Set achievable wellness goals
- Track progress over time
- Maintain professional boundaries

Always be:
- Supportive but structured
- Goal-oriented
- Evidence-based
- Professional yet warm
""",
            CoachPersona.FRIEND: """You are a warm, supportive friend who cares deeply about the user's wellbeing.
Your role is to:
- Listen actively and empathetically
- Validate feelings without judgment
- Offer gentle suggestions
- Be conversational and relatable
- Build trust through consistency

Always be:
- Warm and approachable
- Non-judgmental
- Conversational
- Genuinely caring
""",
            CoachPersona.EXPERT: """You are a mental health expert with deep knowledge of psychology and therapeutic techniques.
Your role is to:
- Provide psychoeducation
- Explain the science behind emotions and behaviors
- Recommend evidence-based interventions
- Help users understand their mental health
- Reference research when appropriate

Always be:
- Informative and educational
- Evidence-based
- Clear and precise
- Respectful of the user's intelligence
"""
        }

        context_additions = f"""

User Context:
- Name: {user_context.get('name', 'there')}
- Recent mood trend: {user_context.get('mood_trend', 'neutral')}
- Current stress level: {user_context.get('stress_level', 'moderate')}
- Previous topics: {', '.join(user_context.get('previous_topics', []))}

CRITICAL SAFETY PROTOCOLS:
1. If you detect ANY signs of self-harm, suicide ideation, or crisis:
   - Express immediate concern
   - Provide crisis hotline: 988 (Suicide & Crisis Lifeline)
   - Encourage professional help
   - DO NOT try to handle the crisis yourself
   - Flag the conversation for human review

2. Boundaries:
   - You are NOT a replacement for therapy or medical care
   - Encourage professional help for serious mental health issues
   - Do not diagnose mental health conditions
   - Do not prescribe medication or treatment plans

3. Privacy:
   - Remind users that conversations are confidential
   - Data is encrypted and HIPAA-compliant
   - Users can delete their data at any time

4. Response Guidelines:
   - Keep responses concise (2-4 paragraphs max)
   - Ask one question at a time
   - Use active listening techniques
   - Validate emotions before problem-solving
   - Provide actionable suggestions when appropriate
"""

        return base_prompts[persona] + context_additions

    async def chat(
        self,
        message: str,
        conversation_history: List[Dict[str, str]],
        persona: CoachPersona = CoachPersona.COACH,
        user_context: Optional[Dict] = None
    ) -> Tuple[str, Dict]:
        """
        Process a chat message and return response with metadata

        Args:
            message: User's message
            conversation_history: List of previous messages
            persona: Coach persona to use
            user_context: User context information

        Returns:
            Tuple of (response_text, metadata_dict)
        """
        if user_context is None:
            user_context = {}

        # Crisis detection
        crisis_level, crisis_keywords_found = self._detect_crisis(message)

        # If critical crisis detected, override response
        if crisis_level == CrisisLevel.CRITICAL:
            return self._generate_crisis_response(crisis_keywords_found)

        # Build messages for API
        system_prompt = self.get_system_prompt(persona, user_context)

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (limit to recent messages)
        recent_history = conversation_history[-settings.MAX_CONVERSATION_HISTORY:]
        messages.extend(recent_history)

        # Add current message
        messages.append({"role": "user", "content": message})

        # Generate response
        try:
            response = await self._call_llm(messages)

            # Analyze sentiment
            sentiment = self._analyze_sentiment(message)

            # Detect if intervention was suggested
            intervention = self._detect_intervention(response)

            # Extract topics
            topics = self._extract_topics(message)

            metadata = {
                'crisis_level': crisis_level.value,
                'crisis_keywords': crisis_keywords_found,
                'sentiment': sentiment,
                'intervention': intervention,
                'topics': topics,
                'persona': persona.value,
                'model_used': settings.AI_MODEL_PRIMARY
            }

            return response, metadata

        except Exception as e:
            # Fallback to Anthropic if OpenAI fails
            if settings.AI_MODEL_FALLBACK:
                return await self._call_llm_fallback(messages)
            raise e

    async def _call_llm(self, messages: List[Dict]) -> str:
        """Call primary LLM (OpenAI)"""
        response = self.openai_client.chat.completions.create(
            model=settings.AI_MODEL_PRIMARY,
            messages=messages,
            temperature=settings.AI_TEMPERATURE,
            max_tokens=settings.AI_MAX_TOKENS
        )
        return response.choices[0].message.content

    async def _call_llm_fallback(self, messages: List[Dict]) -> Tuple[str, Dict]:
        """Fallback to Anthropic Claude"""
        # Convert messages format
        system_msg = next((m['content'] for m in messages if m['role'] == 'system'), '')
        conversation = [m for m in messages if m['role'] != 'system']

        response = self.anthropic_client.messages.create(
            model=settings.AI_MODEL_FALLBACK,
            max_tokens=settings.AI_MAX_TOKENS,
            system=system_msg,
            messages=conversation
        )

        metadata = {
            'crisis_level': CrisisLevel.NONE.value,
            'model_used': settings.AI_MODEL_FALLBACK
        }

        return response.content[0].text, metadata

    def _detect_crisis(self, message: str) -> Tuple[CrisisLevel, List[str]]:
        """
        Detect crisis level in user message

        Returns:
            Tuple of (crisis_level, keywords_found)
        """
        message_lower = message.lower()
        keywords_found = []

        # Check for critical keywords first
        for keyword in self.crisis_keywords['critical']:
            if keyword in message_lower:
                keywords_found.append(keyword)

        if len(keywords_found) > 0:
            return CrisisLevel.CRITICAL, keywords_found

        # Check high risk
        for keyword in self.crisis_keywords['high']:
            if keyword in message_lower:
                keywords_found.append(keyword)

        if len(keywords_found) >= 2:
            return CrisisLevel.HIGH, keywords_found
        elif len(keywords_found) == 1:
            return CrisisLevel.MEDIUM, keywords_found

        # Check medium/low risk
        for keyword in self.crisis_keywords['medium']:
            if keyword in message_lower:
                keywords_found.append(keyword)

        if len(keywords_found) > 0:
            return CrisisLevel.MEDIUM, keywords_found

        for keyword in self.crisis_keywords['low']:
            if keyword in message_lower:
                keywords_found.append(keyword)

        if len(keywords_found) > 0:
            return CrisisLevel.LOW, keywords_found

        return CrisisLevel.NONE, []

    def _generate_crisis_response(self, keywords: List[str]) -> Tuple[str, Dict]:
        """Generate appropriate response for crisis situations"""
        response = f"""I'm really concerned about what you're sharing with me. Your safety is the most important thing right now.

Please reach out for immediate support:

🆘 **National Suicide & Crisis Lifeline: 988**
📞 Available 24/7
💬 Text "HELLO" to 741741 (Crisis Text Line)

If you're in immediate danger, please call 911 or go to your nearest emergency room.

You don't have to go through this alone. These trained professionals are available right now to help you.

I'm here to support you, but I'm not equipped to handle crisis situations. Please connect with a human professional who can give you the immediate help you deserve.

Would you like me to help you find additional resources in your area?"""

        metadata = {
            'crisis_level': CrisisLevel.CRITICAL.value,
            'crisis_keywords': keywords,
            'escalated': True,
            'requires_human_review': True
        }

        return response, metadata

    def _analyze_sentiment(self, message: str) -> float:
        """
        Analyze sentiment of message

        Returns:
            Float between -1 (very negative) and 1 (very positive)
        """
        # Simple keyword-based sentiment for now
        # TODO: Replace with proper sentiment analysis model
        positive_words = ['happy', 'good', 'great', 'better', 'excited', 'grateful']
        negative_words = ['sad', 'bad', 'worse', 'terrible', 'stressed', 'anxious', 'depressed']

        message_lower = message.lower()

        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)

        total = positive_count + negative_count
        if total == 0:
            return 0.0

        return (positive_count - negative_count) / total

    def _detect_intervention(self, response: str) -> Optional[str]:
        """Detect if response includes a specific intervention"""
        response_lower = response.lower()

        interventions = {
            'breathing': ['breath', 'breathing exercise', 'inhale', 'exhale'],
            'grounding': ['grounding', '5-4-3-2-1', 'senses'],
            'mindfulness': ['mindful', 'present moment', 'meditation'],
            'journaling': ['journal', 'write down', 'writing'],
            'progressive_relaxation': ['progressive relaxation', 'muscle relaxation']
        }

        for intervention_type, keywords in interventions.items():
            if any(keyword in response_lower for keyword in keywords):
                return intervention_type

        return None

    def _extract_topics(self, message: str) -> List[str]:
        """Extract main topics from message"""
        # Simple keyword extraction
        # TODO: Replace with proper topic modeling
        topics = []

        topic_keywords = {
            'work_stress': ['work', 'job', 'boss', 'deadline', 'project'],
            'relationships': ['relationship', 'partner', 'friend', 'family'],
            'anxiety': ['anxious', 'anxiety', 'worry', 'nervous'],
            'depression': ['depressed', 'depression', 'sad', 'hopeless'],
            'sleep': ['sleep', 'insomnia', 'tired', 'fatigue'],
            'burnout': ['burnout', 'exhausted', 'overwhelmed']
        }

        message_lower = message.lower()

        for topic, keywords in topic_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                topics.append(topic)

        return topics

    def get_intervention_content(self, intervention_type: InterventionType) -> Dict:
        """Get detailed content for a specific intervention"""

        interventions = {
            InterventionType.BREATHING: {
                'title': '4-7-8 Breathing Exercise',
                'description': 'A calming breathing technique to reduce anxiety and stress',
                'steps': [
                    'Find a comfortable seated position',
                    'Breathe in through your nose for 4 counts',
                    'Hold your breath for 7 counts',
                    'Exhale completely through your mouth for 8 counts',
                    'Repeat 3-4 times'
                ],
                'duration': '2-3 minutes',
                'benefits': ['Reduces anxiety', 'Lowers heart rate', 'Promotes relaxation']
            },
            InterventionType.GROUNDING: {
                'title': '5-4-3-2-1 Grounding Technique',
                'description': 'Bring yourself to the present moment using your senses',
                'steps': [
                    'Name 5 things you can see around you',
                    'Name 4 things you can touch',
                    'Name 3 things you can hear',
                    'Name 2 things you can smell',
                    'Name 1 thing you can taste'
                ],
                'duration': '3-5 minutes',
                'benefits': ['Reduces anxiety', 'Stops panic attacks', 'Returns focus to present']
            },
            InterventionType.MINDFULNESS: {
                'title': 'Mindful Awareness',
                'description': 'Simple mindfulness practice for daily stress',
                'steps': [
                    'Pause what you\'re doing',
                    'Take 3 deep breaths',
                    'Notice your thoughts without judgment',
                    'Bring awareness to your body',
                    'Choose your next action mindfully'
                ],
                'duration': '2-5 minutes',
                'benefits': ['Increases awareness', 'Reduces reactivity', 'Improves focus']
            },
            InterventionType.COGNITIVE_REFRAME: {
                'title': 'Cognitive Reframing',
                'description': 'Challenge and reframe negative thoughts',
                'steps': [
                    'Identify the negative thought',
                    'Ask: Is this thought 100% true?',
                    'What evidence supports/contradicts it?',
                    'What would you tell a friend?',
                    'Create a more balanced thought'
                ],
                'duration': '5-10 minutes',
                'benefits': ['Reduces negative thinking', 'Increases perspective', 'Improves mood']
            },
            InterventionType.JOURNALING: {
                'title': 'Reflective Journaling',
                'description': 'Process emotions through writing',
                'prompts': [
                    'What am I feeling right now?',
                    'What triggered these feelings?',
                    'What do I need in this moment?',
                    'What is one small thing I can do for myself?'
                ],
                'duration': '10-15 minutes',
                'benefits': ['Processes emotions', 'Increases self-awareness', 'Reduces stress']
            },
            InterventionType.PROGRESSIVE_RELAXATION: {
                'title': 'Progressive Muscle Relaxation',
                'description': 'Release physical tension through systematic relaxation',
                'steps': [
                    'Find a comfortable position',
                    'Tense your toes for 5 seconds, then release',
                    'Move up: calves, thighs, abdomen, chest',
                    'Continue: arms, shoulders, neck, face',
                    'Notice the relaxation in your body'
                ],
                'duration': '10-15 minutes',
                'benefits': ['Reduces physical tension', 'Improves sleep', 'Lowers stress']
            }
        }

        return interventions.get(intervention_type, {})
