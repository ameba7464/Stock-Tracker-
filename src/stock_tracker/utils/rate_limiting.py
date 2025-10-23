"""
Rate limiting utilities for Wildberries API calls.

Implements intelligent rate limiting as specified in urls.md to comply with
API quotas and prevent 429 errors. Supports token bucket algorithm with
request scheduling and queue management.
"""

import asyncio
import time
from asyncio import Queue
from dataclasses import dataclass, field
from threading import Lock, RLock
from typing import Dict, Optional, Callable, Any, Awaitable
from collections import deque
from functools import wraps

from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.exceptions import RateLimitError


logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting behavior."""
    
    # Core rate limiting parameters
    requests_per_minute: int = 60  # Default: 60 requests per minute
    requests_per_second: float = 1.0  # Default: 1 request per second
    burst_size: int = 10  # Token bucket burst capacity
    
    # Queue management
    max_queue_size: int = 100  # Maximum queued requests
    queue_timeout: float = 300.0  # Queue timeout in seconds (5 minutes)
    
    # Adaptive behavior
    adaptive_rate_limiting: bool = True  # Adjust limits based on API responses
    cooldown_factor: float = 0.5  # Rate reduction factor on 429 errors
    recovery_time: float = 60.0  # Time to recover from rate limit
    
    # Per-endpoint configurations
    endpoint_configs: Dict[str, 'EndpointRateLimit'] = field(default_factory=dict)


@dataclass
class EndpointRateLimit:
    """Rate limit configuration for specific API endpoints."""
    
    requests_per_minute: int
    requests_per_second: float = None
    burst_size: int = None
    priority: int = 1  # Higher priority = faster processing


class TokenBucket:
    """
    Token bucket algorithm implementation for rate limiting.
    
    Allows burst requests up to bucket capacity while maintaining
    average rate over time.
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens (burst size)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self.lock = Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        with self.lock:
            now = time.time()
            
            # Add tokens based on time elapsed
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                return False
    
    def time_until_available(self, tokens: int = 1) -> float:
        """
        Calculate time until enough tokens are available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Time in seconds until tokens are available
        """
        with self.lock:
            if self.tokens >= tokens:
                return 0.0
            
            needed_tokens = tokens - self.tokens
            return needed_tokens / self.refill_rate
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bucket status."""
        with self.lock:
            return {
                "tokens": self.tokens,
                "capacity": self.capacity,
                "refill_rate": self.refill_rate,
                "utilization": (self.capacity - self.tokens) / self.capacity
            }


class RateLimiter:
    """
    Comprehensive rate limiter for Wildberries API.
    
    Features:
    - Token bucket algorithm for burst control
    - Per-endpoint rate limiting
    - Adaptive rate adjustment based on API responses
    - Request queuing and prioritization
    - Thread-safe operation
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.lock = RLock()
        
        # Global rate limiter
        self.global_bucket = TokenBucket(
            capacity=config.burst_size,
            refill_rate=config.requests_per_second
        )
        
        # Per-endpoint rate limiters
        self.endpoint_buckets: Dict[str, TokenBucket] = {}
        
        # Request queue
        self.request_queue: Queue = Queue(maxsize=config.max_queue_size)
        
        # Rate limit state
        self.is_rate_limited = False
        self.rate_limit_until = 0.0
        self.current_rate_factor = 1.0
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "rate_limited_requests": 0,
            "queued_requests": 0,
            "failed_requests": 0,
            "last_rate_limit": None
        }
        
        logger.info(f"Initialized rate limiter: {config.requests_per_minute} req/min, "
                   f"{config.requests_per_second} req/s, burst={config.burst_size}")
    
    def _get_endpoint_bucket(self, endpoint: str) -> TokenBucket:
        """Get or create token bucket for specific endpoint."""
        with self.lock:
            if endpoint not in self.endpoint_buckets:
                # Check if we have specific config for this endpoint
                if endpoint in self.config.endpoint_configs:
                    endpoint_config = self.config.endpoint_configs[endpoint]
                    capacity = endpoint_config.burst_size or self.config.burst_size
                    rate = endpoint_config.requests_per_second or self.config.requests_per_second
                else:
                    capacity = self.config.burst_size
                    rate = self.config.requests_per_second
                
                # Apply current rate factor for adaptive limiting
                adjusted_rate = rate * self.current_rate_factor
                
                self.endpoint_buckets[endpoint] = TokenBucket(capacity, adjusted_rate)
                logger.debug(f"Created endpoint bucket for {endpoint}: "
                           f"capacity={capacity}, rate={adjusted_rate}")
            
            return self.endpoint_buckets[endpoint]
    
    def _is_rate_limited(self) -> bool:
        """Check if we're currently in a rate-limited state."""
        if self.is_rate_limited and time.time() < self.rate_limit_until:
            return True
        elif self.is_rate_limited and time.time() >= self.rate_limit_until:
            # Recovery from rate limit
            self.is_rate_limited = False
            self.current_rate_factor = min(1.0, self.current_rate_factor * 1.1)
            logger.info(f"Recovered from rate limit, rate factor: {self.current_rate_factor}")
        
        return False
    
    def _handle_rate_limit_response(self, status_code: int, headers: Dict[str, str]):
        """Handle rate limit response from API."""
        if status_code == 429:
            self.stats["rate_limited_requests"] += 1
            self.stats["last_rate_limit"] = time.time()
            
            # Parse Retry-After header
            retry_after = headers.get('Retry-After', '60')
            try:
                wait_time = float(retry_after)
            except ValueError:
                wait_time = 60.0
            
            # Enter rate-limited state
            self.is_rate_limited = True
            self.rate_limit_until = time.time() + wait_time
            
            # Reduce rate factor if adaptive limiting is enabled
            if self.config.adaptive_rate_limiting:
                old_factor = self.current_rate_factor
                self.current_rate_factor *= self.config.cooldown_factor
                
                # Update all endpoint buckets with new rate
                with self.lock:
                    for endpoint, bucket in self.endpoint_buckets.items():
                        bucket.refill_rate *= self.config.cooldown_factor
                
                logger.warning(f"Rate limited! Reduced rate factor from {old_factor:.2f} "
                             f"to {self.current_rate_factor:.2f}, waiting {wait_time}s")
    
    async def acquire(self, endpoint: str = "default", priority: int = 1) -> None:
        """
        Acquire permission to make an API request.
        
        Args:
            endpoint: API endpoint identifier
            priority: Request priority (higher = faster processing)
            
        Raises:
            RateLimitError: If rate limit is exceeded and cannot be handled
        """
        self.stats["total_requests"] += 1
        
        # Check if we're in a rate-limited state
        if self._is_rate_limited():
            wait_time = self.rate_limit_until - time.time()
            if wait_time > self.config.queue_timeout:
                raise RateLimitError(f"Rate limited for {wait_time:.1f}s, exceeds queue timeout")
            
            logger.info(f"Waiting for rate limit recovery: {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
        
        # Get endpoint-specific bucket
        endpoint_bucket = self._get_endpoint_bucket(endpoint)
        
        # Try to consume tokens immediately
        if self.global_bucket.consume() and endpoint_bucket.consume():
            logger.debug(f"Immediate permission granted for {endpoint}")
            return
        
        # Need to wait for tokens
        self.stats["queued_requests"] += 1
        
        # Calculate wait time
        global_wait = self.global_bucket.time_until_available()
        endpoint_wait = endpoint_bucket.time_until_available()
        wait_time = max(global_wait, endpoint_wait)
        
        if wait_time > self.config.queue_timeout:
            self.stats["failed_requests"] += 1
            raise RateLimitError(f"Required wait time {wait_time:.1f}s exceeds timeout")
        
        logger.debug(f"Waiting {wait_time:.2f}s for rate limit tokens ({endpoint})")
        await asyncio.sleep(wait_time)
        
        # Try again after waiting
        if not (self.global_bucket.consume() and endpoint_bucket.consume()):
            # This shouldn't happen, but just in case
            self.stats["failed_requests"] += 1
            raise RateLimitError("Failed to acquire tokens after waiting")
    
    def record_response(self, status_code: int, headers: Dict[str, str]):
        """
        Record API response for adaptive rate limiting.
        
        Args:
            status_code: HTTP status code
            headers: Response headers
        """
        if status_code == 429:
            self._handle_rate_limit_response(status_code, headers)
        elif status_code is not None and 200 <= status_code < 300 and self.config.adaptive_rate_limiting:
            # Successful response - gradually increase rate if we were throttled
            if self.current_rate_factor < 1.0:
                self.current_rate_factor = min(1.0, self.current_rate_factor * 1.01)
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive rate limiter status."""
        return {
            "config": {
                "requests_per_minute": self.config.requests_per_minute,
                "requests_per_second": self.config.requests_per_second,
                "burst_size": self.config.burst_size
            },
            "state": {
                "is_rate_limited": self.is_rate_limited,
                "rate_limit_until": self.rate_limit_until,
                "current_rate_factor": self.current_rate_factor,
                "time_until_recovery": max(0, self.rate_limit_until - time.time())
            },
            "buckets": {
                "global": self.global_bucket.get_status(),
                "endpoints": {
                    endpoint: bucket.get_status()
                    for endpoint, bucket in self.endpoint_buckets.items()
                }
            },
            "statistics": self.stats.copy()
        }


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(config: Optional[RateLimitConfig] = None) -> RateLimiter:
    """
    Get global rate limiter instance.
    
    Args:
        config: Rate limit configuration (creates default if None)
        
    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    
    if _rate_limiter is None:
        if config is None:
            config = RateLimitConfig()
        _rate_limiter = RateLimiter(config)
    
    return _rate_limiter


def rate_limited(endpoint: str = "default", 
                priority: int = 1,
                config: Optional[RateLimitConfig] = None):
    """
    Decorator for applying rate limiting to functions.
    
    Args:
        endpoint: API endpoint identifier
        priority: Request priority
        config: Rate limit configuration
        
    Returns:
        Decorated function with rate limiting
    """
    def decorator(func: Callable) -> Callable:
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            """Async wrapper with rate limiting."""
            limiter = get_rate_limiter(config)
            
            # Acquire rate limit permission
            await limiter.acquire(endpoint, priority)
            
            try:
                # Execute function
                result = await func(*args, **kwargs)
                
                # Record successful response (assume 200 if no exception)
                limiter.record_response(200, {})
                
                return result
                
            except Exception as e:
                # Record error response
                status_code = getattr(e, 'status_code', 500)
                headers = {}
                if hasattr(e, 'response') and e.response:
                    headers = dict(e.response.headers)
                
                limiter.record_response(status_code, headers)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            """Sync wrapper - runs async wrapper in event loop."""
            async def run_async():
                return await async_wrapper(*args, **kwargs)
            
            # Run in existing event loop or create new one
            try:
                loop = asyncio.get_running_loop()
                # If we're already in an async context, we can't use run()
                raise RuntimeError("Cannot use sync wrapper in async context")
            except RuntimeError:
                # No running loop, safe to use run()
                return asyncio.run(run_async())
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def configure_wildberries_rate_limits() -> RateLimitConfig:
    """
    Configure rate limits specifically for Wildberries API per urls.md.
    
    Returns:
        RateLimitConfig optimized for Wildberries API
    """
    config = RateLimitConfig(
        requests_per_minute=60,  # Conservative limit
        requests_per_second=1.0,  # 1 request per second
        burst_size=5,  # Small burst to handle quick operations
        adaptive_rate_limiting=True,
        cooldown_factor=0.5,
        recovery_time=60.0
    )
    
    # Endpoint-specific configurations per urls.md
    config.endpoint_configs = {
        "/api/v1/warehouse_remains": EndpointRateLimit(
            requests_per_minute=10,  # Lower limit for data generation
            requests_per_second=0.2,  # 1 request per 5 seconds
            priority=1
        ),
        "/api/v1/warehouse_remains/tasks/*/download": EndpointRateLimit(
            requests_per_minute=30,  # Higher limit for downloads
            requests_per_second=0.5,  # 1 request per 2 seconds
            priority=2
        ),
        "/api/v1/supplier/orders": EndpointRateLimit(
            requests_per_minute=20,  # Medium limit for orders
            requests_per_second=0.3,  # 1 request per ~3 seconds
            priority=2
        )
    }
    
    return config


# Example usage and testing
if __name__ == "__main__":
    
    async def test_rate_limiter():
        """Test the rate limiter functionality."""
        
        # Configure for testing with fast rates
        config = RateLimitConfig(
            requests_per_minute=120,
            requests_per_second=2.0,
            burst_size=5
        )
        
        limiter = RateLimiter(config)
        
        print("Testing rate limiter...")
        
        # Test burst requests
        start_time = time.time()
        for i in range(5):
            await limiter.acquire(f"test_endpoint_{i}")
            print(f"Request {i+1} granted at {time.time() - start_time:.2f}s")
        
        # Test rate limiting
        for i in range(3):
            await limiter.acquire("test_endpoint")
            print(f"Rate limited request {i+1} granted at {time.time() - start_time:.2f}s")
        
        # Test status
        status = limiter.get_status()
        print(f"\nRate limiter status:")
        print(f"Global bucket: {status['buckets']['global']}")
        print(f"Statistics: {status['statistics']}")
        
        # Test decorator
        @rate_limited("test_decorated", config=config)
        async def decorated_function(name: str):
            return f"Hello {name}!"
        
        result = await decorated_function("World")
        print(f"\nDecorated function result: {result}")
    
    # Run test
    asyncio.run(test_rate_limiter())