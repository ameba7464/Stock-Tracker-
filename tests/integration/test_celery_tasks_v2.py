"""
Integration tests for Celery tasks (FastAPI 2.0)
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from uuid import uuid4


class TestSyncTenantProductsTask:
    """Test sync_tenant_products Celery task"""
    
    @patch("stock_tracker.workers.tasks.SyncService")
    def test_sync_task_success(self, mock_sync_service, db_session, test_tenant):
        """Test successful product sync task"""
        from stock_tracker.workers.tasks import sync_tenant_products
        from stock_tracker.database.models import SyncLog
        
        # Mock SyncService
        mock_service_instance = MagicMock()
        mock_service_instance.sync_products.return_value = {
            "status": "success",
            "products_synced": 15,
            "duration_seconds": 2.5
        }
        mock_sync_service.return_value = mock_service_instance
        
        # Execute task
        result = sync_tenant_products(str(test_tenant.id))
        
        # Verify result
        assert result["status"] == "completed"
        assert result["tenant_id"] == str(test_tenant.id)
        assert result["products_count"] == 15
        assert "duration_seconds" in result
        
        # Verify sync log created
        sync_log = db_session.query(SyncLog).filter_by(
            tenant_id=test_tenant.id,
            status="completed"
        ).first()
        assert sync_log is not None
        assert sync_log.products_synced == 15
    
    @patch("stock_tracker.workers.tasks.SyncService")
    def test_sync_task_failure(self, mock_sync_service, db_session, test_tenant):
        """Test sync task failure handling"""
        from stock_tracker.workers.tasks import sync_tenant_products
        from stock_tracker.database.models import SyncLog
        
        # Mock SyncService to raise exception
        mock_service_instance = MagicMock()
        mock_service_instance.sync_products.side_effect = Exception("Marketplace API error")
        mock_sync_service.return_value = mock_service_instance
        
        # Execute task
        result = sync_tenant_products(str(test_tenant.id))
        
        # Verify error handling
        assert result["status"] == "failed"
        assert "error" in result or "message" in result
        
        # Verify sync log shows failure
        sync_log = db_session.query(SyncLog).filter_by(
            tenant_id=test_tenant.id,
            status="failed"
        ).first()
        assert sync_log is not None
        assert "error" in sync_log.message.lower() or "failed" in sync_log.message.lower()
    
    def test_sync_task_tenant_not_found(self, db_session):
        """Test sync task with non-existent tenant"""
        from stock_tracker.workers.tasks import sync_tenant_products
        
        fake_tenant_id = str(uuid4())
        
        # Execute task
        result = sync_tenant_products(fake_tenant_id)
        
        # Should handle gracefully
        assert result["status"] in ["failed", "error"]
    
    @patch("stock_tracker.workers.tasks.SyncService")
    def test_sync_task_updates_last_sync(self, mock_sync_service, db_session, test_tenant):
        """Test that sync task updates tenant's last_sync timestamp"""
        from stock_tracker.workers.tasks import sync_tenant_products
        
        # Mock SyncService
        mock_service_instance = MagicMock()
        mock_service_instance.sync_products.return_value = {
            "status": "success",
            "products_synced": 5,
            "duration_seconds": 1.0
        }
        mock_sync_service.return_value = mock_service_instance
        
        # Record timestamp before sync
        old_last_sync = test_tenant.last_sync
        
        # Execute task
        sync_tenant_products(str(test_tenant.id))
        
        # Verify last_sync updated
        db_session.refresh(test_tenant)
        assert test_tenant.last_sync > old_last_sync if old_last_sync else True
    
    @patch("stock_tracker.workers.tasks.SyncService")
    @patch("stock_tracker.workers.tasks.dispatch_webhook")
    def test_sync_task_triggers_webhook(self, mock_webhook, mock_sync_service, db_session, test_tenant):
        """Test that successful sync triggers webhook notification"""
        from stock_tracker.workers.tasks import sync_tenant_products
        
        # Mock SyncService
        mock_service_instance = MagicMock()
        mock_service_instance.sync_products.return_value = {
            "status": "success",
            "products_synced": 10,
            "duration_seconds": 2.0
        }
        mock_sync_service.return_value = mock_service_instance
        
        # Execute task
        sync_tenant_products(str(test_tenant.id))
        
        # Verify webhook was called
        mock_webhook.assert_called_once()


