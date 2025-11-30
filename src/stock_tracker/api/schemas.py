"""
Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class UserRole(str, Enum):
    """User roles."""
    OWNER = "owner"
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class MarketplaceType(str, Enum):
    """Marketplace types."""
    WILDBERRIES = "wildberries"
    OZON = "ozon"


class SubscriptionPlan(str, Enum):
    """Subscription plans."""
    FREE = "FREE"
    STARTER = "STARTER"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


# User schemas
class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    role: UserRole = UserRole.USER


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    """User response schema."""
    id: str
    tenant_id: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Tenant schemas
class TenantBase(BaseModel):
    """Base tenant schema."""
    name: str = Field(..., min_length=2, max_length=255)
    marketplace_type: MarketplaceType


class TenantCreate(TenantBase):
    """Tenant creation schema."""
    pass


class TenantResponse(TenantBase):
    """Tenant response schema."""
    id: str
    is_active: bool
    google_sheet_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Auth schemas
class RegisterRequest(BaseModel):
    """Registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    company_name: str = Field(..., min_length=2, max_length=255)
    marketplace_type: MarketplaceType = MarketplaceType.WILDBERRIES


class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


# Product schemas
class ProductBase(BaseModel):
    """Base product schema."""
    sku: str
    name: str
    stock_quantity: int


class ProductResponse(ProductBase):
    """Product response schema."""
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
