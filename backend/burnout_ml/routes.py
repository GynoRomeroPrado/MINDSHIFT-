"""
API routes for Burnout ML system
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from pydantic import BaseModel
from datetime import datetime, timedelta

from database import get_db
from models import User, BurnoutScore, BurnoutRiskLevel, DailyCheckIn, Message, Intervention
from burnout_ml.predictor import BurnoutPredictor
from auth import get_current_user, check_hr_permission
from config import settings

router = APIRouter(prefix="/api/burnout", tags=["Burnout Prediction"])

# Initialize predictor
predictor = BurnoutPredictor(model_path=settings.BURNOUT_MODEL_PATH)


class BurnoutPredictionResponse(BaseModel):
    score: float
    risk_level: str
    confidence: float
    trajectory: str
    contributing_factors: List[dict]
    prediction_date: datetime


class BurnoutHistoryResponse(BaseModel):
    predictions: List[BurnoutPredictionResponse]
    average_score: float
    trend: str


class InterventionTriggerResponse(BaseModel):
    triggered: bool
    intervention_type: str
    reason: str
    resources: List[dict]


@router.post("/predict", response_model=BurnoutPredictionResponse)
async def predict_burnout(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate burnout prediction for current user

    Requires user consent for data collection
    """
    # Check consent
    if not current_user.consent_data_collection:
        raise HTTPException(
            status_code=403,
            detail="Data collection consent required for burnout prediction"
        )

    # Gather all user data
    user_data = await _gather_user_data(current_user.id, db)

    # Generate prediction
    prediction = predictor.predict(user_data)

    # Save prediction to database
    burnout_score = BurnoutScore(
        user_id=current_user.id,
        score=prediction['score'],
        risk_level=BurnoutRiskLevel(prediction['risk_level']),
        confidence=prediction['confidence'],
        factors=prediction['contributing_factors'],
        trajectory=prediction['trajectory'],
        features=prediction['features'],
        model_version="1.0.0",
        prediction_date=datetime.utcnow()
    )
    db.add(burnout_score)
    db.commit()

    # Trigger interventions if needed (run in background)
    background_tasks.add_task(
        _trigger_interventions,
        current_user.id,
        prediction,
        db
    )

    return BurnoutPredictionResponse(
        score=prediction['score'],
        risk_level=prediction['risk_level'],
        confidence=prediction['confidence'],
        trajectory=prediction['trajectory'],
        contributing_factors=prediction['contributing_factors'],
        prediction_date=datetime.utcnow()
    )


@router.get("/history", response_model=BurnoutHistoryResponse)
async def get_burnout_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = 90
):
    """
    Get user's burnout prediction history
    """
    since_date = datetime.utcnow() - timedelta(days=days)

    predictions = db.query(BurnoutScore).filter(
        BurnoutScore.user_id == current_user.id,
        BurnoutScore.prediction_date >= since_date
    ).order_by(BurnoutScore.prediction_date.desc()).all()

    if not predictions:
        return BurnoutHistoryResponse(
            predictions=[],
            average_score=50.0,
            trend="stable"
        )

    # Calculate average
    avg_score = sum(p.score for p in predictions) / len(predictions)

    # Determine trend
    if len(predictions) >= 2:
        recent_avg = sum(p.score for p in predictions[:5]) / min(5, len(predictions))
        older_avg = sum(p.score for p in predictions[-5:]) / min(5, len(predictions[-5:]))

        if recent_avg < older_avg - 10:
            trend = "improving"
        elif recent_avg > older_avg + 10:
            trend = "worsening"
        else:
            trend = "stable"
    else:
        trend = "stable"

    return BurnoutHistoryResponse(
        predictions=[
            BurnoutPredictionResponse(
                score=p.score,
                risk_level=p.risk_level.value,
                confidence=p.confidence or 0.7,
                trajectory=p.trajectory or "stable",
                contributing_factors=p.factors or [],
                prediction_date=p.prediction_date
            )
            for p in predictions
        ],
        average_score=avg_score,
        trend=trend
    )


