"""
Product management routes.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from stock_tracker.database.connection import get_db
from stock_tracker.database.models import Tenant, User, Product
from stock_tracker.api.middleware.tenant_context import get_current_user, get_current_tenant
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ProductResponse(BaseModel):
    """Product information response."""
    id: str
    marketplace_article: str
    seller_article: Optional[str] = None
    product_name: Optional[str] = None
    total_stock: int = 0
    total_orders: int = 0
    in_way_to_client: int = 0
    in_way_from_client: int = 0
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProductDetailResponse(ProductResponse):
    """Detailed product information."""
    warehouse_data: Optional[dict] = None
    created_at: Optional[datetime] = None


class ProductListResponse(BaseModel):
    """Paginated product list."""
    items: List[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("/", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by article or name"),
    min_stock: Optional[int] = Query(None, ge=0, description="Minimum stock level"),
    max_stock: Optional[int] = Query(None, ge=0, description="Maximum stock level"),
    low_stock_only: bool = Query(False, description="Show only low stock products"),
    sort_by: str = Query("updated_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List products with filtering, search, and pagination.
    """
    logger.info(f"Listing products for tenant {tenant.id} (page={page}, size={page_size})")
    
    # Base query
    query = db.query(Product).filter(Product.tenant_id == tenant.id)
    
    # Search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Product.marketplace_article.ilike(search_pattern),
                Product.seller_article.ilike(search_pattern),
                Product.product_name.ilike(search_pattern)
            )
        )
    
    # Stock filters
    if low_stock_only:
        query = query.filter(Product.total_stock < 10)
    elif min_stock is not None or max_stock is not None:
        if min_stock is not None:
            query = query.filter(Product.total_stock >= min_stock)
        if max_stock is not None:
            query = query.filter(Product.total_stock <= max_stock)
    
    # Sorting
    sort_field = getattr(Product, sort_by, Product.updated_at)
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_field))
    else:
        query = query.order_by(sort_field)
    
    # Count total
    total = query.count()
    
    # Pagination
    offset = (page - 1) * page_size
    products = query.offset(offset).limit(page_size).all()
    
    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size
    
    return ProductListResponse(
        items=[ProductResponse.from_orm(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product(
    product_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed product information.
    """
    product = db.query(Product).filter(
        and_(
            Product.id == product_id,
            Product.tenant_id == tenant.id
        )
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return ProductDetailResponse.from_orm(product)


@router.post("/sync")
async def sync_products(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger product synchronization from marketplace.
    
    Dispatches Celery task to sync products asynchronously.
    """
    if user.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can trigger sync"
        )
    
    logger.info(f"Sync triggered for tenant {tenant.id}")
    
    # Dispatch Celery task for async processing
    from stock_tracker.workers.tasks import sync_tenant_products
    task = sync_tenant_products.delay(str(tenant.id))
    
    return {
        "message": "Sync started",
        "tenant_id": str(tenant.id),
        "task_id": task.id,
        "status": "pending"
    }
