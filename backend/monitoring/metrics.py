"""
Prometheus Metrics and Monitoring
"""
from prometheus_client import Counter, Histogram, Gauge, Summary
from functools import wraps
import time
from typing import Callable
import logging

logger = logging.getLogger(__name__)


# ====================
# API Metrics
# ====================

# HTTP Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

http_request_size_bytes = Summary(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint']
)

http_response_size_bytes = Summary(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint']
)


# ====================
# AI Coach Metrics
# ====================

coach_conversations_total = Counter(
    'coach_conversations_total',
    'Total coach conversations started',
    ['persona']
)

coach_messages_total = Counter(
    'coach_messages_total',
    'Total messages exchanged with coach',
    ['role', 'persona']
)

coach_response_time_seconds = Histogram(
    'coach_response_time_seconds',
    'AI coach response time in seconds',
    ['persona', 'model'],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

crisis_detections_total = Counter(
    'crisis_detections_total',
    'Total crisis detections',
    ['level']  # none, low, medium, high, critical
)

interventions_triggered_total = Counter(
    'interventions_triggered_total',
    'Total interventions triggered',
    ['type']  # breathing, grounding, mindfulness, etc.
)


# ====================
# Burnout ML Metrics
# ====================

burnout_predictions_total = Counter(
    'burnout_predictions_total',
    'Total burnout predictions',
    ['risk_level']  # low, moderate, high, critical
)

burnout_prediction_time_seconds = Histogram(
    'burnout_prediction_time_seconds',
    'Time to generate burnout prediction',
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)

burnout_score_distribution = Histogram(
    'burnout_score_distribution',
    'Distribution of burnout scores',
    buckets=(0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)
)


# ====================
# User Engagement Metrics
# ====================

daily_checkins_total = Counter(
    'daily_checkins_total',
    'Total daily check-ins completed'
)

active_users_gauge = Gauge(
    'active_users',
    'Number of active users',
    ['timeframe']  # daily, weekly, monthly
)

user_mood_average = Gauge(
    'user_mood_average',
    'Average user mood score',
    ['timeframe']
)

user_stress_average = Gauge(
    'user_stress_average',
    'Average user stress score',
    ['timeframe']
)


# ====================
# System Metrics
# ====================

database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Database query duration',
    ['operation'],  # select, insert, update, delete
    buckets=(0.001, 0.01, 0.1, 0.5, 1.0, 2.0)
)

cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']  # redis, memory
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

external_api_calls_total = Counter(
    'external_api_calls_total',
    'Total external API calls',
    ['service', 'status']  # service: openai, anthropic, etc.
)

external_api_duration_seconds = Histogram(
    'external_api_duration_seconds',
    'External API call duration',
    ['service'],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)


# ====================
# Business Metrics
# ====================

organizations_total = Gauge(
    'organizations_total',
    'Total number of organizations'
)

employees_monitored_total = Gauge(
    'employees_monitored_total',
    'Total employees being monitored'
)

high_risk_employees_gauge = Gauge(
    'high_risk_employees',
    'Number of high-risk employees',
    ['organization_id']
)


# ====================
# Decorators for Automatic Instrumentation
# ====================

def track_time(metric: Histogram, labels: dict = None):
    """
    Decorator to track execution time

    Usage:
        @track_time(http_request_duration_seconds, {'method': 'GET', 'endpoint': '/api/health'})
        def my_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def count_calls(metric: Counter, labels: dict = None):
    """
    Decorator to count function calls

    Usage:
        @count_calls(http_requests_total, {'method': 'POST', 'endpoint': '/api/chat'})
        def my_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                if labels:
                    metric.labels(**labels).inc()
                else:
                    metric.inc()
                return result
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                if labels:
                    metric.labels(**labels).inc()
                else:
                    metric.inc()
                return result
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ====================
# Helper Functions
# ====================

def record_coach_message(role: str, persona: str):
    """Record a coach message"""
    coach_messages_total.labels(role=role, persona=persona).inc()


def record_burnout_prediction(score: float, risk_level: str):
    """Record a burnout prediction"""
    burnout_predictions_total.labels(risk_level=risk_level).inc()
    burnout_score_distribution.observe(score)


def record_crisis_detection(level: str):
    """Record a crisis detection"""
    crisis_detections_total.labels(level=level).inc()


def record_intervention(intervention_type: str):
    """Record an intervention"""
    interventions_triggered_total.labels(type=intervention_type).inc()


def record_api_call(service: str, status: str, duration: float):
    """Record external API call"""
    external_api_calls_total.labels(service=service, status=status).inc()
    external_api_duration_seconds.labels(service=service).observe(duration)


def update_active_users(timeframe: str, count: int):
    """Update active users gauge"""
    active_users_gauge.labels(timeframe=timeframe).set(count)


def update_high_risk_count(organization_id: int, count: int):
    """Update high risk employees count"""
    high_risk_employees_gauge.labels(organization_id=str(organization_id)).set(count)
