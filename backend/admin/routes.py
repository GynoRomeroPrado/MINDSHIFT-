"""
Admin Portal API Routes
Provides administrative functions for managing the platform
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from database import get_db
from models import (
    User, Organization, Department, Conversation, Message,
    DailyCheckIn, BurnoutScore, Intervention, AnalyticsEvent,
    AuditLog, UserRole, ConversationStatus, BurnoutRiskLevel
)
from auth import check_admin_permission, check_hr_permission

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ==================== Pydantic Models ====================

class OrganizationStats(BaseModel):
    id: int
    name: str
    domain: str
    size: int
    plan_tier: str
    is_active: bool
    total_users: int
    active_users_30d: int
    avg_burnout_score: float
    high_risk_count: int
    total_conversations: int
    total_checkins: int
    created_at: datetime


class UserDetail(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    organization_name: str
    department_name: Optional[str]
    job_title: Optional[str]
    hire_date: Optional[datetime]
    is_active: bool
    last_login: Optional[datetime]
    total_conversations: int
    total_checkins: int
    latest_burnout_score: Optional[float]
    latest_burnout_risk: Optional[str]
    created_at: datetime


class SystemStats(BaseModel):
    total_organizations: int
    total_users: int
    active_users_7d: int
    active_users_30d: int
    total_conversations: int
    conversations_30d: int
    total_messages: int
    messages_30d: int
    total_checkins: int
    checkins_30d: int
    total_burnout_predictions: int
    predictions_30d: int
    crisis_detections_30d: int
    high_risk_users: int
    avg_burnout_score: float


# ==================== Organization Management ====================

@router.get("/organizations", response_model=List[OrganizationStats])
async def list_organizations(
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db),
    limit: int = Query(50, le=100),
    offset: int = 0,
    search: Optional[str] = None
):
    """
    List all organizations with stats (Admin only)
    """
    query = db.query(Organization)

    if search:
        query = query.filter(
            (Organization.name.ilike(f'%{search}%')) |
            (Organization.domain.ilike(f'%{search}%'))
        )

    organizations = query.limit(limit).offset(offset).all()

    result = []
    for org in organizations:
        # Get stats
        total_users = db.query(func.count(User.id)).filter(
            User.organization_id == org.id
        ).scalar()

        active_users_30d = db.query(func.count(User.id.distinct())).filter(
            and_(
                User.organization_id == org.id,
                User.last_login >= datetime.utcnow() - timedelta(days=30)
            )
        ).scalar()

        avg_score = db.query(func.avg(BurnoutScore.score)).join(User).filter(
            User.organization_id == org.id,
            BurnoutScore.prediction_date >= datetime.utcnow() - timedelta(days=7)
        ).scalar() or 0

        high_risk = db.query(func.count(BurnoutScore.id.distinct())).join(User).filter(
            User.organization_id == org.id,
            BurnoutScore.risk_level.in_([BurnoutRiskLevel.HIGH, BurnoutRiskLevel.CRITICAL]),
            BurnoutScore.prediction_date >= datetime.utcnow() - timedelta(days=7)
        ).scalar()

        total_convs = db.query(func.count(Conversation.id)).join(User).filter(
            User.organization_id == org.id
        ).scalar()

        total_checkins = db.query(func.count(DailyCheckIn.id)).join(User).filter(
            User.organization_id == org.id
        ).scalar()

        result.append(OrganizationStats(
            id=org.id,
            name=org.name,
            domain=org.domain,
            size=org.size or total_users,
            plan_tier=org.plan_tier or 'professional',
            is_active=org.is_active,
            total_users=total_users,
            active_users_30d=active_users_30d,
            avg_burnout_score=round(avg_score, 2),
            high_risk_count=high_risk,
            total_conversations=total_convs,
            total_checkins=total_checkins,
            created_at=org.created_at
        ))

    return result


@router.post("/organizations/{org_id}/deactivate")
async def deactivate_organization(
    org_id: int,
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db)
):
    """Deactivate an organization (Admin only)"""
    org = db.query(Organization).filter(Organization.id == org_id).first()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.is_active = False
    db.commit()

    # Log action
    log = AuditLog(
        user_id=current_user.id,
        action='deactivate_organization',
        resource_type='organization',
        resource_id=org_id,
        changes={'is_active': False}
    )
    db.add(log)
    db.commit()

    return {"status": "success", "message": f"Organization {org.name} deactivated"}


@router.post("/organizations/{org_id}/activate")
async def activate_organization(
    org_id: int,
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db)
):
    """Activate an organization (Admin only)"""
    org = db.query(Organization).filter(Organization.id == org_id).first()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.is_active = True
    db.commit()

    # Log action
    log = AuditLog(
        user_id=current_user.id,
        action='activate_organization',
        resource_type='organization',
        resource_id=org_id,
        changes={'is_active': True}
    )
    db.add(log)
    db.commit()

    return {"status": "success", "message": f"Organization {org.name} activated"}


# ==================== User Management ====================

@router.get("/users", response_model=List[UserDetail])
async def list_users(
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db),
    organization_id: Optional[int] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
    search: Optional[str] = None
):
    """
    List users with details (Admin only)
    """
    query = db.query(User)

    if organization_id:
        query = query.filter(User.organization_id == organization_id)

    if search:
        query = query.filter(
            (User.email.ilike(f'%{search}%')) |
            (User.full_name.ilike(f'%{search}%'))
        )

    users = query.limit(limit).offset(offset).all()

    result = []
    for user in users:
        # Get user stats
        total_convs = db.query(func.count(Conversation.id)).filter(
            Conversation.user_id == user.id
        ).scalar()

        total_checkins = db.query(func.count(DailyCheckIn.id)).filter(
            DailyCheckIn.user_id == user.id
        ).scalar()

        latest_score = db.query(BurnoutScore).filter(
            BurnoutScore.user_id == user.id
        ).order_by(BurnoutScore.prediction_date.desc()).first()

        result.append(UserDetail(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value if user.role else 'employee',
            organization_name=user.organization.name if user.organization else '',
            department_name=user.department.name if user.department else None,
            job_title=user.job_title,
            hire_date=user.hire_date,
            is_active=user.is_active,
            last_login=user.last_login,
            total_conversations=total_convs,
            total_checkins=total_checkins,
            latest_burnout_score=latest_score.score if latest_score else None,
            latest_burnout_risk=latest_score.risk_level.value if latest_score else None,
            created_at=user.created_at
        ))

    return result


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db)
):
    """
    Delete a user and all associated data (Admin only, GDPR)
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete associated data
    db.query(Message).filter(
        Message.conversation_id.in_(
            db.query(Conversation.id).filter(Conversation.user_id == user_id)
        )
    ).delete(synchronize_session=False)

    db.query(Conversation).filter(Conversation.user_id == user_id).delete()
    db.query(DailyCheckIn).filter(DailyCheckIn.user_id == user_id).delete()
    db.query(BurnoutScore).filter(BurnoutScore.user_id == user_id).delete()
    db.query(Intervention).filter(Intervention.user_id == user_id).delete()
    db.query(AnalyticsEvent).filter(AnalyticsEvent.user_id == user_id).delete()

    # Delete user
    db.delete(user)

    # Log action
    log = AuditLog(
        user_id=current_user.id,
        action='delete_user',
        resource_type='user',
        resource_id=user_id,
        changes={'email': user.email}
    )
    db.add(log)

    db.commit()

    return {"status": "success", "message": f"User {user.email} deleted"}


