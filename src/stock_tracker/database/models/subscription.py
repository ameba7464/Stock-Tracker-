"""
Subscription model - billing and plan management.
"""

import enum
from datetime import datetime
import uuid

from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class PlanType(str, enum.Enum):
    """Subscription plan types."""
    FREE = "free"           # 100 requests/hour, 100 products max
    STARTER = "starter"     # 500 requests/hour, 500 products, $10/month
    PRO = "pro"             # 1000 requests/hour, 5000 products, $50/month
    ENTERPRISE = "enterprise"  # Unlimited, custom pricing


class SubscriptionStatus(str, enum.Enum):
    """Subscription status."""
    ACTIVE = "active"
    TRIAL = "trial"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"


class Subscription(Base):
    """
    Subscription and billing information for a tenant.
    """
    
    __tablename__ = "subscriptions"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Tenant Relationship
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Plan Information
    plan_type = Column(SQLEnum(PlanType, name="plan_type"), nullable=False, default=PlanType.FREE)
    status = Column(SQLEnum(SubscriptionStatus, name="subscription_status"), nullable=False, default=SubscriptionStatus.TRIAL)
    
    # Stripe Integration
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True, index=True)
    
    # Usage Tracking
    quota_used = Column(Integer, default=0, nullable=False)  # Requests used in current billing period
    quota_limit = Column(Integer, default=100, nullable=False)  # Based on plan
    
    # Billing
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="subscription")
    
    def __repr__(self):
        return f"<Subscription(tenant_id={self.tenant_id}, plan={self.plan_type.value}, status={self.status.value})>"
    
    def is_quota_exceeded(self) -> bool:
        """Check if quota is exceeded."""
        return self.quota_used >= self.quota_limit
    
    def increment_quota(self) -> None:
        """Increment quota usage."""
        self.quota_used += 1
