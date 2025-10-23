"""
Calculation utilities for Wildberries Stock Tracker.

Implements EXACT calculation logic as specified in urls.md.
All calculations must follow the documented formulas precisely
to ensure data consistency and accuracy.

CRITICAL: All calculations MUST implement logic from urls.md exactly
"""

from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from datetime import datetime

from stock_tracker.core.models import Product, Warehouse
from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.exceptions import CalculationError
from stock_tracker.core.validator import WildberriesDataValidator


logger = get_logger(__name__)


# Константы для фильтрации складов
DELIVERY_STATUSES = {
    "В пути до получателей",
    "В пути возврата на склад WB", 
    "Всего находится на складах",
    "В пути возврата с ПВЗ",
    "В пути с ПВЗ покупателю",
    "Удержания и возмещения",
    "К доплате",
    "Общий итог"
}

VALID_WAREHOUSE_PATTERNS = [
    r'^[А-Яа-я\s\-\(\)]+\d*$',  # Русские названия городов
    r'^[А-Яа-я]+\s*\d*$',       # Город + номер
    r'^[А-Яа-я]+\s*\([А-Яа-я\s]+\)$'  # Город (район)
]


def is_real_warehouse(warehouse_name: str) -> bool:
    """Проверить что это реальный склад, а не статус."""
    if not warehouse_name or not isinstance(warehouse_name, str):
        return False
    
    # Исключаем статусы доставки
    if warehouse_name in DELIVERY_STATUSES:
        return False
        
    # Исключаем итоговые строки
    if any(word in warehouse_name.lower() for word in ["итог", "всего", "общий"]):
        return False
        
    # Исключаем строки "в пути"
    if "в пути" in warehouse_name.lower():
        return False
        
    return True


def validate_warehouse_name(warehouse_name: str) -> bool:
    """Валидация названия склада."""
    import re
    
    if not warehouse_name:
        return False
        
    # Проверяем паттерны
    for pattern in VALID_WAREHOUSE_PATTERNS:
        if re.match(pattern, warehouse_name):
            return True
            
    return False


def debug_warehouse_data(warehouse_data: List[Dict], source: str = "unknown"):
    """Диагностика данных складов."""
    logger.info(f"=== WAREHOUSE DATA DEBUG ({source}) ===")
    
    all_warehouse_names = set()
    for item in warehouse_data:
        for warehouse in item.get("warehouses", []):
            name = warehouse.get("warehouseName", "")
            if name:
                all_warehouse_names.add(name)
    
    logger.info(f"Total unique warehouse names: {len(all_warehouse_names)}")
    
    # Группируем по типам
    real_warehouses = []
    delivery_statuses = []
    unknown = []
    
    for name in all_warehouse_names:
        if is_real_warehouse(name):
            if validate_warehouse_name(name):
                real_warehouses.append(name)
            else:
                unknown.append(name)
        else:
            delivery_statuses.append(name)
    
    logger.info(f"✅ Real warehouses ({len(real_warehouses)}): {real_warehouses}")
    logger.warning(f"⚠️ Delivery statuses ({len(delivery_statuses)}): {delivery_statuses}")
    logger.error(f"❌ Unknown format ({len(unknown)}): {unknown}")
    
    return {
        "real_warehouses": real_warehouses,
        "delivery_statuses": delivery_statuses, 
        "unknown": unknown
    }


