"""
Sync service for Celery tasks - synchronous product synchronization.
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from stock_tracker.database.models import Tenant, Product
from stock_tracker.marketplaces.factory import create_marketplace_client
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class SyncService:
    """
    Synchronous service for product synchronization in Celery tasks.
    
    Provides blocking methods suitable for Celery workers.
    """
    
    def __init__(self, tenant: Tenant, db_session: Session):
        """
        Initialize sync service with tenant context.
        
        Args:
            tenant: Tenant instance
            db_session: Database session
        """
        self.tenant = tenant
        self.db = db_session
        self.marketplace_client = create_marketplace_client(tenant)
        logger.info(f"SyncService initialized for tenant {tenant.id} ({tenant.name})")
    
    def sync_products(self) -> Dict[str, Any]:
        """
        Synchronize products from marketplace to database.
        
        Returns:
            dict with sync statistics:
                - products_synced: Total products processed
                - products_created: New products created
                - products_updated: Existing products updated
                - errors: List of error messages
        """
        start_time = datetime.utcnow()
        stats = {
            "products_synced": 0,
            "products_created": 0,
            "products_updated": 0,
            "errors": [],
        }
        
        try:
            logger.info(f"Starting product sync for tenant {self.tenant.id}")
            
            # Fetch products from marketplace (async method, need to run in event loop)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                marketplace_products = loop.run_until_complete(
                    self.marketplace_client.fetch_products(limit=1000)
                )
            finally:
                loop.close()
            
            logger.info(f"Fetched {len(marketplace_products)} products from {self.marketplace_client.marketplace_name}")
            
            # Process each product
            for mp_product in marketplace_products:
                try:
                    self._upsert_product(mp_product)
                    stats["products_synced"] += 1
                except Exception as e:
                    error_msg = f"Failed to sync product {mp_product.wildberries_article}: {e}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)
            
            # Commit all changes
            self.db.commit()
            
            # Update tenant's last_sync_at
            self.tenant.last_sync_at = datetime.utcnow()
            self.db.commit()
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"Sync completed for tenant {self.tenant.id}: "
                f"{stats['products_synced']} products synced in {duration:.2f}s"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Sync failed for tenant {self.tenant.id}: {e}")
            self.db.rollback()
            raise
    
    def _upsert_product(self, mp_product) -> Product:
        """
        Insert or update product in database.
        
        Args:
            mp_product: Product object from marketplace client
            
        Returns:
            Product database model
        """
        # Find existing product
        existing = self.db.query(Product).filter(
            Product.tenant_id == self.tenant.id,
            Product.marketplace_article == str(mp_product.wildberries_article)
        ).first()
        
        if existing:
            # Update existing
            existing.seller_article = mp_product.seller_article or existing.seller_article
            existing.total_stock = mp_product.total_stock
            existing.total_orders = mp_product.total_orders
            existing.last_synced_at = datetime.utcnow()
            logger.debug(f"Updated product {existing.marketplace_article}")
            return existing
        else:
            # Create new
            new_product = Product(
                tenant_id=self.tenant.id,
                marketplace_article=str(mp_product.wildberries_article),
                seller_article=mp_product.seller_article or f"WB-{mp_product.wildberries_article}",
                total_stock=mp_product.total_stock,
                total_orders=mp_product.total_orders,
                last_synced_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            self.db.add(new_product)
            logger.debug(f"Created product {new_product.marketplace_article}")
            return new_product
    
    def get_product_count(self) -> int:
        """Get total product count for tenant."""
        return self.db.query(Product).filter(
            Product.tenant_id == self.tenant.id,
            Product.is_active == True
        ).count()
    
    def get_recent_syncs(self, days: int = 7) -> List[Product]:
        """
        Get products synced in the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of Product models
        """
        since = datetime.utcnow() - timedelta(days=days)
        return self.db.query(Product).filter(
            Product.tenant_id == self.tenant.id,
            Product.last_synced_at >= since
        ).all()
