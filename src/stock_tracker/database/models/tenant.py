"""
Tenant model - represents a seller account with marketplace credentials.
"""

import enum
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .base import Base


class MarketplaceType(str, enum.Enum):
    """Supported marketplace types."""
    WILDBERRIES = "wildberries"
    OZON = "ozon"


class Tenant(Base):
    """
    Tenant (seller account) with marketplace credentials.
    
    Each tenant has:
    - Isolated Google Sheet for data storage
    - Encrypted marketplace API credentials
    - Subscription and billing information
    - Auto-sync configuration
    """
    
    __tablename__ = "tenants"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic Information
    name = Column(String(255), nullable=False)
    marketplace_type = Column(
        SQLEnum(MarketplaceType, name="marketplace_type"),
        nullable=False,
        default=MarketplaceType.WILDBERRIES
    )
    
    # Encrypted Credentials (stored as JSONB for flexibility)
    # For Wildberries: {"api_key": "encrypted_value"}
    # For Ozon: {"client_id": "...", "api_key": "...", "seller_id": "..."}
    credentials_encrypted = Column(JSONB, nullable=True)  # Can be set later
    
    # Google Sheets Configuration
    google_sheet_id = Column(String(255), nullable=True)  # Can be set later
    google_service_account_encrypted = Column(Text, nullable=True)  # Can be set later
    
    # Auto-Sync Configuration
    auto_sync_enabled = Column(Boolean, default=True, nullable=False)
    sync_schedule = Column(String(100), default="0 */6 * * *")  # Cron expression, every 6 hours
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="tenant", lazy="selectin")
    subscription = relationship("Subscription", back_populates="tenant", uselist=False, lazy="selectin")
    sync_logs = relationship("SyncLog", back_populates="tenant", lazy="dynamic")
    webhook_configs = relationship("WebhookConfig", back_populates="tenant", lazy="selectin")
    products = relationship("Product", back_populates="tenant", lazy="dynamic")
    
    # Indexes for common queries
    __table_args__ = (
        Index("ix_tenants_marketplace_type_active", "marketplace_type", "is_active"),
        Index("ix_tenants_last_sync", "last_sync_at"),
    )
    
    def __repr__(self):
        return f"<Tenant(id={self.id}, name='{self.name}', marketplace={self.marketplace_type.value})>"