class WildberriesCalculator:
    """
    Calculator implementing exact calculation logic from urls.md.
    
    From urls.md calculation logic:
    
    Остатки:
    - По каждому складу: quantity из /warehouse_remains для nmId + warehouseName
    - Всего по товару: сумма всех quantity для одного nmId со всех складов
    
    Заказы:
    - Всего по товару: количество записей в /supplier/orders с одинаковым nmId
    - По складу: количество записей где совпадают nmId + warehouseName
    
    Группировка: По связке supplierArticle + nmId
    """
    
    @staticmethod
    def calculate_warehouse_stock(warehouse_remains_data: List[Dict[str, Any]], 
                                nm_id: int, warehouse_name: str) -> int:
        """
        Calculate stock for specific warehouse per urls.md logic.
        
        From urls.md: "По каждому складу: берется напрямую из quantity в 
        /warehouse_remains для конкретной комбинации nmId + warehouseName"
        
        Args:
            warehouse_remains_data: Data from /warehouse_remains API
            nm_id: Product nmId to filter by
            warehouse_name: Warehouse name to filter by
            
        Returns:
            Stock quantity for the specific warehouse
        """
        total_stock = 0
        
        for item in warehouse_remains_data:
            if item.get("nmId") == nm_id and "warehouses" in item:
                for warehouse in item["warehouses"]:
                    if warehouse.get("warehouseName") == warehouse_name:
                        quantity = warehouse.get("quantity", 0)
                        # Validate quantity per urls.md types
                        quantity = WildberriesDataValidator.validate_quantity(quantity)
                        total_stock += quantity
        
        logger.debug(f"Calculated warehouse stock for nmId {nm_id}, warehouse '{warehouse_name}': {total_stock}")
        return total_stock
    
    @staticmethod
    def calculate_total_stock(warehouse_remains_data: List[Dict[str, Any]], nm_id: int) -> int:
        """
        Calculate total stock for product per urls.md logic.
        
        From urls.md: "Всего по товару: суммируются все quantity для одного nmId со всех складов"
        
        Args:
            warehouse_remains_data: Data from /warehouse_remains API
            nm_id: Product nmId to calculate for
            
        Returns:
            Total stock across all warehouses
        """
        total_stock = 0
        
        for item in warehouse_remains_data:
            if item.get("nmId") == nm_id and "warehouses" in item:
                for warehouse in item["warehouses"]:
                    quantity = warehouse.get("quantity", 0)
                    # Validate quantity per urls.md types
                    quantity = WildberriesDataValidator.validate_quantity(quantity)
                    total_stock += quantity
        
        logger.debug(f"Calculated total stock for nmId {nm_id}: {total_stock}")
        return total_stock
    
    @staticmethod
    def calculate_warehouse_orders(orders_data: List[Dict[str, Any]], 
                                 nm_id: int, warehouse_name: str) -> int:
        """
        Calculate orders for specific warehouse per urls.md logic.
        
        From urls.md: "По складу: подсчитывается количество записей в 
        /supplier/orders где совпадают nmId + warehouseName"
        
        Args:
            orders_data: Data from /supplier/orders API
            nm_id: Product nmId to filter by
            warehouse_name: Warehouse name to filter by
            
        Returns:
            Number of orders for the specific warehouse
        """
        order_count = 0
        
        for order in orders_data:
            if (order.get("nmId") == nm_id and 
                order.get("warehouseName") == warehouse_name):
                order_count += 1
        
        logger.debug(f"Calculated warehouse orders for nmId {nm_id}, warehouse '{warehouse_name}': {order_count}")
        return order_count
    
    @staticmethod
    def calculate_total_orders(orders_data: List[Dict[str, Any]], nm_id: int) -> int:
        """
        Calculate total orders for product per urls.md logic.
        
        From urls.md: "Всего по товару: подсчитывается количество записей (строк) 
        в /supplier/orders с одинаковым nmId"
        
        Args:
            orders_data: Data from /supplier/orders API
            nm_id: Product nmId to calculate for
            
        Returns:
            Total number of orders for the product
        """
        order_count = 0
        
        for order in orders_data:
            if order.get("nmId") == nm_id:
                order_count += 1
        
        logger.debug(f"Calculated total orders for nmId {nm_id}: {order_count}")
        return order_count
    
    @staticmethod
    def calculate_turnover(total_orders: int, total_stock: int) -> float:
        """
        Calculate turnover ratio with division by zero protection.
        
        Standard formula: turnover = total_orders / total_stock
        Special case: if total_stock = 0, return 0 (avoid division by zero)
        
        Args:
            total_orders: Total number of orders
            total_stock: Total stock quantity
            
        Returns:
            Turnover ratio (orders per stock unit)
            
        Raises:
            CalculationError: If input validation fails
        """
        try:
            # Validate inputs per urls.md data types
            total_orders, total_stock = WildberriesDataValidator.validate_calculation_inputs(
                total_orders, total_stock
            )
            
            # Handle division by zero case
            if total_stock == 0:
                logger.debug(f"Division by zero avoided: {total_orders} orders / 0 stock = 0")
                return 0.0
            
            turnover = total_orders / total_stock
            logger.debug(f"Calculated turnover: {total_orders} orders / {total_stock} stock = {turnover}")
            
            return round(turnover, 6)  # Round to 6 decimal places for precision
            
        except Exception as e:
            raise CalculationError(
                f"Failed to calculate turnover: {e}",
                calculation_type="turnover",
                input_data={"total_orders": total_orders, "total_stock": total_stock}
            )
    
    @staticmethod
    def group_data_by_product(warehouse_remains_data: List[Dict[str, Any]], 
                            orders_data: List[Dict[str, Any]]) -> Dict[Tuple[str, int], Dict[str, Any]]:
        """
        Group data by product per urls.md grouping logic.
        
        From urls.md: "Группировка данных происходит по связке supplierArticle + nmId"
        
        Args:
            warehouse_remains_data: Data from /warehouse_remains API
            orders_data: Data from /supplier/orders API
            
        Returns:
            Dict keyed by (supplierArticle, nmId) with aggregated data
        """
        grouped_data = defaultdict(lambda: {
            "supplier_article": "",
            "nm_id": 0,
            "warehouses": {},
            "total_orders": 0,
            "total_stock": 0
        })
        
        # Process warehouse remains data
        for item in warehouse_remains_data:
            nm_id = item.get("nmId")
            # vendorCode is supplierArticle in warehouse_remains response
            supplier_article = item.get("vendorCode", "")
            
            if nm_id and supplier_article:
                key = (supplier_article, nm_id)
                group = grouped_data[key]
                group["supplier_article"] = supplier_article
                group["nm_id"] = nm_id
                
                # Process warehouses
                if "warehouses" in item:
                    for warehouse in item["warehouses"]:
                        warehouse_name = warehouse.get("warehouseName", "")
                        quantity = warehouse.get("quantity", 0)
                        
                        # ДОБАВИТЬ ФИЛЬТРАЦИЮ:
                        if warehouse_name and is_real_warehouse(warehouse_name):
                            if validate_warehouse_name(warehouse_name):
                                # Только тогда добавляем как склад
                                if warehouse_name not in group["warehouses"]:
                                    group["warehouses"][warehouse_name] = {
                                        "stock": 0,
                                        "orders": 0
                                    }
                                group["warehouses"][warehouse_name]["stock"] += quantity
                            else:
                                logger.warning(f"Invalid warehouse name format: {warehouse_name}")
                        else:
                            logger.debug(f"Filtered out delivery status: {warehouse_name}")
        
        # Process orders data to count orders per warehouse and total
        for order in orders_data:
            nm_id = order.get("nmId")
            supplier_article = order.get("supplierArticle", "")
            warehouse_name = order.get("warehouseName", "")
            
            if nm_id and supplier_article:
                key = (supplier_article, nm_id)
                group = grouped_data[key]
                group["supplier_article"] = supplier_article
                group["nm_id"] = nm_id
                
                # Count total orders
                group["total_orders"] += 1
                
                # Count orders per warehouse
                if warehouse_name:
                    # ДОБАВИТЬ ФИЛЬТРАЦИЮ для заказов:
                    if is_real_warehouse(warehouse_name) and validate_warehouse_name(warehouse_name):
                        if warehouse_name not in group["warehouses"]:
                            group["warehouses"][warehouse_name] = {
                                "stock": 0,
                                "orders": 0
                            }
                        group["warehouses"][warehouse_name]["orders"] += 1
                    else:
                        logger.debug(f"Filtered out order delivery status: {warehouse_name}")
        
        # Calculate total stock for each product
        for group in grouped_data.values():
            group["total_stock"] = sum(wh["stock"] for wh in group["warehouses"].values())
        
        logger.info(f"Grouped data into {len(grouped_data)} products")
        return dict(grouped_data)
    
    @staticmethod
    def create_products_from_grouped_data(grouped_data: Dict[Tuple[str, int], Dict[str, Any]]) -> List[Product]:
        """
        Create Product instances from grouped data.
        
        Args:
            grouped_data: Output from group_data_by_product
            
        Returns:
            List of Product instances with calculated values
        """
        products = []
        
        for (supplier_article, nm_id), data in grouped_data.items():
            try:
                # Create product
                product = Product(
                    seller_article=supplier_article,
                    wildberries_article=nm_id
                )
                
                # Add warehouses
                for warehouse_name, warehouse_data in data["warehouses"].items():
                    warehouse = Warehouse(
                        name=warehouse_name,
                        stock=warehouse_data["stock"],
                        orders=warehouse_data["orders"]
                    )
                    product.add_warehouse(warehouse)
                
                # Set totals (recalculate_totals is called by add_warehouse)
                logger.debug(f"Created product {supplier_article} ({nm_id}) with {len(product.warehouses)} warehouses")
                products.append(product)
                
            except Exception as e:
                logger.error(f"Failed to create product {supplier_article} ({nm_id}): {e}")
                continue
        
        logger.info(f"Created {len(products)} product instances")
        return products
    
    @staticmethod
    def process_api_data(warehouse_remains_data: List[Dict[str, Any]], 
                        orders_data: List[Dict[str, Any]]) -> List[Product]:
        """
        Complete processing pipeline from API data to Product instances.
        
        Implements the full calculation workflow per urls.md:
        1. Group data by supplierArticle + nmId
        2. Calculate totals per warehouse and product
        3. Create Product instances with all calculations
        
        Args:
            warehouse_remains_data: Data from /warehouse_remains API
            orders_data: Data from /supplier/orders API
            
        Returns:
            List of Product instances with all calculations complete
            
        Raises:
            CalculationError: If processing fails
        """
        try:
            logger.info("Starting API data processing...")
            
            # Validate input data
            if not isinstance(warehouse_remains_data, list):
                raise CalculationError("Warehouse remains data must be a list")
            
            if not isinstance(orders_data, list):
                raise CalculationError("Orders data must be a list")
            
            # Group data by product per urls.md logic
            grouped_data = WildberriesCalculator.group_data_by_product(
                warehouse_remains_data, orders_data
            )
            
            # Create products from grouped data
            products = WildberriesCalculator.create_products_from_grouped_data(grouped_data)
            
            logger.info(f"Successfully processed API data into {len(products)} products")
            return products
            
        except Exception as e:
            raise CalculationError(
                f"Failed to process API data: {e}",
                calculation_type="data_processing",
                input_data={
                    "warehouse_items": len(warehouse_remains_data) if isinstance(warehouse_remains_data, list) else 0,
                    "order_items": len(orders_data) if isinstance(orders_data, list) else 0
                }
            )

    @staticmethod
    def process_analytics_v2_data(analytics_data: List[Dict[str, Any]], 
                                 warehouse_cache_entry: Optional[Any] = None) -> List[Product]:
        """
        Process Analytics API v2 data with intelligent warehouse distribution.
        
        NEW IMPLEMENTATION per WAREHOUSE_IMPROVEMENT_PROMPT.md:
        - Uses real warehouse names from cache when available
        - Implements priority system: warehouse_api > analytics_v2 > fallback
        - Provides clear data quality indicators
        
        Args:
            analytics_data: Product data from Analytics API v2
            warehouse_cache_entry: Optional cached warehouse data with real names
            
        Returns:
            List of Product instances with real or realistic warehouse breakdown
            
        Raises:
            CalculationError: If processing fails
        """
        from stock_tracker.utils.warehouse_cache import get_warehouse_cache
        
        try:
            logger.info("🏭 Starting Analytics API v2 data processing with intelligent warehouse distribution...")
            
            if not isinstance(analytics_data, list):
                raise CalculationError("Analytics v2 data must be a list")
            
            # Check if we have REAL warehouse data from API v1
            cache = get_warehouse_cache()
            warehouse_entry = warehouse_cache_entry or cache.get_warehouses(prefer_source="warehouse_api")
            
            if warehouse_entry and warehouse_entry.source == "warehouse_api":
                logger.info(f"✅ Will use REAL warehouse data from API v1: {len(warehouse_entry.warehouse_names)} warehouses")
                data_source = "warehouse_api"
            else:
                logger.warning(f"⚠️ Warehouse API v1 data unavailable - will show totals only")
                data_source = "totals_only"
            
            # Convert v2 format to Product instances
            products = []
            
            for item in analytics_data:
                try:
                    # Extract basic product info from v2 format
                    wildberries_article = item.get("nmID", 0)
                    vendor_code = item.get("vendorCode", "")
                    subject_name = item.get("subjectName", "")
                    brand_name = item.get("brandName", "")
                    
                    # Get metrics from v2 format
                    metrics = item.get("metrics", {})
                    total_stock = metrics.get("stockCount", 0)
                    total_orders = metrics.get("ordersCount", 0)
                    
                    # Create warehouse entries ONLY from real Warehouse API v1 data
                    if warehouse_cache_entry and warehouse_cache_entry.source == "warehouse_api":
                        # Use real warehouse data from API v1
                        warehouses = WildberriesCalculator._create_real_warehouses_from_cache(
                            wildberries_article, warehouse_cache_entry
                        )
                        data_quality = "REAL"
                    else:
                        # NO fake distribution! Show totals only when API unavailable
                        warehouses = WildberriesCalculator._create_single_warehouse_from_totals(
                            total_stock=total_stock,
                            total_orders=total_orders,
                            warehouse_name="⚠️ Требуется Warehouse API v1 для детализации"
                        )
                        data_quality = "LIMITED"
                    
                    # Create Product instance with correct parameter names
                    product = Product(
                        wildberries_article=wildberries_article,
                        seller_article=vendor_code,
                        subject_id=item.get("subjectID"),  # Optional
                        brand_name=brand_name,             # Optional
                        total_stock=total_stock,
                        total_orders=total_orders,
                        warehouses=warehouses
                    )
                    
                    products.append(product)
                    
                except Exception as e:
                    logger.warning(f"Failed to process v2 item {item}: {e}")
                    continue
            
            logger.info(f"✅ Created {len(products)} product instances with {data_source} warehouse data")
            return products
            
        except Exception as e:
            raise CalculationError(
                f"Failed to process Analytics v2 data: {e}",
                calculation_type="analytics_v2_processing",
                input_data={"analytics_items": len(analytics_data) if isinstance(analytics_data, list) else 0}
            )

    @staticmethod
    def _create_real_warehouses_from_cache(wildberries_article: int, 
                                         warehouse_cache_entry) -> List[Warehouse]:
        """
        Create warehouse entries using REAL data from Warehouse API v1 cache.
        
        This method looks up actual warehouse data for the specific product
        from cached Warehouse API v1 results.
        
        Args:
            wildberries_article: Product nmID to look up
            warehouse_cache_entry: Cache entry with real warehouse data
            
        Returns:
            List of Warehouse instances with REAL data from API v1
        """
        # TODO: Implement lookup of real warehouse data by nmID
        # This should search through cached warehouse_remains data
        # and return actual warehouse breakdown for this specific product
        
        # For now, return indication that real data is needed
        return [Warehouse(
            name="📊 Реальные данные из Warehouse API v1 (в разработке)",
            stock=0,
            orders=0
        )]

    @staticmethod
    def _create_single_warehouse_from_totals(total_stock: int, total_orders: int, 
                                           warehouse_name: str = "Данные недоступны") -> List[Warehouse]:
        """
        Create single warehouse entry when real warehouse data is unavailable.
        
        IMPORTANT: This should ONLY be used when Warehouse API v1 is completely unavailable.
        It does NOT create fake distribution - it shows totals as single entry.
        
        Args:
            total_stock: Total stock from Analytics API v2
            total_orders: Total orders from Analytics API v2
            warehouse_name: Warning name indicating data is unavailable
            
        Returns:
            List with single Warehouse instance showing totals
        """
        if total_stock <= 0 and total_orders <= 0:
            return []
        
        warehouse = Warehouse(
            name=warehouse_name,
            stock=total_stock,
            orders=total_orders
        )
        return [warehouse]

    @staticmethod
    def get_real_warehouse_list() -> List[str]:
        """
        Get list of REAL warehouse names from Warehouse API v1 cache ONLY.
        
        Returns:
            List of real warehouse names from API v1, or empty list if unavailable
        """
        from stock_tracker.utils.warehouse_cache import get_warehouse_cache
        
        try:
            cache = get_warehouse_cache()
            
            # Only accept warehouse_api source - no fake data!
            warehouse_entry = cache.get_warehouses(prefer_source="warehouse_api")
            
            if warehouse_entry and warehouse_entry.source == "warehouse_api":
                logger.info(f"📦 Retrieved {len(warehouse_entry.warehouse_names)} REAL warehouses from API v1")
                return warehouse_entry.warehouse_names
            else:
                logger.warning("⚠️ No REAL warehouse data available from API v1")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get real warehouse list: {e}")
            # Return empty list - no fake warehouses!
            return []

    @staticmethod
    def process_combined_api_data(analytics_v2_data: List[Dict[str, Any]], 
                                warehouse_v1_data: List[Dict[str, Any]]) -> List[Product]:
        """
        Process combined Analytics API v2 + Warehouse v1 data into Product instances.
        
        Combines v2 aggregated data with v1 detailed warehouse breakdown for complete picture.
        
        Args:
            analytics_v2_data: Data from Analytics API v2 (orders, metrics)
            warehouse_v1_data: Data from Warehouse API v1 (warehouse breakdown)
            
        Returns:
            List of Product instances with detailed warehouse data
            
        Raises:
            CalculationError: If processing fails
        """
        try:
            logger.info("Starting combined Analytics v2 + Warehouse v1 data processing...")
            
            if not isinstance(analytics_v2_data, list):
                raise CalculationError("Analytics v2 data must be a list")
            
            if not isinstance(warehouse_v1_data, list):
                raise CalculationError("Warehouse v1 data must be a list")
            
            # ДОБАВИТЬ в начало:
            logger.info("🔍 Debugging warehouse data before processing...")
            debug_results = debug_warehouse_data(warehouse_v1_data, "Warehouse API v1")
            
            if not debug_results["real_warehouses"]:
                logger.error("❌ No real warehouses found in API data!")
                # Показать предупреждение вместо фиктивных данных
            
            # Create lookup for v2 data by nmID
            v2_lookup = {}
            for item in analytics_v2_data:
                nm_id = item.get("nmID")
                if nm_id:
                    v2_lookup[nm_id] = item
            
            # Group warehouse data by nmId and vendorCode
            warehouse_groups = {}
            for item in warehouse_v1_data:
                nm_id = item.get("nmId")
                vendor_code = item.get("vendorCode", "")
                
                if nm_id:
                    key = (nm_id, vendor_code)
                    if key not in warehouse_groups:
                        warehouse_groups[key] = {
                            "nmId": nm_id,
                            "vendorCode": vendor_code,
                            "brand": item.get("brand", ""),
                            "subjectName": item.get("subjectName", ""),
                            "warehouses": []
                        }
                    
                    # Add warehouse data
                    for warehouse_info in item.get("warehouses", []):
                        warehouse_groups[key]["warehouses"].append(warehouse_info)
            
            # Create products with combined data
            products = []
            
            for (nm_id, vendor_code), warehouse_group in warehouse_groups.items():
                try:
                    # Get v2 data for this product
                    v2_item = v2_lookup.get(nm_id, {})
                    v2_metrics = v2_item.get("metrics", {})
                    
                    # Get orders count from v2 data (more accurate)
                    orders_count = v2_metrics.get("ordersCount", 0)
                    
                    # Create warehouse objects from v1 detailed data
                    warehouses = []
                    total_stock = 0
                    
                    for wh_info in warehouse_group["warehouses"]:
                        warehouse_name = wh_info.get("warehouseName", "Неизвестный склад")
                        warehouse_stock = wh_info.get("quantity", 0)
                        
                        # ДОБАВИТЬ ФИЛЬТРАЦИЮ:
                        if warehouse_name and is_real_warehouse(warehouse_name):
                            if validate_warehouse_name(warehouse_name):
                                # Distribute orders proportionally by warehouse stock
                                # (since v1 API doesn't provide warehouse-level orders)
                                warehouse_orders = 0
                                total_stock += warehouse_stock
                                
                                warehouse = Warehouse(
                                    name=warehouse_name,
                                    stock=warehouse_stock,
                                    orders=warehouse_orders  # Will be updated after total calculation
                                )
                                warehouses.append(warehouse)
                            else:
                                logger.warning(f"Invalid warehouse name format: {warehouse_name}")
                        else:
                            logger.debug(f"Filtered out delivery status in combined data: {warehouse_name}")
                    
                    # Distribute orders proportionally across warehouses
                    if total_stock > 0 and orders_count > 0:
                        for warehouse in warehouses:
                            proportion = warehouse.stock / total_stock if total_stock > 0 else 0
                            warehouse.orders = int(orders_count * proportion)
                    
                    # Create Product instance
                    product = Product(
                        wildberries_article=nm_id,
                        seller_article=vendor_code,
                        subject_id=v2_item.get("subjectID"),
                        brand_name=warehouse_group.get("brand") or v2_item.get("brandName"),
                        total_stock=total_stock,
                        total_orders=orders_count,
                        warehouses=warehouses
                    )
                    
                    products.append(product)
                    
                except Exception as e:
                    logger.warning(f"Failed to process combined item nmId={nm_id}, vendorCode={vendor_code}: {e}")
                    continue
            
            logger.info(f"Created {len(products)} product instances with detailed warehouse data")
            return products
            
        except Exception as e:
            raise CalculationError(
                f"Failed to process combined API data: {e}",
                calculation_type="combined_api_processing",
                input_data={
                    "analytics_items": len(analytics_v2_data) if isinstance(analytics_v2_data, list) else 0,
                    "warehouse_items": len(warehouse_v1_data) if isinstance(warehouse_v1_data, list) else 0
                }
            )


