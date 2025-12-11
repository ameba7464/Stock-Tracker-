"""
WebhookConfig model - webhook configuration per tenant.
"""

from datetime import datetime
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .base import Base


class WebhookConfig(Base):
    """
    Webhook configuration for tenant notifications.
    
    Supports events: sync_completed, sync_failed, low_stock_alert
    """
    
    __tablename__ = "webhook_configs"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Tenant Relationship
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Webhook Configuration
    url = Column(String(2048), nullable=False)
    secret = Column(String(255), nullable=False)  # For HMAC signature
    events = Column(JSONB, nullable=False)  # Array of event types to listen to
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Circuit Breaker State
    failure_count = Column(Integer, default=0, nullable=False)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant")
    
    def __repr__(self):
        return f"<WebhookConfig(id={self.id}, tenant_id={self.tenant_id}, url='{self.url[:50]}...', active={self.is_active})>"
    
    def increment_failure(self) -> None:
        """Increment failure count and update timestamp."""
        self.failure_count += 1
        self.last_failure_at = datetime.utcnow()
        
        # Disable webhook after 5 consecutive failures
        if self.failure_count >= 5:
            self.is_active = False
    
    def reset_failures(self) -> None:
        """Reset failure count on successful delivery."""
        self.failure_count = 0
        self.last_failure_at = None
