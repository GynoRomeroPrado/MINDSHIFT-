"""
Tests for AI Coach system
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from ai_coach.coach import AICoach, CoachPersona, CrisisLevel


@pytest.fixture
def coach():
    """Create AICoach instance for testing"""
    return AICoach()


@pytest.fixture
def user_context():
    """Sample user context"""
    return {
        'name': 'John Doe',
        'mood_trend': 'negative',
        'stress_level': 'high',
        'previous_topics': ['work_stress', 'anxiety']
    }


class TestCrisisDetection:
    """Test crisis detection functionality"""

    def test_detect_critical_crisis(self, coach):
        """Test detection of critical crisis keywords"""
        message = "I want to kill myself"
        level, keywords = coach._detect_crisis(message)

        assert level == CrisisLevel.CRITICAL
        assert len(keywords) > 0
        assert 'kill myself' in keywords

    def test_detect_high_crisis(self, coach):
        """Test detection of high-risk keywords"""
        message = "I've been thinking about self harm lately"
        level, keywords = coach._detect_crisis(message)

        assert level in [CrisisLevel.HIGH, CrisisLevel.MEDIUM]
        assert len(keywords) > 0

    def test_detect_no_crisis(self, coach):
        """Test no crisis in normal message"""
        message = "I had a good day at work today"
        level, keywords = coach._detect_crisis(message)

        assert level == CrisisLevel.NONE
        assert len(keywords) == 0

    def test_crisis_response_format(self, coach):
        """Test crisis response contains required information"""
        keywords = ['suicide', 'kill myself']
        response, metadata = coach._generate_crisis_response(keywords)

        assert '988' in response  # Crisis hotline number
        assert 'crisis' in response.lower()
        assert metadata['crisis_level'] == CrisisLevel.CRITICAL.value
        assert metadata['escalated'] is True


class TestSentimentAnalysis:
    """Test sentiment analysis"""

    def test_positive_sentiment(self, coach):
        """Test positive message sentiment"""
        message = "I'm feeling great and excited about my new project"
        sentiment = coach._analyze_sentiment(message)

        assert sentiment > 0

    def test_negative_sentiment(self, coach):
        """Test negative message sentiment"""
        message = "I'm feeling terrible and stressed about everything"
        sentiment = coach._analyze_sentiment(message)

        assert sentiment < 0

    def test_neutral_sentiment(self, coach):
        """Test neutral message sentiment"""
        message = "The meeting is at 3pm today"
        sentiment = coach._analyze_sentiment(message)

        assert sentiment == 0.0


class TestTopicExtraction:
    """Test topic extraction"""

    def test_work_stress_topic(self, coach):
        """Test work stress topic extraction"""
        message = "My boss is giving me too many deadlines and I can't keep up"
        topics = coach._extract_topics(message)

        assert 'work_stress' in topics

    def test_anxiety_topic(self, coach):
        """Test anxiety topic extraction"""
        message = "I'm feeling really anxious and worried about tomorrow"
        topics = coach._extract_topics(message)

        assert 'anxiety' in topics

    def test_multiple_topics(self, coach):
        """Test extraction of multiple topics"""
        message = "I'm depressed about my relationship and can't sleep"
        topics = coach._extract_topics(message)

        assert len(topics) >= 2
        assert 'depression' in topics or 'relationships' in topics


class TestInterventionDetection:
    """Test intervention detection in responses"""

    def test_breathing_intervention(self, coach):
        """Test detection of breathing exercise"""
        response = "Let's try a breathing exercise. Take a deep breath in..."
        intervention = coach._detect_intervention(response)

        assert intervention == 'breathing'

    def test_grounding_intervention(self, coach):
        """Test detection of grounding technique"""
        response = "Try the 5-4-3-2-1 grounding technique..."
        intervention = coach._detect_intervention(response)

        assert intervention == 'grounding'

    def test_no_intervention(self, coach):
        """Test no intervention in regular response"""
        response = "That sounds challenging. Can you tell me more?"
        intervention = coach._detect_intervention(response)

        assert intervention is None


class TestSystemPrompts:
    """Test system prompt generation"""

    def test_coach_persona_prompt(self, coach, user_context):
        """Test coach persona system prompt"""
        prompt = coach.get_system_prompt(CoachPersona.COACH, user_context)

        assert 'professional' in prompt.lower()
        assert 'CBT' in prompt or 'DBT' in prompt
        assert user_context['name'] in prompt

    def test_friend_persona_prompt(self, coach, user_context):
        """Test friend persona system prompt"""
        prompt = coach.get_system_prompt(CoachPersona.FRIEND, user_context)

        assert 'friend' in prompt.lower()
        assert 'supportive' in prompt.lower()

    def test_expert_persona_prompt(self, coach, user_context):
        """Test expert persona system prompt"""
        prompt = coach.get_system_prompt(CoachPersona.EXPERT, user_context)

        assert 'expert' in prompt.lower()
        assert 'evidence-based' in prompt.lower()

    def test_safety_protocols_in_prompt(self, coach, user_context):
        """Test that safety protocols are included"""
        prompt = coach.get_system_prompt(CoachPersona.COACH, user_context)

        assert '988' in prompt  # Crisis hotline
        assert 'crisis' in prompt.lower()
        assert 'professional help' in prompt.lower()


@pytest.mark.asyncio
class TestChatFunctionality:
    """Test main chat functionality"""

    @patch('ai_coach.coach.openai.OpenAI')
    async def test_normal_chat_flow(self, mock_openai, coach, user_context):
        """Test normal chat without crisis"""
        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="I understand you're feeling stressed."))]
        mock_client.chat.completions.create.return_value = mock_response
        coach.openai_client = mock_client

        message = "I'm feeling a bit stressed today"
        conversation_history = []

        response, metadata = await coach.chat(
            message=message,
            conversation_history=conversation_history,
            persona=CoachPersona.COACH,
            user_context=user_context
        )

        assert response == "I understand you're feeling stressed."
        assert metadata['crisis_level'] == CrisisLevel.NONE.value
        assert 'sentiment' in metadata
        assert 'topics' in metadata

    async def test_crisis_override(self, coach, user_context):
        """Test that crisis messages get special handling"""
        message = "I want to end my life"
        conversation_history = []

        response, metadata = await coach.chat(
            message=message,
            conversation_history=conversation_history,
            persona=CoachPersona.COACH,
            user_context=user_context
        )

        assert '988' in response
        assert metadata['crisis_level'] == CrisisLevel.CRITICAL.value
        assert metadata['escalated'] is True


class TestInterventionContent:
    """Test intervention content retrieval"""

    def test_breathing_intervention_content(self, coach):
        """Test breathing intervention content"""
        from ai_coach.coach import InterventionType
        content = coach.get_intervention_content(InterventionType.BREATHING)

        assert 'title' in content
        assert 'steps' in content
        assert 'benefits' in content
        assert len(content['steps']) > 0

    def test_grounding_intervention_content(self, coach):
        """Test grounding intervention content"""
        from ai_coach.coach import InterventionType
        content = coach.get_intervention_content(InterventionType.GROUNDING)

        assert '5-4-3-2-1' in content['title']
        assert len(content['steps']) == 5  # Five senses

    def test_all_interventions_available(self, coach):
        """Test all intervention types have content"""
        from ai_coach.coach import InterventionType

        for intervention_type in InterventionType:
            content = coach.get_intervention_content(intervention_type)
            assert content is not None
            assert 'title' in content
            assert 'description' in content


# Integration tests would require actual API keys
@pytest.mark.integration
@pytest.mark.asyncio
class TestRealAPIIntegration:
    """Integration tests with real APIs (requires API keys)"""

    async def test_real_openai_call(self, coach):
        """Test actual OpenAI API call"""
        # Skip if no API key
        import os
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("No OpenAI API key available")

        message = "Hello, how are you?"
        conversation_history = []
        user_context = {'name': 'Test User'}

        response, metadata = await coach.chat(
            message=message,
            conversation_history=conversation_history,
            user_context=user_context
        )

        assert len(response) > 0
        assert metadata['model_used'] == 'gpt-4-turbo-preview'
