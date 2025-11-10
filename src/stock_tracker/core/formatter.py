"""
Data formatting utilities for Google Sheets display.

Provides functions to format Product data for proper display in Google Sheets,
including multi-line warehouse data and proper number formatting.
Supports multi-warehouse data handling as specified in User Story 2.
"""

from typing import List, Any, Dict, Optional, Tuple
from datetime import datetime

from stock_tracker.core.models import Product, Warehouse
from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.exceptions import ValidationError


logger = get_logger(__name__)


class ProductDataFormatter:
    """
    Formats product data for Google Sheets display.
    
    Handles the conversion from Product objects to the specific format
    required for Google Sheets, including multi-line warehouse data
    and proper number formatting. Enhanced for User Story 2 with
    advanced multi-warehouse support.
    """
    
    @staticmethod
    def format_product_for_sheets(product: Product) -> List[Any]:
        """
        Format a single product for Google Sheets row.
        
        Converts Product object to list format matching the table structure:
        [seller_article, wildberries_article, total_orders, total_stock, 
         turnover, warehouse_names, warehouse_orders, warehouse_stock]
        
        Enhanced for User Story 2 with synchronized multi-warehouse data.
        
        Args:
            product: Product instance to format
            
        Returns:
            List of values for Google Sheets row
            
        Raises:
            ValidationError: If product data is invalid
        """
        try:
            # Validate product
            if not isinstance(product, Product):
                raise ValidationError(
                    "Invalid product type",
                    field="product",
                    value=type(product).__name__,
                    expected_type="Product"
                )
            
            # Format multi-warehouse data with synchronized ordering
            warehouse_names, warehouse_orders, warehouse_stock, warehouse_turnover = ProductDataFormatter._format_synchronized_warehouse_data(
                product.warehouses
            )
            
            # Basic product data
            row_data = [
                product.seller_article,           # Column A: Артикул продавца
                product.wildberries_article,      # Column B: Артикул товара
                product.total_orders,             # Column C: Заказы (всего)
                product.total_stock,              # Column D: Остатки (всего)
                int(product.turnover),            # Column E: Оборачиваемость (целое число)
                warehouse_names,                  # Column F: Название склада (multi-line)
                warehouse_orders,                 # Column G: Заказы со склада (multi-line)
                warehouse_stock,                  # Column H: Остатки на складе (multi-line)
                warehouse_turnover                # Column I: Оборачиваемость по складам (multi-line)
            ]
            
            logger.debug(f"Formatted product {product.seller_article} for sheets with {len(product.warehouses)} warehouses")
            return row_data
            
        except Exception as e:
            logger.error(f"Failed to format product for sheets: {e}")
            raise ValidationError(f"Product formatting failed: {e}")
    
    @staticmethod
    def _format_synchronized_warehouse_data(warehouses: List[Warehouse]) -> Tuple[str, str, str, str]:
        """
        Format warehouse data with synchronized ordering for columns F, G, H, I.
        
        This ensures that warehouse names, orders, stock and turnover data are properly
        aligned in their respective columns using newline separation.
        
        УЛУЧШЕНО 30.10.2025: Добавлено визуальное разделение между складами
        для улучшения читаемости в Google Sheets.
        
        ДОБАВЛЕНО 10.11.2025: Добавлена колонка оборачиваемости по складам.
        
        Args:
            warehouses: List of Warehouse objects in desired order
            
        Returns:
            Tuple of (names, orders, stock, turnover) as multi-line strings
        """
        if not warehouses:
            return "", "", "", ""
        
        try:
            # Extract data in synchronized order
            names = []
            orders = []
            stock = []
            turnover = []
            
            for warehouse in warehouses:
                names.append(str(warehouse.name))
                orders.append(str(warehouse.orders))
                stock.append(str(warehouse.stock))
                # Format turnover as integer
                turnover.append(str(warehouse.turnover))
            
            # УЛУЧШЕНО: Join с двойным переносом строки для визуального разделения
            # Это создаёт пустую строку между складами в Google Sheets
            names_str = "\n\n".join(names)
            orders_str = "\n\n".join(orders)
            stock_str = "\n\n".join(stock)
            turnover_str = "\n\n".join(turnover)
            
            logger.debug(f"Formatted {len(warehouses)} warehouses with synchronized data and visual separation")
            return names_str, orders_str, stock_str, turnover_str
            
        except Exception as e:
            logger.error(f"Failed to format synchronized warehouse data: {e}")
            return "", "", "", ""
    
    @staticmethod
    def format_products_batch(products: List[Product]) -> List[List[Any]]:
        """
        Format multiple products for batch Google Sheets update.
        
        Enhanced for User Story 2 with consistent warehouse ordering
        across all products in the batch.
        
        Args:
            products: List of Product instances
            
        Returns:
            List of rows for Google Sheets batch update
        """
        try:
            formatted_rows = []
            
            for i, product in enumerate(products):
                try:
                    row_data = ProductDataFormatter.format_product_for_sheets(product)
                    formatted_rows.append(row_data)
                except Exception as e:
                    logger.warning(f"Failed to format product {i}: {e}")
                    continue
            
            logger.info(f"Formatted {len(formatted_rows)} products for batch update")
            return formatted_rows
            
        except Exception as e:
            logger.error(f"Failed to format products batch: {e}")
            raise ValidationError(f"Batch formatting failed: {e}")
    
    @staticmethod
    def format_warehouse_data_multiline(warehouses: List[Warehouse], 
                                      field: str) -> str:
        """
        Format warehouse data as multi-line string for Google Sheets.
        
        Enhanced for User Story 2 with better error handling and
        consistent ordering support.
        
        Args:
            warehouses: List of Warehouse objects
            field: Field to extract ('name', 'orders', 'stock')
            
        Returns:
            Multi-line string with warehouse data
        """
        if not warehouses:
            return ""
        
        try:
            values = []
            for warehouse in warehouses:
                if field == "name":
                    values.append(str(warehouse.name))
                elif field == "orders":
                    values.append(str(warehouse.orders))
                elif field == "stock":
                    values.append(str(warehouse.stock))
                else:
                    raise ValidationError(f"Invalid field: {field}")
            
            # Join with newlines for multi-line cell display
            result = "\n".join(values)
            logger.debug(f"Formatted {len(values)} warehouse {field} values")
            return result
            
        except Exception as e:
            logger.error(f"Failed to format warehouse {field} data: {e}")
            return ""
    
    @staticmethod
    def format_warehouse_cell_with_wrapping(warehouses: List[Warehouse], 
                                          field: str, 
                                          max_line_length: int = 30) -> str:
        """
        Format warehouse data with text wrapping for better display.
        
        New method for User Story 2 to handle long warehouse names
        and improve readability in Google Sheets cells.
        
        Args:
            warehouses: List of Warehouse objects
            field: Field to extract ('name', 'orders', 'stock')
            max_line_length: Maximum characters per line before wrapping
            
        Returns:
            Multi-line string with text wrapping applied
        """
        if not warehouses:
            return ""
        
        try:
            formatted_lines = []
            
            for warehouse in warehouses:
                if field == "name":
                    value = str(warehouse.name)
                    # Wrap long warehouse names
                    if len(value) > max_line_length:
                        # Simple word wrapping
                        words = value.split()
                        wrapped_lines = []
                        current_line = ""
                        
                        for word in words:
                            if len(current_line + " " + word) <= max_line_length:
                                current_line = (current_line + " " + word).strip()
                            else:
                                if current_line:
                                    wrapped_lines.append(current_line)
                                current_line = word
                        
                        if current_line:
                            wrapped_lines.append(current_line)
                        
                        formatted_lines.extend(wrapped_lines)
                    else:
                        formatted_lines.append(value)
                elif field == "orders":
                    formatted_lines.append(str(warehouse.orders))
                elif field == "stock":
                    formatted_lines.append(str(warehouse.stock))
                else:
                    raise ValidationError(f"Invalid field: {field}")
            
            result = "\n".join(formatted_lines)
            logger.debug(f"Formatted {len(warehouses)} warehouse {field} values with wrapping")
            return result
            
        except Exception as e:
            logger.error(f"Failed to format warehouse {field} data with wrapping: {e}")
            return ProductDataFormatter.format_warehouse_data_multiline(warehouses, field)
    
    @staticmethod
    def format_turnover(turnover: float) -> str:
        """
        Format turnover value for display as whole number.
        
        Args:
            turnover: Turnover ratio
            
        Returns:
            Formatted turnover string as whole number
        """
        try:
            # Convert to integer to get whole number only
            return str(int(turnover))
        except Exception:
            return "0"
    
    @staticmethod
    def parse_product_from_sheets_row(row_data: List[Any], 
                                    row_number: int) -> Optional[Product]:
        """
        Parse Product from Google Sheets row data.
        
        Enhanced for User Story 2 with improved multi-warehouse parsing
        and better error handling for synchronized data.
        
        Args:
            row_data: List of cell values from Google Sheets
            row_number: Row number for error reporting
            
        Returns:
            Product instance or None if parsing fails
        """
        try:
            # Ensure we have enough columns (updated to 10 columns with FBO/FBS)
            min_columns = 10
            if len(row_data) < min_columns:
                logger.warning(f"Row {row_number}: insufficient columns ({len(row_data)}) - will pad with empty values")
                # Pad with empty values to reach min_columns for compatibility
                while len(row_data) < min_columns:
                    row_data.append("")
            
            # Extract basic product data
            seller_article = str(row_data[0]).strip() if row_data[0] else ""
            
            try:
                wildberries_article = int(row_data[1]) if row_data[1] else 0
            except (ValueError, TypeError):
                logger.warning(f"Row {row_number}: invalid wildberries_article")
                return None
            
            if not seller_article or wildberries_article <= 0:
                logger.warning(f"Row {row_number}: missing required product data")
                return None
            
            # Create product
            product = Product(
                seller_article=seller_article,
                wildberries_article=wildberries_article
            )
            
            # Parse totals if available
            try:
                product.total_orders = int(row_data[2]) if row_data[2] else 0
                product.total_stock = int(row_data[3]) if row_data[3] else 0
                # Parse turnover as integer since we store it as whole number
                product.turnover = float(int(row_data[4])) if row_data[4] else 0.0
            except (ValueError, TypeError):
                logger.debug(f"Row {row_number}: could not parse totals, will recalculate")
            
            # Parse warehouse data with synchronized ordering
            try:
                warehouse_turnover = row_data[8] if len(row_data) > 8 else ""
                warehouses = ProductDataFormatter._parse_synchronized_warehouse_data(
                    row_data[5],  # warehouse names
                    row_data[6],  # warehouse orders
                    row_data[7],  # warehouse stock
                    warehouse_turnover  # warehouse turnover
                )
                
                # Add warehouses to product
                for warehouse in warehouses:
                    product.add_warehouse(warehouse)
                        
            except Exception as e:
                logger.debug(f"Row {row_number}: could not parse warehouse data: {e}")
            
            logger.debug(f"Parsed product {seller_article} from row {row_number} with {len(product.warehouses)} warehouses")
            return product
            
        except Exception as e:
            logger.warning(f"Failed to parse product from row {row_number}: {e}")
            return None
    
    @staticmethod
    def _parse_synchronized_warehouse_data(names_cell: str, orders_cell: str, 
                                         stock_cell: str, turnover_cell: str = "") -> List[Warehouse]:
        """
        Parse synchronized warehouse data from multi-line Google Sheets cells.
        
        New method for User Story 2 to properly handle the synchronized
        data structure across columns F, G, H, I.
        
        ДОБАВЛЕНО 10.11.2025: Добавлена поддержка парсинга оборачиваемости по складам.
        
        Args:
            names_cell: Multi-line cell with warehouse names
            orders_cell: Multi-line cell with orders data
            stock_cell: Multi-line cell with stock data
            turnover_cell: Multi-line cell with turnover data
            
        Returns:
            List of Warehouse objects with synchronized data
        """
        try:
            # Split multi-line cells
            names = str(names_cell).split('\n') if names_cell else []
            orders = str(orders_cell).split('\n') if orders_cell else []
            stock = str(stock_cell).split('\n') if stock_cell else []
            turnover = str(turnover_cell).split('\n') if turnover_cell else []
            
            # Clean up entries
            names = [name.strip() for name in names if name.strip()]
            orders = [order.strip() for order in orders if order.strip()]
            stock = [stock_val.strip() for stock_val in stock if stock_val.strip()]
            turnover = [turn.strip() for turn in turnover if turn.strip()]
            
            # Create synchronized warehouse list
            warehouses = []
            max_length = max(len(names), len(orders), len(stock), len(turnover)) if (names or orders or stock or turnover) else 0
            
            for i in range(max_length):
                # Get values with safe indexing
                name = names[i] if i < len(names) else ""
                orders_val = orders[i] if i < len(orders) else "0"
                stock_val = stock[i] if i < len(stock) else "0"
                turnover_val = turnover[i] if i < len(turnover) else "0"
                
                # Only create warehouse if it has a name
                if name:
                    try:
                        orders_int = int(orders_val) if orders_val.isdigit() else 0
                        stock_int = int(stock_val) if stock_val.isdigit() else 0
                        
                        # Parse turnover as integer
                        try:
                            turnover_int = int(turnover_val) if turnover_val else 0
                        except ValueError:
                            turnover_int = 0
                        
                        # Ensure non-negative values
                        orders_int = max(0, orders_int)
                        stock_int = max(0, stock_int)
                        turnover_int = max(0, turnover_int)
                        
                        warehouse = Warehouse(
                            name=name,
                            orders=orders_int,
                            stock=stock_int,
                            turnover=turnover_int
                        )
                        warehouses.append(warehouse)
                        
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to parse warehouse data for {name}: {e}")
                        continue
            
            logger.debug(f"Parsed {len(warehouses)} synchronized warehouses")
            return warehouses
            
        except Exception as e:
            logger.error(f"Failed to parse synchronized warehouse data: {e}")
            return []
    
    @staticmethod
    def validate_synchronized_data_integrity(names: str, orders: str, stock: str) -> Dict[str, Any]:
        """
        Validate integrity of synchronized warehouse data across columns F, G, H.
        
        New method for User Story 2 to ensure data consistency
        across the three warehouse columns.
        
        Args:
            names: Multi-line names data (column F)
            orders: Multi-line orders data (column G)  
            stock: Multi-line stock data (column H)
            
        Returns:
            Dict with validation results
        """
        try:
            validation = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "line_counts": {}
            }
            
            # Split and count lines
            names_lines = names.split('\n') if names else []
            orders_lines = orders.split('\n') if orders else []
            stock_lines = stock.split('\n') if stock else []
            
            # Clean empty lines
            names_lines = [line.strip() for line in names_lines if line.strip()]
            orders_lines = [line.strip() for line in orders_lines if line.strip()]
            stock_lines = [line.strip() for line in stock_lines if line.strip()]
            
            validation["line_counts"] = {
                "names": len(names_lines),
                "orders": len(orders_lines),
                "stock": len(stock_lines)
            }
            
            # Check line count consistency
            line_counts = [len(names_lines), len(orders_lines), len(stock_lines)]
            if len(set(line_counts)) > 1:
                validation["warnings"].append(
                    f"Inconsistent line counts: names={len(names_lines)}, "
                    f"orders={len(orders_lines)}, stock={len(stock_lines)}"
                )
            
            # Validate orders and stock are numeric
            for i, orders_val in enumerate(orders_lines):
                if not orders_val.isdigit():
                    validation["errors"].append(f"Non-numeric orders value at line {i+1}: {orders_val}")
                    validation["valid"] = False
            
            for i, stock_val in enumerate(stock_lines):
                if not stock_val.isdigit():
                    validation["errors"].append(f"Non-numeric stock value at line {i+1}: {stock_val}")
                    validation["valid"] = False
            
            # Check for empty warehouse names
            for i, name in enumerate(names_lines):
                if not name.strip():
                    validation["errors"].append(f"Empty warehouse name at line {i+1}")
                    validation["valid"] = False
            
            return validation
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation failed: {e}"],
                "warnings": [],
                "line_counts": {}
            }
    
    @staticmethod
    def create_empty_row() -> List[Any]:
        """
        Create an empty row with correct structure.
        
        Returns:
            List with empty values for each column
        """
        return ["", "", 0, 0, 0.0, "", "", "", ""]  # Updated to 9 columns (added warehouse turnover)
    
    @staticmethod
    def validate_row_data(row_data: List[Any]) -> Dict[str, Any]:
        """
        Validate row data structure and content.
        
        Args:
            row_data: List of cell values
            
        Returns:
            Dict with validation results
        """
        try:
            if len(row_data) < 9:
                return {
                    "valid": False,
                    "error": f"Insufficient columns: expected 9, got {len(row_data)}"
                }
            
            # Check required fields
            seller_article = str(row_data[0]).strip() if row_data[0] else ""
            if not seller_article:
                return {
                    "valid": False,
                    "error": "Missing seller article (column A)"
                }
            
            try:
                wildberries_article = int(row_data[1]) if row_data[1] else 0
                if wildberries_article <= 0:
                    return {
                        "valid": False,
                        "error": "Invalid wildberries article (column B): must be positive integer"
                    }
            except (ValueError, TypeError):
                return {
                    "valid": False,
                    "error": "Invalid wildberries article (column B): must be integer"
                }
            
            # Validate numeric fields
            for i, field_name in enumerate(["total_orders", "total_stock", "turnover"], start=2):
                try:
                    value = float(row_data[i]) if row_data[i] else 0
                    if value < 0:
                        return {
                            "valid": False,
                            "error": f"Negative value in {field_name} (column {chr(ord('A') + i)})"
                        }
                except (ValueError, TypeError):
                    return {
                        "valid": False,
                        "error": f"Invalid numeric value in {field_name} (column {chr(ord('A') + i)})"
                    }
            
            return {
                "valid": True,
                "seller_article": seller_article,
                "wildberries_article": wildberries_article
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation failed: {e}"
            }


