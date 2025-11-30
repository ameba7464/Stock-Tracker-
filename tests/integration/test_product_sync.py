"""
Integration tests for product synchronization
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import status


class TestProductSync:
    """Test product synchronization flow"""
    
    @patch("stock_tracker.services.marketplace_clients.wildberries_client.WildberriesAPIClient")
    def test_trigger_sync(self, mock_wb_client, client, test_user, test_tenant, auth_headers):
        """Test triggering product sync"""
        # Mock API responses
        mock_instance = MagicMock()
        mock_instance.get_stocks.return_value = [
            {
                "sku": "TEST-001",
                "barcode": "1234567890",
                "quantity": 50,
                "warehouse_name": "Подольск"
            }
        ]
        mock_wb_client.return_value = mock_instance
        
        response = client.post(
            "/api/v1/products/sync",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "task_id" in data or "status" in data
    
    def test_sync_requires_credentials(self, client, test_user, auth_headers, db_session):
        """Test sync fails without marketplace credentials"""
        # Ensure tenant has no credentials
        from stock_tracker.db.models import Tenant
        tenant = db_session.query(Tenant).filter_by(id=test_user.tenant_id).first()
        tenant.wb_credentials_encrypted = None
        db_session.commit()
        
        response = client.post(
            "/api/v1/products/sync",
            headers=auth_headers
        )
        
        # Should return error or redirect to credentials setup
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND]
    
    def test_get_sync_status(self, client, auth_headers, db_session, test_tenant):
        """Test getting sync status"""
        from stock_tracker.db.models import SyncLog
        from datetime import datetime
        
        # Create sync log
        sync_log = SyncLog(
            tenant_id=test_tenant.id,
            status="completed",
            started_at=datetime.utcnow(),
            products_synced=10,
            duration_seconds=5.2
        )
        db_session.add(sync_log)
        db_session.commit()
        
        response = client.get(
            f"/api/v1/sync/status/{sync_log.id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "completed"
        assert data["products_synced"] == 10
    
    def test_get_sync_history(self, client, auth_headers, db_session, test_tenant):
        """Test getting sync history"""
        from stock_tracker.db.models import SyncLog
        from datetime import datetime
        
        # Create multiple sync logs
        for i in range(3):
            sync_log = SyncLog(
                tenant_id=test_tenant.id,
                status="completed",
                started_at=datetime.utcnow(),
                products_synced=10 + i
            )
            db_session.add(sync_log)
        db_session.commit()
        
        response = client.get(
            "/api/v1/sync/history",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 3
        assert all("status" in item for item in data)


class TestCredentialsManagement:
    """Test credentials management via Telegram bot"""
    
    def test_save_credentials(self, client, auth_headers, test_tenant):
        """Test saving marketplace credentials"""
        credentials_data = {
            "marketplace": "wildberries",
            "api_key": "test-api-key-12345"
        }
        
        response = client.post(
            "/api/v1/credentials/",
            json=credentials_data,
            headers=auth_headers
        )
        
        # Credentials should be encrypted and saved
        assert response.status_code == status.HTTP_200_OK
        assert "encrypted" not in response.text.lower()  # Should not expose encryption details
    
    def test_get_credentials_status(self, client, auth_headers, db_session, test_tenant):
        """Test checking if credentials are configured"""
        response = client.get(
            "/api/v1/credentials/status",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "wildberries" in data
        assert isinstance(data["wildberries"], bool)
    
    def test_delete_credentials(self, client, auth_headers, db_session, test_tenant):
        """Test deleting credentials"""
        from stock_tracker.core.encryption import encrypt_data
        
        # Set credentials first
        test_tenant.wb_credentials_encrypted = encrypt_data("test-key")
        db_session.commit()
        
        response = client.delete(
            "/api/v1/credentials/wildberries",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify deleted
        db_session.refresh(test_tenant)
        assert test_tenant.wb_credentials_encrypted is None


class TestCaching:
    """Test caching functionality"""
    
    @patch("stock_tracker.services.product_service.ProductService.sync_all_products")
    def test_sync_results_cached(self, mock_sync, client, auth_headers, cache, test_tenant):
        """Test that sync results are cached"""
        mock_sync.return_value = {
            "products_synced": 10,
            "updated_count": 5,
            "error_count": 0,
            "duration_seconds": 2.5
        }
        
        # First request - should hit service
        response1 = client.get(
            "/api/v1/products/",
            headers=auth_headers
        )
        
        # Second request - should hit cache
        response2 = client.get(
            "/api/v1/products/",
            headers=auth_headers
        )
        
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK
        
        # Service should be called only once
        assert mock_sync.call_count == 1
    
    def test_cache_invalidation_on_sync(self, client, auth_headers, cache, test_tenant):
        """Test that cache is invalidated after sync"""
        # Get products (cache)
        client.get("/api/v1/products/", headers=auth_headers)
        
        # Trigger sync
        client.post("/api/v1/products/sync", headers=auth_headers)
        
        # Cache should be invalidated
        cache_key = f"tenant:{test_tenant.id}:products"
        cached = cache.get(cache_key)
        assert cached is None


class TestRateLimiting:
    """Test rate limiting"""
    
    def test_rate_limit_enforced(self, client, auth_headers):
        """Test that rate limits are enforced"""
        import time
        
        # Make requests until rate limit
        responses = []
        for i in range(150):  # Exceed tenant limit of 100/min
            response = client.get("/api/v1/products/", headers=auth_headers)
            responses.append(response.status_code)
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                break
            time.sleep(0.01)  # Small delay
        
        # Should eventually get rate limited
        assert status.HTTP_429_TOO_MANY_REQUESTS in responses
    
    def test_rate_limit_headers(self, client, auth_headers):
        """Test rate limit headers are present"""
        response = client.get("/api/v1/products/", headers=auth_headers)
        
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