@router.get("/analytics/team", response_model=dict)
async def get_team_analytics(
    current_user: User = Depends(check_hr_permission),
    db: Session = Depends(get_db),
    department_id: int = None
):
    """
    Get aggregated team burnout analytics (HR/Manager only)

    Privacy: Only shows aggregated data for groups of 5+ employees
    """
    # Build query
    query = db.query(BurnoutScore).join(User)

    # Filter by department if specified
    if department_id:
        query = query.filter(User.department_id == department_id)
    else:
        # Show organization-wide if HR
        query = query.filter(User.organization_id == current_user.organization_id)

    # Get recent predictions (last 7 days)
    recent_date = datetime.utcnow() - timedelta(days=7)

    # Use subquery to get latest prediction per user
    latest_predictions = db.query(
        BurnoutScore.user_id,
        func.max(BurnoutScore.prediction_date).label('max_date')
    ).filter(
        BurnoutScore.prediction_date >= recent_date
    ).group_by(BurnoutScore.user_id).subquery()

    predictions = query.join(
        latest_predictions,
        (BurnoutScore.user_id == latest_predictions.c.user_id) &
        (BurnoutScore.prediction_date == latest_predictions.c.max_date)
    ).all()

    # Privacy check
    if len(predictions) < settings.ANALYTICS_AGGREGATION_MINIMUM:
        raise HTTPException(
            status_code=403,
            detail=f"Insufficient data for privacy (minimum {settings.ANALYTICS_AGGREGATION_MINIMUM} employees required)"
        )

    # Calculate aggregated metrics
    total_employees = len(predictions)
    avg_score = sum(p.score for p in predictions) / total_employees

    risk_distribution = {
        'low': len([p for p in predictions if p.risk_level == BurnoutRiskLevel.LOW]),
        'moderate': len([p for p in predictions if p.risk_level == BurnoutRiskLevel.MODERATE]),
        'high': len([p for p in predictions if p.risk_level == BurnoutRiskLevel.HIGH]),
        'critical': len([p for p in predictions if p.risk_level == BurnoutRiskLevel.CRITICAL])
    }

    # Aggregate contributing factors
    all_factors = []
    for p in predictions:
        if p.factors:
            all_factors.extend([f['category'] for f in p.factors])

    factor_counts = {}
    for factor in all_factors:
        factor_counts[factor] = factor_counts.get(factor, 0) + 1

    top_factors = sorted(
        [{'category': k, 'count': v} for k, v in factor_counts.items()],
        key=lambda x: x['count'],
        reverse=True
    )[:5]

    return {
        'total_employees': total_employees,
        'average_score': round(avg_score, 2),
        'risk_distribution': risk_distribution,
        'top_contributing_factors': top_factors,
        'high_risk_count': risk_distribution['high'] + risk_distribution['critical'],
        'timestamp': datetime.utcnow().isoformat()
    }


