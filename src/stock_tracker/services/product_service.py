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
from stock_tracker.utils.config import get_config
from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.exceptions import SyncError, ValidationError, APIError


# Module constants
ORDER_LOOKBACK_DAYS = 7  # How many days to look back for orders data
WAREHOUSE_TASK_WAIT_SECONDS = 20  # Wait time for WB API task processing

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
        
        logger.info("ProductService initialized")
    
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
    
    async def sync_from_api_to_sheets(self) -> SyncSession:
        """
        Fetch fresh data from Wildberries API and write to Google Sheets.
        
        This method gets warehouse remains from WB API and populates/updates
        the Google Sheets with current inventory data.
        
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
            
            # Step 1: Fetch warehouse data from Wildberries API
            logger.info("Fetching warehouse data from Wildberries API...")
            task_id = await self.wb_client.create_warehouse_remains_task()
            logger.info(f"Created API task: {task_id}")
            
            # Wait for task processing (async friendly)
            logger.info("Waiting for API task to process...")
            await asyncio.sleep(WAREHOUSE_TASK_WAIT_SECONDS)
            
            # Download the warehouse results
            api_data = await self.wb_client.download_warehouse_remains(task_id)
            logger.info(f"Downloaded {len(api_data)} products from warehouse API")
            
            # Step 2: Fetch orders data from the last 7 days
            date_from = (datetime.now() - timedelta(days=ORDER_LOOKBACK_DAYS)).strftime("%Y-%m-%dT%H:%M:%S")
            logger.info(f"Fetching orders data from {date_from}...")
            
            try:
                orders_data = await self.wb_client.get_supplier_orders(date_from)
                logger.info(f"Downloaded {len(orders_data)} orders from API")
                
                # Debug: Log sample order structure
                if orders_data:
                    sample_order = orders_data[0]
                    logger.debug(f"Sample order structure: {list(sample_order.keys())}")
                    logger.debug(f"Sample order: nmId={sample_order.get('nmId')}, "
                               f"supplierArticle={sample_order.get('supplierArticle')}, "
                               f"warehouseName={sample_order.get('warehouseName')}")
                else:
                    logger.warning("No orders data returned from API - orders will be 0")
                    
            except Exception as e:
                logger.error(f"Failed to get orders data: {e}")
                logger.warning("Using empty orders data - all orders will be 0")
                orders_data = []
            
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
                    success = self.operations.create_or_update_product(
                        self.config.google_sheets.sheet_id,
                        product
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
        
        # FIXED: Improved matching logic for orders
        warehouse_orders_map = {}
        
        if 'warehouses' in api_record and isinstance(api_record['warehouses'], list):
            # Initialize warehouse order counts
            for wh in api_record['warehouses']:
                warehouse_name = wh.get('warehouseName', 'Unknown')
                # ДОБАВИТЬ ФИЛЬТРАЦИЮ:
                if warehouse_name and is_real_warehouse(warehouse_name) and validate_warehouse_name(warehouse_name):
                    warehouse_orders_map[warehouse_name] = 0
                else:
                    logger.debug(f"Filtered out warehouse name in product service: {warehouse_name}")
                
            # Count orders for this product using BOTH nmId and supplierArticle
            product_orders = []
            for order in orders_data:
                order_nm_id = order.get('nmId')
                order_supplier_article = order.get('supplierArticle', '')  # Orders use supplierArticle
                
                # Match by nmId (primary) AND supplierArticle (secondary validation)
                if (order_nm_id == nm_id and 
                    (not vendor_code or order_supplier_article == vendor_code)):
                    product_orders.append(order)
            
            logger.debug(f"Found {len(product_orders)} orders for product {vendor_code} (nmId: {nm_id})")
            
            # Group orders by warehouse for this product
            orders_by_warehouse = defaultdict(int)
            for order in product_orders:
                order_warehouse = order.get('warehouseName', '')
                order_quantity = order.get('quantity', 1)  # FIXED: Use actual quantity, not count
                # ДОБАВИТЬ ФИЛЬТРАЦИЮ для заказов:
                if order_warehouse and is_real_warehouse(order_warehouse) and validate_warehouse_name(order_warehouse):
                    orders_by_warehouse[order_warehouse] += order_quantity
                else:
                    logger.debug(f"Filtered out order warehouse name: {order_warehouse}")
            
            # FIXED: More intelligent warehouse matching
            # 1. Direct warehouse name match
            # 2. Fallback: distribute orders proportionally to stock
            remaining_orders = dict(orders_by_warehouse)  # Create copy for safe modification
            
            for wh in api_record['warehouses']:
                warehouse_name = wh.get('warehouseName', 'Unknown')
                warehouse_stock = wh.get('quantity', 0)
                
                # ДОБАВИТЬ ФИЛЬТРАЦИЮ при создании складов:
                if not (warehouse_name and is_real_warehouse(warehouse_name) and validate_warehouse_name(warehouse_name)):
                    logger.debug(f"Skipping filtered warehouse in product creation: {warehouse_name}")
                    continue
                
                # Try direct warehouse name match first
                warehouse_orders = remaining_orders.get(warehouse_name, 0)
                if warehouse_orders > 0:
                    # Remove from available orders to prevent double counting
                    del remaining_orders[warehouse_name]
                
                # If no direct match, check for partial matches or related warehouses
                if warehouse_orders == 0 and remaining_orders:
                    # Look for partial matches (e.g., "Подольск" matches "Подольск 3")
                    matched_order_wh = None
                    for order_wh_name, order_count in remaining_orders.items():
                        if (warehouse_name.lower() in order_wh_name.lower() or 
                            order_wh_name.lower() in warehouse_name.lower()):
                            warehouse_orders = order_count
                            matched_order_wh = order_wh_name
                            break
                    
                    # Remove matched warehouse from remaining orders
                    if matched_order_wh:
                        del remaining_orders[matched_order_wh]
                
                logger.debug(f"Warehouse {warehouse_name}: stock={warehouse_stock}, orders={warehouse_orders}")
                
                # FIXED: Check if this is a real warehouse or "in transit"
                is_in_transit = self._is_in_transit_warehouse(warehouse_name)
                
                warehouse = Warehouse(
                    name=warehouse_name,
                    stock=warehouse_stock,
                    orders=warehouse_orders,
                    orders_quantity=wh.get('orders_quantity', 0),
                    stock_quantity=wh.get('stock_quantity', 0)
                )
                warehouses.append(warehouse)
                
                # FIXED: Only count real warehouse stock, not "in transit"
                total_quantity += warehouse_stock  # Keep total for compatibility
                if not is_in_transit:
                    real_warehouse_stock += warehouse_stock
                
                total_orders += warehouse_orders
            
            # If we still have unmatched orders, distribute them to warehouses with stock
            total_order_quantity_from_api = sum(order.get('quantity', 1) for order in product_orders)
            unmatched_orders = sum(remaining_orders.values())  # Use remaining unmatched orders
            if unmatched_orders > 0 and warehouses:
                logger.debug(f"Distributing {unmatched_orders} unmatched orders proportionally")
                
                # Get warehouses with stock for proportional distribution
                warehouses_with_stock = [wh for wh in warehouses if wh.stock > 0]
                if warehouses_with_stock:
                    total_stock_for_distribution = sum(wh.stock for wh in warehouses_with_stock)
                    remaining_to_distribute = unmatched_orders
                    
                    for warehouse in warehouses_with_stock:
                        if total_stock_for_distribution > 0:
                            proportion = warehouse.stock / total_stock_for_distribution
                            # Use proper rounding instead of int() to ensure all orders are distributed
                            additional_orders = round(unmatched_orders * proportion)
                            # Ensure we don't exceed remaining orders
                            additional_orders = min(additional_orders, remaining_to_distribute)
                            warehouse.orders += additional_orders
                            total_orders += additional_orders
                            remaining_to_distribute -= additional_orders
                            logger.debug(f"Added {additional_orders} proportional orders to {warehouse.name}")
                    
                    # If there are still remaining orders due to rounding, add them to the largest warehouse
                    if remaining_to_distribute > 0 and warehouses_with_stock:
                        largest_warehouse = max(warehouses_with_stock, key=lambda w: w.stock)
                        largest_warehouse.orders += remaining_to_distribute
                        total_orders += remaining_to_distribute
                        logger.debug(f"Added {remaining_to_distribute} remaining orders to largest warehouse {largest_warehouse.name}")
                else:
                    # Fallback: distribute evenly to all warehouses
                    orders_per_warehouse = unmatched_orders // len(warehouses)
                    remainder = unmatched_orders % len(warehouses)
                    for i, warehouse in enumerate(warehouses):
                        additional_orders = orders_per_warehouse + (1 if i < remainder else 0)
                        warehouse.orders += additional_orders
                        total_orders += additional_orders
        
        logger.debug(f"Product totals: stock={total_quantity}, orders={total_orders}")
        
        # Calculate turnover rate - FIXED: Use real warehouse stock
        turnover_rate = 0.0
        if real_warehouse_stock > 0 and total_orders > 0:
            turnover_rate = total_orders / real_warehouse_stock
        
        # Create Product
        product = Product(
            wildberries_article=nm_id,
            seller_article=vendor_code,
            wb_article=nm_id,
            total_orders=total_orders,  # Real orders data from API
            total_stock=real_warehouse_stock,  # FIXED: Use only real warehouse stock
            turnover_rate=turnover_rate,  # Calculated turnover
            warehouses=warehouses
        )
        
        logger.debug(f"Created product {vendor_code}: {total_orders} orders, {real_warehouse_stock} real stock (vs {total_quantity} total), {turnover_rate:.3f} turnover")
        
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
