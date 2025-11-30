"""
Integration tests for authentication flow
"""
import pytest
from fastapi import status


class TestAuthenticationFlow:
    """Test complete authentication flow"""
    
    def test_register_user(self, client, test_user_data):
        """Test user registration"""
        response = client.post(
            "/api/v1/auth/register",
            json=test_user_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["email"] == test_user_data["email"]
        assert "hashed_password" not in data
    
    def test_register_duplicate_email(self, client, test_user, test_user_data):
        """Test registration with duplicate email"""
        response = client.post(
            "/api/v1/auth/register",
            json=test_user_data
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()
    
    def test_login_success(self, client, test_user, test_user_data):
        """Test successful login"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client, test_user, test_user_data):
        """Test login with wrong password"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user_data["email"],
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent email"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "SomePassword123!"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user(self, client, test_user, auth_headers):
        """Test getting current user info"""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user.email
        assert data["tenant_id"] == str(test_user.tenant_id)
    
    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without token"""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_refresh_token(self, client, test_user, test_user_data):
        """Test token refresh"""
        # Login first
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"]
            }
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_logout(self, client, auth_headers):
        """Test logout"""
        response = client.post(
            "/api/v1/auth/logout",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Successfully logged out"


class TestTenantContext:
    """Test tenant context middleware"""
    
    def test_tenant_context_set(self, client, test_user, auth_headers):
        """Test that tenant context is set from JWT"""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        # Tenant context should be available in request
    
    def test_requests_isolated_by_tenant(self, client, db_session):
        """Test that tenant data is isolated"""
        # Create two tenants
        from stock_tracker.db.models import Tenant, User
        from stock_tracker.core.security import get_password_hash, create_access_token
        
        tenant1 = Tenant(company_name="Company 1", is_active=True)
        tenant2 = Tenant(company_name="Company 2", is_active=True)
        db_session.add_all([tenant1, tenant2])
        db_session.commit()
        
        user1 = User(
            email="user1@company1.com",
            hashed_password=get_password_hash("password"),
            tenant_id=tenant1.id,
            is_active=True
        )
        user2 = User(
            email="user2@company2.com",
            hashed_password=get_password_hash("password"),
            tenant_id=tenant2.id,
            is_active=True
        )
        db_session.add_all([user1, user2])
        db_session.commit()
        
        token1 = create_access_token({"sub": user1.email, "tenant_id": str(tenant1.id)})
        token2 = create_access_token({"sub": user2.email, "tenant_id": str(tenant2.id)})
        
        # Each user should only see their own tenant data
        response1 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})
        response2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token2}"})
        
        assert response1.json()["tenant_id"] == str(tenant1.id)
        assert response2.json()["tenant_id"] == str(tenant2.id)
