"""
Analytics and Dashboard API routes.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from stock_tracker.database.connection import get_db
from stock_tracker.database.models import Tenant, User
from stock_tracker.api.middleware.tenant_context import get_current_user, get_current_tenant
from stock_tracker.services.analytics_service import AnalyticsService
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class DashboardSummary(BaseModel):
    """Dashboard summary response."""
    total_products: int
    total_stock: int
    total_orders: int
    low_stock_count: int
    out_of_stock_count: int
    average_stock_per_product: float
    last_sync: Dict[str, Any] | None
    health_score: float


class LowStockProduct(BaseModel):
    """Low stock product response."""
    id: str
    marketplace_article: str
    seller_article: str | None
    product_name: str | None
    total_stock: int
    total_orders: int
    updated_at: str | None


class TopProduct(BaseModel):
    """Top product response."""
    id: str
    marketplace_article: str
    seller_article: str | None
    product_name: str | None
    total_stock: int
    total_orders: int
    stock_to_orders_ratio: float | None


class SyncHistoryItem(BaseModel):
    """Sync history item."""
    id: str
    started_at: str
    completed_at: str | None
    status: str
    products_synced: int | None
    duration_ms: int | None
    message: str | None


class StockDistribution(BaseModel):
    """Stock distribution response."""
    out_of_stock: int
    critical: int
    low: int
    medium: int
    good: int
    excellent: int


class WarehouseStats(BaseModel):
    """Warehouse statistics."""
    warehouse_name: str
    total_stock: int
    total_orders: int
    product_count: int


@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get dashboard summary with key metrics.
    """
    logger.info(f"Dashboard requested by user {user.id} for tenant {tenant.id}")
    
    analytics = AnalyticsService(tenant=tenant, db_session=db)
    summary = analytics.get_dashboard_summary()
    
    return DashboardSummary(**summary)


@router.get("/low-stock", response_model=List[LowStockProduct])
async def get_low_stock_products(
    threshold: int = Query(10, ge=0, le=100, description="Stock threshold"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get products with low stock levels.
    """
    logger.info(f"Low stock products requested (threshold={threshold})")
    
    analytics = AnalyticsService(tenant=tenant, db_session=db)
    products = analytics.get_low_stock_products(threshold=threshold, limit=limit)
    
    return [LowStockProduct(**p) for p in products]


@router.get("/top-products", response_model=List[TopProduct])
async def get_top_products(
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get top products by order count.
    """
    logger.info(f"Top products requested (limit={limit})")
    
    analytics = AnalyticsService(tenant=tenant, db_session=db)
    products = analytics.get_top_products_by_orders(limit=limit)
    
    return [TopProduct(**p) for p in products]


@router.get("/sync-history", response_model=List[SyncHistoryItem])
async def get_sync_history(
    days: int = Query(7, ge=1, le=90, description="Days to look back"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get sync history for the past N days.
    """
    logger.info(f"Sync history requested (days={days})")
    
    analytics = AnalyticsService(tenant=tenant, db_session=db)
    history = analytics.get_sync_history(days=days, limit=limit)
    
    return [SyncHistoryItem(**h) for h in history]


@router.get("/stock-distribution", response_model=StockDistribution)
async def get_stock_distribution(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get stock distribution across different ranges.
    """
    logger.info("Stock distribution requested")
    
    analytics = AnalyticsService(tenant=tenant, db_session=db)
    distribution = analytics.get_stock_distribution()
    
    return StockDistribution(**distribution)


@router.get("/warehouses", response_model=List[WarehouseStats])
async def get_warehouse_breakdown(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get stock breakdown by warehouse.
    """
    logger.info("Warehouse breakdown requested")
    
    analytics = AnalyticsService(tenant=tenant, db_session=db)
    warehouses = analytics.get_warehouse_breakdown()
    
    return [WarehouseStats(**w) for w in warehouses]
