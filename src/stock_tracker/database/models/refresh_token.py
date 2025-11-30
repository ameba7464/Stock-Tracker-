"""
RefreshToken model - JWT refresh token management.
"""

from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class RefreshToken(Base):
    """
    Refresh token for JWT authentication.
    
    Stores hashed refresh tokens to enable revocation.
    """
    
    __tablename__ = "refresh_tokens"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User Relationship
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Token Information
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    
    # Device/Session Information
    device_info = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    
    # Status
    is_revoked = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
    
    # Indexes
    __table_args__ = (
        Index("ix_refresh_tokens_expires", "expires_at"),
        Index("ix_refresh_tokens_user_active", "user_id", "is_revoked"),
    )
    
    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, revoked={self.is_revoked})>"
    
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if token is valid (not expired, not revoked)."""
        return not self.is_revoked and not self.is_expired()
