"""
SyncLog model - history of sync operations.
"""

from datetime import datetime
import uuid

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class SyncLog(Base):
    """
    Log entry for each sync operation.
    
    Partitioned by started_at for efficient historical queries.
    """
    
    __tablename__ = "sync_logs"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Tenant Relationship
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Sync Information
    status = Column(String(50), nullable=False)  # success, failed, in_progress
    products_synced = Column(Integer, default=0)
    duration_ms = Column(Integer, nullable=True)  # Duration in milliseconds
    
    # Error Information
    error_message = Column(Text, nullable=True)
    error_code = Column(String(100), nullable=True)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="sync_logs")
    
    # Indexes for common queries
    __table_args__ = (
        Index("ix_sync_logs_tenant_started", "tenant_id", "started_at"),
        Index("ix_sync_logs_status", "status"),
        # Partition by month for large datasets (PostgreSQL 10+)
        # {'postgresql_partition_by': 'RANGE (started_at)'}
    )
    
    def __repr__(self):
        return f"<SyncLog(id={self.id}, tenant_id={self.tenant_id}, status='{self.status}', products={self.products_synced})>"
