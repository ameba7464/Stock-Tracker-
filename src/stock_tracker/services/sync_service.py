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
                # Получаем продукты из Analytics API v2
                marketplace_products = loop.run_until_complete(
                    self.marketplace_client.fetch_products(limit=1000)
                )
                
                # Получаем данные по складам из Warehouse API v1
                warehouse_data = {}
                try:
                    warehouse_remains = loop.run_until_complete(
                        self.marketplace_client.api_client.get_warehouse_remains_with_retry(max_wait_time=600)
                    )
                    # Индексируем данные по nmId для быстрого поиска
                    warehouse_data = self._index_warehouse_data(warehouse_remains)
                    logger.info(f"Fetched warehouse data for {len(warehouse_data)} products")
                except Exception as e:
                    logger.warning(f"Failed to fetch warehouse data: {e}. Products will have no warehouse breakdown.")
            finally:
                loop.close()
            
            logger.info(f"Fetched {len(marketplace_products)} products from {self.marketplace_client.marketplace_name}")
            
            # Process each product
            for mp_product in marketplace_products:
                try:
                    # Получаем данные о складах для этого товара
                    # wildberries_article — это int (nmId из API)
                    nm_id = mp_product.wildberries_article
                    product_warehouse_data = warehouse_data.get(nm_id, {})
                    
                    if product_warehouse_data:
                        logger.debug(f"Found warehouse data for nmId {nm_id}: {len(product_warehouse_data.get('warehouses', []))} warehouses")
                    
                    self._upsert_product(mp_product, product_warehouse_data)
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
    
    def _index_warehouse_data(self, warehouse_remains: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """
        Индексирует данные о складах по nmId для быстрого поиска.
        
        Args:
            warehouse_remains: Данные из Warehouse API v1
            
        Returns:
            Dict[nmId -> warehouse_data_dict]
        """
        indexed = {}
        
        # Служебные склады для исключения
        service_warehouses = {
            'В пути до получателей',
            'В пути возвраты на склад WB',
            'Всего находится на складах',
            'Остальные'
        }
        
        logger.debug(f"Indexing warehouse data from {len(warehouse_remains)} items")
        
        for item in warehouse_remains:
            nm_id = item.get("nmId")
            if not nm_id:
                continue
            
            # Обрабатываем склады из записи
            warehouses_list = []
            for wh in item.get("warehouses", []):
                wh_name = wh.get("warehouseName", "")
                if wh_name and wh_name not in service_warehouses:
                    warehouses_list.append({
                        "name": wh_name,
                        "stock": wh.get("quantity", 0),
                        "orders": 0  # API v1 не содержит заказы, добавим позже из v2
                    })
            
            if nm_id not in indexed:
                indexed[nm_id] = {"warehouses": warehouses_list}
            else:
                # Объединяем склады если продукт уже есть
                indexed[nm_id]["warehouses"].extend(warehouses_list)
        
        # Логируем статистику
        total_warehouses = sum(len(v.get("warehouses", [])) for v in indexed.values())
        logger.info(f"Indexed {len(indexed)} products with {total_warehouses} total warehouse entries")
        
        if indexed:
            sample_keys = list(indexed.keys())[:3]
            logger.debug(f"Sample indexed nmIds: {sample_keys}")
        
        return indexed
    
    def _upsert_product(self, mp_product, warehouse_data: Dict[str, Any] = None) -> Product:
        """
        Insert or update product in database.
        
        Uses SELECT FOR UPDATE to prevent race conditions during concurrent syncs.
        
        Args:
            mp_product: Product object from marketplace client
            warehouse_data: Данные о складах из Warehouse API v1
            
        Returns:
            Product database model
        """
        if warehouse_data is None:
            warehouse_data = {}
            
        # Find existing product with row-level lock (SELECT FOR UPDATE)
        # This prevents concurrent updates to the same product
        # skip_locked=False: wait for lock (default behavior)
        # nowait=True would raise error immediately if locked
        existing = self.db.query(Product).filter(
            Product.tenant_id == self.tenant.id,
            Product.marketplace_article == str(mp_product.wildberries_article)
        ).with_for_update(skip_locked=False).first()
        
        # Подготавливаем warehouse_data с заказами, распределёнными пропорционально
        wh_list = warehouse_data.get("warehouses", [])
        total_stock = sum(wh.get("stock", 0) for wh in wh_list)
        total_orders = mp_product.total_orders
        
        if total_stock > 0 and total_orders > 0:
            for wh in wh_list:
                wh_stock = wh.get("stock", 0)
                # Распределяем заказы пропорционально остаткам
                wh["orders"] = int(total_orders * (wh_stock / total_stock))
        
        warehouse_data_to_save = {"warehouses": wh_list} if wh_list else {}
        
        if existing:
            # Update existing
            existing.seller_article = mp_product.seller_article or existing.seller_article
            existing.total_stock = mp_product.total_stock
            existing.total_orders = mp_product.total_orders
            existing.warehouse_data = warehouse_data_to_save
            existing.last_synced_at = datetime.utcnow()
            logger.debug(f"Updated product {existing.marketplace_article} with {len(wh_list)} warehouses")
            return existing
        else:
            # Create new
            new_product = Product(
                tenant_id=self.tenant.id,
                marketplace_article=str(mp_product.wildberries_article),
                seller_article=mp_product.seller_article or f"WB-{mp_product.wildberries_article}",
                total_stock=mp_product.total_stock,
                total_orders=mp_product.total_orders,
                warehouse_data=warehouse_data_to_save,
                last_synced_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            self.db.add(new_product)
            logger.debug(f"Created product {new_product.marketplace_article} with {len(wh_list)} warehouses")
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