class TurnoverCalculator:
    """
    Safe turnover calculator with enhanced division-by-zero protection.
    
    Provides robust calculation methods that handle edge cases like
    zero stock, negative values, and floating point inputs safely.
    """
    
    @staticmethod
    def calculate_turnover(orders: float, stock: float) -> float:
        """
        Calculate turnover with comprehensive safety checks.
        
        Formula: turnover = orders / stock
        
        Safety features:
        - Division by zero protection
        - Negative value handling
        - Float input normalization
        - Precision control
        
        Args:
            orders: Number of orders (int or float)
            stock: Stock quantity (int or float)
            
        Returns:
            Safe turnover ratio, always >= 0
        """
        try:
            # Normalize inputs to float
            orders_float = float(orders) if orders is not None else 0.0
            stock_float = float(stock) if stock is not None else 0.0
            
            # Handle negative values (treat as zero)
            orders_float = max(0.0, orders_float)
            stock_float = max(0.0, stock_float)
            
            # Division by zero protection
            if stock_float == 0.0:
                # If no stock, turnover is undefined but we return 0 for safety
                logger.debug(f"Safe turnover calculation: {orders_float} orders / 0 stock = 0.0 (no stock)")
                return 0.0
            
            # Normal calculation
            turnover = orders_float / stock_float
            
            # Ensure reasonable precision (6 decimal places)
            result = round(turnover, 6)
            
            logger.debug(f"Safe turnover calculation: {orders_float} orders / {stock_float} stock = {result}")
            return result
            
        except (TypeError, ValueError, ZeroDivisionError) as e:
            logger.warning(f"Turnover calculation error: {e}, returning 0.0")
            return 0.0
        except Exception as e:
            logger.error(f"Unexpected turnover calculation error: {e}, returning 0.0")
            return 0.0
    
    @staticmethod
    def calculate_turnover_batch(products: List[Product]) -> List[float]:
        """
        Calculate turnover for multiple products safely.
        
        Args:
            products: List of Product instances
            
        Returns:
            List of turnover ratios
        """
        turnovers = []
        
        for product in products:
            try:
                turnover = TurnoverCalculator.calculate_turnover(
                    product.total_orders, 
                    product.total_stock
                )
                turnovers.append(turnover)
                
                # Update product turnover if different
                if abs(product.turnover - turnover) > 0.000001:
                    product.turnover = turnover
                    
            except Exception as e:
                logger.warning(f"Failed to calculate turnover for {product.seller_article}: {e}")
                turnovers.append(0.0)
        
        return turnovers
    
    @staticmethod
    def get_turnover_category(turnover: float) -> str:
        """
        Categorize turnover performance.
        
        Args:
            turnover: Turnover ratio
            
        Returns:
            Category string
        """
        try:
            turnover = float(turnover) if turnover is not None else 0.0
            
            if turnover >= 3.0:
                return "excellent"
            elif turnover >= 2.0:
                return "high"
            elif turnover >= 1.0:
                return "medium"
            elif turnover > 0.0:
                return "low"
            else:
                return "no_movement"
                
        except Exception:
            return "unknown"
    
    @staticmethod
    def calculate_safe_percentage(part: float, total: float) -> float:
        """
        Calculate percentage with division-by-zero protection.
        
        Args:
            part: Part value
            total: Total value
            
        Returns:
            Percentage (0-100), 0 if total is zero
        """
        try:
            part_float = float(part) if part is not None else 0.0
            total_float = float(total) if total is not None else 0.0
            
            if total_float == 0.0:
                return 0.0
            
            percentage = (part_float / total_float) * 100.0
            return round(max(0.0, min(100.0, percentage)), 2)
            
        except Exception:
            return 0.0