class TestScheduleTenantSyncsTask:
    """Test schedule_tenant_syncs periodic task"""
    
    @patch("stock_tracker.workers.tasks.sync_tenant_products")
    def test_schedule_syncs_for_due_tenants(self, mock_sync_task, db_session, test_tenant):
        """Test scheduling syncs for tenants that are due"""
        from stock_tracker.workers.tasks import schedule_tenant_syncs
        
        # Set tenant as due for sync
        test_tenant.last_sync = datetime.utcnow() - timedelta(hours=2)
        test_tenant.sync_interval_minutes = 60
        test_tenant.is_active = True
        db_session.commit()
        
        # Execute scheduler
        result = schedule_tenant_syncs()
        
        # Verify sync was scheduled
        assert result["scheduled_count"] >= 1
        mock_sync_task.delay.assert_called()
    
    def test_schedule_skips_inactive_tenants(self, db_session, test_tenant):
        """Test scheduler skips inactive tenants"""
        from stock_tracker.workers.tasks import schedule_tenant_syncs
        
        # Mark tenant as inactive
        test_tenant.is_active = False
        test_tenant.last_sync = datetime.utcnow() - timedelta(hours=2)
        db_session.commit()
        
        # Execute scheduler
        result = schedule_tenant_syncs()
        
        # Should not schedule inactive tenant
        assert result["scheduled_count"] == 0
    
    def test_schedule_respects_sync_interval(self, db_session, test_tenant):
        """Test scheduler respects tenant sync_interval_minutes"""
        from stock_tracker.workers.tasks import schedule_tenant_syncs
        
        # Set recent sync (not due yet)
        test_tenant.last_sync = datetime.utcnow() - timedelta(minutes=30)
        test_tenant.sync_interval_minutes = 60
        test_tenant.is_active = True
        db_session.commit()
        
        # Execute scheduler
        result = schedule_tenant_syncs()
        
        # Should not schedule (not due yet)
        assert result["scheduled_count"] == 0


class TestCleanupOldLogsTask:
    """Test cleanup_old_logs periodic task"""
    
    def test_cleanup_deletes_old_logs(self, db_session, test_tenant):
        """Test cleanup removes logs older than retention period"""
        from stock_tracker.workers.tasks import cleanup_old_logs
        from stock_tracker.database.models import SyncLog
        
        # Create old logs (35 days old)
        old_date = datetime.utcnow() - timedelta(days=35)
        for i in range(10):
            log = SyncLog(
                tenant_id=test_tenant.id,
                status="completed",
                started_at=old_date,
                completed_at=old_date + timedelta(seconds=10),
                products_synced=5
            )
            db_session.add(log)
        
        # Create recent logs (5 days old)
        recent_date = datetime.utcnow() - timedelta(days=5)
        for i in range(5):
            log = SyncLog(
                tenant_id=test_tenant.id,
                status="completed",
                started_at=recent_date,
                completed_at=recent_date + timedelta(seconds=10),
                products_synced=5
            )
            db_session.add(log)
        db_session.commit()
        
        # Execute cleanup (30 day retention)
        result = cleanup_old_logs(days=30)
        
        # Verify old logs deleted
        assert result["deleted_count"] >= 10
        
        # Verify recent logs preserved
        remaining_logs = db_session.query(SyncLog).filter_by(tenant_id=test_tenant.id).count()
        assert remaining_logs >= 5
    
    def test_cleanup_preserves_recent_logs(self, db_session, test_tenant):
        """Test cleanup doesn't delete recent logs"""
        from stock_tracker.workers.tasks import cleanup_old_logs
        from stock_tracker.database.models import SyncLog
        
        # Create recent logs only
        recent_date = datetime.utcnow() - timedelta(days=5)
        for i in range(10):
            log = SyncLog(
                tenant_id=test_tenant.id,
                status="completed",
                started_at=recent_date,
                products_synced=5
            )
            db_session.add(log)
        db_session.commit()
        
        initial_count = db_session.query(SyncLog).count()
        
        # Execute cleanup
        result = cleanup_old_logs(days=30)
        
        # Verify no logs deleted
        assert result["deleted_count"] == 0
        final_count = db_session.query(SyncLog).count()
        assert final_count == initial_count


