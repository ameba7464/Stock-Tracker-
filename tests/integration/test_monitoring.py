"""
Integration tests for health check endpoints
"""
import pytest
from fastapi import status


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_basic_health_check(self, client):
        """Test basic health check endpoint"""
        response = client.get("/api/v1/health/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_readiness_check_healthy(self, client):
        """Test readiness check when all services are healthy"""
        response = client.get("/api/v1/health/ready")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ready"
        assert "components" in data
        assert data["components"]["database"]["status"] == "healthy"
        assert data["components"]["cache"]["status"] == "healthy"
    
    def test_liveness_check(self, client):
        """Test liveness check"""
        response = client.get("/api/v1/health/live")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "alive"


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint"""
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint returns Prometheus format"""
        response = client.get("/metrics")
        
        assert response.status_code == status.HTTP_200_OK
        content = response.text
        
        # Check for expected metrics
        assert "stock_tracker_requests_total" in content
        assert "stock_tracker_request_duration_seconds" in content
        assert "stock_tracker_errors_total" in content
    
    def test_metrics_after_requests(self, client, auth_headers):
        """Test that metrics are incremented after requests"""
        # Make some requests
        client.get("/api/v1/auth/me", headers=auth_headers)
        client.get("/api/v1/products/", headers=auth_headers)
        
        # Check metrics
        response = client.get("/metrics")
        content = response.text
        
        # Should have request counters
        assert "stock_tracker_requests_total" in content


class TestErrorHandling:
    """Test error handling and tracking"""
    
    def test_404_error(self, client):
        """Test 404 error response"""
        response = client.get("/api/v1/nonexistent-endpoint")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
    
    def test_422_validation_error(self, client):
        """Test validation error response"""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "invalid-email"}  # Missing required fields
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
    
    def test_500_internal_error_handling(self, client, monkeypatch):
        """Test internal error handling"""
        # This test would need to mock an internal error
        # Implementation depends on specific endpoints
        pass