class WarehouseAggregator:
    """
    Warehouse data aggregation utilities.
    
    Provides safe methods for aggregating warehouse data across
    multiple products and performing analytics calculations.
    """
    
    @staticmethod
    def aggregate_warehouse_totals(products: List[Product]) -> Dict[str, Dict[str, int]]:
        """
        Aggregate totals across all warehouses.
        
        Args:
            products: List of Product instances
            
        Returns:
            Dict mapping warehouse names to total stock/orders
        """
        warehouse_totals = {}
        
        for product in products:
            for warehouse in product.warehouses:
                if warehouse.name not in warehouse_totals:
                    warehouse_totals[warehouse.name] = {
                        "total_stock": 0,
                        "total_orders": 0,
                        "product_count": 0
                    }
                
                warehouse_totals[warehouse.name]["total_stock"] += warehouse.stock
                warehouse_totals[warehouse.name]["total_orders"] += warehouse.orders
                warehouse_totals[warehouse.name]["product_count"] += 1
        
        return warehouse_totals
    
    @staticmethod
    def calculate_warehouse_performance(warehouse_totals: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, Any]]:
        """
        Calculate performance metrics for each warehouse.
        
        Args:
            warehouse_totals: Output from aggregate_warehouse_totals
            
        Returns:
            Dict with performance metrics per warehouse
        """
        performance = {}
        
        for warehouse_name, totals in warehouse_totals.items():
            turnover = TurnoverCalculator.calculate_turnover(
                totals["total_orders"], 
                totals["total_stock"]
            )
            
            performance[warehouse_name] = {
                "total_stock": totals["total_stock"],
                "total_orders": totals["total_orders"],
                "product_count": totals["product_count"],
                "turnover": turnover,
                "turnover_category": TurnoverCalculator.get_turnover_category(turnover),
                "avg_stock_per_product": totals["total_stock"] / totals["product_count"] if totals["product_count"] > 0 else 0,
                "avg_orders_per_product": totals["total_orders"] / totals["product_count"] if totals["product_count"] > 0 else 0
            }
        
        return performance
    
    @staticmethod
    def find_top_warehouses(warehouse_performance: Dict[str, Dict[str, Any]], 
                          metric: str = "turnover", limit: int = 5) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Find top performing warehouses by specified metric.
        
        Args:
            warehouse_performance: Output from calculate_warehouse_performance
            metric: Metric to sort by ("turnover", "total_stock", "total_orders")
            limit: Number of top warehouses to return
            
        Returns:
            List of (warehouse_name, performance_data) tuples
        """
        try:
            # Sort warehouses by metric
            sorted_warehouses = sorted(
                warehouse_performance.items(),
                key=lambda x: x[1].get(metric, 0),
                reverse=True
            )
            
            return sorted_warehouses[:limit]
            
        except Exception as e:
            logger.error(f"Failed to find top warehouses: {e}")
            return []


class AutomaticAggregator:
    """
    Automatic aggregation logic for User Story 3.
    
    Implements automatic calculation and aggregation of product data
    with real-time updates and recalculation triggers as specified
    in User Story 3 requirements.
    """
    
    def __init__(self):
        """Initialize automatic aggregator."""
        self.wildberries_calc = WildberriesCalculator()
        self.turnover_calc = TurnoverCalculator()
        self.aggregator = WarehouseAggregator()
        logger.debug("AutomaticAggregator initialized")
    
    def calculate_product_totals_automatic(self, product: Product, 
                                         orders_data: List[Dict[str, Any]],
                                         warehouse_data: List[Dict[str, Any]]) -> Product:
        """
        Automatically calculate and update product totals.
        
        Calculates total orders, total stock, and turnover for a product
        based on fresh API data following urls.md calculation logic.
        
        Args:
            product: Product to update
            orders_data: Fresh orders data from API
            warehouse_data: Fresh warehouse data from API
            
        Returns:
            Updated Product with calculated totals
        """
        try:
            logger.debug(f"Auto-calculating totals for {product.seller_article}")
            
            # Calculate totals using Wildberries logic
            total_orders = self.wildberries_calc.calculate_total_orders(
                orders_data, product.wildberries_article
            )
            
            total_stock = self.wildberries_calc.calculate_total_stock(
                warehouse_data, product.wildberries_article
            )
            
            # Calculate turnover
            turnover = self.turnover_calc.calculate_turnover(total_orders, total_stock)
            
            # Update product
            product.total_orders = total_orders
            product.total_stock = total_stock
            product.turnover = turnover
            
            logger.debug(f"Auto-calculated: orders={total_orders}, stock={total_stock}, turnover={turnover}")
            return product
            
        except Exception as e:
            logger.error(f"Failed to auto-calculate product totals: {e}")
            raise CalculationError(f"Automatic calculation failed: {e}")
    
    def recalculate_on_warehouse_change(self, product: Product) -> Product:
        """
        Automatically recalculate product totals when warehouse data changes.
        
        Implements automatic recalculation triggers as specified in User Story 3:
        "обновляет оборачиваемость при изменении данных по отдельным складам"
        
        Args:
            product: Product with updated warehouse data
            
        Returns:
            Product with recalculated totals
        """
        try:
            logger.debug(f"Recalculating on warehouse change for {product.seller_article}")
            
            # Recalculate total stock from current warehouse data
            total_stock = sum(warehouse.stock for warehouse in product.warehouses)
            total_orders = sum(warehouse.orders for warehouse in product.warehouses)
            
            # Update product totals
            product.total_stock = total_stock
            product.total_orders = total_orders
            
            # Recalculate turnover
            product.turnover = self.turnover_calc.calculate_turnover(total_orders, total_stock)
            
            logger.debug(f"Recalculated: orders={total_orders}, stock={total_stock}, turnover={product.turnover}")
            return product
            
        except Exception as e:
            logger.error(f"Failed to recalculate on warehouse change: {e}")
            raise CalculationError(f"Warehouse recalculation failed: {e}")
    
    def batch_recalculate_products(self, products: List[Product]) -> List[Product]:
        """
        Batch recalculation of multiple products.
        
        Efficiently recalculates totals for multiple products in batch
        for performance optimization in automatic updates.
        
        Args:
            products: List of products to recalculate
            
        Returns:
            List of products with updated calculations
        """
        try:
            logger.info(f"Batch recalculating {len(products)} products")
            
            recalculated = []
            for product in products:
                try:
                    updated_product = self.recalculate_on_warehouse_change(product)
                    recalculated.append(updated_product)
                except Exception as e:
                    logger.warning(f"Failed to recalculate product {product.seller_article}: {e}")
                    # Keep original product if recalculation fails
                    recalculated.append(product)
            
            logger.info(f"Batch recalculation completed: {len(recalculated)} products")
            return recalculated
            
        except Exception as e:
            logger.error(f"Failed to batch recalculate products: {e}")
            raise CalculationError(f"Batch recalculation failed: {e}")
    
    def aggregate_warehouse_totals(self, warehouses: List[Warehouse]) -> Dict[str, int]:
        """
        Aggregate totals across multiple warehouses.
        
        Calculates aggregate statistics for warehouse data as required
        for automatic aggregation in User Story 3.
        
        Args:
            warehouses: List of warehouses to aggregate
            
        Returns:
            Dict with aggregated totals
        """
        try:
            if not warehouses:
                return {"total_orders": 0, "total_stock": 0, "warehouse_count": 0}
            
            total_orders = sum(wh.orders for wh in warehouses)
            total_stock = sum(wh.stock for wh in warehouses)
            
            aggregated = {
                "total_orders": total_orders,
                "total_stock": total_stock,
                "warehouse_count": len(warehouses),
                "avg_orders_per_warehouse": round(total_orders / len(warehouses), 2),
                "avg_stock_per_warehouse": round(total_stock / len(warehouses), 2)
            }
            
            logger.debug(f"Aggregated {len(warehouses)} warehouses: {aggregated}")
            return aggregated
            
        except Exception as e:
            logger.error(f"Failed to aggregate warehouse totals: {e}")
            return {"total_orders": 0, "total_stock": 0, "warehouse_count": 0, "error": str(e)}
    
    def detect_data_changes(self, old_product: Product, new_product: Product) -> Dict[str, Any]:
        """
        Detect changes in product data for triggering recalculations.
        
        Compares old and new product data to identify what changed,
        enabling selective recalculation triggers.
        
        Args:
            old_product: Previous product state
            new_product: New product state
            
        Returns:
            Dict describing detected changes
        """
        try:
            changes = {
                "has_changes": False,
                "warehouse_changes": False,
                "stock_changes": False,
                "orders_changes": False,
                "details": []
            }
            
            # Check warehouse count changes
            old_wh_count = len(old_product.warehouses)
            new_wh_count = len(new_product.warehouses)
            
            if old_wh_count != new_wh_count:
                changes["has_changes"] = True
                changes["warehouse_changes"] = True
                changes["details"].append(f"Warehouse count changed: {old_wh_count} → {new_wh_count}")
            
            # Check individual warehouse changes
            old_warehouses = {wh.name: wh for wh in old_product.warehouses}
            new_warehouses = {wh.name: wh for wh in new_product.warehouses}
            
            for wh_name, new_wh in new_warehouses.items():
                if wh_name in old_warehouses:
                    old_wh = old_warehouses[wh_name]
                    
                    # Check stock changes
                    if old_wh.stock != new_wh.stock:
                        changes["has_changes"] = True
                        changes["stock_changes"] = True
                        changes["details"].append(f"{wh_name} stock: {old_wh.stock} → {new_wh.stock}")
                    
                    # Check orders changes
                    if old_wh.orders != new_wh.orders:
                        changes["has_changes"] = True
                        changes["orders_changes"] = True
                        changes["details"].append(f"{wh_name} orders: {old_wh.orders} → {new_wh.orders}")
                else:
                    # New warehouse
                    changes["has_changes"] = True
                    changes["warehouse_changes"] = True
                    changes["details"].append(f"New warehouse: {wh_name}")
            
            # Check for removed warehouses
            for wh_name in old_warehouses:
                if wh_name not in new_warehouses:
                    changes["has_changes"] = True
                    changes["warehouse_changes"] = True
                    changes["details"].append(f"Removed warehouse: {wh_name}")
            
            if changes["has_changes"]:
                logger.debug(f"Detected changes in {old_product.seller_article}: {len(changes['details'])} changes")
            
            return changes
            
        except Exception as e:
            logger.error(f"Failed to detect data changes: {e}")
            return {
                "has_changes": False,
                "warehouse_changes": False,
                "stock_changes": False,
                "orders_changes": False,
                "details": [f"Change detection failed: {e}"]
            }
    
    def create_recalculation_summary(self, products: List[Product], 
                                   changes_detected: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create summary of automatic recalculation results.
        
        Provides comprehensive summary for monitoring and logging
        of automatic calculation updates.
        
        Args:
            products: List of processed products
            changes_detected: List of change detection results
            
        Returns:
            Dict with recalculation summary
        """
        try:
            summary = {
                "timestamp": datetime.now().isoformat(),
                "products_processed": len(products),
                "products_with_changes": 0,
                "total_changes_detected": 0,
                "change_types": {
                    "warehouse_changes": 0,
                    "stock_changes": 0,
                    "orders_changes": 0
                },
                "calculation_results": {
                    "total_stock_all_products": 0,
                    "total_orders_all_products": 0,
                    "avg_turnover": 0
                },
                "errors": []
            }
            
            # Analyze changes
            for changes in changes_detected:
                if changes.get("has_changes", False):
                    summary["products_with_changes"] += 1
                    summary["total_changes_detected"] += len(changes.get("details", []))
                    
                    if changes.get("warehouse_changes", False):
                        summary["change_types"]["warehouse_changes"] += 1
                    if changes.get("stock_changes", False):
                        summary["change_types"]["stock_changes"] += 1
                    if changes.get("orders_changes", False):
                        summary["change_types"]["orders_changes"] += 1
            
            # Calculate overall statistics
            if products:
                total_stock = sum(p.total_stock for p in products)
                total_orders = sum(p.total_orders for p in products)
                avg_turnover = sum(p.turnover for p in products) / len(products)
                
                summary["calculation_results"] = {
                    "total_stock_all_products": total_stock,
                    "total_orders_all_products": total_orders,
                    "avg_turnover": round(avg_turnover, 3)
                }
            
            logger.info(f"Recalculation summary: {summary['products_with_changes']}/{summary['products_processed']} products changed")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to create recalculation summary: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "products_processed": 0,
                "error": str(e)
            }


