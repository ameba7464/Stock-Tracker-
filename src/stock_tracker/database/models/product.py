"""
Product model for storing marketplace product data.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Index, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .base import Base


class Product(Base):
    """
    Product from marketplace (Wildberries, Ozon, etc.).
    
    Stores product data synced from marketplace APIs with:
    - Multi-tenant isolation via tenant_id
    - Stock and order analytics
    - Warehouse breakdown (JSONB)
    - Historical tracking
    """
    
    __tablename__ = "products"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign keys
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Marketplace identifiers
    marketplace_article = Column(String(100), nullable=False, index=True)  # nmID for WB, SKU for Ozon
    seller_article = Column(String(255), nullable=False)  # Seller's internal SKU
    nm_id = Column(Integer, index=True)  # nmID (Wildberries article number) - alias for marketplace_article
    wildberries_article = Column(Integer, index=True)  # Alternative alias for nmID
    
    # Product details
    name = Column(String(500))
    product_name = Column(String(500))  # Alias for name
    brand = Column(String(255))
    brand_name = Column(String(255))  # Alias for brand
    category = Column(String(255))
    subject = Column(String(255))  # Category/subject name
    subject_id = Column(Integer)  # Category/subject ID
    size = Column(String(100))
    barcode = Column(String(100))
    vendor_code = Column(String(255))  # Seller's vendor code - alias for seller_article
    
    # Stock data
    total_stock = Column(Integer, default=0)
    available_stock = Column(Integer, default=0)  # Available for sale
    reserved_stock = Column(Integer, default=0)   # Reserved by orders
    stocks_total = Column(Integer, default=0)  # Alias for total_stock
    stocks_wb = Column(Integer, default=0)  # Stock on WB warehouses
    stocks_mp = Column(Integer, default=0)  # Stock on MP warehouses
    fbo_stock = Column(Integer, default=0)  # Fulfillment by Ozon/WB
    fbs_stock = Column(Integer, default=0)  # Fulfillment by Seller
    
    # Sales analytics (last 7 days typical)
    total_orders = Column(Integer, default=0)
    cancelled_orders = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)
    orders_wb_warehouses = Column(Integer, default=0)  # Orders from WB warehouses
    orders_fbs_warehouses = Column(Integer, default=0)  # Orders from FBS warehouses
    
    # Logistics
    in_way_to_client = Column(Integer, default=0)  # В пути до покупателя
    in_transit_to_customer = Column(Integer, default=0)  # Alias
    in_way_from_client = Column(Integer, default=0)  # В пути возврат на склад WB
    in_transit_to_wb_warehouse = Column(Integer, default=0)  # Alias
    
    # Analytics
    avg_orders_per_day = Column(Float, default=0.0)
    conversion_to_cart = Column(Integer, default=0)
    conversion_to_order = Column(Integer, default=0)
    buyout_percent = Column(Integer, default=0)
    avg_price = Column(Integer, default=0)
    order_sum_total = Column(Integer, default=0)
    buyout_count = Column(Integer, default=0)
    buyout_sum = Column(Integer, default=0)
    
    # Turnover calculation
    turnover_days = Column(Float)  # Days until stock runs out
    turnover = Column(Float)  # Alias for turnover_days
    
    # Metadata
    last_synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Alias
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Additional data (marketplace-specific)
    raw_data = Column(JSONB, default=dict)  # Store raw API response
    
    # Warehouse breakdown (JSONB for flexibility)
    # Structure: {"warehouses": [{"name": "...", "stock": 10, "orders": 2}, ...]}
    warehouse_data = Column(JSONB, default=dict)
    stocks_by_warehouse = Column(JSONB, default=dict)  # {"warehouse_name": stock_count}
    orders_by_warehouse = Column(JSONB, default=dict)  # {"warehouse_name": orders_count}
    
    # Relationships
    tenant = relationship("Tenant", back_populates="products")
    
    # Composite indexes for performance
    __table_args__ = (
        Index("idx_tenant_marketplace_article", "tenant_id", "marketplace_article", unique=True),
        Index("idx_tenant_seller_article", "tenant_id", "seller_article"),
        Index("idx_tenant_last_synced", "tenant_id", "last_synced_at"),
        Index("idx_tenant_active", "tenant_id", "is_active"),
    )
    
    def __repr__(self):
        return (
            f"<Product(id={self.id}, tenant={self.tenant_id}, "
            f"article={self.marketplace_article}, stock={self.total_stock})>"
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "marketplace_article": self.marketplace_article,
            "seller_article": self.seller_article,
            "name": self.name,
            "brand": self.brand,
            "category": self.category,
            "size": self.size,
            "barcode": self.barcode,
            "total_stock": self.total_stock,
            "available_stock": self.available_stock,
            "reserved_stock": self.reserved_stock,
            "total_orders": self.total_orders,
            "cancelled_orders": self.cancelled_orders,
            "revenue": self.revenue,
            "warehouse_data": self.warehouse_data,
            "turnover_days": self.turnover_days,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active,
        }