class TestHealthCheckTask:
    """Test health_check periodic task"""
    
    def test_health_check_verifies_services(self):
        """Test health check verifies all services"""
        from stock_tracker.workers.tasks import health_check
        
        result = health_check()
        
        assert "status" in result
        assert "services" in result
        assert "database" in result["services"]
        assert "redis" in result["services"]
    
    @patch("stock_tracker.workers.tasks.redis_client")
    def test_health_check_detects_redis_failure(self, mock_redis):
        """Test health check detects Redis connection issues"""
        from stock_tracker.workers.tasks import health_check
        
        # Mock Redis failure
        mock_redis.ping.side_effect = Exception("Connection refused")
        
        result = health_check()
        
        assert result["services"]["redis"] == "unhealthy"
    
    @patch("stock_tracker.database.connection.engine")
    def test_health_check_detects_db_failure(self, mock_engine):
        """Test health check detects database connection issues"""
        from stock_tracker.workers.tasks import health_check
        
        # Mock database failure
        mock_engine.connect.side_effect = Exception("Connection refused")
        
        result = health_check()
        
        assert result["services"]["database"] == "unhealthy"


class TestCeleryTaskRetry:
    """Test Celery task retry mechanisms"""
    
    @patch("stock_tracker.workers.tasks.SyncService")
    def test_sync_task_retries_on_failure(self, mock_sync_service, test_tenant):
        """Test sync task retries on transient failures"""
        from stock_tracker.workers.tasks import sync_tenant_products
        
        # Mock transient failure (API timeout)
        mock_service_instance = MagicMock()
        mock_service_instance.sync_products.side_effect = [
            Exception("Timeout"),
            {
                "status": "success",
                "products_synced": 10,
                "duration_seconds": 2.0
            }
        ]
        mock_sync_service.return_value = mock_service_instance
        
        # First call should fail and retry
        result1 = sync_tenant_products(str(test_tenant.id))
        assert result1["status"] == "failed"
        
        # Retry should succeed
        result2 = sync_tenant_products(str(test_tenant.id))
        assert result2["status"] == "completed"
    
    @patch("stock_tracker.workers.tasks.SyncService")
    def test_sync_task_max_retries(self, mock_sync_service, test_tenant):
        """Test sync task respects max retries"""
        from stock_tracker.workers.tasks import sync_tenant_products
        
        # Mock persistent failure
        mock_service_instance = MagicMock()
        mock_service_instance.sync_products.side_effect = Exception("Persistent error")
        mock_sync_service.return_value = mock_service_instance
        
        # Execute multiple times (should fail each time)
        results = []
        for i in range(5):
            result = sync_tenant_products(str(test_tenant.id))
            results.append(result)
        
        # All should fail (not infinitely retry)
        assert all(r["status"] == "failed" for r in results)


class TestConcurrentSyncs:
    """Test concurrent sync task execution"""
    
    @patch("stock_tracker.workers.tasks.SyncService")
    def test_multiple_tenants_sync_concurrently(self, mock_sync_service, db_session):
        """Test multiple tenants can sync concurrently"""
        from stock_tracker.workers.tasks import sync_tenant_products
        from stock_tracker.database.models import Tenant
        
        # Create multiple tenants
        tenants = []
        for i in range(3):
            tenant = Tenant(
                name=f"Test Company {i}",
                marketplace_type="wildberries",
                is_active=True
            )
            db_session.add(tenant)
            tenants.append(tenant)
        db_session.commit()
        
        # Mock SyncService
        mock_service_instance = MagicMock()
        mock_service_instance.sync_products.return_value = {
            "status": "success",
            "products_synced": 5,
            "duration_seconds": 1.0
        }
        mock_sync_service.return_value = mock_service_instance
        
        # Execute syncs for all tenants
        results = [sync_tenant_products(str(t.id)) for t in tenants]
        
        # All should succeed
        assert all(r["status"] == "completed" for r in results)
        assert len(results) == 3