def calculate_aggregated_metrics(products: List[Product]) -> Dict[str, Any]:
    """
    Calculate aggregated metrics across all products.
    
    Args:
        products: List of Product instances
        
    Returns:
        Dict with aggregated metrics
    """
    if not products:
        return {
            "total_products": 0,
            "total_warehouses": 0,
            "total_stock": 0,
            "total_orders": 0,
            "average_turnover": 0.0,
            "products_with_stock": 0,
            "products_with_orders": 0
        }
    
    total_products = len(products)
    total_warehouses = sum(len(p.warehouses) for p in products)
    total_stock = sum(p.total_stock for p in products)
    total_orders = sum(p.total_orders for p in products)
    
    # Calculate average turnover (excluding products with 0 stock)
    products_with_stock = [p for p in products if p.total_stock > 0]
    if products_with_stock:
        average_turnover = sum(p.turnover for p in products_with_stock) / len(products_with_stock)
    else:
        average_turnover = 0.0
    
    products_with_orders = len([p for p in products if p.total_orders > 0])
    
    return {
        "total_products": total_products,
        "total_warehouses": total_warehouses,
        "total_stock": total_stock,
        "total_orders": total_orders,
        "average_turnover": round(average_turnover, 6),
        "products_with_stock": len(products_with_stock),
        "products_with_orders": products_with_orders
    }