# ==================== System Statistics ====================

@router.get("/stats/system", response_model=SystemStats)
async def get_system_stats(
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db)
):
    """
    Get platform-wide statistics (Admin only)
    """
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    stats = SystemStats(
        total_organizations=db.query(func.count(Organization.id)).scalar(),
        total_users=db.query(func.count(User.id)).scalar(),

        active_users_7d=db.query(func.count(User.id.distinct())).filter(
            User.last_login >= seven_days_ago
        ).scalar(),

        active_users_30d=db.query(func.count(User.id.distinct())).filter(
            User.last_login >= thirty_days_ago
        ).scalar(),

        total_conversations=db.query(func.count(Conversation.id)).scalar(),

        conversations_30d=db.query(func.count(Conversation.id)).filter(
            Conversation.created_at >= thirty_days_ago
        ).scalar(),

        total_messages=db.query(func.count(Message.id)).scalar(),

        messages_30d=db.query(func.count(Message.id)).filter(
            Message.created_at >= thirty_days_ago
        ).scalar(),

        total_checkins=db.query(func.count(DailyCheckIn.id)).scalar(),

        checkins_30d=db.query(func.count(DailyCheckIn.id)).filter(
            DailyCheckIn.check_in_date >= thirty_days_ago
        ).scalar(),

        total_burnout_predictions=db.query(func.count(BurnoutScore.id)).scalar(),

        predictions_30d=db.query(func.count(BurnoutScore.id)).filter(
            BurnoutScore.prediction_date >= thirty_days_ago
        ).scalar(),

        crisis_detections_30d=db.query(func.count(Conversation.id)).filter(
            and_(
                Conversation.crisis_detected == True,
                Conversation.created_at >= thirty_days_ago
            )
        ).scalar(),

        high_risk_users=db.query(func.count(BurnoutScore.id.distinct())).filter(
            and_(
                BurnoutScore.risk_level.in_([BurnoutRiskLevel.HIGH, BurnoutRiskLevel.CRITICAL]),
                BurnoutScore.prediction_date >= seven_days_ago
            )
        ).scalar(),

        avg_burnout_score=db.query(func.avg(BurnoutScore.score)).filter(
            BurnoutScore.prediction_date >= seven_days_ago
        ).scalar() or 0
    )

    return stats


