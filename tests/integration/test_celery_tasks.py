"""
Integration tests for Celery tasks
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestCeleryTasks:
    """Test Celery background tasks"""
    
    @patch("stock_tracker.workers.tasks.ProductService")
    def test_sync_tenant_products_success(self, mock_service, db_session, test_tenant, cache):
        """Test successful tenant product sync"""
        from stock_tracker.workers.tasks import sync_tenant_products
        
        # Mock ProductService
        mock_instance = MagicMock()
        mock_instance.sync_all_products.return_value = {
            "products_synced": 10,
            "updated_count": 5,
            "error_count": 0,
            "duration_seconds": 2.5
        }
        mock_service.return_value = mock_instance
        
        # Execute task
        result = sync_tenant_products(str(test_tenant.id))
        
        assert result["status"] == "success"
        assert result["products_count"] == 10
        assert "duration_seconds" in result
    
    @patch("stock_tracker.workers.tasks.ProductService")
    def test_sync_tenant_products_failure(self, mock_service, db_session, test_tenant):
        """Test failed tenant product sync"""
        from stock_tracker.workers.tasks import sync_tenant_products
        
        # Mock ProductService to raise exception
        mock_service.side_effect = Exception("API Error")
        
        # Execute task - should handle error gracefully
        result = sync_tenant_products(str(test_tenant.id))
        
        assert result["status"] == "failed"
        assert "error" in result
    
    def test_cleanup_old_logs(self, db_session, test_tenant):
        """Test cleanup of old sync logs"""
        from stock_tracker.workers.tasks import cleanup_old_logs
        from stock_tracker.db.models import SyncLog
        from datetime import timedelta
        
        # Create old logs
        old_date = datetime.utcnow() - timedelta(days=35)
        for i in range(5):
            log = SyncLog(
                tenant_id=test_tenant.id,
                status="completed",
                started_at=old_date,
                products_synced=10
            )
            db_session.add(log)
        db_session.commit()
        
        # Execute cleanup
        result = cleanup_old_logs(days=30)
        
        assert result["deleted_count"] >= 5
    
    def test_schedule_tenant_syncs(self, db_session, test_tenant):
        """Test scheduling tenant syncs"""
        from stock_tracker.workers.tasks import schedule_tenant_syncs
        from datetime import timedelta
        
        # Set last sync time to trigger new sync
        test_tenant.last_sync = datetime.utcnow() - timedelta(hours=2)
        test_tenant.sync_interval_minutes = 60
        db_session.commit()
        
        # Execute scheduler
        result = schedule_tenant_syncs()
        
        assert result["scheduled_count"] >= 1


class TestWebhookDispatcher:
    """Test webhook notification system"""
    
    @patch("requests.post")
    def test_dispatch_webhook_success(self, mock_post, db_session, test_tenant):
        """Test successful webhook dispatch"""
        from stock_tracker.services.webhook_dispatcher import dispatch_webhook
        from stock_tracker.db.models import WebhookConfig
        
        # Create webhook config
        webhook = WebhookConfig(
            tenant_id=test_tenant.id,
            url="https://example.com/webhook",
            events=["sync_completed"],
            is_active=True
        )
        db_session.add(webhook)
        db_session.commit()
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Dispatch webhook
        result = dispatch_webhook(
            tenant=test_tenant,
            event_type="sync_completed",
            data={"products_synced": 10},
            db_session=db_session
        )
        
        assert result is True
        assert mock_post.called
    
    @patch("requests.post")
    def test_dispatch_webhook_failure(self, mock_post, db_session, test_tenant):
        """Test webhook dispatch failure handling"""
        from stock_tracker.services.webhook_dispatcher import dispatch_webhook
        from stock_tracker.db.models import WebhookConfig
        
        # Create webhook config
        webhook = WebhookConfig(
            tenant_id=test_tenant.id,
            url="https://example.com/webhook",
            events=["sync_completed"],
            is_active=True,
            failure_count=0
        )
        db_session.add(webhook)
        db_session.commit()
        
        # Mock failed response
        mock_post.side_effect = Exception("Connection error")
        
        # Dispatch webhook
        result = dispatch_webhook(
            tenant=test_tenant,
            event_type="sync_completed",
            data={"products_synced": 10},
            db_session=db_session
        )
        
        assert result is False
        
        # Check failure count incremented
        db_session.refresh(webhook)
        assert webhook.failure_count > 0
    
    @patch("requests.post")
    def test_telegram_notification(self, mock_post):
        """Test Telegram notification sending"""
        from stock_tracker.services.webhook_dispatcher import send_telegram_notification
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response
        
        # Send notification
        result = send_telegram_notification(
            chat_id="123456789",
            message="Test message",
            bot_token="test_token"
        )
        
        assert result is True
        assert mock_post.called


class TestRateLimiter:
    """Test rate limiting functionality"""
    
    def test_rate_limit_check(self, redis_client):
        """Test rate limit checking"""
        from stock_tracker.api.middleware.rate_limiter.redis_rate_limiter import RedisRateLimiter
        
        limiter = RedisRateLimiter(redis_client)
        
        # First request - should be allowed
        allowed, remaining, reset = limiter.check_rate_limit("test_key", limit=5, window_seconds=60)
        
        assert allowed is True
        assert remaining == 4
    
    def test_rate_limit_exceeded(self, redis_client):
        """Test rate limit exceeded"""
        from stock_tracker.api.middleware.rate_limiter.redis_rate_limiter import RedisRateLimiter
        
        limiter = RedisRateLimiter(redis_client)
        
        # Make requests until limit
        for i in range(5):
            limiter.check_rate_limit("test_key", limit=5, window_seconds=60)
        
        # Next request should be denied
        allowed, remaining, reset = limiter.check_rate_limit("test_key", limit=5, window_seconds=60)
        
        assert allowed is False
        assert remaining == 0
    
    def test_rate_limit_sliding_window(self, redis_client):
        """Test sliding window algorithm"""
        from stock_tracker.api.middleware.rate_limiter.redis_rate_limiter import RedisRateLimiter
        import time
        
        limiter = RedisRateLimiter(redis_client)
        
        # Make 3 requests
        for i in range(3):
            limiter.check_rate_limit("test_key", limit=5, window_seconds=2)
        
        # Wait for window to partially expire
        time.sleep(1)
        
        # Make 2 more requests - should still have capacity
        allowed1, _, _ = limiter.check_rate_limit("test_key", limit=5, window_seconds=2)
        allowed2, _, _ = limiter.check_rate_limit("test_key", limit=5, window_seconds=2)
        
        assert allowed1 is True
        assert allowed2 is True
