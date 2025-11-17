"""
API routes for AI Coach
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database import get_db, get_redis
from models import User, Conversation, Message, ConversationStatus
from ai_coach.coach import AICoach, CoachPersona, InterventionType
from auth import get_current_user

router = APIRouter(prefix="/api/coach", tags=["AI Coach"])

# Pydantic models for request/response
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    persona: Optional[CoachPersona] = CoachPersona.COACH


class ChatResponse(BaseModel):
    response: str
    conversation_id: int
    metadata: dict


class ConversationResponse(BaseModel):
    id: int
    title: Optional[str]
    status: str
    message_count: int
    started_at: datetime
    coach_persona: Optional[str]


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    sentiment: Optional[float]


class InterventionResponse(BaseModel):
    type: str
    title: str
    description: str
    steps: Optional[List[str]] = None
    prompts: Optional[List[str]] = None
    duration: str
    benefits: List[str]


# Initialize AI Coach
ai_coach = AICoach()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis = Depends(get_redis)
):
    """
    Send a message to the AI coach and get a response
    """
    # Get or create conversation
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user.id
        ).first()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    else:
        # Create new conversation
        conversation = Conversation(
            user_id=current_user.id,
            coach_persona=request.persona.value,
            status=ConversationStatus.ACTIVE
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Get conversation history
    messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.created_at).all()

    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in messages
    ]

    # Get user context
    user_context = {
        'name': current_user.full_name or 'there',
        'mood_trend': _get_mood_trend(current_user.id, db),
        'stress_level': _get_stress_level(current_user.id, db),
        'previous_topics': _get_previous_topics(conversation.id, db)
    }

    # Get AI response
    response_text, metadata = await ai_coach.chat(
        message=request.message,
        conversation_history=conversation_history,
        persona=request.persona,
        user_context=user_context
    )

    # Save user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
        sentiment=metadata.get('sentiment'),
        keywords=metadata.get('topics')
    )
    db.add(user_message)

    # Save assistant response
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=response_text,
        intervention_triggered=metadata.get('intervention')
    )
    db.add(assistant_message)

    # Update conversation
    conversation.message_count += 2
    conversation.updated_at = datetime.utcnow()

    # Check for crisis
    if metadata.get('crisis_level') in ['critical', 'high']:
        conversation.crisis_detected = True
        conversation.crisis_keywords_found = metadata.get('crisis_keywords')
        conversation.status = ConversationStatus.CRISIS

        # Trigger alert (implement notification system)
        # await _send_crisis_alert(current_user, conversation, metadata)

    db.commit()

    return ChatResponse(
        response=response_text,
        conversation_id=conversation.id,
        metadata=metadata
    )


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20,
    offset: int = 0
):
    """
    Get user's conversation history
    """
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(
        Conversation.updated_at.desc()
    ).limit(limit).offset(offset).all()

    return [
        ConversationResponse(
            id=conv.id,
            title=conv.title,
            status=conv.status.value,
            message_count=conv.message_count,
            started_at=conv.started_at,
            coach_persona=conv.coach_persona
        )
        for conv in conversations
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get messages from a specific conversation
    """
    # Verify conversation belongs to user
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()

    return [
        MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at,
            sentiment=msg.sentiment
        )
        for msg in messages
    ]


@router.get("/interventions/{intervention_type}", response_model=InterventionResponse)
async def get_intervention(
    intervention_type: InterventionType,
    current_user: User = Depends(get_current_user)
):
    """
    Get details for a specific intervention/exercise
    """
    content = ai_coach.get_intervention_content(intervention_type)

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intervention not found"
        )

    return InterventionResponse(
        type=intervention_type.value,
        **content
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a conversation (GDPR right to deletion)
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Delete messages
    db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).delete()

    # Delete conversation
    db.delete(conversation)
    db.commit()

    return {"status": "deleted", "conversation_id": conversation_id}


# Helper functions
def _get_mood_trend(user_id: int, db: Session) -> str:
    """Get user's recent mood trend"""
    from models import DailyCheckIn
    from datetime import timedelta

    recent_checkins = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.check_in_date >= datetime.utcnow() - timedelta(days=7)
    ).order_by(DailyCheckIn.check_in_date.desc()).limit(7).all()

    if not recent_checkins:
        return "neutral"

    avg_mood = sum(c.mood_score for c in recent_checkins if c.mood_score) / len(recent_checkins)

    if avg_mood >= 7:
        return "positive"
    elif avg_mood <= 4:
        return "negative"
    else:
        return "neutral"


def _get_stress_level(user_id: int, db: Session) -> str:
    """Get user's current stress level"""
    from models import DailyCheckIn
    from datetime import timedelta

    recent_checkin = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.check_in_date >= datetime.utcnow() - timedelta(days=1)
    ).order_by(DailyCheckIn.check_in_date.desc()).first()

    if not recent_checkin or not recent_checkin.stress_score:
        return "moderate"

    if recent_checkin.stress_score >= 8:
        return "high"
    elif recent_checkin.stress_score <= 4:
        return "low"
    else:
        return "moderate"


def _get_previous_topics(conversation_id: int, db: Session) -> List[str]:
    """Get main topics discussed in conversation"""
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id,
        Message.keywords.isnot(None)
    ).all()

    all_topics = []
    for msg in messages:
        if msg.keywords:
            all_topics.extend(msg.keywords)

    # Return unique topics
    return list(set(all_topics))
