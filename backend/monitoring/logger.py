"""
Structured Logging Configuration
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter for structured logging
    """

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)

        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat()

        # Add level
        log_record['level'] = record.levelname

        # Add logger name
        log_record['logger'] = record.name

        # Add file and line info
        log_record['file'] = record.pathname
        log_record['line'] = record.lineno
        log_record['function'] = record.funcName

        # Add process/thread info
        log_record['process_id'] = record.process
        log_record['thread_id'] = record.thread

        # Add app info
        log_record['app'] = 'mindshift'
        log_record['environment'] = self.get_environment()

    @staticmethod
    def get_environment():
        """Get current environment"""
        try:
            from config import settings
            return settings.ENVIRONMENT
        except:
            return 'unknown'


def setup_logging(log_level: str = 'INFO', json_logs: bool = True):
    """
    Configure application logging

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to use JSON format (True) or plain text (False)
    """
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    if json_logs:
        # JSON formatter for production
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
    else:
        # Plain text formatter for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Log startup
    logger.info("Logging configured", extra={
        'log_level': log_level,
        'json_logs': json_logs
    })

    return logger


class StructuredLogger:
    """
    Wrapper for structured logging with context
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context = {}

    def add_context(self, **kwargs):
        """Add persistent context to all log messages"""
        self.context.update(kwargs)

    def clear_context(self):
        """Clear persistent context"""
        self.context.clear()

    def _log(self, level: str, message: str, **kwargs):
        """Internal log method with context"""
        extra = {**self.context, **kwargs}
        getattr(self.logger, level)(message, extra=extra)

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log('debug', message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log('info', message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log('warning', message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log('error', message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log('critical', message, **kwargs)

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        user_id: int = None
    ):
        """Log HTTP request"""
        self.info(
            "HTTP request",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2),
            user_id=user_id
        )

    def log_database_query(
        self,
        query_type: str,
        table: str,
        duration: float,
        rows_affected: int = None
    ):
        """Log database query"""
        self.debug(
            "Database query",
            query_type=query_type,
            table=table,
            duration_ms=round(duration * 1000, 4),
            rows_affected=rows_affected
        )

    def log_external_api_call(
        self,
        service: str,
        endpoint: str,
        method: str,
        status_code: int,
        duration: float
    ):
        """Log external API call"""
        self.info(
            "External API call",
            service=service,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2)
        )

    def log_coach_conversation(
        self,
        user_id: int,
        conversation_id: int,
        message_count: int,
        crisis_detected: bool = False
    ):
        """Log coach conversation"""
        self.info(
            "Coach conversation",
            user_id=user_id,
            conversation_id=conversation_id,
            message_count=message_count,
            crisis_detected=crisis_detected
        )

    def log_burnout_prediction(
        self,
        user_id: int,
        score: float,
        risk_level: str,
        prediction_time: float
    ):
        """Log burnout prediction"""
        self.info(
            "Burnout prediction",
            user_id=user_id,
            score=score,
            risk_level=risk_level,
            prediction_time_ms=round(prediction_time * 1000, 2)
        )

    def log_security_event(
        self,
        event_type: str,
        user_id: int = None,
        ip_address: str = None,
        details: str = None
    ):
        """Log security event"""
        self.warning(
            "Security event",
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            details=details
        )

    def log_error_with_trace(self, message: str, exception: Exception):
        """Log error with full traceback"""
        import traceback
        self.error(
            message,
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            traceback=traceback.format_exc()
        )


# Global logger instances
app_logger = StructuredLogger('mindshift.app')
api_logger = StructuredLogger('mindshift.api')
coach_logger = StructuredLogger('mindshift.coach')
ml_logger = StructuredLogger('mindshift.ml')
security_logger = StructuredLogger('mindshift.security')


# Request ID middleware context (for tracking requests across services)
class RequestContext:
    """Thread-local request context"""

    def __init__(self):
        import threading
        self._local = threading.local()

    def set_request_id(self, request_id: str):
        """Set request ID for current request"""
        self._local.request_id = request_id

    def get_request_id(self) -> str:
        """Get request ID for current request"""
        return getattr(self._local, 'request_id', None)

    def set_user_id(self, user_id: int):
        """Set user ID for current request"""
        self._local.user_id = user_id

    def get_user_id(self) -> int:
        """Get user ID for current request"""
        return getattr(self._local, 'user_id', None)


request_context = RequestContext()


# FastAPI middleware for request logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic request/response logging
    """

    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request_context.set_request_id(request_id)

        # Get user ID if available
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            request_context.set_user_id(user_id)

        # Start timer
        start_time = time.time()

        # Log request
        api_logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            user_id=user_id,
            client_ip=request.client.host if request.client else None
        )

        # Process request
        try:
            response: Response = await call_next(request)
            duration = time.time() - start_time

            # Log response
            api_logger.log_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration,
                user_id=user_id
            )

            # Add request ID to response headers
            response.headers['X-Request-ID'] = request_id

            return response

        except Exception as e:
            duration = time.time() - start_time

            # Log error
            api_logger.log_error_with_trace(
                "Request failed",
                e
            )

            # Re-raise
            raise
