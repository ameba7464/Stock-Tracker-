"""
Rate limiting decorators for individual endpoints.

Allows fine-grained control over rate limits for specific routes.
"""

import time
import logging
from typing import Optional, Callable
from functools import wraps

from fastapi import HTTPException, status, Request

from .redis_rate_limiter import RedisRateLimiter

logger = logging.getLogger(__name__)


def rate_limit(
    limit: int,
    window_seconds: int = 60,
    key_func: Optional[Callable[[Request], str]] = None,
):
    """
    Decorator for rate limiting specific endpoints.
    
    Usage:
        @router.get("/expensive-operation")
        @rate_limit(limit=10, window_seconds=60)
        async def expensive_operation(request: Request):
            return {"result": "success"}
    
    Args:
        limit: Maximum requests allowed in window
        window_seconds: Time window in seconds
        key_func: Optional function to generate rate limit key from request
                 Default: uses tenant_id if available, else client IP
    
    Returns:
        Decorated function
    """
    limiter = RedisRateLimiter()
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find Request object in args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request and "request" in kwargs:
                request = kwargs["request"]
            
            if not request:
                logger.warning(
                    f"Rate limit decorator on {func.__name__} but no Request found"
                )
                return await func(*args, **kwargs)
            
            # Generate rate limit key
            if key_func:
                key = key_func(request)
            else:
                # Default: use tenant_id or client IP
                if hasattr(request.state, "tenant") and request.state.tenant:
                    key = f"endpoint:{func.__name__}:tenant:{request.state.tenant.id}"
                else:
                    key = f"endpoint:{func.__name__}:ip:{request.client.host}"
            
            # Check rate limit
            allowed, remaining, reset_time = limiter.check_rate_limit(
                key,
                limit,
                window_seconds,
            )
            
            if not allowed:
                retry_after = max(0, reset_time - int(time.time()))
                logger.warning(
                    f"Rate limit exceeded for {func.__name__}: key={key}"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "limit": limit,
                        "window_seconds": window_seconds,
                        "reset_at": reset_time,
                    },
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time),
                        "Retry-After": str(retry_after),
                    },
                )
            
            # Execute endpoint
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def rate_limit_by_tenant(limit: int, window_seconds: int = 60):
    """
    Rate limit by tenant ID.
    
    Usage:
        @router.post("/sync")
        @rate_limit_by_tenant(limit=5, window_seconds=300)
        async def trigger_sync(request: Request):
            return {"status": "started"}
    """
    def key_func(request: Request) -> str:
        if hasattr(request.state, "tenant") and request.state.tenant:
            return f"tenant:{request.state.tenant.id}"
        return f"ip:{request.client.host}"
    
    return rate_limit(limit, window_seconds, key_func)


def rate_limit_by_user(limit: int, window_seconds: int = 60):
    """
    Rate limit by user ID.
    
    Usage:
        @router.get("/user/profile")
        @rate_limit_by_user(limit=100, window_seconds=60)
        async def get_profile(request: Request):
            return request.state.user
    """
    def key_func(request: Request) -> str:
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.id}"
        return f"ip:{request.client.host}"
    
    return rate_limit(limit, window_seconds, key_func)


def rate_limit_by_ip(limit: int, window_seconds: int = 60):
    """
    Rate limit by client IP address.
    
    Usage:
        @router.post("/auth/login")
        @rate_limit_by_ip(limit=5, window_seconds=300)
        async def login(request: Request):
            return {"token": "..."}
    """
    def key_func(request: Request) -> str:
        return f"ip:{request.client.host}"
    
    return rate_limit(limit, window_seconds, key_func)
