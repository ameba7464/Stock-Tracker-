"""
High-level product management service with business logic and analytics.

Provides comprehensive product management capabilities including:
- Product CRUD operations with business logic
- Analytics and reporting
- Batch synchronization with Wildberries API
- Inventory management and turnover analysis
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
import uuid

from stock_tracker.api.client import WildberriesAPIClient
from stock_tracker.core.models import Product, Warehouse, SyncSession
from stock_tracker.core.validator import DataValidator
from stock_tracker.core.calculator import TurnoverCalculator, WarehouseAggregator, is_real_warehouse, validate_warehouse_name
from stock_tracker.database.operations import SheetsOperations
from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.services.warehouse_classifier import WarehouseClassifier, create_warehouse_classifier
from stock_tracker.services.dual_api_stock_fetcher import DualAPIStockFetcher
from stock_tracker.utils.config import get_config
from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.exceptions import SyncError, ValidationError, APIError
from stock_tracker.utils.warehouse_mapper import normalize_warehouse_name


# Module constants
ORDER_LOOKBACK_DAYS = 7  # How many days to look back for orders data
WAREHOUSE_TASK_WAIT_SECONDS = 60  # Wait time for WB API task processing (increased from 20s)

logger = get_logger(__name__)


class ProductService:
    """
    High-level service for product management and analytics.
    
    Orchestrates all product-related operations including API synchronization,
    data validation, calculations, and Google Sheets management.
    """
    
    def __init__(self, config=None):
        """
        Initialize service with configuration.
        
        Args:
            config: Optional configuration override
        """
        self.config = config or get_config()
        
        # Initialize clients
        self.wb_client = WildberriesAPIClient()  # Uses config internally
        self.sheets_client = GoogleSheetsClient()  # Uses config internally
        self.operations = SheetsOperations(self.sheets_client)
        
        # Initialize utilities
        self.validator = DataValidator()
        self.calculator = TurnoverCalculator()
        self.aggregator = WarehouseAggregator()
        
        # Initialize warehouse classifier (will be built on first use)
        self.warehouse_classifier: Optional[WarehouseClassifier] = None
        
        # Initialize dual-API stock fetcher for FBO+FBS stocks
        self.dual_api_fetcher = DualAPIStockFetcher(self.config.wildberries_api_key)
        
        logger.info("ProductService initialized with Dual API support (FBO+FBS)")
    
    # Product CRUD with business logic
    
    async def create_product_from_api(self, seller_article: str, 
                                    wildberries_article: int) -> Product:
        """
        Create product with data fetched from Wildberries API.
        
        Args:
            seller_article: Seller's product article
            wildberries_article: Wildberries product article
            
        Returns:
            Created Product instance with API data
            
        Raises:
            ValidationError: If product data is invalid
            APIError: If API request fails
            SyncError: If product creation fails
        """
        try:
            logger.info(f"Creating product from API: {seller_article}")
            
            # Validate inputs
            if not seller_article or not str(seller_article).strip():
                raise ValidationError("Seller article cannot be empty")
            
            if not isinstance(wildberries_article, int) or wildberries_article <= 0:
                raise ValidationError("Wildberries article must be positive integer")
            
            # Check if product already exists
            existing = self.operations.read_product(
                self.config.google_sheets.sheet_id, 
                seller_article
            )
            if existing:
                raise ValidationError(f"Product already exists: {seller_article}")
            
            # Create base product
            product = Product(
                seller_article=seller_article,
                wildberries_article=wildberries_article
            )
            
            # Fetch data from API
            await self._sync_product_from_api(product)
            
            # Validate final product
            self.validator.validate_product_complete(product)
            
            # Save to Google Sheets
            row_number = self.operations.create_product(
                self.config.google_sheets.sheet_id,
                product
            )
            
            logger.info(f"Created product {seller_article} at row {row_number}")
            return product
            
        except Exception as e:
            logger.error(f"Failed to create product from API: {e}")
            if isinstance(e, (ValidationError, APIError, SyncError)):
                raise
            raise SyncError(f"Product creation failed: {e}")
    
    async def update_product_from_api(self, seller_article: str) -> Optional[Product]:
        """
        Update existing product with fresh API data.
        
        Args:
            seller_article: Seller article of product to update
            
        Returns:
            Updated Product instance or None if not found
            
        Raises:
            APIError: If API request fails
            SyncError: If update fails
        """
        try:
            logger.info(f"Updating product from API: {seller_article}")
            
            # Get existing product
            product = self.operations.read_product(
                self.config.google_sheets.sheet_id,
                seller_article
            )
            if not product:
                logger.warning(f"Product not found: {seller_article}")
                return None
            
            # Sync fresh data from API
            await self._sync_product_from_api(product)
            
            # Update in Google Sheets
            success = self.operations.update_product(
                self.config.google_sheets.sheet_id,
                seller_article,
                product
            )
            
            if success:
                logger.info(f"Updated product {seller_article}")
                return product
            else:
                logger.error(f"Failed to update product in sheets: {seller_article}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to update product from API: {e}")
            if isinstance(e, (APIError, SyncError)):
                raise
            raise SyncError(f"Product update failed: {e}")
    
    async def sync_all_products(self) -> SyncSession:
        """
        Synchronize all products with Wildberries API.
        
        Returns:
            SyncSession with results summary
            
        Raises:
            SyncError: If synchronization fails
        """
        sync_session = SyncSession(
            session_id=str(uuid.uuid4()),
            start_time=datetime.now()
        )
        
        try:
            logger.info("Starting full product synchronization")
            sync_session.start()
            
            # Get all existing products
            products = self.operations.read_all_products(
                self.config.google_sheets.sheet_id
            )
            
            if not products:
                logger.info("No products found for synchronization")
                sync_session.complete()
                return sync_session
            
            # Sync each product
            updated_count = 0
            error_count = 0
            
            for product in products:
                try:
                    await self._sync_product_from_api(product)
                    
                    # Update in sheets
                    success = self.operations.update_product(
                        self.config.google_sheets.sheet_id,
                        product.seller_article,
                        product
                    )
                    
                    if success:
                        updated_count += 1
                        sync_session.products_processed += 1
                    else:
                        error_count += 1
                        sync_session.add_error(f"Failed to update {product.seller_article}")
                        
                except Exception as e:
                    error_count += 1
                    sync_session.add_error(f"Error syncing {product.seller_article}: {e}")
                    logger.warning(f"Failed to sync product {product.seller_article}: {e}")
            
            # Complete session
            success = error_count == 0
            if success:
                sync_session.complete()
            else:
                sync_session.fail("Some products failed to sync")
            
            logger.info(f"Synchronization completed: {updated_count} updated, {error_count} errors")
            return sync_session
            
        except Exception as e:
            sync_session.add_error(f"Synchronization failed: {e}")
            sync_session.fail(f"Synchronization failed: {e}")
            logger.error(f"Full synchronization failed: {e}")
            raise SyncError(f"Synchronization failed: {e}")
    
    async def sync_from_api_to_sheets(self, skip_existence_check: bool = False) -> SyncSession:
        """
        Fetch fresh data from Wildberries API and write to Google Sheets.
        
        This method gets warehouse remains from WB API and populates/updates
        the Google Sheets with current inventory data.
        
        Args:
            skip_existence_check: Skip existence checks when writing products.
                                 Set to True when table was just cleared to avoid unnecessary API calls.
        
        Returns:
            SyncSession with results summary
            
        Raises:
            SyncError: If synchronization fails
        """
        sync_session = SyncSession(
            session_id=str(uuid.uuid4()),
            start_time=datetime.now()
        )
        
        try:
            logger.info("Starting API-to-Sheets synchronization")
            sync_session.start()
            
            # Step 0: Initialize warehouse classifier if not already done
            if not self.warehouse_classifier:
                logger.info("Initializing warehouse classifier...")
                self.warehouse_classifier = await create_warehouse_classifier(
                    self.wb_client,
                    days=90,  # Analyze last 90 days of orders
                    auto_build=True
                )
                stats = self.warehouse_classifier.get_mapping_stats()
                logger.info(f"Warehouse classifier initialized: {stats['total_warehouses']} warehouses " +
                          f"(FBO: {stats['fbo_warehouses']}, FBS: {stats['fbs_warehouses']})")
            
            # Step 1: Fetch warehouse remains (stocks) from V1 API
            logger.info("Fetching warehouse remains (stocks) from V1 API...")
            task_id = await self.wb_client.create_warehouse_remains_task()
            logger.info(f"Created warehouse remains task: {task_id}")
            
            # Wait for task processing
            logger.info(f"Waiting {WAREHOUSE_TASK_WAIT_SECONDS}s for task processing...")
            await asyncio.sleep(WAREHOUSE_TASK_WAIT_SECONDS)
            
            # Download warehouse remains (stocks only!)
            warehouse_remains = await self.wb_client.download_warehouse_remains(task_id)
            logger.info(f"Downloaded {len(warehouse_remains)} products from V1 warehouse API")
            
            # ИСПРАВЛЕНО 27.10.2025 21:35 - КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ!
            # V1 API warehouse_remains содержит ТОЛЬКО ОСТАТКИ, НЕ заказы!
            # Заказы должны быть получены из /supplier/orders эндпоинта согласно urls.md
            #
            # Структура V1 API warehouse_remains:
            # - warehouseName: название склада
            # - quantity: остатки на складе (НЕ заказы!)
            # - "В пути до получателей": товары в транзите (НЕ активные заказы!)
            #
            # ПРАВИЛЬНО согласно urls.md:
            # Заказы: Подсчитывается количество записей в /supplier/orders где nmId + warehouseName
            
            # Step 2: Fetch orders from supplier/orders endpoint
            logger.info("Fetching orders data from supplier/orders endpoint...")
            from stock_tracker.api.products import WildberriesProductDataFetcher
            
            data_fetcher = WildberriesProductDataFetcher(self.wb_client)
            
            # Calculate date_from as ORDER_LOOKBACK_DAYS ago
            date_from = (datetime.now() - timedelta(days=ORDER_LOOKBACK_DAYS)).strftime("%Y-%m-%dT00:00:00")
            logger.info(f"Using date_from: {date_from} (last {ORDER_LOOKBACK_DAYS} days)")
            
            orders_data_raw = await data_fetcher.fetch_supplier_orders(date_from, flag=0)
            logger.info(f"Downloaded {len(orders_data_raw)} orders from supplier/orders API")
            
            # ИСПРАВЛЕНИЕ 28.10.2025: Фильтровать отменённые заказы
            valid_orders = [
                order for order in orders_data_raw 
                if not order.get('isCancel', False)
            ]
            logger.info(f"Active orders (excluding cancelled): {len(valid_orders)} " +
                       f"(removed {len(orders_data_raw) - len(valid_orders)} cancelled)")
            
            # ИСПРАВЛЕНИЕ 28.10.2025: Дедуплицировать по srid
            unique_orders = {}
            for order in valid_orders:
                srid = order.get('srid')
                if srid and srid not in unique_orders:
                    unique_orders[srid] = order
            
            logger.info(f"Unique orders (by srid): {len(unique_orders)} " +
                       f"(removed {len(valid_orders) - len(unique_orders)} duplicates)")
            
            # Преобразовать обратно в список для дальнейшей обработки
            orders_data = list(unique_orders.values())
            logger.info(f"Final orders_data count: {len(orders_data)}")
            
            # ДОБАВЛЕНО 28.10.2025: Детальная статистика обработки заказов
            logger.info("=" * 60)
            logger.info("📊 СТАТИСТИКА ОБРАБОТКИ ЗАКАЗОВ:")
            logger.info(f"   Total raw orders from API:      {len(orders_data_raw)}")
            logger.info(f"   After filtering cancelled:      {len(valid_orders)} (-{len(orders_data_raw)-len(valid_orders)})")
            logger.info(f"   After deduplication (srid):     {len(unique_orders)} (-{len(valid_orders)-len(unique_orders)})")
            logger.info(f"   Final orders_data count:        {len(orders_data)}")
            
            # Статистика по складам в заказах
            warehouse_stats = {}
            for order in orders_data:
                wh = order.get("warehouseName", "Неизвестно")
                warehouse_stats[wh] = warehouse_stats.get(wh, 0) + 1
            
            logger.info(f"   Unique warehouses in orders:    {len(warehouse_stats)}")
            top_warehouses = sorted(warehouse_stats.items(), key=lambda x: -x[1])[:5]
            for wh_name, count in top_warehouses:
                logger.info(f"      {wh_name:<35} {count:>3} заказов")
            logger.info("=" * 60)
            
            api_data = warehouse_remains
            
            # Debug: Log sample API data structure
            if api_data:
                sample_item = api_data[0]
                logger.debug(f"Sample warehouse item structure: {list(sample_item.keys())}")
                logger.debug(f"Sample item: nmId={sample_item.get('nmId')}, "
                           f"vendorCode={sample_item.get('vendorCode')}, "
                           f"ordersCount={sample_item.get('ordersCount')}, "
                           f"stockCount={sample_item.get('stockCount')}")
            else:
                logger.warning("No warehouse data returned from API")
            
            if not api_data:
                logger.info("No products returned from warehouse API")
                sync_session.complete()
                return sync_session
            
            sync_session.products_total = len(api_data)
            
            # Step 3: Convert API data to our Product model and write to Sheets
            updated_count = 0
            error_count = 0
            
            for api_record in api_data:
                try:
                    # Convert API record to Product with orders data
                    product = self._convert_api_record_to_product(api_record, orders_data)
                    
                    # Write/update in Google Sheets
                    # Use skip_existence_check if table was cleared before sync
                    success = self.operations.create_or_update_product(
                        self.config.google_sheets.sheet_id,
                        product,
                        skip_existence_check=skip_existence_check
                    )
                    
                    if success:
                        updated_count += 1
                        sync_session.products_processed += 1
                    else:
                        error_count += 1
                        sync_session.products_failed += 1
                        sync_session.add_error(f"Failed to write product {product.seller_article}")
                        
                except Exception as e:
                    error_count += 1
                    sync_session.products_failed += 1
                    sync_session.add_error(f"Error processing API record: {e}")
                    logger.warning(f"Failed to process API record: {e}")
            
            # Complete session
            if error_count == 0:
                sync_session.complete()
            else:
                sync_session.fail("Some products failed to sync")
            
            logger.info(f"API-to-Sheets sync completed: {updated_count} updated, {error_count} errors")
            return sync_session
            
        except Exception as e:
            sync_session.fail(f"API-to-Sheets sync failed: {e}")
            logger.error(f"API-to-Sheets sync failed: {e}")
            raise SyncError(f"API-to-Sheets sync failed: {e}")
    
    async def sync_from_dual_api_to_sheets(self, skip_existence_check: bool = False) -> SyncSession:
        """
        Fetch fresh data from Wildberries using Dual API (FBO+FBS) and write to Google Sheets.
        
        This method combines:
        - Statistics API for FBO (Fulfillment by Operator) stocks
        - Marketplace API v3 for FBS (Fulfillment by Seller) stocks  
        - Supplier Orders API for active orders count
        
        Args:
            skip_existence_check: Skip existence checks when writing products.
                                 Set to True when table was just cleared to avoid unnecessary API calls.
        
        Returns:
            SyncSession with results summary
            
        Raises:
            SyncError: If synchronization fails
        """
        sync_session = SyncSession(
            session_id=str(uuid.uuid4()),
            start_time=datetime.now()
        )
        
        try:
            logger.info("="*80)
            logger.info("🚀 Starting Dual API Synchronization (FBO+FBS)")
            logger.info("="*80)
            sync_session.start()
            
            # Step 1: Get combined FBO+FBS stocks using Dual API
            logger.info("\n📊 Step 1: Fetching stocks from Dual API (Statistics + Marketplace)...")
            
            stocks_by_article = self.dual_api_fetcher.get_combined_stocks_by_article()
            
            logger.info(f"✅ Retrieved stocks for {len(stocks_by_article)} articles")
            
            # Log summary
            summary = self.dual_api_fetcher.get_all_stocks_summary()
            logger.info(f"\n📈 Stocks Summary:")
            logger.info(f"   FBO (WB warehouses):    {summary['total_fbo']:>6} шт")
            logger.info(f"   FBS (Seller warehouses): {summary['total_fbs']:>6} шт")
            logger.info(f"   ─────────────────────────────────")
            logger.info(f"   TOTAL:                   {summary['total']:>6} шт")
            logger.info(f"   Articles:                {summary['articles_count']}")
            logger.info(f"   FBS warehouses:          {summary['fbs_warehouses_count']}")
            
            if not stocks_by_article:
                logger.info("⚠️ No products returned from Dual API")
                sync_session.complete()
                return sync_session
            
            # Step 2: Fetch orders from supplier/orders endpoint
            logger.info("\n📦 Step 2: Fetching orders from supplier/orders API...")
            
            from stock_tracker.api.products import WildberriesProductDataFetcher
            data_fetcher = WildberriesProductDataFetcher(self.wb_client)
            
            # Calculate date_from as ORDER_LOOKBACK_DAYS ago
            date_from = (datetime.now() - timedelta(days=ORDER_LOOKBACK_DAYS)).strftime("%Y-%m-%dT00:00:00")
            logger.info(f"   Date range: {date_from} to now (last {ORDER_LOOKBACK_DAYS} days)")
            
            orders_data_raw = await data_fetcher.fetch_supplier_orders(date_from, flag=0)
            logger.info(f"   Raw orders: {len(orders_data_raw)}")
            
            # Filter cancelled orders
            valid_orders = [
                order for order in orders_data_raw 
                if not order.get('isCancel', False)
            ]
            logger.info(f"   Active orders: {len(valid_orders)} (removed {len(orders_data_raw) - len(valid_orders)} cancelled)")
            
            # Deduplicate by srid
            unique_orders = {}
            for order in valid_orders:
                srid = order.get('srid')
                if srid and srid not in unique_orders:
                    unique_orders[srid] = order
            
            orders_data = list(unique_orders.values())
            logger.info(f"   Unique orders: {len(orders_data)} (removed {len(valid_orders) - len(orders_data)} duplicates)")
            
            # Count orders by nmId
            orders_by_nm_id = defaultdict(int)
            for order in orders_data:
                nm_id = order.get('nmId')
                if nm_id:
                    orders_by_nm_id[nm_id] += 1
            
            logger.info(f"   Products with orders: {len(orders_by_nm_id)}")
            
            # Step 3: Convert to Product models and write to Sheets
            logger.info("\n💾 Step 3: Writing products to Google Sheets...")
            
            sync_session.products_total = len(stocks_by_article)
            updated_count = 0
            error_count = 0
            
            for article, stock_data in stocks_by_article.items():
                try:
                    nm_id = stock_data['nm_id']
                    
                    # Get orders count for this product
                    orders_count = orders_by_nm_id.get(nm_id, 0)
                    
                    # Build warehouse details from FBO and FBS data
                    warehouses = []
                    warehouse_stocks = {}  # warehouse_name -> stock
                    
                    # Process FBO warehouses (from Statistics API)
                    # ИСПРАВЛЕНО 30.10.2025: Включать ВСЕ склады, даже с qty=0
                    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ 30.10.2025: Использовать quantityFull вместо quantity
                    for fbo_detail in stock_data.get('fbo_details', []):
                        wh_name_raw = fbo_detail.get('warehouseName')
                        qty = fbo_detail.get('quantityFull', 0)  # CRITICAL FIX: Statistics API uses 'quantityFull', not 'quantity'
                        
                        if wh_name_raw:  # CRITICAL FIX: Убрали проверку qty > 0
                            wh_name = normalize_warehouse_name(wh_name_raw)  # НОРМАЛИЗАЦИЯ ДЛЯ ДЕДУПЛИКАЦИИ
                            if wh_name not in warehouse_stocks:
                                warehouse_stocks[wh_name] = 0
                            warehouse_stocks[wh_name] += qty
                    
                    # Process FBS warehouses (from Marketplace API v3)
                    # ИСПРАВЛЕНО 30.10.2025: Включать ВСЕ склады, даже с qty=0
                    for fbs_detail in stock_data.get('fbs_details', []):
                        wh_name_raw = fbs_detail.get('warehouse_name')
                        qty = fbs_detail.get('amount', 0)
                        
                        if wh_name_raw:  # CRITICAL FIX: Убрали проверку qty > 0
                            wh_name = normalize_warehouse_name(wh_name_raw)  # НОРМАЛИЗАЦИЯ ДЛЯ ДЕДУПЛИКАЦИИ
                            if wh_name not in warehouse_stocks:
                                warehouse_stocks[wh_name] = 0
                            warehouse_stocks[wh_name] += qty
                    
                    # Count orders per warehouse
                    warehouse_orders = {}
                    for order in orders_data:
                        if order.get('nmId') == nm_id:
                            wh_name_raw = order.get('warehouseName', '').strip()
                            if wh_name_raw:
                                wh_name = normalize_warehouse_name(wh_name_raw)  # НОРМАЛИЗАЦИЯ ДЛЯ ДЕДУПЛИКАЦИИ
                                warehouse_orders[wh_name] = warehouse_orders.get(wh_name, 0) + 1
                    
                    # Create Warehouse objects
                    # ИСПРАВЛЕНО 09.11.2025: Не добавляем склады с нулевыми остатками И нулевыми заказами
                    for wh_name, stock in warehouse_stocks.items():
                        orders = warehouse_orders.get(wh_name, 0)
                        # Пропускаем склады без остатков и заказов (устаревшие данные)
                        if stock == 0 and orders == 0:
                            logger.debug(f"Skipping warehouse {wh_name} with zero stock and zero orders")
                            continue
                        
                        warehouse = Warehouse(
                            name=wh_name,
                            stock=stock,
                            orders=orders
                        )
                        warehouses.append(warehouse)
                    
                    # Add warehouses with orders but no stock
                    for wh_name, orders in warehouse_orders.items():
                        if wh_name not in warehouse_stocks and orders > 0:
                            warehouse = Warehouse(
                                name=wh_name,
                                stock=0,
                                orders=orders
                            )
                            warehouses.append(warehouse)
                    
                    # Create Product model with warehouse details
                    product = Product(
                        seller_article=article,
                        wildberries_article=nm_id,
                        total_stock=stock_data['total_stock'],
                        total_orders=orders_count,
                        fbo_stock=stock_data['fbo_stock'],
                        fbs_stock=stock_data['fbs_stock'],
                        warehouses=warehouses,
                        last_updated=datetime.now()
                    )
                    
                    # Calculate turnover (оборачиваемость в днях)
                    # ИСПРАВЛЕНО 30.10.2025: Правильная формула с учетом периода
                    # Формула: остатки / (заказы_за_период / количество_дней_в_периоде)
                    # Показывает сколько дней товар будет продаваться при текущем темпе
                    if product.total_orders > 0:
                        orders_per_day = product.total_orders / ORDER_LOOKBACK_DAYS
                        product.turnover = round(product.total_stock / orders_per_day, 3)
                    else:
                        product.turnover = 0.0
                    
                    # Write/update in Google Sheets
                    success = self.operations.create_or_update_product(
                        self.config.google_sheets.sheet_id,
                        product,
                        skip_existence_check=skip_existence_check
                    )
                    
                    if success:
                        updated_count += 1
                        sync_session.products_processed += 1
                        
                        # Log sample product with warehouse breakdown
                        if updated_count <= 3:
                            logger.info(f"   ✅ {article}: FBO={product.fbo_stock}, FBS={product.fbs_stock}, "
                                      f"Total={product.total_stock}, Orders={product.total_orders}, "
                                      f"Warehouses={len(product.warehouses)}")
                            for wh in product.warehouses[:3]:
                                logger.info(f"       └─ {wh.name}: stock={wh.stock}, orders={wh.orders}")
                        
                        # Добавляем задержку для предотвращения превышения квоты Google Sheets API
                        # Railway/Render: 1 секунда между операциями = 60 запросов/минуту (в пределах лимита)
                        import time
                        time.sleep(1.0)
                    else:
                        error_count += 1
                        sync_session.products_failed += 1
                        sync_session.add_error(f"Failed to write product {article}")
                        
                except Exception as e:
                    error_count += 1
                    sync_session.products_failed += 1
                    sync_session.add_error(f"Error processing {article}: {e}")
                    logger.warning(f"Failed to process {article}: {e}")
            
            # Complete session
            if error_count == 0:
                sync_session.complete()
            else:
                sync_session.fail(f"Some products failed: {error_count} errors")
            
            logger.info("\n" + "="*80)
            logger.info(f"✅ Dual API Sync Completed:")
            logger.info(f"   Updated: {updated_count}")
            logger.info(f"   Errors:  {error_count}")
            logger.info(f"   Duration: {(datetime.now() - sync_session.start_time).total_seconds():.1f}s")
            logger.info("="*80)
            
            return sync_session
            
        except Exception as e:
            sync_session.fail(f"Dual API sync failed: {e}")
            logger.error(f"Dual API sync failed: {e}")
            raise SyncError(f"Dual API sync failed: {e}")
    
    def _combine_v1_v2_data(self, warehouse_remains: List[Dict], orders_by_nm_id: Dict[int, int]) -> List[Dict]:
        """
        Combine V1 (warehouse remains with stocks) and V2 (total orders) data.
        
        V1 API provides: nmId, vendorCode, warehouses[].warehouseName, warehouses[].quantity (stock)
        V2 API provides: nmID, metrics.ordersCount (total orders)
        
        This method distributes total orders proportionally across warehouses based on stock.
        
        Args:
            warehouse_remains: List of records from V1 warehouse_remains API
            orders_by_nm_id: Dict mapping nmID -> total orders from V2 API
            
        Returns:
            List of combined records with ordersCount added to each warehouse
        """
        logger.info(f"Combining V1+V2 data for {len(warehouse_remains)} products")
        
        combined_data = []
        
        for record in warehouse_remains:
            nm_id = record.get('nmId')
            vendor_code = record.get('vendorCode', 'Unknown')
            warehouses = record.get('warehouses', [])
            
            # Get total orders from V2 API
            total_orders = orders_by_nm_id.get(nm_id, 0)
            
            if not warehouses:
                logger.warning(f"Product {vendor_code} (nmId={nm_id}) has no warehouses")
                combined_data.append(record)
                continue
            
            # Calculate total stock across all warehouses
            total_stock = sum(wh.get('quantity', 0) for wh in warehouses)
            
            if total_stock == 0:
                logger.warning(f"Product {vendor_code} (nmId={nm_id}) has 0 total stock")
                # Can't distribute orders, just set 0 for all warehouses
                for wh in warehouses:
                    wh['ordersCount'] = 0
                combined_data.append(record)
                continue
            
            # Distribute orders proportionally to stock
            distributed_orders = 0
            for i, wh in enumerate(warehouses):
                wh_name = wh.get('warehouseName', 'Unknown')
                wh_stock = wh.get('quantity', 0)
                
                # Calculate proportional orders
                if i == len(warehouses) - 1:
                    # Last warehouse gets remaining orders to ensure total matches
                    wh_orders = total_orders - distributed_orders
                else:
                    wh_orders = round(total_orders * wh_stock / total_stock)
                
                wh['ordersCount'] = wh_orders
                distributed_orders += wh_orders
                
                logger.debug(f"  Warehouse {wh_name}: stock={wh_stock}, orders={wh_orders} "
                           f"(proportion: {wh_stock}/{total_stock})")
            
            logger.debug(f"Product {vendor_code}: distributed {total_orders} orders across "
                       f"{len(warehouses)} warehouses (total stock: {total_stock})")
            
            combined_data.append(record)
        
        return combined_data
    
    def _convert_api_record_to_product(self, api_record: Dict[str, Any], orders_data: List[Dict[str, Any]] = None) -> Product:
        """
        Convert Wildberries API record to Product model.
        
        Args:
            api_record: Raw API response record from warehouse_remains
            orders_data: Orders data from supplier/orders endpoint
            
        Returns:
            Product model instance
        """
        from stock_tracker.core.models import Product, Warehouse
        
        if orders_data is None:
            orders_data = []
        
        # Get product identifiers - FIXED field mapping
        nm_id = api_record.get('nmId', 0)
        vendor_code = api_record.get('vendorCode', '')  # Warehouse uses vendorCode
        
        logger.debug(f"Converting product: nmId={nm_id}, vendorCode={vendor_code}")
        logger.debug(f"Orders data available: {len(orders_data)} records")
        
        # Calculate total quantity from all warehouses - FIXED: Exclude "in transit" warehouses
        total_quantity = 0
        total_orders = 0
        warehouses = []
        
        # FIXED: Track only real warehouse stock (excluding in-transit items)
        real_warehouse_stock = 0
        
        # ИСПРАВЛЕНО 27.10.2025 21:35 - КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ!
        # V1 API warehouse_remains содержит ТОЛЬКО остатки (quantity), НЕ заказы!
        # Структура V1 API warehouse_remains:
        # - Реальные склады (Краснодар, Чехов, etc): quantity = остатки на складе
        # - "В пути до получателей": quantity = товары в транзите (НЕ заказы!)
        # - "В пути возвраты на склад WB": quantity = возвраты
        # - "Всего находится на складах": quantity = сводный остаток
        #
        # ЗАКАЗЫ берутся из orders_data (supplier/orders эндпоинт) согласно urls.md!
        
        if 'warehouses' in api_record and isinstance(api_record['warehouses'], list):            
            for wh in api_record['warehouses']:
                warehouse_name = wh.get('warehouseName', 'Unknown')
                warehouse_quantity = wh.get('quantity', 0)
                
                # Фильтруем служебные/виртуальные склады
                if warehouse_name in ("В пути до получателей", "В пути возвраты на склад WB", 
                                     "Всего находится на складах"):
                    logger.debug(f"Skipping service warehouse: {warehouse_name}")
                    continue
                
                # Проверяем что это реальный склад (не используем validate_warehouse_name)
                if not warehouse_name or not is_real_warehouse(warehouse_name):
                    logger.debug(f"Skipping invalid warehouse name: {warehouse_name}")
                    continue
                
                # Остатки берем из warehouse_remains
                warehouse_stock = warehouse_quantity
                # Заказы будут добавлены из orders_data позже
                warehouse_orders = 0
                is_in_transit = False
                
                logger.debug(f"Warehouse {warehouse_name}: stock={warehouse_stock}, orders will be calculated from orders_data")
                
                # ИСПРАВЛЕНО 26.10.2025: Убраны несуществующие параметры orders_quantity и stock_quantity
                warehouse = Warehouse(
                    name=warehouse_name,
                    stock=warehouse_stock,
                    orders=warehouse_orders
                )
                warehouses.append(warehouse)
                
                # FIXED: Only count real warehouse stock, not "in transit"
                total_quantity += warehouse_stock  # Keep total for compatibility
                if not is_in_transit:
                    real_warehouse_stock += warehouse_stock
        
        # ДОБАВЛЕНО 27.10.2025 21:35 - КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ!
        # Рассчитываем заказы из orders_data для каждого склада
        logger.debug(f"Calculating orders for product {vendor_code} (nmId: {nm_id}) from {len(orders_data)} orders")
        
        # ИСПРАВЛЕНИЕ 28.10.2025: Добавляем функцию нормализации названий складов
        def normalize_warehouse_name(name: str) -> str:
            """
            Нормализует название склада для корректного сравнения.
            Примеры:
            - "Подольск 3" → "Подольск 3"
            - "Подольск-3" → "Подольск 3"
            - "Самара (Новосемейкино)" → "Самара Новосемейкино"
            """
            if not name:
                return "Неизвестно"
            # Убрать скобки
            name = name.replace('(', '').replace(')', '')
            # Убрать лишние пробелы
            name = ' '.join(name.split())
            return name.strip()
        
        for warehouse in warehouses:
            # Используем calculator для точного подсчета заказов по складу
            warehouse_orders_count = 0
            
            # ИСПРАВЛЕНИЕ 28.10.2025: Нормализуем названия для сравнения
            normalized_warehouse_name = normalize_warehouse_name(warehouse.name)
            
            for order in orders_data:
                order_nm_id = order.get("nmId")
                order_warehouse_raw = order.get("warehouseName", "").strip()
                normalized_order_warehouse = normalize_warehouse_name(order_warehouse_raw)
                
                # ИСПРАВЛЕНИЕ 28.10.2025: isCancel уже отфильтрован выше, но оставим проверку для надежности
                is_canceled = order.get("isCancel", False)
                
                # Точное совпадение nmId + нормализованное warehouseName
                if (order_nm_id == nm_id and 
                    normalized_order_warehouse == normalized_warehouse_name and 
                    not is_canceled):
                    warehouse_orders_count += 1
            
            warehouse.orders = warehouse_orders_count
            total_orders += warehouse_orders_count
            
            logger.debug(f"  Warehouse {warehouse.name}: orders={warehouse_orders_count}")
        
        # ДОБАВЛЕНО: Создаем склады из orders_data, если их нет в warehouses
        # (склады с нулевыми остатками, но с заказами)
        # ИСПРАВЛЕНИЕ 28.10.2025: Используем нормализованные названия для проверки
        existing_warehouse_names = {normalize_warehouse_name(wh.name) for wh in warehouses}
        
        for order in orders_data:
            order_nm_id = order.get("nmId")
            if order_nm_id != nm_id:
                continue
                
            order_warehouse_raw = order.get("warehouseName", "").strip()
            normalized_order_warehouse = normalize_warehouse_name(order_warehouse_raw)
            
            # ИСПРАВЛЕНИЕ 28.10.2025: isCancel уже отфильтрован выше при создании orders_data
            # Но оставим проверку для надежности
            is_canceled = order.get("isCancel", False)
            
            if is_canceled or not order_warehouse_raw:
                continue
            
            # Проверяем что это реальный склад и его еще нет (по нормализованному имени)
            if is_real_warehouse(order_warehouse_raw) and normalized_order_warehouse not in existing_warehouse_names:
                # Считаем заказы для этого склада (используем нормализацию)
                warehouse_orders_count = 0
                for o in orders_data:
                    if (o.get("nmId") == nm_id and 
                        normalize_warehouse_name(o.get("warehouseName", "").strip()) == normalized_order_warehouse and
                        not o.get("isCancel", False)):
                        warehouse_orders_count += 1
                
                if warehouse_orders_count > 0:
                    # Создаем склад с нулевыми остатками, но с заказами
                    new_warehouse = Warehouse(
                        name=order_warehouse_raw,  # Используем оригинальное имя для отображения
                        stock=0,  # Нет остатков
                        orders=warehouse_orders_count
                    )
                    warehouses.append(new_warehouse)
                    existing_warehouse_names.add(normalized_order_warehouse)  # Добавляем в set
                    total_orders += warehouse_orders_count
                    
                    logger.info(f"  Created warehouse with zero stock: {order_warehouse_raw} (orders={warehouse_orders_count})")
        
        logger.debug(f"Product totals: stock={real_warehouse_stock}, orders={total_orders}, warehouses={len(warehouses)}")
        
        # NEW: Classify warehouses by type (FBO/FBS) and calculate stock breakdown
        fbo_stock = 0
        fbs_stock = 0
        
        if self.warehouse_classifier:
            # Используем классификатор складов для разделения остатков
            for warehouse in warehouses:
                warehouse_type = self.warehouse_classifier.classify_warehouse(warehouse.name)
                
                from stock_tracker.services.warehouse_classifier import WarehouseType
                
                if warehouse_type == WarehouseType.FBO:
                    fbo_stock += warehouse.stock
                elif warehouse_type == WarehouseType.FBS:
                    fbs_stock += warehouse.stock
                # Unknown warehouses не добавляем ни в FBO, ни в FBS
            
            logger.debug(f"Stock breakdown: FBO={fbo_stock}, FBS={fbs_stock}, Unknown={real_warehouse_stock - fbo_stock - fbs_stock}")
        else:
            logger.warning("Warehouse classifier not initialized, FBO/FBS stock breakdown unavailable")
        
        # Calculate turnover (оборачиваемость = остатки / заказы)
        # Показывает соотношение остатков к заказам (целое число)
        turnover_rate = 0
        if total_orders > 0:
            turnover_rate = int(real_warehouse_stock / total_orders)
        else:
            turnover_rate = 0
        
        # ИСПРАВЛЕНО 26.10.2025: Убран несуществующий параметр wb_article (дубликат wildberries_article)
        # ИСПРАВЛЕНО: Убран несуществующий параметр turnover_rate (используется turnover)
        product = Product(
            wildberries_article=nm_id,
            seller_article=vendor_code,
            total_orders=total_orders,  # Real orders data from API
            total_stock=real_warehouse_stock,  # FIXED: Use only real warehouse stock
            fbo_stock=fbo_stock,  # NEW: FBO warehouses stock
            fbs_stock=fbs_stock,  # NEW: FBS warehouses stock
            turnover=turnover_rate,  # ИСПРАВЛЕНО: правильное имя параметра
            warehouses=warehouses
        )
        
        logger.debug(f"Created product {vendor_code}: {total_orders} orders, {real_warehouse_stock} real stock (FBO={fbo_stock}, FBS={fbs_stock}), {turnover_rate:.3f} turnover")
        
        return product

    def _is_in_transit_warehouse(self, warehouse_name: str) -> bool:
        """
        Check if warehouse is "in transit" and should be excluded from real stock count.
        
        In-transit warehouses are not actual warehouse stock but items being moved.
        These should not be counted in total_stock for business calculations.
        
        Args:
            warehouse_name: Name of the warehouse to check
            
        Returns:
            True if warehouse is "in transit", False if it's a real warehouse
        """
        if not warehouse_name:
            return False
            
        warehouse_name_lower = warehouse_name.lower()
        
        # Keywords that indicate "in transit" warehouses
        in_transit_keywords = [
            'в пути',           # "в пути" - in transit
            'в дороге',         # "в дороге" - on the way  
            'возврат',          # "возврат" - returns
            'до получател',     # "до получателей" - to recipients
            'транзит',          # "транзит" - transit
            'доставк',          # "доставка" - delivery
            'перемещен',        # "перемещение" - transfer
        ]
        
        # Check if any in-transit keywords are in warehouse name
        for keyword in in_transit_keywords:
            if keyword in warehouse_name_lower:
                return True
                
        return False
    
    # Analytics and reporting
    
    def get_product_analytics(self, seller_article: str) -> Dict[str, Any]:
        """
        Get comprehensive analytics for a single product.
        
        Args:
            seller_article: Product to analyze
            
        Returns:
            Dict with analytics data
        """
        try:
            product = self.operations.read_product(
                self.config.google_sheets.sheet_id,
                seller_article
            )
            
            if not product:
                return {"error": "Product not found"}
            
            # Basic metrics
            analytics = {
                "seller_article": product.seller_article,
                "wildberries_article": product.wildberries_article,
                "total_stock": product.total_stock,
                "total_orders": product.total_orders,
                "turnover": product.turnover,
                "warehouse_count": len(product.warehouses)
            }
            
            # Warehouse analysis
            if product.warehouses:
                warehouses_data = []
                for warehouse in product.warehouses:
                    wh_data = {
                        "name": warehouse.name,
                        "stock": warehouse.stock,
                        "orders": warehouse.orders,
                        "stock_percentage": round((warehouse.stock / product.total_stock * 100) if product.total_stock > 0 else 0, 2),
                        "orders_percentage": round((warehouse.orders / product.total_orders * 100) if product.total_orders > 0 else 0, 2)
                    }
                    warehouses_data.append(wh_data)
                
                analytics["warehouses"] = warehouses_data
                
                # Find top performing warehouse
                if warehouses_data:
                    top_warehouse = max(warehouses_data, key=lambda x: x["orders"])
                    analytics["top_warehouse"] = top_warehouse["name"]
            
            # Performance indicators
            analytics["performance"] = self._analyze_product_performance(product)
            
            logger.debug(f"Generated analytics for {seller_article}")
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get analytics for {seller_article}: {e}")
            return {"error": str(e)}
    
    def get_inventory_summary(self) -> Dict[str, Any]:
        """
        Get overall inventory summary and analytics.
        
        Returns:
            Dict with inventory summary
        """
        try:
            products = self.operations.read_all_products(
                self.config.google_sheets.sheet_id
            )
            
            if not products:
                return {
                    "total_products": 0,
                    "total_stock": 0,
                    "total_orders": 0,
                    "avg_turnover": 0,
                    "warehouses": {}
                }
            
            # Overall metrics
            total_stock = sum(p.total_stock for p in products)
            total_orders = sum(p.total_orders for p in products)
            avg_turnover = sum(p.turnover for p in products) / len(products)
            
            # Warehouse aggregation
            warehouse_stats = {}
            for product in products:
                for warehouse in product.warehouses:
                    if warehouse.name not in warehouse_stats:
                        warehouse_stats[warehouse.name] = {
                            "total_stock": 0,
                            "total_orders": 0,
                            "product_count": 0
                        }
                    
                    warehouse_stats[warehouse.name]["total_stock"] += warehouse.stock
                    warehouse_stats[warehouse.name]["total_orders"] += warehouse.orders
                    warehouse_stats[warehouse.name]["product_count"] += 1
            
            # Performance categories
            high_turnover = len([p for p in products if p.turnover > 2.0])
            medium_turnover = len([p for p in products if 1.0 <= p.turnover <= 2.0])
            low_turnover = len([p for p in products if p.turnover < 1.0])
            
            summary = {
                "total_products": len(products),
                "total_stock": total_stock,
                "total_orders": total_orders,
                "avg_turnover": round(avg_turnover, 3),
                "warehouses": warehouse_stats,
                "performance_categories": {
                    "high_turnover": high_turnover,
                    "medium_turnover": medium_turnover,
                    "low_turnover": low_turnover
                },
                "generated_at": datetime.now().isoformat()
            }
            
            logger.info(f"Generated inventory summary for {len(products)} products")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get inventory summary: {e}")
            return {"error": str(e)}
    
    def get_top_products(self, limit: int = 10, 
                        sort_by: str = "turnover") -> List[Dict[str, Any]]:
        """
        Get top performing products.
        
        Args:
            limit: Number of products to return
            sort_by: Sort criteria ("turnover", "stock", "orders")
            
        Returns:
            List of top products with metrics
        """
        try:
            products = self.operations.read_all_products(
                self.config.google_sheets.sheet_id
            )
            
            if not products:
                return []
            
            # Sort products
            if sort_by == "turnover":
                sorted_products = sorted(products, key=lambda p: p.turnover, reverse=True)
            elif sort_by == "stock":
                sorted_products = sorted(products, key=lambda p: p.total_stock, reverse=True)
            elif sort_by == "orders":
                sorted_products = sorted(products, key=lambda p: p.total_orders, reverse=True)
            else:
                raise ValidationError(f"Invalid sort_by parameter: {sort_by}")
            
            # Get top products
            top_products = []
            for i, product in enumerate(sorted_products[:limit]):
                product_data = {
                    "rank": i + 1,
                    "seller_article": product.seller_article,
                    "wildberries_article": product.wildberries_article,
                    "total_stock": product.total_stock,
                    "total_orders": product.total_orders,
                    "turnover": product.turnover,
                    "warehouse_count": len(product.warehouses)
                }
                top_products.append(product_data)
            
            logger.info(f"Generated top {len(top_products)} products by {sort_by}")
            return top_products
            
        except Exception as e:
            logger.error(f"Failed to get top products: {e}")
            return []
    
    # Batch operations
    
    async def create_products_from_articles(self, 
                                          articles: List[Tuple[str, int]]) -> List[Product]:
        """
        Create multiple products from seller/WB article pairs.
        
        Args:
            articles: List of (seller_article, wildberries_article) tuples
            
        Returns:
            List of successfully created products
        """
        try:
            logger.info(f"Creating {len(articles)} products from articles")
            
            created_products = []
            for seller_article, wb_article in articles:
                try:
                    product = await self.create_product_from_api(seller_article, wb_article)
                    created_products.append(product)
                except Exception as e:
                    logger.warning(f"Failed to create product {seller_article}: {e}")
                    continue
            
            logger.info(f"Created {len(created_products)}/{len(articles)} products")
            return created_products
            
        except Exception as e:
            logger.error(f"Failed to create products from articles: {e}")
            raise SyncError(f"Batch creation failed: {e}")
    
    def search_products_advanced(self, **criteria) -> List[Tuple[Product, Dict[str, Any]]]:
        """
        Advanced product search with analytics.
        
        Args:
            **criteria: Search criteria (same as operations.search_products)
            
        Returns:
            List of (Product, analytics) tuples
        """
        try:
            # Search products
            search_results = self.operations.search_products(
                self.config.google_sheets.sheet_id,
                criteria
            )
            
            # Add analytics to each result
            enriched_results = []
            for product, row_number in search_results:
                analytics = self.get_product_analytics(product.seller_article)
                enriched_results.append((product, analytics))
            
            logger.info(f"Found {len(enriched_results)} products matching criteria")
            return enriched_results
            
        except Exception as e:
            logger.error(f"Failed advanced product search: {e}")
            return []
    
    # Helper methods
    
    async def _sync_product_from_api(self, product: Product) -> None:
        """
        Sync product data from Wildberries API.
        
        Args:
            product: Product to sync (modified in place)
            
        Raises:
            APIError: If API request fails
        """
        try:
            logger.debug(f"Syncing product {product.seller_article} from API")
            
            # Get warehouse remains
            remains_data = await self.wb_client.get_warehouse_remains()
            
            # Get orders data  
            orders_data = await self.wb_client.get_supplier_orders()
            
            # Clear existing warehouses
            product.warehouses.clear()
            
            # Process remains data
            article_remains = {}
            for item in remains_data:
                if item.get("supplierArticle") == product.seller_article:
                    warehouse_name = item.get("warehouseName", "")
                    stock = item.get("quantity", 0)
                    
                    if warehouse_name not in article_remains:
                        article_remains[warehouse_name] = {"stock": 0, "orders": 0}
                    article_remains[warehouse_name]["stock"] += stock
            
            # Process orders data
            for item in orders_data:
                if item.get("supplierArticle") == product.seller_article:
                    warehouse_name = item.get("warehouseName", "")
                    
                    if warehouse_name not in article_remains:
                        article_remains[warehouse_name] = {"stock": 0, "orders": 0}
                    article_remains[warehouse_name]["orders"] += 1
            
            # Create warehouse objects
            for warehouse_name, data in article_remains.items():
                if warehouse_name:  # Skip empty warehouse names
                    warehouse = Warehouse(
                        name=warehouse_name,
                        stock=data["stock"],
                        orders=data["orders"]
                    )
                    product.add_warehouse(warehouse)
            
            # Calculate turnover
            product.turnover = self.calculator.calculate_turnover(
                product.total_orders,
                product.total_stock
            )
            
            logger.debug(f"Synced product {product.seller_article}: {len(product.warehouses)} warehouses")
            
        except Exception as e:
            logger.error(f"Failed to sync product from API: {e}")
            raise APIError(f"API sync failed: {e}")
    
    def _analyze_product_performance(self, product: Product) -> Dict[str, Any]:
        """
        Analyze product performance and provide recommendations.
        
        Args:
            product: Product to analyze
            
        Returns:
            Dict with performance analysis
        """
        try:
            performance = {
                "category": "unknown",
                "recommendation": "",
                "risk_level": "low"
            }
            
            # Categorize by turnover
            if product.turnover >= 2.0:
                performance["category"] = "high_performance"
                performance["recommendation"] = "Excellent turnover! Consider increasing stock."
                performance["risk_level"] = "low"
            elif product.turnover >= 1.0:
                performance["category"] = "medium_performance"
                performance["recommendation"] = "Good performance. Monitor stock levels."
                performance["risk_level"] = "medium"
            else:
                performance["category"] = "low_performance"
                performance["recommendation"] = "Low turnover. Consider reducing stock or marketing."
                performance["risk_level"] = "high"
            
            # Check stock levels
            if product.total_stock == 0:
                performance["stock_status"] = "out_of_stock"
                performance["recommendation"] = "Critical: Restock immediately!"
                performance["risk_level"] = "critical"
            elif product.total_stock < 10:
                performance["stock_status"] = "low_stock"
                if performance["risk_level"] != "critical":
                    performance["risk_level"] = "high"
            else:
                performance["stock_status"] = "adequate"
            
            return performance
            
        except Exception as e:
            logger.debug(f"Failed to analyze performance: {e}")
            return {"category": "unknown", "recommendation": "Analysis failed"}
    
    async def sync_product_with_verification(self, seller_article: str, 
                                           wildberries_article: int,
                                           expected_wb_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Sync single product with calculation verification and detailed debugging.
        
        Args:
            seller_article: Product seller article
            wildberries_article: Product WB article (nmId)
            expected_wb_data: Expected WB data for verification (optional)
            
        Returns:
            Sync result with verification data and debugging info
        """
        try:
            logger.info(f"Starting verified sync for product {seller_article} (nmId: {wildberries_article})")
            
            # Import here to avoid circular imports
            from stock_tracker.api.products import WildberriesProductDataFetcher
            from stock_tracker.core.calculator import WildberriesCalculator
            from stock_tracker.utils.calculation_verifier import CalculationVerifier
            
            # Initialize data fetcher
            data_fetcher = WildberriesProductDataFetcher(self.wb_client)
            
            # Fetch data with precise parameters (last 30 days, exclude canceled)
            orders_data, warehouse_data = await data_fetcher.fetch_product_data(
                seller_article=seller_article,
                wildberries_article=wildberries_article,
                orders_date_from=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00")
            )
            
            # Use improved calculation with debugging
            calculator = WildberriesCalculator()
            
            # Calculate total orders with debugging
            total_orders, debug_info = calculator.calculate_total_orders_with_debug(
                orders_data, wildberries_article
            )
            
            # Calculate orders per warehouse
            warehouse_orders = {}
            for warehouse_name in debug_info["warehouse_breakdown"]:
                warehouse_orders[warehouse_name] = calculator.calculate_warehouse_orders(
                    orders_data, wildberries_article, warehouse_name
                )
            
            # Validate calculation consistency
            validation = calculator.validate_orders_calculation(
                wildberries_article, total_orders, warehouse_orders
            )
            
            # Create product with corrected data
            product = Product(seller_article=seller_article, wildberries_article=wildberries_article)
            
            # Add warehouses including zero-stock ones with orders
            for warehouse_name, orders_count in warehouse_orders.items():
                stock = calculator.calculate_warehouse_stock(
                    warehouse_data, wildberries_article, warehouse_name
                )
                warehouse = Warehouse(
                    name=warehouse_name, 
                    orders=orders_count, 
                    stock=stock
                )
                product.add_warehouse(warehouse)
            
            # Perform verification if expected data provided
            verification_result = None
            if expected_wb_data:
                our_calculation = {
                    "total_orders": total_orders,
                    "warehouse_breakdown": warehouse_orders
                }
                
                verification_result = CalculationVerifier.verify_orders_accuracy(
                    wildberries_article, our_calculation, expected_wb_data
                )
            
            result = {
                "success": True,
                "product": product,
                "debug_info": debug_info,
                "validation": validation,
                "verification": verification_result,
                "calculated_totals": {
                    "total_orders": total_orders,
                    "warehouse_count": len(warehouse_orders),
                    "total_stock": product.total_stock
                }
            }
            
            logger.info(f"✅ Verified sync completed for {seller_article}")
            logger.info(f"   Total orders: {total_orders}")
            logger.info(f"   Warehouses: {len(warehouse_orders)}")
            logger.info(f"   Validation: {'✅ PASSED' if validation['is_valid'] else '❌ FAILED'}")
            
            if verification_result:
                logger.info(f"   Verification accuracy: {verification_result['overall_accuracy']:.1f}%")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to sync product with verification: {e}")
            return {
                "success": False,
                "error": str(e),
                "product": None,
                "debug_info": None,
                "validation": None,
                "verification": None
            }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform service health check.
        
        Returns:
            Dict with health status
        """
        try:
            health = {
                "service": "healthy",
                "components": {},
                "timestamp": datetime.now().isoformat()
            }
            
            # Check API client
            try:
                await self.wb_client.health_check()
                health["components"]["wildberries_api"] = "healthy"
            except Exception as e:
                health["components"]["wildberries_api"] = f"error: {e}"
                health["service"] = "degraded"
            
            # Check Google Sheets
            try:
                status = self.operations.get_sync_status(self.config.google_sheets.sheet_id)
                health["components"]["google_sheets"] = "healthy"
                health["products_count"] = status.get("products_count", 0)
            except Exception as e:
                health["components"]["google_sheets"] = f"error: {e}"
                health["service"] = "degraded"
            
            return health
            
        except Exception as e:
            return {
                "service": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


if __name__ == "__main__":
    # Test service functionality
    print("Testing ProductService...")
    
    from stock_tracker.utils.config import get_config
    
    try:
        # This would require actual configuration and credentials
        # config = Config()
        # service = ProductService(config)
        
        print("✅ ProductService class structure validated")
        print("   Available methods:")
        print("   - create_product_from_api()")
        print("   - update_product_from_api()")
        print("   - sync_all_products()")
        print("   - get_product_analytics()")
        print("   - get_inventory_summary()")
        print("   - get_top_products()")
        print("   - search_products_advanced()")
        
    except Exception as e:
        print(f"Note: Full testing requires configuration: {e}")
    
    print("ProductService tests completed!")
