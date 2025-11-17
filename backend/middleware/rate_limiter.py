"""
Rate Limiting Middleware
Protects API endpoints from abuse and DoS attacks
"""
import time
import hashlib
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
import redis
from functools import wraps

from config import settings
from database import get_redis


class RateLimitExceeded(HTTPException):
    """Rate limit exceeded exception"""
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Please try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )


class RateLimiter:
    """
    Redis-based rate limiter using Token Bucket algorithm
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        requests_per_minute: int = 60,
        burst: int = 10
    ):
        self.redis = redis_client
        self.requests_per_minute = requests_per_minute
        self.burst = burst
        self.rate_per_second = requests_per_minute / 60.0

    def is_allowed(self, key: str) -> tuple[bool, int]:
        """
        Check if request is allowed using Token Bucket algorithm

        Args:
            key: Unique identifier for the rate limit (e.g., user_id, ip_address)

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        now = time.time()
        bucket_key = f"rate_limit:{key}"

        # Get current bucket state
        pipe = self.redis.pipeline()
        pipe.get(f"{bucket_key}:tokens")
        pipe.get(f"{bucket_key}:last_update")
        tokens_str, last_update_str = pipe.execute()

        # Initialize bucket if it doesn't exist
        if tokens_str is None:
            tokens = float(self.burst)
            last_update = now
        else:
            tokens = float(tokens_str)
            last_update = float(last_update_str) if last_update_str else now

        # Calculate time passed and add tokens
        time_passed = now - last_update
        tokens = min(
            float(self.burst),
            tokens + time_passed * self.rate_per_second
        )

        # Check if we have enough tokens
        if tokens >= 1.0:
            # Consume one token
            tokens -= 1.0

            # Update bucket
            pipe = self.redis.pipeline()
            pipe.setex(f"{bucket_key}:tokens", 60, str(tokens))
            pipe.setex(f"{bucket_key}:last_update", 60, str(now))
            pipe.execute()

            return True, 0
        else:
            # Calculate retry_after
            tokens_needed = 1.0 - tokens
            retry_after = int(tokens_needed / self.rate_per_second) + 1

            return False, retry_after

    def get_remaining(self, key: str) -> int:
        """Get remaining requests allowed"""
        bucket_key = f"rate_limit:{key}"
        tokens_str = self.redis.get(f"{bucket_key}:tokens")

        if tokens_str is None:
            return self.burst

        return max(0, int(float(tokens_str)))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting
    """

    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.redis_client = redis_client or get_redis()
        self.rate_limiter = RateLimiter(
            self.redis_client,
            requests_per_minute=settings.RATE_LIMIT_PER_MINUTE
        )

        # Paths to exclude from rate limiting
        self.excluded_paths = [
            "/health",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json"
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""
        # Skip rate limiting for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Get identifier for rate limiting
        identifier = self._get_identifier(request)

        # Check rate limit
        is_allowed, retry_after = self.rate_limiter.is_allowed(identifier)

        if not is_allowed:
            raise RateLimitExceeded(retry_after=retry_after)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = self.rate_limiter.get_remaining(identifier)
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)

        return response

    def _get_identifier(self, request: Request) -> str:
        """
        Get unique identifier for rate limiting

        Priority:
        1. User ID (from auth)
        2. API Key (if present)
        3. IP Address (fallback)
        """
        # Try to get user ID from request state (set by auth middleware)
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"

        # Try to get API key from headers
        api_key = request.headers.get('X-API-Key')
        if api_key:
            # Hash API key for privacy
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            return f"apikey:{key_hash}"

        # Fallback to IP address
        client_ip = request.client.host if request.client else 'unknown'

        # Check for forwarded IP (behind proxy)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            client_ip = forwarded_for.split(',')[0].strip()

        return f"ip:{client_ip}"


def rate_limit(
    requests_per_minute: Optional[int] = None,
    burst: Optional[int] = None
):
    """
    Decorator for rate limiting specific endpoints

    Usage:
        @router.get("/expensive-operation")
        @rate_limit(requests_per_minute=10)
        async def expensive_operation():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if request is None:
                # Try to find in kwargs
                request = kwargs.get('request')

            if request is None:
                # Can't rate limit without request object
                return await func(*args, **kwargs)

            # Create rate limiter with custom limits
            redis_client = get_redis()
            limiter = RateLimiter(
                redis_client,
                requests_per_minute=requests_per_minute or settings.RATE_LIMIT_PER_MINUTE,
                burst=burst or 10
            )

            # Get identifier
            middleware = RateLimitMiddleware(None)
            identifier = middleware._get_identifier(request)

            # Check rate limit
            is_allowed, retry_after = limiter.is_allowed(f"custom:{identifier}")

            if not is_allowed:
                raise RateLimitExceeded(retry_after=retry_after)

            # Call function
            return await func(*args, **kwargs)

        return wrapper
    return decorator


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts based on system load
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.base_rate = settings.RATE_LIMIT_PER_MINUTE

    def get_current_rate(self) -> int:
        """
        Get current rate limit based on system load

        Returns:
            Current requests per minute allowed
        """
        # Get system metrics
        active_requests = self._get_active_requests()
        error_rate = self._get_error_rate()

        # Adjust rate based on load
        if error_rate > 0.1:  # More than 10% errors
            # Reduce rate by 50%
            return int(self.base_rate * 0.5)
        elif active_requests > 1000:  # High load
            # Reduce rate by 25%
            return int(self.base_rate * 0.75)
        else:
            # Normal rate
            return self.base_rate

    def _get_active_requests(self) -> int:
        """Get number of active requests"""
        # This would be implemented based on your metrics system
        # For now, return 0
        return 0

    def _get_error_rate(self) -> float:
        """Get current error rate"""
        # This would be implemented based on your metrics system
        # For now, return 0
        return 0.0


