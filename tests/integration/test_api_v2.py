"""
Integration tests for new API endpoints (FastAPI 2.0)
"""
import pytest
from fastapi import status
from unittest.mock import patch, MagicMock


class TestAuthenticationFlow:
    """Test authentication and JWT flow"""
    
    def test_register_new_user(self, client):
        """Test user registration"""
        user_data = {
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "name": "New User",
            "company_name": "New Company"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "access_token" in data
        assert "tenant_id" in data
        assert data["email"] == user_data["email"]
    
    def test_register_duplicate_email(self, client):
        """Test registration with existing email"""
        user_data = {
            "email": "test@example.com",  # Already exists from fixture
            "password": "SecurePass123!",
            "name": "Duplicate User",
            "company_name": "Duplicate Company"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"].lower()
    
    def test_login_success(self, client):
        """Test successful login"""
        credentials = {
            "email": "test@example.com",
            "password": "test123"
        }
        
        response = client.post("/api/v1/auth/login", json=credentials)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client):
        """Test login with wrong password"""
        credentials = {
            "email": "test@example.com",
            "password": "wrong_password"
        }
        
        response = client.post("/api/v1/auth/login", json=credentials)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_refresh_token(self, client, auth_headers):
        """Test refreshing access token"""
        # First login to get refresh token
        login_response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "test123"
        })
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "expires_in" in data


