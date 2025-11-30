"""
User model - team members with role-based access control.
"""

import enum
from datetime import datetime
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class UserRole(str, enum.Enum):
    """User roles with different permission levels."""
    OWNER = "owner"      # Full access, billing management
    ADMIN = "admin"      # Can manage users and settings
    USER = "user"        # Can trigger syncs and view data
    VIEWER = "viewer"    # Read-only access


class User(Base):
    """
    User account with role-based access to tenant data.
    
    Each user belongs to one tenant and has a specific role.
    """
    
    __tablename__ = "users"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(255), nullable=True)
    
    # Tenant Relationship
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(SQLEnum(UserRole, name="user_role"), nullable=False, default=UserRole.USER)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)  # Email verification
    
    # Activity Tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user", lazy="dynamic")
    
    # Indexes
    __table_args__ = (
        Index("ix_users_tenant_role", "tenant_id", "role"),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role={self.role.value})>"