# IP-based rate limiting for public endpoints
class IPRateLimiter:
    """
    Simple IP-based rate limiter for public endpoints
    """

    def __init__(self, redis_client: redis.Redis, requests_per_hour: int = 100):
        self.redis = redis_client
        self.requests_per_hour = requests_per_hour

    def is_allowed(self, ip_address: str) -> bool:
        """
        Check if IP is allowed

        Args:
            ip_address: IP address to check

        Returns:
            True if allowed, False otherwise
        """
        key = f"ip_rate_limit:{ip_address}"
        current_count = self.redis.get(key)

        if current_count is None:
            # First request from this IP
            self.redis.setex(key, 3600, "1")  # 1 hour expiry
            return True

        current_count = int(current_count)

        if current_count >= self.requests_per_hour:
            return False

        # Increment count
        self.redis.incr(key)
        return True

    def get_remaining(self, ip_address: str) -> int:
        """Get remaining requests for IP"""
        key = f"ip_rate_limit:{ip_address}"
        current_count = self.redis.get(key)

        if current_count is None:
            return self.requests_per_hour

        return max(0, self.requests_per_hour - int(current_count))


# Cost-based rate limiting (for expensive operations)
class CostBasedRateLimiter:
    """
    Rate limiter that assigns costs to different operations
    """

    def __init__(self, redis_client: redis.Redis, budget_per_hour: int = 1000):
        self.redis = redis_client
        self.budget_per_hour = budget_per_hour

    def consume(self, key: str, cost: int) -> tuple[bool, int]:
        """
        Try to consume cost from budget

        Args:
            key: Identifier
            cost: Cost of operation

        Returns:
            Tuple of (is_allowed, remaining_budget)
        """
        budget_key = f"cost_budget:{key}"
        current_budget = self.redis.get(budget_key)

        if current_budget is None:
            # Initialize budget
            self.redis.setex(budget_key, 3600, str(self.budget_per_hour - cost))
            return True, self.budget_per_hour - cost

        current_budget = int(current_budget)

        if current_budget < cost:
            return False, current_budget

        # Deduct cost
        new_budget = self.redis.decrby(budget_key, cost)
        return True, int(new_budget)
