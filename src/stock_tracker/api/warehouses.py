"""
Warehouse data processing logic for Wildberries API integration.

Handles warehouse-specific data processing, synchronization, and formatting
for multi-warehouse inventory management according to User Story 2.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio

from stock_tracker.core.models import Product, Warehouse
from stock_tracker.core.calculator import is_real_warehouse, validate_warehouse_name
from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.exceptions import APIError, ValidationError, CalculationError


logger = get_logger(__name__)


class WarehouseDataProcessor:
    """
    Processes warehouse data from Wildberries API for multi-warehouse inventory.
    
    Handles the synchronization and formatting of warehouse-specific data
    ensuring proper ordering and consistency across columns F, G, H.
    """
    
    def __init__(self):
        """Initialize warehouse data processor."""
        logger.debug("WarehouseDataProcessor initialized")
    
    def process_warehouse_remains(self, remains_data: List[Dict[str, Any]], 
                                seller_article: str) -> List[Warehouse]:
        """
        Process warehouse remains data for a specific product.
        
        Args:
            remains_data: Raw warehouse remains from API
            seller_article: Product seller article to filter
            
        Returns:
            List of Warehouse objects with stock data
            
        Raises:
            ValidationError: If data structure is invalid
            DataProcessingError: If processing fails
        """
        try:
            logger.debug(f"Processing warehouse remains for {seller_article}")
            
            if not isinstance(remains_data, list):
                raise ValidationError("remains_data must be a list")
            
            # Group data by warehouse
            warehouse_data = {}
            
            for item in remains_data:
                try:
                    # Validate item structure
                    if not isinstance(item, dict):
                        continue
                    
                    item_article = item.get("supplierArticle", "")
                    if item_article != seller_article:
                        continue
                    
                    warehouse_name = item.get("warehouseName", "").strip()
                    quantity = item.get("quantity", 0)
                    
                    # ДОБАВИТЬ ФИЛЬТРАЦИЮ:
                    if not warehouse_name:
                        logger.warning(f"Empty warehouse name for {seller_article}")
                        continue
                    
                    if not is_real_warehouse(warehouse_name):
                        logger.debug(f"Filtered out delivery status in warehouse processor: {warehouse_name}")
                        continue
                        
                    if not validate_warehouse_name(warehouse_name):
                        logger.warning(f"Invalid warehouse name format in processor: {warehouse_name}")
                        continue
                    
                    try:
                        quantity = int(quantity) if quantity is not None else 0
                        if quantity < 0:
                            logger.warning(f"Negative quantity {quantity} for {warehouse_name}")
                            quantity = 0
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid quantity for {warehouse_name}: {quantity}")
                        quantity = 0
                    
                    # Aggregate by warehouse
                    if warehouse_name not in warehouse_data:
                        warehouse_data[warehouse_name] = {
                            "name": warehouse_name,
                            "stock": 0,
                            "orders": 0  # Will be filled by process_warehouse_orders
                        }
                    
                    warehouse_data[warehouse_name]["stock"] += quantity
                    
                except Exception as e:
                    logger.warning(f"Failed to process remains item: {e}")
                    continue
            
            # Create Warehouse objects
            warehouses = []
            for wh_data in warehouse_data.values():
                warehouse = Warehouse(
                    name=wh_data["name"],
                    stock=wh_data["stock"],
                    orders=wh_data["orders"]
                )
                warehouses.append(warehouse)
            
            # Sort warehouses by name for consistent ordering
            warehouses.sort(key=lambda w: w.name)
            
            logger.info(f"Processed {len(warehouses)} warehouses for {seller_article}")
            return warehouses
            
        except Exception as e:
            logger.error(f"Failed to process warehouse remains: {e}")
            raise CalculationError(f"Warehouse remains processing failed: {e}")
    
    def process_warehouse_orders(self, orders_data: List[Dict[str, Any]], 
                               seller_article: str, 
                               existing_warehouses: List[Warehouse]) -> List[Warehouse]:
        """
        Process warehouse orders data and merge with existing warehouse data.
        
        Args:
            orders_data: Raw orders data from API
            seller_article: Product seller article to filter
            existing_warehouses: Existing warehouses to update
            
        Returns:
            Updated list of Warehouse objects with orders data
            
        Raises:
            ValidationError: If data structure is invalid
            DataProcessingError: If processing fails
        """
        try:
            logger.debug(f"Processing warehouse orders for {seller_article}")
            
            if not isinstance(orders_data, list):
                raise ValidationError("orders_data must be a list")
            
            # Create warehouse lookup for existing warehouses
            warehouse_lookup = {wh.name: wh for wh in existing_warehouses}
            
            # Count orders by warehouse
            warehouse_orders = {}
            
            for item in orders_data:
                try:
                    # Validate item structure
                    if not isinstance(item, dict):
                        continue
                    
                    item_article = item.get("supplierArticle", "")
                    if item_article != seller_article:
                        continue
                    
                    warehouse_name = item.get("warehouseName", "").strip()
                    
                    if not warehouse_name:
                        continue
                    
                    # ДОБАВИТЬ ФИЛЬТРАЦИЮ для заказов:
                    if not is_real_warehouse(warehouse_name):
                        logger.debug(f"Filtered out delivery status in orders processor: {warehouse_name}")
                        continue
                        
                    if not validate_warehouse_name(warehouse_name):
                        logger.warning(f"Invalid warehouse name format in orders processor: {warehouse_name}")
                        continue
                    
                    # Count orders
                    if warehouse_name not in warehouse_orders:
                        warehouse_orders[warehouse_name] = 0
                    warehouse_orders[warehouse_name] += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to process orders item: {e}")
                    continue
            
            # Update existing warehouses with orders data
            updated_warehouses = []
            
            for warehouse in existing_warehouses:
                orders_count = warehouse_orders.get(warehouse.name, 0)
                
                # Create updated warehouse
                updated_warehouse = Warehouse(
                    name=warehouse.name,
                    stock=warehouse.stock,
                    orders=orders_count
                )
                updated_warehouses.append(updated_warehouse)
            
            # Add warehouses that have orders but no stock
            for warehouse_name, orders_count in warehouse_orders.items():
                if warehouse_name not in warehouse_lookup:
                    new_warehouse = Warehouse(
                        name=warehouse_name,
                        stock=0,
                        orders=orders_count
                    )
                    updated_warehouses.append(new_warehouse)
            
            # Sort warehouses by name for consistent ordering
            updated_warehouses.sort(key=lambda w: w.name)
            
            logger.info(f"Updated {len(updated_warehouses)} warehouses with orders for {seller_article}")
            return updated_warehouses
            
        except Exception as e:
            logger.error(f"Failed to process warehouse orders: {e}")
            raise CalculationError(f"Warehouse orders processing failed: {e}")
    
    def merge_warehouse_data(self, remains_warehouses: List[Warehouse], 
                           orders_warehouses: List[Warehouse]) -> List[Warehouse]:
        """
        Merge warehouse data from remains and orders API calls.
        
        Args:
            remains_warehouses: Warehouses with stock data
            orders_warehouses: Warehouses with orders data
            
        Returns:
            Merged list of warehouses with complete data
        """
        try:
            logger.debug("Merging warehouse data from remains and orders")
            
            # Create lookup for efficient merging
            remains_lookup = {wh.name: wh for wh in remains_warehouses}
            orders_lookup = {wh.name: wh for wh in orders_warehouses}
            
            # Get all unique warehouse names
            all_warehouse_names = set(remains_lookup.keys()) | set(orders_lookup.keys())
            
            # Create merged warehouses
            merged_warehouses = []
            for warehouse_name in sorted(all_warehouse_names):
                stock = remains_lookup.get(warehouse_name, Warehouse(warehouse_name, 0, 0)).stock
                orders = orders_lookup.get(warehouse_name, Warehouse(warehouse_name, 0, 0)).orders
                
                merged_warehouse = Warehouse(
                    name=warehouse_name,
                    stock=stock,
                    orders=orders
                )
                merged_warehouses.append(merged_warehouse)
            
            logger.info(f"Merged data for {len(merged_warehouses)} warehouses")
            return merged_warehouses
            
        except Exception as e:
            logger.error(f"Failed to merge warehouse data: {e}")
            raise CalculationError(f"Warehouse data merging failed: {e}")
    
    def synchronize_warehouse_order(self, warehouses: List[Warehouse], 
                                  reference_order: List[str]) -> List[Warehouse]:
        """
        Synchronize warehouse order to match a reference order.
        
        This ensures consistent ordering across columns F, G, H in Google Sheets.
        
        Args:
            warehouses: List of warehouses to reorder
            reference_order: Desired order of warehouse names
            
        Returns:
            Reordered list of warehouses
        """
        try:
            logger.debug(f"Synchronizing warehouse order for {len(warehouses)} warehouses")
            
            # Create lookup for existing warehouses
            warehouse_lookup = {wh.name: wh for wh in warehouses}
            
            # Reorder according to reference
            synchronized_warehouses = []
            
            # First, add warehouses in reference order
            for warehouse_name in reference_order:
                if warehouse_name in warehouse_lookup:
                    synchronized_warehouses.append(warehouse_lookup[warehouse_name])
            
            # Add any remaining warehouses not in reference (at the end)
            for warehouse in warehouses:
                if warehouse.name not in reference_order:
                    synchronized_warehouses.append(warehouse)
            
            logger.debug(f"Synchronized {len(synchronized_warehouses)} warehouses")
            return synchronized_warehouses
            
        except Exception as e:
            logger.error(f"Failed to synchronize warehouse order: {e}")
            return warehouses  # Return original order on error
    
    def validate_warehouse_data_consistency(self, warehouses: List[Warehouse]) -> Dict[str, Any]:
        """
        Validate consistency of warehouse data.
        
        Args:
            warehouses: List of warehouses to validate
            
        Returns:
            Dict with validation results
        """
        try:
            validation = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "warehouse_count": len(warehouses)
            }
            
            if not warehouses:
                validation["warnings"].append("No warehouses found")
                return validation
            
            # Check for duplicate warehouse names
            warehouse_names = [wh.name for wh in warehouses]
            if len(warehouse_names) != len(set(warehouse_names)):
                validation["valid"] = False
                validation["errors"].append("Duplicate warehouse names found")
            
            # Check for empty warehouse names
            empty_names = [wh.name for wh in warehouses if not wh.name.strip()]
            if empty_names:
                validation["valid"] = False
                validation["errors"].append(f"Empty warehouse names: {len(empty_names)}")
            
            # Check for negative values
            negative_stock = [wh.name for wh in warehouses if wh.stock < 0]
            if negative_stock:
                validation["warnings"].append(f"Negative stock values: {negative_stock}")
            
            negative_orders = [wh.name for wh in warehouses if wh.orders < 0]
            if negative_orders:
                validation["warnings"].append(f"Negative orders values: {negative_orders}")
            
            # Check data ranges (reasonable limits)
            high_stock = [wh.name for wh in warehouses if wh.stock > 10000]
            if high_stock:
                validation["warnings"].append(f"Very high stock values: {high_stock}")
            
            high_orders = [wh.name for wh in warehouses if wh.orders > 1000]
            if high_orders:
                validation["warnings"].append(f"Very high orders values: {high_orders}")
            
            logger.debug(f"Validated {len(warehouses)} warehouses: {validation['valid']}")
            return validation
            
        except Exception as e:
            logger.error(f"Failed to validate warehouse data: {e}")
            return {
                "valid": False,
                "errors": [f"Validation failed: {e}"],
                "warnings": [],
                "warehouse_count": 0
            }
    
    def extract_warehouse_names_order(self, formatted_cell: str) -> List[str]:
        """
        Extract warehouse names from a formatted multi-line cell.
        
        Used to determine the existing order in Google Sheets.
        
        Args:
            formatted_cell: Multi-line cell content with warehouse names
            
        Returns:
            List of warehouse names in order
        """
        try:
            if not formatted_cell:
                return []
            
            # Split by newlines and clean up
            names = []
            for line in formatted_cell.split('\n'):
                cleaned_name = line.strip()
                if cleaned_name:
                    names.append(cleaned_name)
            
            logger.debug(f"Extracted {len(names)} warehouse names from cell")
            return names
            
        except Exception as e:
            logger.warning(f"Failed to extract warehouse names: {e}")
            return []
    
    def create_warehouse_summary(self, warehouses: List[Warehouse]) -> Dict[str, Any]:
        """
        Create a summary of warehouse data for reporting.
        
        Args:
            warehouses: List of warehouses to summarize
            
        Returns:
            Dict with warehouse summary statistics
        """
        try:
            if not warehouses:
                return {
                    "total_warehouses": 0,
                    "total_stock": 0,
                    "total_orders": 0,
                    "avg_stock_per_warehouse": 0,
                    "avg_orders_per_warehouse": 0,
                    "top_warehouse_by_stock": None,
                    "top_warehouse_by_orders": None
                }
            
            total_stock = sum(wh.stock for wh in warehouses)
            total_orders = sum(wh.orders for wh in warehouses)
            
            # Find top performers
            top_stock_warehouse = max(warehouses, key=lambda wh: wh.stock)
            top_orders_warehouse = max(warehouses, key=lambda wh: wh.orders)
            
            summary = {
                "total_warehouses": len(warehouses),
                "total_stock": total_stock,
                "total_orders": total_orders,
                "avg_stock_per_warehouse": round(total_stock / len(warehouses), 2),
                "avg_orders_per_warehouse": round(total_orders / len(warehouses), 2),
                "top_warehouse_by_stock": {
                    "name": top_stock_warehouse.name,
                    "stock": top_stock_warehouse.stock
                },
                "top_warehouse_by_orders": {
                    "name": top_orders_warehouse.name,
                    "orders": top_orders_warehouse.orders
                },
                "warehouses": [
                    {
                        "name": wh.name,
                        "stock": wh.stock,
                        "orders": wh.orders,
                        "stock_percentage": round((wh.stock / total_stock * 100) if total_stock > 0 else 0, 2),
                        "orders_percentage": round((wh.orders / total_orders * 100) if total_orders > 0 else 0, 2)
                    }
                    for wh in warehouses
                ]
            }
            
            logger.debug(f"Created summary for {len(warehouses)} warehouses")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to create warehouse summary: {e}")
            return {"error": str(e)}


class WarehouseSynchronizer:
    """
    Handles synchronization of warehouse data ordering across Google Sheets columns.
    
    Ensures that warehouse names (column F), orders (column G), and stock (column H)
    maintain consistent ordering as required by User Story 2.
    """
    
    def __init__(self):
        """Initialize warehouse synchronizer."""
        self.processor = WarehouseDataProcessor()
        logger.debug("WarehouseSynchronizer initialized")
    
    def synchronize_product_warehouses(self, product: Product, 
                                     existing_order: Optional[List[str]] = None) -> Product:
        """
        Synchronize warehouse ordering for a product.
        
        Args:
            product: Product with warehouses to synchronize
            existing_order: Existing warehouse order to maintain (optional)
            
        Returns:
            Product with synchronized warehouse ordering
        """
        try:
            logger.debug(f"Synchronizing warehouses for product {product.seller_article}")
            
            if not product.warehouses:
                logger.debug("No warehouses to synchronize")
                return product
            
            # Use existing order if provided, otherwise sort alphabetically
            if existing_order:
                synchronized_warehouses = self.processor.synchronize_warehouse_order(
                    product.warehouses, existing_order
                )
            else:
                # Default alphabetical ordering
                synchronized_warehouses = sorted(product.warehouses, key=lambda w: w.name)
            
            # Replace warehouses in product
            product.warehouses.clear()
            for warehouse in synchronized_warehouses:
                product.add_warehouse(warehouse)
            
            logger.debug(f"Synchronized {len(synchronized_warehouses)} warehouses")
            return product
            
        except Exception as e:
            logger.error(f"Failed to synchronize product warehouses: {e}")
            return product  # Return original product on error
    
    def get_consistent_warehouse_order(self, products: List[Product]) -> List[str]:
        """
        Determine a consistent warehouse order across multiple products.
        
        Args:
            products: List of products to analyze
            
        Returns:
            List of warehouse names in consistent order
        """
        try:
            logger.debug(f"Determining consistent order for {len(products)} products")
            
            # Count frequency of each warehouse across all products
            warehouse_frequency = {}
            
            for product in products:
                for warehouse in product.warehouses:
                    if warehouse.name not in warehouse_frequency:
                        warehouse_frequency[warehouse.name] = 0
                    warehouse_frequency[warehouse.name] += 1
            
            # Sort by frequency (most common first), then alphabetically
            sorted_warehouses = sorted(
                warehouse_frequency.keys(),
                key=lambda name: (-warehouse_frequency[name], name)
            )
            
            logger.info(f"Determined consistent order for {len(sorted_warehouses)} warehouses")
            return sorted_warehouses
            
        except Exception as e:
            logger.error(f"Failed to determine consistent warehouse order: {e}")
            return []


# Utility functions for warehouse processing

def format_warehouse_data_for_sheets(warehouses: List[Warehouse]) -> Tuple[str, str, str]:
    """
    Format warehouse data for Google Sheets columns F, G, H.
    
    Args:
        warehouses: List of warehouses to format
        
    Returns:
        Tuple of (names, orders, stock) as multi-line strings
    """
    if not warehouses:
        return "", "", ""
    
    names = "\n".join(wh.name for wh in warehouses)
    orders = "\n".join(str(wh.orders) for wh in warehouses)
    stock = "\n".join(str(wh.stock) for wh in warehouses)
    
    return names, orders, stock


def parse_warehouse_data_from_sheets(names_cell: str, orders_cell: str, 
                                   stock_cell: str) -> List[Warehouse]:
    """
    Parse warehouse data from Google Sheets multi-line cells.
    
    Args:
        names_cell: Multi-line cell with warehouse names
        orders_cell: Multi-line cell with orders data
        stock_cell: Multi-line cell with stock data
        
    Returns:
        List of Warehouse objects
    """
    try:
        names = names_cell.split('\n') if names_cell else []
        orders = orders_cell.split('\n') if orders_cell else []
        stock = stock_cell.split('\n') if stock_cell else []
        
        # Ensure all lists have same length
        max_length = max(len(names), len(orders), len(stock))
        names.extend([''] * (max_length - len(names)))
        orders.extend(['0'] * (max_length - len(orders)))
        stock.extend(['0'] * (max_length - len(stock)))
        
        warehouses = []
        for i in range(max_length):
            name = names[i].strip()
            if name:  # Only create warehouse if it has a name
                try:
                    orders_val = int(orders[i]) if orders[i].isdigit() else 0
                    stock_val = int(stock[i]) if stock[i].isdigit() else 0
                except (ValueError, IndexError):
                    orders_val = 0
                    stock_val = 0
                
                warehouse = Warehouse(name=name, orders=orders_val, stock=stock_val)
                warehouses.append(warehouse)
        
        return warehouses
        
    except Exception as e:
        logger.warning(f"Failed to parse warehouse data from sheets: {e}")
        return []


if __name__ == "__main__":
    # Test warehouse processing functionality
    print("Testing warehouse data processing...")
    
    from stock_tracker.core.models import Warehouse
    
    # Test data processor
    processor = WarehouseDataProcessor()
    
    # Test warehouse data
    test_remains = [
        {"supplierArticle": "WB001", "warehouseName": "СЦ Волгоград", "quantity": 654},
        {"supplierArticle": "WB001", "warehouseName": "СЦ Москва", "quantity": 453},
        {"supplierArticle": "OTHER", "warehouseName": "СЦ Другой", "quantity": 100}
    ]
    
    test_orders = [
        {"supplierArticle": "WB001", "warehouseName": "СЦ Волгоград"},
        {"supplierArticle": "WB001", "warehouseName": "СЦ Волгоград"},
        {"supplierArticle": "WB001", "warehouseName": "СЦ Москва"}
    ]
    
    try:
        # Test remains processing
        remains_warehouses = processor.process_warehouse_remains(test_remains, "WB001")
        print(f"✅ Processed {len(remains_warehouses)} warehouses from remains")
        
        # Test orders processing
        orders_warehouses = processor.process_warehouse_orders(test_orders, "WB001", remains_warehouses)
        print(f"✅ Updated {len(orders_warehouses)} warehouses with orders")
        
        # Test synchronization
        synchronizer = WarehouseSynchronizer()
        test_order = ["СЦ Москва", "СЦ Волгоград"]
        
        # Create test product
        from stock_tracker.core.models import Product
        product = Product("WB001", 12345678)
        for wh in orders_warehouses:
            product.add_warehouse(wh)
        
        sync_product = synchronizer.synchronize_product_warehouses(product, test_order)
        print(f"✅ Synchronized warehouses: {[wh.name for wh in sync_product.warehouses]}")
        
        # Test formatting
        names, orders, stock = format_warehouse_data_for_sheets(sync_product.warehouses)
        print(f"✅ Formatted for sheets:")
        print(f"   Names: {repr(names)}")
        print(f"   Orders: {repr(orders)}")
        print(f"   Stock: {repr(stock)}")
        
        # Test validation
        validation = processor.validate_warehouse_data_consistency(sync_product.warehouses)
        print(f"✅ Validation: {validation['valid']}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    print("Warehouse processing tests completed!")