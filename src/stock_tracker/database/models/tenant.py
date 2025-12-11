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
    Simplified tenant model matching cloud database structure.
    
    Each tenant represents an organizational unit with users.
    """
    
    __tablename__ = "tenants"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic Information
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="tenant", lazy="selectin")
    
    def __repr__(self):
        return f"<Tenant(id={self.id}, name='{self.name}', slug='{self.slug}')>"
