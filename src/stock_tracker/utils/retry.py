"""
Retry utilities with exponential backoff for API calls.

Implements comprehensive retry logic as specified in urls.md for handling
API rate limits, temporary failures, and network issues with intelligent
backoff strategies.
"""

import asyncio
import random
import time
from functools import wraps
from typing import Callable, Type, Tuple, Optional, Any, Union, Awaitable
from dataclasses import dataclass

from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.exceptions import (
    WildberriesAPIError, RateLimitError, TaskTimeoutError,
    AuthenticationError
)


logger = get_logger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    
    max_retries: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    exponential_base: float = 2.0  # Exponential backoff multiplier
    jitter: bool = True  # Add random jitter to prevent thundering herd
    
    # Retry conditions
    retry_on_status_codes: Tuple[int, ...] = (429, 500, 502, 503, 504)
    retry_on_exceptions: Tuple[Type[Exception], ...] = (
        RateLimitError,
        ConnectionError,
        TimeoutError
    )
    
    # Rate limiting
    respect_retry_after: bool = True  # Use Retry-After header from 429 responses
    max_retry_after: float = 300.0  # Maximum time to wait for Retry-After (5 minutes)


class ExponentialBackoff:
    """
    Exponential backoff calculator with jitter.
    
    Implements the retry strategy specified in urls.md:
    - Base delay starts at 1 second
    - Each retry doubles the delay (exponential backoff)
    - Random jitter prevents thundering herd effect
    - Maximum delay cap prevents excessive waiting
    """
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.attempt = 0
    
    def reset(self) -> None:
        """Reset attempt counter."""
        self.attempt = 0
    
    def calculate_delay(self, retry_after_header: Optional[str] = None) -> float:
        """
        Calculate delay for current attempt.
        
        Args:
            retry_after_header: Retry-After header value from API response
            
        Returns:
            Delay in seconds
        """
        # Respect Retry-After header if provided (for 429 responses)
        if (retry_after_header and 
            self.config.respect_retry_after and 
            self.attempt > 0):
            try:
                retry_after = float(retry_after_header)
                if retry_after <= self.config.max_retry_after:
                    logger.debug(f"Using Retry-After header: {retry_after}s")
                    return retry_after
                else:
                    logger.warning(f"Retry-After too large ({retry_after}s), using exponential backoff")
            except (ValueError, TypeError):
                logger.warning(f"Invalid Retry-After header: {retry_after_header}")
        
        # Calculate exponential backoff delay
        delay = self.config.base_delay * (self.config.exponential_base ** self.attempt)
        
        # Add jitter if enabled (±25% random variation)
        if self.config.jitter:
            jitter_range = delay * 0.25
            jitter = random.uniform(-jitter_range, jitter_range)
            delay += jitter
        
        # Apply maximum delay cap
        delay = min(delay, self.config.max_delay)
        
        self.attempt += 1
        
        logger.debug(f"Calculated retry delay: {delay:.2f}s (attempt {self.attempt})")
        return delay
    
    def should_retry(self, exception: Exception, status_code: Optional[int] = None) -> bool:
        """
        Determine if we should retry based on exception or status code.
        
        Args:
            exception: Exception that occurred
            status_code: HTTP status code if available
            
        Returns:
            True if should retry, False otherwise
        """
        if self.attempt >= self.config.max_retries:
            logger.debug(f"Max retries ({self.config.max_retries}) exceeded")
            return False
        
        # Check status code conditions
        if status_code and status_code in self.config.retry_on_status_codes:
            logger.debug(f"Retrying on status code: {status_code}")
            return True
        
        # Check exception conditions
        for retry_exception in self.config.retry_on_exceptions:
            if isinstance(exception, retry_exception):
                logger.debug(f"Retrying on exception: {type(exception).__name__}")
                return True
        
        # Special handling for WildberriesAPIError
        if isinstance(exception, WildberriesAPIError):
            if exception.status_code in self.config.retry_on_status_codes:
                logger.debug(f"Retrying WildberriesAPIError with status: {exception.status_code}")
                return True
        
        logger.debug(f"Not retrying exception: {type(exception).__name__}")
        return False