class TestTenantManagement:
    """Test tenant management endpoints"""
    
    def test_get_tenant_info(self, client, auth_headers, test_tenant):
        """Test getting tenant information"""
        response = client.get("/api/v1/tenant/", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(test_tenant.id)
        assert data["name"] == test_tenant.name
        assert "marketplace_type" in data
    
    def test_update_tenant_info(self, client, auth_headers):
        """Test updating tenant information"""
        update_data = {
            "name": "Updated Company Name",
            "settings": {
                "sync_interval": 60,
                "enable_notifications": True
            }
        }
        
        response = client.put(
            "/api/v1/tenant/",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == update_data["name"]
    
    def test_get_tenant_requires_auth(self, client):
        """Test tenant endpoint requires authentication"""
        response = client.get("/api/v1/tenant/")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestProductSyncEndpoints:
    """Test product synchronization endpoints"""
    
    @patch("stock_tracker.workers.tasks.sync_tenant_products")
    def test_trigger_sync(self, mock_task, client, auth_headers, test_tenant):
        """Test triggering product sync"""
        # Mock Celery task
        mock_result = MagicMock()
        mock_result.id = "test-task-id-12345"
        mock_task.delay.return_value = mock_result
        
        response = client.post(
            "/api/v1/products/sync",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Sync started"
        assert data["task_id"] == "test-task-id-12345"
        assert data["status"] == "pending"
        
        # Verify task was dispatched
        mock_task.delay.assert_called_once_with(str(test_tenant.id))
    
    def test_trigger_sync_requires_credentials(self, client, auth_headers, db_session, test_tenant):
        """Test sync fails without credentials"""
        # Remove credentials
        test_tenant.marketplace_credentials = None
        db_session.commit()
        
        response = client.post(
            "/api/v1/products/sync",
            headers=auth_headers
        )
        
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND]
        assert "credential" in response.json()["detail"].lower()
    
    def test_get_sync_status(self, client, auth_headers, db_session, test_tenant):
        """Test getting sync task status"""
        from stock_tracker.database.models import SyncLog
        from datetime import datetime
        
        # Create sync log
        sync_log = SyncLog(
            tenant_id=test_tenant.id,
            status="completed",
            started_at=datetime.utcnow(),
            products_synced=25,
            duration_ms=3500
        )
        db_session.add(sync_log)
        db_session.commit()
        
        response = client.get(
            f"/api/v1/sync/status?sync_id={sync_log.id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "completed"
        assert data["products_synced"] == 25
    
    def test_get_sync_history(self, client, auth_headers, db_session, test_tenant):
        """Test getting sync history"""
        from stock_tracker.database.models import SyncLog
        from datetime import datetime, timedelta
        
        # Create multiple sync logs
        for i in range(5):
            sync_log = SyncLog(
                tenant_id=test_tenant.id,
                status="completed" if i % 2 == 0 else "failed",
                started_at=datetime.utcnow() - timedelta(hours=i),
                products_synced=10 + i,
                duration_ms=2000 + (i * 100)
            )
            db_session.add(sync_log)
        db_session.commit()
        
        response = client.get(
            "/api/v1/sync/history?limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 5
        assert all("status" in item for item in data)
        assert all("products_synced" in item for item in data)


class TestCredentialsManagement:
    """Test marketplace credentials management"""
    
    def test_update_credentials(self, client, auth_headers, test_tenant):
        """Test updating marketplace credentials"""
        credentials_data = {
            "api_key": "new-test-api-key-67890"
        }
        
        response = client.put(
            "/api/v1/credentials/wildberries",
            json=credentials_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Credentials updated successfully"
        assert "api_key" not in data  # Should not return sensitive data
    
    def test_get_credentials_status(self, client, auth_headers, test_tenant):
        """Test checking credentials status"""
        response = client.get(
            "/api/v1/credentials/status",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "wildberries" in data
        assert isinstance(data["wildberries"], bool)
    
    def test_delete_credentials(self, client, auth_headers, db_session, test_tenant):
        """Test deleting marketplace credentials"""
        # Set credentials first
        test_tenant.marketplace_credentials = {"api_key": "test_key"}
        db_session.commit()
        
        response = client.delete(
            "/api/v1/credentials/wildberries",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify deleted
        db_session.refresh(test_tenant)
        assert test_tenant.marketplace_credentials is None


class TestProductListing:
    """Test product listing and filtering"""
    
    def test_list_products(self, client, auth_headers, db_session, test_tenant):
        """Test listing all products"""
        from stock_tracker.database.models import Product
        
        # Create test products
        for i in range(3):
            product = Product(
                tenant_id=test_tenant.id,
                marketplace_article=f"16338332{i}",
                seller_article=f"TEST-00{i}",
                product_name=f"Test Product {i}",
                total_stock=10 + i,
                total_orders=i
            )
            db_session.add(product)
        db_session.commit()
        
        response = client.get(
            "/api/v1/products/",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 3
        assert all("marketplace_article" in item for item in data)
    
    def test_list_products_pagination(self, client, auth_headers, db_session, test_tenant):
        """Test product listing with pagination"""
        from stock_tracker.database.models import Product
        
        # Create 25 test products
        for i in range(25):
            product = Product(
                tenant_id=test_tenant.id,
                marketplace_article=f"1633833{i:02d}",
                seller_article=f"TEST-{i:03d}",
                product_name=f"Test Product {i}",
                total_stock=10,
                total_orders=0
            )
            db_session.add(product)
        db_session.commit()
        
        # Get first page
        response = client.get(
            "/api/v1/products/?limit=10&offset=0",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 10
    
    def test_filter_products_by_stock(self, client, auth_headers, db_session, test_tenant):
        """Test filtering products by stock level"""
        from stock_tracker.database.models import Product
        
        # Create products with different stock levels
        product_low = Product(
            tenant_id=test_tenant.id,
            marketplace_article="163383301",
            seller_article="LOW-STOCK",
            product_name="Low Stock Product",
            total_stock=5,
            total_orders=0
        )
        product_high = Product(
            tenant_id=test_tenant.id,
            marketplace_article="163383302",
            seller_article="HIGH-STOCK",
            product_name="High Stock Product",
            total_stock=100,
            total_orders=0
        )
        db_session.add_all([product_low, product_high])
        db_session.commit()
        
        # Filter for low stock (< 10)
        response = client.get(
            "/api/v1/products/?min_stock=0&max_stock=10",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert any(p["seller_article"] == "LOW-STOCK" for p in data)
        assert not any(p["seller_article"] == "HIGH-STOCK" for p in data)


class TestHealthAndStatus:
    """Test health check and status endpoints"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "operational"
        assert "version" in data
    
    def test_api_docs_accessible(self, client):
        """Test API documentation is accessible"""
        response = client.get("/docs")
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_openapi_schema(self, client):
        """Test OpenAPI schema is available"""
        response = client.get("/openapi.json")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