@router.post("/check-in")
async def daily_check_in(
    mood: int,
    energy: int,
    stress: int,
    sleep: int,
    workload: int,
    notes: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit daily wellbeing check-in

    All scores should be 1-10 scale
    """
    # Validate scores
    for score in [mood, energy, stress, sleep, workload]:
        if score < 1 or score > 10:
            raise HTTPException(
                status_code=400,
                detail="All scores must be between 1 and 10"
            )

    # Create check-in
    check_in = DailyCheckIn(
        user_id=current_user.id,
        mood_score=mood,
        energy_score=energy,
        stress_score=stress,
        sleep_quality=sleep,
        workload_score=workload,
        notes=notes,
        check_in_date=datetime.utcnow()
    )

    db.add(check_in)
    db.commit()

    return {
        'status': 'success',
        'message': 'Check-in recorded',
        'check_in_date': check_in.check_in_date
    }


# Helper functions
async def _gather_user_data(user_id: int, db: Session) -> dict:
    """Gather all available data for a user"""
    user = db.query(User).filter(User.id == user_id).first()

    # Get check-ins
    checkins_7d = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.check_in_date >= datetime.utcnow() - timedelta(days=7)
    ).all()

    checkins_30d = db.query(DailyCheckIn).filter(
        DailyCheckIn.user_id == user_id,
        DailyCheckIn.check_in_date >= datetime.utcnow() - timedelta(days=30)
    ).all()

    # Get conversation data
    messages_30d = db.query(Message).join(
        Message.conversation
    ).filter(
        Message.conversation.has(user_id=user_id),
        Message.created_at >= datetime.utcnow() - timedelta(days=30)
    ).all()

    avg_sentiment = (
        sum(m.sentiment for m in messages_30d if m.sentiment)
        / len([m for m in messages_30d if m.sentiment])
    ) if messages_30d else 0

    crisis_keywords = sum(
        len(m.keywords or [])
        for m in messages_30d
        if m.keywords and any('crisis' in str(k).lower() for k in m.keywords)
    )

    return {
        'hire_date': user.hire_date,
        'days_since_role_change': 180,  # TODO: Track role changes

        'communication': {
            'email': {
                'count_7d': 0,  # TODO: Integrate with email
                'count_30d': 0,
                'after_hours_ratio': 0,
                'weekend_ratio': 0,
                'avg_response_time_hours': 0
            },
            'messaging': {
                'count_7d': 0,  # TODO: Integrate with Slack/Teams
                'avg_response_time_minutes': 0,
                'avg_sentiment': 0,
                'negative_ratio': 0
            },
            'meetings': {
                'hours_per_week': 0,  # TODO: Integrate with calendar
                'back_to_back_ratio': 0,
                'overlaps_per_week': 0
            }
        },

        'work_behavior': {
            'avg_login_hour': 9,  # TODO: Track login patterns
            'avg_logout_hour': 17,
            'avg_work_hours': 8,
            'work_hours_variance': 1,
            'weekend_hours_avg': 0,
            'sessions_after_10pm': 0,
            'vacation_days_ytd': 0,  # TODO: Integrate with HR system
            'days_since_last_vacation': 60,
            'sick_days_last_30d': 0,
            'task_completion_rate': 0.8,
            'deadline_miss_rate': 0.1,
            'active_projects': 3,
            'avg_focus_time_hours': 4,
            'avg_context_switches': 20
        },

        'self_report': {
            'checkins_7d': [
                {
                    'mood': c.mood_score,
                    'energy': c.energy_score,
                    'stress': c.stress_score,
                    'sleep': c.sleep_quality,
                    'workload': c.workload_score
                }
                for c in checkins_7d
            ],
            'checkins_30d': [
                {
                    'mood': c.mood_score,
                    'energy': c.energy_score,
                    'stress': c.stress_score,
                    'sleep': c.sleep_quality,
                    'workload': c.workload_score
                }
                for c in checkins_30d
            ],
            'coach_sessions_count': len(set(m.conversation_id for m in messages_30d)),
            'crisis_keywords_count': crisis_keywords,
            'avg_sentiment': avg_sentiment
        },

        'social': {
            'team_size': 5,  # TODO: Calculate from department
            'manager_1on1_per_month': 2,
            'peer_interactions_weekly': 10,
            'manager_response_time_hours': 24,
            'manager_tenure_months': 12,
            'peer_feedback_score': 7
        }
    }


async def _trigger_interventions(user_id: int, prediction: dict, db: Session):
    """Trigger appropriate interventions based on burnout score"""
    score = prediction['score']
    risk_level = prediction['risk_level']

    interventions_triggered = []

    # Self-help resources (40-60)
    if 40 <= score < 60:
        intervention = Intervention(
            user_id=user_id,
            type='self_help',
            trigger='burnout_score',
            trigger_value=score,
            title='Self-Care Resources',
            description='Your burnout risk is moderate. Here are some resources to help.',
            resources=[
                {'type': 'article', 'title': 'Managing Workplace Stress', 'url': '/resources/stress'},
                {'type': 'exercise', 'title': 'Breathing Techniques', 'url': '/exercises/breathing'},
                {'type': 'video', 'title': 'Work-Life Balance Tips', 'url': '/videos/balance'}
            ]
        )
        interventions_triggered.append(intervention)

    # Coach outreach (60-75)
    elif 60 <= score < 75:
        intervention = Intervention(
            user_id=user_id,
            type='coach',
            trigger='burnout_score',
            trigger_value=score,
            title='Talk to Your AI Coach',
            description='Your burnout risk is elevated. Consider talking to your AI coach.',
            resources=[
                {'type': 'action', 'title': 'Start Coaching Session', 'url': '/coach/new'}
            ]
        )
        interventions_triggered.append(intervention)

    # Manager alert (75-85)
    elif 75 <= score < 85:
        intervention = Intervention(
            user_id=user_id,
            type='manager',
            trigger='burnout_score',
            trigger_value=score,
            title='Manager Support Recommended',
            description='Your burnout risk is high. We recommend connecting with your manager.',
            resources=[
                {'type': 'action', 'title': 'Request 1-on-1', 'url': '/manager/request-1on1'},
                {'type': 'coach', 'title': 'Prepare for Conversation', 'url': '/coach/manager-prep'}
            ]
        )
        interventions_triggered.append(intervention)

        # TODO: Notify manager (with user permission)

    # HR intervention (85+)
    elif score >= 85:
        intervention = Intervention(
            user_id=user_id,
            type='hr',
            trigger='burnout_score',
            trigger_value=score,
            title='Urgent: HR Support Available',
            description='Your burnout risk is critical. Please connect with HR for support.',
            resources=[
                {'type': 'action', 'title': 'Contact HR', 'url': '/hr/contact'},
                {'type': 'emergency', 'title': 'Crisis Resources', 'url': '/crisis'}
            ]
        )
        interventions_triggered.append(intervention)

        # TODO: Alert HR team

    # Save all interventions
    for intervention in interventions_triggered:
        db.add(intervention)

    db.commit()