def retry_with_backoff(config: Optional[RetryConfig] = None):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        config: Retry configuration (uses default if None)
        
    Returns:
        Decorated function with retry logic
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            """Synchronous retry wrapper."""
            backoff = ExponentialBackoff(config)
            last_exception = None
            
            while True:
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    
                    # Extract status code if available
                    status_code = getattr(e, 'status_code', None)
                    
                    # Extract Retry-After header if available
                    retry_after = None
                    if hasattr(e, 'response') and e.response:
                        retry_after = e.response.headers.get('Retry-After')
                    
                    # Check if we should retry
                    if not backoff.should_retry(e, status_code):
                        logger.error(f"Max retries exceeded for {func.__name__}: {e}")
                        raise e
                    
                    # Calculate delay and wait
                    delay = backoff.calculate_delay(retry_after)
                    logger.info(f"Retrying {func.__name__} in {delay:.2f}s (attempt {backoff.attempt})")
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            """Asynchronous retry wrapper."""
            backoff = ExponentialBackoff(config)
            last_exception = None
            
            while True:
                try:
                    return await func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    
                    # Extract status code if available
                    status_code = getattr(e, 'status_code', None)
                    
                    # Extract Retry-After header if available
                    retry_after = None
                    if hasattr(e, 'response') and e.response:
                        retry_after = e.response.headers.get('Retry-After')
                    
                    # Check if we should retry
                    if not backoff.should_retry(e, status_code):
                        logger.error(f"Max retries exceeded for {func.__name__}: {e}")
                        raise e
                    
                    # Calculate delay and wait
                    delay = backoff.calculate_delay(retry_after)
                    logger.info(f"Retrying {func.__name__} in {delay:.2f}s (attempt {backoff.attempt})")
                    await asyncio.sleep(delay)
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def retry_on_rate_limit(max_retries: int = 5, 
                       base_delay: float = 1.0,
                       max_delay: float = 300.0):
    """
    Specialized retry decorator for rate limiting (429 errors).
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        
    Returns:
        Decorator function
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        retry_on_status_codes=(429,),
        retry_on_exceptions=(RateLimitError,),
        respect_retry_after=True
    )
    
    return retry_with_backoff(config)


def retry_on_server_error(max_retries: int = 3,
                         base_delay: float = 1.0,
                         max_delay: float = 60.0):
    """
    Specialized retry decorator for server errors (5xx errors).
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        
    Returns:
        Decorator function
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        retry_on_status_codes=(500, 502, 503, 504),
        retry_on_exceptions=(ConnectionError, TimeoutError),
        respect_retry_after=False
    )
    
    return retry_with_backoff(config)


class RetryableOperation:
    """
    Context manager for retryable operations.
    
    Example:
        async with RetryableOperation(RetryConfig(max_retries=5)) as retry:
            result = await retry.execute(some_api_call, arg1, arg2)
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.backoff = ExponentialBackoff(self.config)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retry attempts fail
        """
        self.backoff.reset()
        last_exception = None
        
        while True:
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
                    
            except Exception as e:
                last_exception = e
                
                # Extract status code if available
                status_code = getattr(e, 'status_code', None)
                
                # Extract Retry-After header if available
                retry_after = None
                if hasattr(e, 'response') and e.response:
                    retry_after = e.response.headers.get('Retry-After')
                
                # Check if we should retry
                if not self.backoff.should_retry(e, status_code):
                    logger.error(f"Max retries exceeded for operation: {e}")
                    raise e
                
                # Calculate delay and wait
                delay = self.backoff.calculate_delay(retry_after)
                logger.info(f"Retrying operation in {delay:.2f}s (attempt {self.backoff.attempt})")
                await asyncio.sleep(delay)
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception


# Example usage and testing
if __name__ == "__main__":
    import requests
    
    # Test the retry decorator
    @retry_with_backoff(RetryConfig(max_retries=3, base_delay=0.1))
    def test_function():
        """Test function that fails a few times."""
        if not hasattr(test_function, 'attempts'):
            test_function.attempts = 0
        
        test_function.attempts += 1
        
        if test_function.attempts < 3:
            raise RateLimitError(f"Simulated failure (attempt {test_function.attempts})")
        
        return f"Success after {test_function.attempts} attempts"
    
    # Test async version
    @retry_with_backoff(RetryConfig(max_retries=3, base_delay=0.1))
    async def test_async_function():
        """Test async function that fails a few times."""
        if not hasattr(test_async_function, 'attempts'):
            test_async_function.attempts = 0
        
        test_async_function.attempts += 1
        
        if test_async_function.attempts < 3:
            raise ConnectionError(f"Simulated async failure (attempt {test_async_function.attempts})")
        
        return f"Async success after {test_async_function.attempts} attempts"
    
    # Run tests
    try:
        print("Testing synchronous retry...")
        result = test_function()
        print(f"✅ {result}")
        
        print("\nTesting asynchronous retry...")
        async def run_async_test():
            result = await test_async_function()
            print(f"✅ {result}")
        
        asyncio.run(run_async_test())
        
        print("\nTesting RetryableOperation...")
        async def run_context_test():
            async with RetryableOperation(RetryConfig(max_retries=2, base_delay=0.1)) as retry:
                def failing_func():
                    if not hasattr(failing_func, 'attempts'):
                        failing_func.attempts = 0
                    failing_func.attempts += 1
                    if failing_func.attempts == 1:
                        raise TimeoutError("Simulated timeout")
                    return "Context manager success"
                
                result = await retry.execute(failing_func)
                print(f"✅ {result}")
        
        asyncio.run(run_context_test())
        
    except Exception as e:
        print(f"❌ Test failed: {e}")