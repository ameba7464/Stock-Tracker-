"""
Redis-based rate limiter using sliding window algorithm.

Implements:
- Per-tenant rate limiting
- Global API rate limiting
- Sliding window for accurate rate measurement
- Automatic cleanup of expired keys
"""

import time
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta

from redis import Redis
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from stock_tracker.cache.redis_cache import get_cache

logger = logging.getLogger(__name__)


class RedisRateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm.
    
    The sliding window algorithm provides more accurate rate limiting
    compared to fixed windows by tracking individual request timestamps.
    """
    
    def __init__(self, redis_client: Optional[Redis] = None):
        """
        Initialize rate limiter.
        
        Args:
            redis_client: Redis client instance (optional, will use get_cache if not provided)
        """
        self.cache = get_cache() if not redis_client else None
        self.redis_client = redis_client
        self._redis_available = None
    
    def _get_redis(self) -> Optional[Redis]:
        """Get Redis connection or None if unavailable."""
        if self.redis_client:
            return self.redis_client
        if self.cache and hasattr(self.cache, 'client'):
            return self.cache.client
        return None
    
    def _is_redis_available(self) -> bool:
        """Check if Redis is available."""
        if self._redis_available is not None:
            return self._redis_available
        
        redis = self._get_redis()
        if redis is None:
            self._redis_available = False
            return False
        
        try:
            redis.ping()
            self._redis_available = True
        except Exception:
            self._redis_available = False
        
        return self._redis_available
    
    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> Tuple[bool, int, int]:
        """
        Check if request is within rate limit using sliding window.
        
        Args:
            key: Unique identifier for the rate limit (e.g., "tenant:{uuid}")
            limit: Maximum number of requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (allowed, remaining, reset_time):
                - allowed: Whether request is allowed
                - remaining: Number of requests remaining in window
                - reset_time: Unix timestamp when window resets
        """
        # If Redis is unavailable, allow all requests
        if not self._is_redis_available():
            now = time.time()
            return (True, limit, int(now + window_seconds))
        
        redis = self._get_redis()
        now = time.time()
        window_start = now - window_seconds
        
        # Build sorted set key
        rate_limit_key = f"rate_limit:{key}"
        
        try:
            # Start pipeline for atomic operations
            pipe = redis.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(rate_limit_key, 0, window_start)
            
            # Count requests in current window
            pipe.zcard(rate_limit_key)
            
            # Execute pipeline
            results = pipe.execute()
            current_count = results[1]
            
            # Check if limit exceeded
            allowed = current_count < limit
            remaining = max(0, limit - current_count)
            
            if allowed:
                # Add current request to sorted set
                request_id = f"{now}:{id(redis)}"
                redis.zadd(rate_limit_key, {request_id: now})
                
                # Set expiration to cleanup automatically
                redis.expire(rate_limit_key, window_seconds + 1)
                
                remaining -= 1  # Account for current request
            
            # Calculate reset time (when oldest request expires)
            oldest_scores = redis.zrange(rate_limit_key, 0, 0, withscores=True)
            if oldest_scores:
                oldest_time = oldest_scores[0][1]
                reset_time = int(oldest_time + window_seconds)
            else:
                reset_time = int(now + window_seconds)
            
            return allowed, remaining, reset_time
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}", exc_info=True)
            # Fail open - allow request if Redis is down
            return True, limit, int(now + window_seconds)
    
    def get_rate_limit_info(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> dict:
        """
        Get current rate limit info without incrementing counter.
        
        Args:
            key: Unique identifier for the rate limit
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            dict with rate limit information
        """
        redis = self._get_redis()
        now = time.time()
        window_start = now - window_seconds
        
        rate_limit_key = f"rate_limit:{key}"
        
        try:
            # Count requests in current window
            current_count = redis.zcount(rate_limit_key, window_start, now)
            remaining = max(0, limit - current_count)
            
            # Get reset time
            oldest_scores = redis.zrange(rate_limit_key, 0, 0, withscores=True)
            if oldest_scores:
                oldest_time = oldest_scores[0][1]
                reset_time = int(oldest_time + window_seconds)
            else:
                reset_time = int(now + window_seconds)
            
            return {
                "limit": limit,
                "remaining": remaining,
                "reset": reset_time,
                "window_seconds": window_seconds,
            }
            
        except Exception as e:
            logger.error(f"Failed to get rate limit info: {e}")
            return {
                "limit": limit,
                "remaining": limit,
                "reset": int(now + window_seconds),
                "window_seconds": window_seconds,
            }
    
    def reset_rate_limit(self, key: str) -> bool:
        """
        Reset rate limit for a specific key.
        
        Args:
            key: Rate limit key to reset
            
        Returns:
            bool: True if reset successful
        """
        redis = self._get_redis()
        rate_limit_key = f"rate_limit:{key}"
        
        try:
            redis.delete(rate_limit_key)
            logger.info(f"Rate limit reset for key: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    
    Implements:
    - Per-tenant rate limits
    - Global API rate limits
    - Rate limit headers in responses
    - 429 Too Many Requests responses
    """
    
    def __init__(
        self,
        app,
        global_limit: int = 1000,
        global_window: int = 60,
        tenant_limit: int = 100,
        tenant_window: int = 60,
    ):
        """
        Initialize rate limit middleware.
        
        Args:
            app: FastAPI application
            global_limit: Max requests per window globally (default: 1000/min)
            global_window: Global window in seconds (default: 60)
            tenant_limit: Max requests per tenant per window (default: 100/min)
            tenant_window: Tenant window in seconds (default: 60)
        """
        super().__init__(app)
        self.limiter = RedisRateLimiter()
        
        self.global_limit = global_limit
        self.global_window = global_window
        self.tenant_limit = tenant_limit
        self.tenant_window = tenant_window
        
        logger.info(
            f"Rate limiter initialized: "
            f"global={global_limit}/{global_window}s, "
            f"tenant={tenant_limit}/{tenant_window}s"
        )
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting.
        
        Checks both global and tenant-specific rate limits.
        """
        # Skip rate limiting for health check endpoints
        if request.url.path in ["/health", "/metrics", "/api/health"]:
            return await call_next(request)
        
        # Check global rate limit
        global_key = "global"
        global_allowed, global_remaining, global_reset = self.limiter.check_rate_limit(
            global_key,
            self.global_limit,
            self.global_window,
        )
        
        if not global_allowed:
            logger.warning(f"Global rate limit exceeded from {request.client.host}")
            return self._rate_limit_response(
                global_remaining,
                global_reset,
                "Global rate limit exceeded",
            )
        
        # Check tenant-specific rate limit if tenant context exists
        tenant_id = None
        if hasattr(request.state, "tenant") and request.state.tenant:
            tenant_id = str(request.state.tenant.id)
            tenant_key = f"tenant:{tenant_id}"
            
            tenant_allowed, tenant_remaining, tenant_reset = self.limiter.check_rate_limit(
                tenant_key,
                self.tenant_limit,
                self.tenant_window,
            )
            
            if not tenant_allowed:
                logger.warning(f"Tenant rate limit exceeded: {tenant_id}")
                return self._rate_limit_response(
                    tenant_remaining,
                    tenant_reset,
                    "Tenant rate limit exceeded",
                )
            
            # Use tenant limits for response headers
            remaining = tenant_remaining
            reset_time = tenant_reset
        else:
            # Use global limits for response headers
            remaining = global_remaining
            reset_time = global_reset
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(
            self.tenant_limit if tenant_id else self.global_limit
        )
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        if tenant_id:
            response.headers["X-RateLimit-Tenant"] = tenant_id
        
        return response
    
    def _rate_limit_response(
        self,
        remaining: int,
        reset_time: int,
        message: str,
    ) -> Response:
        """
        Create 429 Too Many Requests response.
        
        Args:
            remaining: Requests remaining (should be 0)
            reset_time: Unix timestamp when limit resets
            message: Error message
            
        Returns:
            Response with 429 status
        """
        headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(reset_time),
            "Retry-After": str(max(0, reset_time - int(time.time()))),
        }
        
        return Response(
            content=f'{{"error": "{message}", "reset_at": {reset_time}}}',
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers=headers,
            media_type="application/json",
        )