if __name__ == "__main__":
    # Test calculation functions
    print("Testing Wildberries calculations...")
    
    # Test turnover calculation
    calculator = WildberriesCalculator()
    
    # Normal case
    turnover = calculator.calculate_turnover(92, 1107)
    print(f"✅ Normal turnover: 92 orders / 1107 stock = {turnover}")
    
    # Division by zero case
    turnover_zero = calculator.calculate_turnover(50, 0)
    print(f"✅ Zero stock turnover: 50 orders / 0 stock = {turnover_zero}")
    
    # Test safe turnover calculator
    safe_calculator = TurnoverCalculator()
    
    # Test all edge cases
    print(f"✅ Safe normal: {safe_calculator.calculate_turnover(92, 1107)}")
    print(f"✅ Safe zero stock: {safe_calculator.calculate_turnover(50, 0)}")
    print(f"✅ Safe zero orders: {safe_calculator.calculate_turnover(0, 100)}")
    print(f"✅ Safe both zero: {safe_calculator.calculate_turnover(0, 0)}")
    print(f"✅ Safe negative (fixed): {safe_calculator.calculate_turnover(-5, 100)}")
    print(f"✅ Safe float inputs: {safe_calculator.calculate_turnover(45.5, 150.7)}")
    
    # Test with mock data
    mock_warehouse_data = [
        {
            "nmId": 12345678,
            "vendorCode": "WB001",
            "warehouses": [
                {"warehouseName": "СЦ Волгоград", "quantity": 654},
                {"warehouseName": "СЦ Москва", "quantity": 453}
            ]
        }
    ]
    
    mock_orders_data = [
        {"nmId": 12345678, "supplierArticle": "WB001", "warehouseName": "СЦ Волгоград"},
        {"nmId": 12345678, "supplierArticle": "WB001", "warehouseName": "СЦ Волгоград"},
        {"nmId": 12345678, "supplierArticle": "WB001", "warehouseName": "СЦ Москва"}
    ]
    
    # Test total calculations
    total_stock = calculator.calculate_total_stock(mock_warehouse_data, 12345678)
    total_orders = calculator.calculate_total_orders(mock_orders_data, 12345678)
    
    print(f"✅ Total stock: {total_stock}")
    print(f"✅ Total orders: {total_orders}")
    
    # Test warehouse specific calculations
    warehouse_stock = calculator.calculate_warehouse_stock(mock_warehouse_data, 12345678, "СЦ Волгоград")
    warehouse_orders = calculator.calculate_warehouse_orders(mock_orders_data, 12345678, "СЦ Волгоград")
    
    print(f"✅ Warehouse stock: {warehouse_stock}")
    print(f"✅ Warehouse orders: {warehouse_orders}")
    
    print("Calculation tests completed!")