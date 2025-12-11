"""
Subscription model - simple access control.
"""

from datetime import datetime
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class Subscription(Base):
    """
    Simple subscription model - has access or not.
    """
    
    __tablename__ = "subscriptions"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User Relationship (changed from tenant to user)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Simple Access Control
    has_access = Column(Boolean, nullable=False, default=False)  # Access to table or not
    status = Column(String, nullable=False, default='unpaid')  # 'paid' or 'unpaid'
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscription")
    
    def __repr__(self):
        return f"<Subscription(user_id={self.user_id}, has_access={self.has_access}, status={self.status})>"
    
    def grant_access(self) -> None:
        """Grant access and set status to paid."""
        self.has_access = True
        self.status = 'paid'
    
    def revoke_access(self) -> None:
        """Revoke access and set status to unpaid."""
        self.has_access = False
        self.status = 'unpaid'