@router.get("/stats/usage")
async def get_usage_stats(
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db),
    days: int = Query(30, le=90)
):
    """
    Get daily usage statistics over time (Admin only)
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Daily active users
    daily_active = db.query(
        func.date(User.last_login).label('date'),
        func.count(User.id.distinct()).label('count')
    ).filter(
        User.last_login >= cutoff_date
    ).group_by(func.date(User.last_login)).all()

    # Daily conversations
    daily_convs = db.query(
        func.date(Conversation.created_at).label('date'),
        func.count(Conversation.id).label('count')
    ).filter(
        Conversation.created_at >= cutoff_date
    ).group_by(func.date(Conversation.created_at)).all()

    # Daily check-ins
    daily_checkins = db.query(
        func.date(DailyCheckIn.check_in_date).label('date'),
        func.count(DailyCheckIn.id).label('count')
    ).filter(
        DailyCheckIn.check_in_date >= cutoff_date
    ).group_by(func.date(DailyCheckIn.check_in_date)).all()

    return {
        'daily_active_users': [{'date': str(d[0]), 'count': d[1]} for d in daily_active],
        'daily_conversations': [{'date': str(d[0]), 'count': d[1]} for d in daily_convs],
        'daily_checkins': [{'date': str(d[0]), 'count': d[1]} for d in daily_checkins]
    }


# ==================== Crisis Management ====================

@router.get("/crises/recent")
async def get_recent_crises(
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db),
    limit: int = Query(20, le=100)
):
    """
    Get recent crisis detections (Admin only)
    """
    crises = db.query(Conversation).filter(
        Conversation.crisis_detected == True
    ).order_by(
        Conversation.escalated_at.desc()
    ).limit(limit).all()

    return [
        {
            'id': c.id,
            'user_id': c.user_id,
            'user_email': c.user.email,
            'user_name': c.user.full_name,
            'organization': c.user.organization.name,
            'crisis_keywords': c.crisis_keywords_found,
            'escalated_at': c.escalated_at,
            'status': c.status.value
        }
        for c in crises
    ]


# ==================== Audit Log ====================

@router.get("/audit-log")
async def get_audit_log(
    current_user: User = Depends(check_admin_permission),
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = 0,
    user_id: Optional[int] = None,
    action: Optional[str] = None
):
    """
    Get audit log entries (Admin only)
    """
    query = db.query(AuditLog)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    if action:
        query = query.filter(AuditLog.action == action)

    logs = query.order_by(
        AuditLog.created_at.desc()
    ).limit(limit).offset(offset).all()

    return [
        {
            'id': log.id,
            'user_id': log.user_id,
            'user_email': log.user.email if log.user else None,
            'action': log.action,
            'resource_type': log.resource_type,
            'resource_id': log.resource_id,
            'ip_address': log.ip_address,
            'changes': log.changes,
            'created_at': log.created_at
        }
        for log in logs
    ]
