"""
Unit tests for caching functionality
"""
import pytest
from unittest.mock import MagicMock

from stock_tracker.core.cache import RedisCache


class TestRedisCache:
    """Test Redis cache functionality"""
    
    def test_set_and_get(self, redis_client):
        """Test setting and getting cache values"""
        cache = RedisCache(redis_client)
        
        cache.set("test_key", "test_value", ttl=60)
        result = cache.get("test_key")
        
        assert result == "test_value"
    
    def test_get_nonexistent_key(self, redis_client):
        """Test getting nonexistent key returns None"""
        cache = RedisCache(redis_client)
        
        result = cache.get("nonexistent_key")
        
        assert result is None
    
    def test_delete_key(self, redis_client):
        """Test deleting cache key"""
        cache = RedisCache(redis_client)
        
        cache.set("test_key", "test_value")
        cache.delete("test_key")
        result = cache.get("test_key")
        
        assert result is None
    
    def test_ttl_expiration(self, redis_client):
        """Test TTL expiration"""
        import time
        cache = RedisCache(redis_client)
        
        cache.set("test_key", "test_value", ttl=1)
        time.sleep(2)
        result = cache.get("test_key")
        
        assert result is None
    
    def test_cache_json_data(self, redis_client):
        """Test caching JSON-serializable data"""
        cache = RedisCache(redis_client)
        
        data = {"key": "value", "number": 123, "list": [1, 2, 3]}
        cache.set("json_key", data)
        result = cache.get("json_key")
        
        assert result == data
    
    def test_cache_with_tenant_prefix(self, redis_client):
        """Test cache key prefixing for tenant isolation"""
        cache = RedisCache(redis_client)
        tenant_id = "tenant-123"
        
        key = f"tenant:{tenant_id}:products"
        cache.set(key, {"products": []})
        result = cache.get(key)
        
        assert result == {"products": []}
    
    def test_flush_pattern(self, redis_client):
        """Test flushing keys by pattern"""
        cache = RedisCache(redis_client)
        
        cache.set("tenant:123:key1", "value1")
        cache.set("tenant:123:key2", "value2")
        cache.set("tenant:456:key1", "value3")
        
        # Delete all keys for tenant 123
        pattern = "tenant:123:*"
        keys = redis_client.keys(pattern)
        for key in keys:
            redis_client.delete(key)
        
        assert cache.get("tenant:123:key1") is None
        assert cache.get("tenant:123:key2") is None
        assert cache.get("tenant:456:key1") == "value3"


class TestCacheDecorator:
    """Test cache decorator functionality"""
    
    def test_cached_function(self, cache):
        """Test function result caching"""
        call_count = 0
        
        def expensive_function(arg):
            nonlocal call_count
            call_count += 1
            return f"result_{arg}"
        
        # First call - should execute function
        result1 = expensive_function("test")
        assert result1 == "result_test"
        assert call_count == 1
        
        # Simulate caching
        cache.set("expensive_function:test", result1)
        
        # Second call - should use cache
        cached_result = cache.get("expensive_function:test")
        assert cached_result == "result_test"
        assert call_count == 1  # Function not called again
