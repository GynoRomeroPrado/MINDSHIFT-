"""
Configuration management for MindShift backend
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "MindShift"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # API Keys
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str
    PINECONE_API_KEY: Optional[str] = None

    # Database
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379"

    # Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ENCRYPTION_KEY: str

    # AI Coach Settings
    AI_MODEL_PRIMARY: str = "gpt-4-turbo-preview"
    AI_MODEL_FALLBACK: str = "claude-3-sonnet-20240229"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 1000
    MAX_CONVERSATION_HISTORY: int = 50

    # Voice Settings
    ENABLE_VOICE: bool = True
    WHISPER_MODEL: str = "base"

    # Crisis Detection
    ENABLE_CRISIS_DETECTION: bool = True
    CRISIS_KEYWORDS_THRESHOLD: int = 3
    CRISIS_HOTLINE: str = "988"
    ESCALATION_EMAIL: str = "crisis@mindshift.ai"

    # Burnout Detection
    BURNOUT_MODEL_PATH: str = "./ml_models/burnout_model.pkl"
    BURNOUT_PREDICTION_INTERVAL: int = 86400  # 24 hours in seconds
    BURNOUT_HIGH_RISK_THRESHOLD: int = 75

    # Analytics
    ANALYTICS_AGGREGATION_MINIMUM: int = 5  # Minimum group size for privacy

    # Integrations
    ENABLE_SLACK_INTEGRATION: bool = False
    ENABLE_TEAMS_INTEGRATION: bool = False
    SLACK_WEBHOOK_URL: Optional[str] = None

    # Monitoring
    SENTRY_DSN: Optional[str] = None
    ENABLE_PROMETHEUS: bool = True

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "https://app.mindshift.ai"]

    # Privacy
    DATA_RETENTION_DAYS: int = 90
    ENABLE_DIFFERENTIAL_PRIVACY: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
