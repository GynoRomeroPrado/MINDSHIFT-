"""
SQLAlchemy ORM models for MindShift
"""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    ForeignKey, Text, JSON, Enum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class UserRole(str, enum.Enum):
    """User role types"""
    EMPLOYEE = "employee"
    MANAGER = "manager"
    HR = "hr"
    ADMIN = "admin"


class ConversationStatus(str, enum.Enum):
    """Conversation status types"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    CRISIS = "crisis"


class BurnoutRiskLevel(str, enum.Enum):
    """Burnout risk levels"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class Organization(Base):
    """Organization model"""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=False)
    size = Column(Integer)  # Number of employees
    industry = Column(String(100))
    plan_tier = Column(String(50))  # essentials, professional, enterprise
    is_active = Column(Boolean, default=True)
    settings = Column(JSON)  # Organization-specific settings
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="organization")
    departments = relationship("Department", back_populates="organization")


class Department(Base):
    """Department/Team model"""
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    parent_department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="departments")
    users = relationship("User", back_populates="department")
    parent = relationship("Department", remote_side=[id], backref="sub_departments")


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(Enum(UserRole), default=UserRole.EMPLOYEE)

    # Profile
    job_title = Column(String(255))
    hire_date = Column(DateTime(timezone=True))
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")

    # Preferences
    preferences = Column(JSON)  # Communication preferences, coach persona, etc.

    # Privacy settings
    consent_data_collection = Column(Boolean, default=False)
    consent_analytics = Column(Boolean, default=False)

    # Status
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="users")
    department = relationship("Department", back_populates="users")
    conversations = relationship("Conversation", back_populates="user")
    check_ins = relationship("DailyCheckIn", back_populates="user")
    burnout_scores = relationship("BurnoutScore", back_populates="user")
    interventions = relationship("Intervention", back_populates="user")


class Conversation(Base):
    """AI Coach conversation model"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255))
    status = Column(Enum(ConversationStatus), default=ConversationStatus.ACTIVE)
    coach_persona = Column(String(50))  # coach, friend, expert

    # Conversation metadata
    message_count = Column(Integer, default=0)
    sentiment_score = Column(Float)  # Average sentiment
    topics = Column(JSON)  # Main topics discussed

    # Crisis detection
    crisis_detected = Column(Boolean, default=False)
    crisis_keywords_found = Column(JSON)
    escalated_at = Column(DateTime(timezone=True))

    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    """Chat message model"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)

    # Analytics
    sentiment = Column(Float)  # -1 to 1
    keywords = Column(JSON)
    intervention_triggered = Column(String(100))  # breathing, grounding, etc.

    # Voice
    is_voice = Column(Boolean, default=False)
    audio_url = Column(String(500))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class DailyCheckIn(Base):
    """Daily wellbeing check-in model"""
    __tablename__ = "daily_checkins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Scores (1-10 scale)
    mood_score = Column(Integer)
    energy_score = Column(Integer)
    stress_score = Column(Integer)
    sleep_quality = Column(Integer)
    workload_score = Column(Integer)

    # Optional text
    notes = Column(Text)

    # Timestamps
    check_in_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="check_ins")


class BurnoutScore(Base):
    """Burnout prediction scores"""
    __tablename__ = "burnout_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Prediction
    score = Column(Float, nullable=False)  # 0-100
    risk_level = Column(Enum(BurnoutRiskLevel), nullable=False)
    confidence = Column(Float)  # 0-1

    # Contributing factors
    factors = Column(JSON)  # List of contributing factors
    trajectory = Column(String(20))  # improving, stable, worsening

    # Feature values used
    features = Column(JSON)

    # Model metadata
    model_version = Column(String(50))

    # Timestamps
    prediction_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="burnout_scores")


class Intervention(Base):
    """Intervention tracking"""
    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Intervention details
    type = Column(String(50), nullable=False)  # self_help, coach, manager, hr, crisis
    trigger = Column(String(100))  # burnout_score, crisis_detected, etc.
    trigger_value = Column(Float)

    # Content
    title = Column(String(255))
    description = Column(Text)
    resources = Column(JSON)  # Links, exercises, etc.

    # Outcome
    completed = Column(Boolean, default=False)
    effectiveness_rating = Column(Integer)  # 1-5
    user_feedback = Column(Text)

    # Timestamps
    triggered_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="interventions")


class AnalyticsEvent(Base):
    """Analytics event tracking"""
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)

    # Event details
    event_type = Column(String(100), nullable=False, index=True)
    event_data = Column(JSON)

    # Privacy - individual events are anonymized after aggregation
    anonymized = Column(Boolean, default=False)

    # Timestamps
    event_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """Audit log for compliance"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Action details
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(Integer)

    # Request details
    ip_address = Column(String(45))
    user_agent = Column(String(500))

    # Changes
    changes = Column(JSON)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
