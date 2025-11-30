"""
Redis caching implementation for Stock Tracker.
"""

import os
import json
import functools
from typing import Optional, Any, Callable
from datetime import timedelta

import redis
from redis.connection import ConnectionPool

from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class RedisCache:
    """
    Redis cache manager with connection pooling.
    
    Supports:
    - Get/Set/Delete operations
    - TTL management
    - JSON serialization
    - Connection pooling for 20-30 concurrent tenants
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 300,
        max_connections: int = 50,
        decode_responses: bool = True
    ):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL (default from env REDIS_URL)
            default_ttl: Default TTL in seconds (5 minutes)
            max_connections: Maximum pool connections
            decode_responses: Auto-decode bytes to strings
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.default_ttl = default_ttl
        
        # Create connection pool
        self.pool = ConnectionPool.from_url(
            self.redis_url,
            max_connections=max_connections,
            decode_responses=decode_responses
        )
        
        # Redis client
        self.client = redis.Redis(connection_pool=self.pool)
        
        logger.info(f"Redis cache initialized (url={self.redis_url}, ttl={default_ttl}s, pool={max_connections})")
    
    def _make_key(self, tenant_id: str, key: str) -> str:
        """
        Create tenant-scoped cache key.
        
        Args:
            tenant_id: Tenant UUID
            key: Cache key
            
        Returns:
            Scoped key format: tenant:{tenant_id}:{key}
        """
        return f"tenant:{tenant_id}:{key}"
    
    def get(self, tenant_id: str, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            tenant_id: Tenant UUID
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        cache_key = self._make_key(tenant_id, key)
        
        try:
            value = self.client.get(cache_key)
            
            if value is None:
                logger.debug(f"Cache miss: {cache_key}")
                return None
            
            # Deserialize JSON
            result = json.loads(value)
            logger.debug(f"Cache hit: {cache_key}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Cache JSON decode error for {cache_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Cache get error for {cache_key}: {e}")
            return None
    
    def set(
        self,
        tenant_id: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            tenant_id: Tenant UUID
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: TTL in seconds (default: self.default_ttl)
            
        Returns:
            True if successful, False otherwise
        """
        cache_key = self._make_key(tenant_id, key)
        ttl = ttl or self.default_ttl
        
        try:
            # Serialize to JSON
            serialized = json.dumps(value)
            
            # Set with TTL
            self.client.setex(cache_key, ttl, serialized)
            
            logger.debug(f"Cache set: {cache_key} (ttl={ttl}s)")
            return True
            
        except (TypeError, ValueError) as e:
            logger.error(f"Cache serialization error for {cache_key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Cache set error for {cache_key}: {e}")
            return False
    
    def delete(self, tenant_id: str, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            tenant_id: Tenant UUID
            key: Cache key
            
        Returns:
            True if deleted, False otherwise
        """
        cache_key = self._make_key(tenant_id, key)
        
        try:
            result = self.client.delete(cache_key)
            logger.debug(f"Cache delete: {cache_key} (deleted={result})")
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error for {cache_key}: {e}")
            return False
    
    def invalidate_pattern(self, tenant_id: str, pattern: str) -> int:
        """
        Invalidate all keys matching pattern for tenant.
        
        Args:
            tenant_id: Tenant UUID
            pattern: Key pattern (e.g., "products:*")
            
        Returns:
            Number of keys deleted
        """
        cache_pattern = self._make_key(tenant_id, pattern)
        
        try:
            # Find matching keys
            keys = self.client.keys(cache_pattern)
            
            if not keys:
                return 0
            
            # Delete all matching keys
            deleted = self.client.delete(*keys)
            logger.info(f"Cache invalidated: {cache_pattern} ({deleted} keys)")
            return deleted
            
        except Exception as e:
            logger.error(f"Cache invalidate error for {cache_pattern}: {e}")
            return 0
    
    def exists(self, tenant_id: str, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            tenant_id: Tenant UUID
            key: Cache key
            
        Returns:
            True if exists, False otherwise
        """
        cache_key = self._make_key(tenant_id, key)
        
        try:
            return self.client.exists(cache_key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for {cache_key}: {e}")
            return False
    
    def get_ttl(self, tenant_id: str, key: str) -> int:
        """
        Get remaining TTL for key.
        
        Args:
            tenant_id: Tenant UUID
            key: Cache key
            
        Returns:
            TTL in seconds, -2 if not exists, -1 if no expiry
        """
        cache_key = self._make_key(tenant_id, key)
        
        try:
            return self.client.ttl(cache_key)
        except Exception as e:
            logger.error(f"Cache TTL error for {cache_key}: {e}")
            return -2
    
    def ping(self) -> bool:
        """
        Check Redis connection.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    def flush_tenant(self, tenant_id: str) -> int:
        """
        Flush all cache entries for tenant.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Number of keys deleted
        """
        return self.invalidate_pattern(tenant_id, "*")
    
    def close(self):
        """Close Redis connection pool."""
        try:
            self.client.close()
            self.pool.disconnect()
            logger.info("Redis cache closed")
        except Exception as e:
            logger.error(f"Redis close error: {e}")


# Global cache instance
_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """
    Get or create global Redis cache instance.
    
    Returns:
        RedisCache instance
    """
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = RedisCache()
    
    return _cache_instance


def cached(
    key_prefix: str,
    ttl: Optional[int] = None,
    key_builder: Optional[Callable] = None
):
    """
    Decorator to cache function results.
    
    Usage:
        @cached("products:list", ttl=300)
        async def get_products(tenant_id: str):
            return await fetch_products()
    
    Args:
        key_prefix: Cache key prefix
        ttl: TTL in seconds (default: cache default)
        key_builder: Custom function to build cache key from args
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Extract tenant_id (assume first arg or kwarg)
            tenant_id = kwargs.get("tenant_id") or (args[0] if args else None)
            
            if not tenant_id:
                logger.warning(f"@cached: No tenant_id found, skipping cache for {func.__name__}")
                return await func(*args, **kwargs)
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default: prefix + function args
                args_str = ":".join(str(a) for a in args[1:])  # Skip tenant_id
                kwargs_str = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()) if k != "tenant_id")
                cache_key = f"{key_prefix}:{args_str}:{kwargs_str}".rstrip(":")
            
            # Try cache
            cached_value = cache.get(tenant_id, cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            cache.set(tenant_id, cache_key, result, ttl=ttl)
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Extract tenant_id
            tenant_id = kwargs.get("tenant_id") or (args[0] if args else None)
            
            if not tenant_id:
                logger.warning(f"@cached: No tenant_id found, skipping cache for {func.__name__}")
                return func(*args, **kwargs)
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                args_str = ":".join(str(a) for a in args[1:])
                kwargs_str = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()) if k != "tenant_id")
                cache_key = f"{key_prefix}:{args_str}:{kwargs_str}".rstrip(":")
            
            # Try cache
            cached_value = cache.get(tenant_id, cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(tenant_id, cache_key, result, ttl=ttl)
            
            return result
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
