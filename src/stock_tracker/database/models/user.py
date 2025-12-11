"""
User model - unified structure for Telegram bot and admin panel.
"""

import enum
from datetime import datetime
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Index, BigInteger, Text, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class UserRole(str, enum.Enum):
    """User roles with different permission levels."""
    OWNER = "OWNER"      # Full access, billing management
    ADMIN = "ADMIN"      # Can manage users and settings
    USER = "USER"        # Can trigger syncs and view data
    VIEWER = "VIEWER"    # Read-only access


class PaymentStatus(str, enum.Enum):
    """Payment and subscription status."""
    FREE = "FREE"
    TRIAL = "TRIAL"
    PAID = "PAID"
    EXPIRED = "EXPIRED"


class User(Base):
    """
    Unified user model combining Telegram bot and admin panel functionality.
    
    Each user can have:
    - Email/password authentication (for admin panel)
    - Telegram integration (for bot access)
    - Wildberries API integration
    - Google Sheets integration
    - Multi-tenancy support
    """
    
    __tablename__ = "users"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # NULL for telegram-only users
    
    # Telegram Integration
    telegram_id = Column(BigInteger, unique=True, nullable=True, index=True)
    telegram_username = Column(String(100), nullable=True)
    
    # Profile
    full_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Wildberries Integration
    wb_api_key = Column(Text, nullable=True)
    wb_api_key_encrypted = Column(Text, nullable=True)  # Encrypted version
    
    # Google Sheets Integration
    google_sheet_id = Column(String(255), nullable=True)
    google_sheet_sent = Column(Boolean, default=False, nullable=False)
    
    # Tenant Relationship
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    role = Column(SQLEnum(UserRole, name="user_role"), nullable=False, default=UserRole.USER)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False, index=True)
    
    # Payment & Subscription
    payment_status = Column(SQLEnum(PaymentStatus, name="payment_status_enum"), nullable=False, default=PaymentStatus.FREE, index=True)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    
    # Activity Tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    
    # Activity Tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user", lazy="dynamic")
    subscription = relationship("Subscription", back_populates="user", uselist=False, lazy="selectin")
    
    # Indexes
    __table_args__ = (
        Index("ix_users_tenant_role", "tenant_id", "role"),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role={self.role.value})>"