def format_timestamp(timestamp: Optional[datetime] = None) -> str:
    """
    Format timestamp for display in sheets.
    
    Args:
        timestamp: Datetime to format (None for current time)
        
    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def sanitize_cell_value(value: Any) -> str:
    """
    Sanitize cell value for Google Sheets.
    
    Args:
        value: Value to sanitize
        
    Returns:
        Sanitized string value
    """
    if value is None:
        return ""
    
    # Convert to string and strip whitespace
    str_value = str(value).strip()
    
    # Remove any problematic characters that might break CSV/Sheets
    # Keep newlines for multi-line cells
    problematic_chars = ['\r', '\t']
    for char in problematic_chars:
        str_value = str_value.replace(char, ' ')
    
    return str_value


if __name__ == "__main__":
    # Test formatting functions
    print("Testing product data formatting...")
    
    from stock_tracker.core.models import Product, Warehouse
    
    # Create test product
    product = Product(seller_article="WB001", wildberries_article=12345678)
    
    # Add test warehouses
    warehouse1 = Warehouse(name="СЦ Волгоград", orders=32, stock=654)
    warehouse2 = Warehouse(name="СЦ Москва", orders=60, stock=453)
    
    product.add_warehouse(warehouse1)
    product.add_warehouse(warehouse2)
    
    # Test formatting
    formatter = ProductDataFormatter()
    row_data = formatter.format_product_for_sheets(product)
    
    print(f"✅ Formatted product: {row_data}")
    print(f"   Warehouse names: {repr(row_data[5])}")
    print(f"   Warehouse orders: {repr(row_data[6])}")
    print(f"   Warehouse stock: {repr(row_data[7])}")
    
    # Test parsing back
    parsed_product = formatter.parse_product_from_sheets_row(row_data, 2)
    if parsed_product:
        print(f"✅ Parsed back: {parsed_product.seller_article} with {len(parsed_product.warehouses)} warehouses")
    else:
        print("❌ Failed to parse product back")
    
    print("Formatting tests completed!")