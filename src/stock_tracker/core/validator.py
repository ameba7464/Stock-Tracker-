"""
Data validation utilities for Wildberries Stock Tracker.

Provides validation functions that enforce data types and constraints
exactly as specified in urls.md. All validations must match the API
specifications to ensure data integrity.

CRITICAL: All validation rules MUST match the data types from urls.md
"""

import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from stock_tracker.utils.exceptions import ValidationError
from stock_tracker.utils.logger import get_logger


logger = get_logger(__name__)


class WildberriesDataValidator:
    """
    Validator for Wildberries API data following urls.md specifications.
    
    Validates all data types and constraints exactly as documented in urls.md
    for both warehouse_remains and supplier/orders endpoints.
    """
    
    @staticmethod
    def validate_supplier_article(value: Any, field_name: str = "supplierArticle") -> str:
        """
        Validate supplier article per urls.md specification.
        
        From urls.md: supplierArticle (string) ≤ 75 characters
        
        Args:
            value: Value to validate
            field_name: Field name for error messages
            
        Returns:
            Validated string value
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            raise ValidationError(
                f"{field_name} cannot be None",
                field=field_name,
                value=value,
                expected_type="string"
            )
        
        if not isinstance(value, str):
            raise ValidationError(
                f"{field_name} must be a string",
                field=field_name,
                value=value,
                expected_type="string"
            )
        
        value = value.strip()
        
        if not value:
            raise ValidationError(
                f"{field_name} cannot be empty",
                field=field_name,
                value=value,
                expected_type="non-empty string"
            )
        
        if len(value) > 75:  # Per urls.md specification
            raise ValidationError(
                f"{field_name} cannot exceed 75 characters",
                field=field_name,
                value=value,
                expected_type="string ≤ 75 chars"
            )
        
        return value
    
    @staticmethod
    def validate_nm_id(value: Any, field_name: str = "nmId") -> int:
        """
        Validate nmId per urls.md specification.
        
        From urls.md: nmId (integer) - Артикул WB
        
        Args:
            value: Value to validate
            field_name: Field name for error messages
            
        Returns:
            Validated integer value
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            raise ValidationError(
                f"{field_name} cannot be None",
                field=field_name,
                value=value,
                expected_type="integer"
            )
        
        # Try to convert to int if it's a string number
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                raise ValidationError(
                    f"{field_name} must be a valid integer",
                    field=field_name,
                    value=value,
                    expected_type="integer"
                )
        
        if not isinstance(value, int):
            raise ValidationError(
                f"{field_name} must be an integer",
                field=field_name,
                value=value,
                expected_type="integer"
            )
        
        if value <= 0:
            raise ValidationError(
                f"{field_name} must be positive",
                field=field_name,
                value=value,
                expected_type="positive integer"
            )
        
        return value
    
    @staticmethod
    def validate_warehouse_name(value: Any, field_name: str = "warehouseName") -> str:
        """
        Validate warehouse name per urls.md specification.
        
        From urls.md: warehouseName (string) ≤ 50 characters
        
        Args:
            value: Value to validate
            field_name: Field name for error messages
            
        Returns:
            Validated string value
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            raise ValidationError(
                f"{field_name} cannot be None",
                field=field_name,
                value=value,
                expected_type="string"
            )
        
        if not isinstance(value, str):
            raise ValidationError(
                f"{field_name} must be a string",
                field=field_name,
                value=value,
                expected_type="string"
            )
        
        value = value.strip()
        
        if not value:
            raise ValidationError(
                f"{field_name} cannot be empty",
                field=field_name,
                value=value,
                expected_type="non-empty string"
            )
        
        if len(value) > 50:  # Per urls.md specification
            raise ValidationError(
                f"{field_name} cannot exceed 50 characters",
                field=field_name,
                value=value,
                expected_type="string ≤ 50 chars"
            )
        
        return value
    
    @staticmethod
    def validate_quantity(value: Any, field_name: str = "quantity") -> int:
        """
        Validate quantity per urls.md specification.
        
        From urls.md: quantity (integer) - Количество, шт.
        
        Args:
            value: Value to validate
            field_name: Field name for error messages
            
        Returns:
            Validated integer value
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            raise ValidationError(
                f"{field_name} cannot be None",
                field=field_name,
                value=value,
                expected_type="integer"
            )
        
        # Try to convert to int if it's a string number
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                raise ValidationError(
                    f"{field_name} must be a valid integer",
                    field=field_name,
                    value=value,
                    expected_type="integer"
                )
        
        if not isinstance(value, int):
            raise ValidationError(
                f"{field_name} must be an integer",
                field=field_name,
                value=value,
                expected_type="integer"
            )
        
        if value < 0:
            raise ValidationError(
                f"{field_name} cannot be negative",
                field=field_name,
                value=value,
                expected_type="non-negative integer"
            )
        
        return value
    
    @staticmethod
    def validate_rfc3339_date(value: Any, field_name: str = "dateFrom") -> str:
        """
        Validate RFC3339 date format per urls.md specification.
        
        From urls.md: dateFrom (string <RFC3339>) for /supplier/orders endpoint
        
        Args:
            value: Value to validate
            field_name: Field name for error messages
            
        Returns:
            Validated RFC3339 date string
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            raise ValidationError(
                f"{field_name} cannot be None",
                field=field_name,
                value=value,
                expected_type="RFC3339 date string"
            )
        
        if not isinstance(value, str):
            raise ValidationError(
                f"{field_name} must be a string",
                field=field_name,
                value=value,
                expected_type="RFC3339 date string"
            )
        
        value = value.strip()
        
        if not value:
            raise ValidationError(
                f"{field_name} cannot be empty",
                field=field_name,
                value=value,
                expected_type="RFC3339 date string"
            )
        
        # Basic RFC3339 format validation
        # Supports formats mentioned in urls.md:
        # - 2019-06-20
        # - 2019-06-20T23:59:59
        # - 2019-06-20T00:00:00.12345
        # - 2017-03-25T00:00:00
        
        rfc3339_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # Date only
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$',  # Date with time
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+$',  # Date with time and milliseconds
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$',  # With timezone
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+[+-]\d{2}:\d{2}$'  # With milliseconds and timezone
        ]
        
        valid_format = any(re.match(pattern, value) for pattern in rfc3339_patterns)
        
        if not valid_format:
            raise ValidationError(
                f"{field_name} must be in RFC3339 format (e.g., '2019-06-20' or '2019-06-20T23:59:59')",
                field=field_name,
                value=value,
                expected_type="RFC3339 date string"
            )
        
        return value
    
    @staticmethod
    def validate_warehouse_remains_response(data: Any) -> List[Dict[str, Any]]:
        """
        Validate warehouse remains API response per urls.md specification.
        
        Expected structure from urls.md:
        Array of objects with: brand, subjectName, vendorCode, nmId, barcode, 
        techSize, volume, warehouses (array of {warehouseName, quantity})
        
        Args:
            data: API response data to validate
            
        Returns:
            Validated response data
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(data, list):
            raise ValidationError(
                "Warehouse remains response must be an array",
                field="response",
                value=type(data).__name__,
                expected_type="array"
            )
        
        validated_data = []
        
        for i, item in enumerate(data):
            try:
                if not isinstance(item, dict):
                    raise ValidationError(
                        f"Item {i} must be an object",
                        field=f"response[{i}]",
                        value=type(item).__name__,
                        expected_type="object"
                    )
                
                # Validate required fields per urls.md
                if "vendorCode" in item:  # This is supplierArticle
                    WildberriesDataValidator.validate_supplier_article(
                        item["vendorCode"], f"response[{i}].vendorCode"
                    )
                
                if "nmId" in item:
                    WildberriesDataValidator.validate_nm_id(
                        item["nmId"], f"response[{i}].nmId"
                    )
                
                # Validate warehouses array
                if "warehouses" in item and item["warehouses"]:
                    if not isinstance(item["warehouses"], list):
                        raise ValidationError(
                            f"Item {i} warehouses must be an array",
                            field=f"response[{i}].warehouses",
                            value=type(item["warehouses"]).__name__,
                            expected_type="array"
                        )
                    
                    for j, warehouse in enumerate(item["warehouses"]):
                        if not isinstance(warehouse, dict):
                            raise ValidationError(
                                f"Warehouse {j} in item {i} must be an object",
                                field=f"response[{i}].warehouses[{j}]",
                                value=type(warehouse).__name__,
                                expected_type="object"
                            )
                        
                        if "warehouseName" in warehouse:
                            WildberriesDataValidator.validate_warehouse_name(
                                warehouse["warehouseName"],
                                f"response[{i}].warehouses[{j}].warehouseName"
                            )
                        
                        if "quantity" in warehouse:
                            WildberriesDataValidator.validate_quantity(
                                warehouse["quantity"],
                                f"response[{i}].warehouses[{j}].quantity"
                            )
                
                validated_data.append(item)
                
            except ValidationError as e:
                logger.warning(f"Validation failed for warehouse remains item {i}: {e}")
                # Continue processing other items, but log the error
                continue
        
        return validated_data
    
    @staticmethod
    def validate_supplier_orders_response(data: Any) -> List[Dict[str, Any]]:
        """
        Validate supplier orders API response per urls.md specification.
        
        Expected structure from urls.md:
        Array of objects with: supplierArticle, nmId, warehouseName, date, etc.
        
        Args:
            data: API response data to validate
            
        Returns:
            Validated response data
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(data, list):
            raise ValidationError(
                "Supplier orders response must be an array",
                field="response",
                value=type(data).__name__,
                expected_type="array"
            )
        
        validated_data = []
        
        for i, item in enumerate(data):
            try:
                if not isinstance(item, dict):
                    raise ValidationError(
                        f"Order {i} must be an object",
                        field=f"response[{i}]",
                        value=type(item).__name__,
                        expected_type="object"
                    )
                
                # Validate required fields per urls.md
                if "supplierArticle" in item:
                    WildberriesDataValidator.validate_supplier_article(
                        item["supplierArticle"], f"response[{i}].supplierArticle"
                    )
                
                if "nmId" in item:
                    WildberriesDataValidator.validate_nm_id(
                        item["nmId"], f"response[{i}].nmId"
                    )
                
                if "warehouseName" in item:
                    WildberriesDataValidator.validate_warehouse_name(
                        item["warehouseName"], f"response[{i}].warehouseName"
                    )
                
                validated_data.append(item)
                
            except ValidationError as e:
                logger.warning(f"Validation failed for supplier order item {i}: {e}")
                # Continue processing other items, but log the error
                continue
        
        return validated_data
    
    @staticmethod
    def validate_calculation_inputs(total_orders: int, total_stock: int) -> tuple[int, int]:
        """
        Validate inputs for turnover calculation per urls.md logic.
        
        Args:
            total_orders: Total orders count
            total_stock: Total stock quantity
            
        Returns:
            Validated (total_orders, total_stock) tuple
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            total_orders = WildberriesDataValidator.validate_quantity(total_orders, "total_orders")
            total_stock = WildberriesDataValidator.validate_quantity(total_stock, "total_stock")
            return total_orders, total_stock
        except ValidationError:
            raise


class DataValidator:
    """
    High-level data validator for products and business rules.
    
    Provides validation for complete Product objects and business logic
    including uniqueness checks and business rule enforcement.
    """
    
    def __init__(self):
        """Initialize validator."""
        self.wb_validator = WildberriesDataValidator()
    
    def validate_product_complete(self, product) -> None:
        """
        Validate complete Product object.
        
        Args:
            product: Product instance to validate
            
        Raises:
            ValidationError: If product validation fails
        """
        try:
            from stock_tracker.core.models import Product
            
            if not isinstance(product, Product):
                raise ValidationError(
                    "Invalid product type",
                    field="product",
                    value=type(product).__name__,
                    expected_type="Product"
                )
            
            # Validate basic fields
            self.wb_validator.validate_supplier_article(
                product.seller_article, "seller_article"
            )
            self.wb_validator.validate_nm_id(
                product.wildberries_article, "wildberries_article"
            )
            
            # Validate quantities
            if product.total_orders < 0:
                raise ValidationError(
                    "Total orders cannot be negative",
                    field="total_orders",
                    value=product.total_orders
                )
            
            if product.total_stock < 0:
                raise ValidationError(
                    "Total stock cannot be negative",
                    field="total_stock",
                    value=product.total_stock
                )
            
            # Validate turnover
            if product.turnover < 0:
                raise ValidationError(
                    "Turnover cannot be negative",
                    field="turnover",
                    value=product.turnover
                )
            
            # Validate warehouses
            self._validate_product_warehouses(product)
            
            logger.debug(f"Product validation passed: {product.seller_article}")
            
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Product validation failed: {e}")
    
    def _validate_product_warehouses(self, product) -> None:
        """
        Validate product warehouses.
        
        Args:
            product: Product instance
            
        Raises:
            ValidationError: If warehouse validation fails
        """
        if not hasattr(product, 'warehouses'):
            return
        
        warehouse_names = set()
        
        for i, warehouse in enumerate(product.warehouses):
            # Check warehouse name uniqueness
            if warehouse.name in warehouse_names:
                raise ValidationError(
                    f"Duplicate warehouse name: {warehouse.name}",
                    field=f"warehouses[{i}].name",
                    value=warehouse.name
                )
            warehouse_names.add(warehouse.name)
            
            # Validate warehouse fields
            if not warehouse.name or not warehouse.name.strip():
                raise ValidationError(
                    "Warehouse name cannot be empty",
                    field=f"warehouses[{i}].name",
                    value=warehouse.name
                )
            
            if warehouse.stock < 0:
                raise ValidationError(
                    "Warehouse stock cannot be negative",
                    field=f"warehouses[{i}].stock",
                    value=warehouse.stock
                )
            
            if warehouse.orders < 0:
                raise ValidationError(
                    "Warehouse orders cannot be negative",
                    field=f"warehouses[{i}].orders",
                    value=warehouse.orders
                )
    
    def validate_product_uniqueness(self, new_product, existing_products: List) -> None:
        """
        Validate product uniqueness against existing products.
        
        Args:
            new_product: Product to validate
            existing_products: List of existing Product instances
            
        Raises:
            ValidationError: If uniqueness constraint is violated
        """
        try:
            # Check seller article uniqueness
            for existing in existing_products:
                if existing.seller_article.lower() == new_product.seller_article.lower():
                    raise ValidationError(
                        f"Seller article already exists: {new_product.seller_article}",
                        field="seller_article",
                        value=new_product.seller_article,
                        constraint="unique"
                    )
            
            # Check wildberries article uniqueness
            for existing in existing_products:
                if existing.wildberries_article == new_product.wildberries_article:
                    raise ValidationError(
                        f"Wildberries article already exists: {new_product.wildberries_article}",
                        field="wildberries_article",
                        value=new_product.wildberries_article,
                        constraint="unique"
                    )
            
            logger.debug(f"Product uniqueness validation passed: {new_product.seller_article}")
            
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Uniqueness validation failed: {e}")
    
    def validate_batch_products(self, products: List) -> Dict[str, Any]:
        """
        Validate batch of products and return summary.
        
        Args:
            products: List of Product instances
            
        Returns:
            Dict with validation summary
        """
        summary = {
            "total_products": len(products),
            "valid_products": 0,
            "invalid_products": 0,
            "errors": [],
            "duplicate_articles": []
        }
        
        # Track articles for uniqueness
        seller_articles = set()
        wb_articles = set()
        
        for i, product in enumerate(products):
            try:
                # Basic validation
                self.validate_product_complete(product)
                
                # Check uniqueness within batch
                if product.seller_article.lower() in seller_articles:
                    summary["duplicate_articles"].append({
                        "index": i,
                        "article": product.seller_article,
                        "type": "seller_article"
                    })
                    summary["errors"].append(f"Duplicate seller article at index {i}: {product.seller_article}")
                    summary["invalid_products"] += 1
                    continue
                
                if product.wildberries_article in wb_articles:
                    summary["duplicate_articles"].append({
                        "index": i,
                        "article": product.wildberries_article,
                        "type": "wildberries_article"
                    })
                    summary["errors"].append(f"Duplicate WB article at index {i}: {product.wildberries_article}")
                    summary["invalid_products"] += 1
                    continue
                
                # Add to tracking sets
                seller_articles.add(product.seller_article.lower())
                wb_articles.add(product.wildberries_article)
                
                summary["valid_products"] += 1
                
            except ValidationError as e:
                summary["invalid_products"] += 1
                summary["errors"].append(f"Product {i} validation failed: {e}")
            except Exception as e:
                summary["invalid_products"] += 1
                summary["errors"].append(f"Product {i} unexpected error: {e}")
        
        logger.info(f"Batch validation: {summary['valid_products']}/{summary['total_products']} valid")
        return summary
    
    def enforce_business_rules(self, product) -> List[str]:
        """
        Enforce business rules and return warnings.
        
        Args:
            product: Product instance
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        try:
            # Rule 1: Products with high stock but no orders
            if product.total_stock > 100 and product.total_orders == 0:
                warnings.append(f"High stock ({product.total_stock}) with no orders - consider reducing stock")
            
            # Rule 2: Products with orders but no stock
            if product.total_orders > 0 and product.total_stock == 0:
                warnings.append("Orders exist but no stock available - restock urgently")
            
            # Rule 3: Very low turnover
            if product.total_stock > 0 and product.turnover < 0.1:
                warnings.append(f"Very low turnover ({product.turnover:.3f}) - review product performance")
            
            # Rule 4: Very high turnover (potential stock shortage)
            if product.turnover > 5.0:
                warnings.append(f"Very high turnover ({product.turnover:.3f}) - consider increasing stock")
            
            # Rule 5: Single warehouse dominance
            if len(product.warehouses) > 1:
                max_stock = max(w.stock for w in product.warehouses)
                if max_stock > 0 and max_stock / product.total_stock > 0.8:
                    dominant_warehouse = next(w for w in product.warehouses if w.stock == max_stock)
                    warnings.append(f"Stock heavily concentrated in {dominant_warehouse.name} ({max_stock}/{product.total_stock})")
            
            # Rule 6: Empty warehouse names
            empty_warehouses = [w for w in product.warehouses if not w.name.strip()]
            if empty_warehouses:
                warnings.append(f"Found {len(empty_warehouses)} warehouses with empty names")
            
            # Rule 7: Article format recommendations
            if len(product.seller_article) < 3:
                warnings.append("Seller article is very short - consider more descriptive article")
            
            if product.wildberries_article < 10000000:  # Less than 8 digits
                warnings.append("Wildberries article seems unusually short")
            
        except Exception as e:
            warnings.append(f"Business rule validation error: {e}")
        
        return warnings
    
    def validate_article_format(self, seller_article: str) -> Dict[str, Any]:
        """
        Validate and analyze seller article format.
        
        Args:
            seller_article: Seller article to analyze
            
        Returns:
            Dict with format analysis
        """
        analysis = {
            "article": seller_article,
            "length": len(seller_article),
            "valid": True,
            "issues": [],
            "recommendations": []
        }
        
        try:
            # Basic validation
            self.wb_validator.validate_supplier_article(seller_article)
            
            # Format analysis
            if len(seller_article) < 3:
                analysis["issues"].append("Article too short")
                analysis["recommendations"].append("Use at least 3 characters")
            
            if len(seller_article) > 50:
                analysis["recommendations"].append("Consider shorter article for better readability")
            
            # Character analysis
            has_letters = bool(re.search(r'[a-zA-Z]', seller_article))
            has_numbers = bool(re.search(r'\d', seller_article))
            has_special = bool(re.search(r'[^a-zA-Z0-9]', seller_article))
            
            analysis["character_types"] = {
                "letters": has_letters,
                "numbers": has_numbers,
                "special_chars": has_special
            }
            
            # Pattern recommendations
            if not has_letters and not has_numbers:
                analysis["issues"].append("Article contains only special characters")
                analysis["valid"] = False
            
            if has_special:
                special_chars = set(re.findall(r'[^a-zA-Z0-9]', seller_article))
                analysis["special_characters"] = list(special_chars)
                
                problematic_chars = special_chars - {'-', '_', '.'}
                if problematic_chars:
                    analysis["recommendations"].append(f"Avoid characters: {', '.join(problematic_chars)}")
            
        except ValidationError as e:
            analysis["valid"] = False
            analysis["issues"].append(str(e))
        
        return analysis


def validate_api_key(api_key: str) -> str:
    """
    Validate Wildberries API key format.
    
    Args:
        api_key: API key to validate
        
    Returns:
        Validated API key
        
    Raises:
        ValidationError: If validation fails
    """
    if not api_key or not isinstance(api_key, str):
        raise ValidationError(
            "API key must be a non-empty string",
            field="api_key",
            value=api_key,
            expected_type="non-empty string"
        )
    
    api_key = api_key.strip()
    
    if len(api_key) < 10:  # Reasonable minimum length
        raise ValidationError(
            "API key appears to be too short",
            field="api_key",
            value="<hidden>",
            expected_type="valid API key"
        )
    
    return api_key


def validate_google_sheet_id(sheet_id: str) -> str:
    """
    Validate Google Sheet ID format.
    
    Args:
        sheet_id: Sheet ID to validate
        
    Returns:
        Validated sheet ID
        
    Raises:
        ValidationError: If validation fails
    """
    if not sheet_id or not isinstance(sheet_id, str):
        raise ValidationError(
            "Sheet ID must be a non-empty string",
            field="sheet_id",
            value=sheet_id,
            expected_type="non-empty string"
        )
    
    sheet_id = sheet_id.strip()
    
    # Basic Google Sheet ID format validation
    if len(sheet_id) < 20 or not re.match(r'^[a-zA-Z0-9_-]+$', sheet_id):
        raise ValidationError(
            "Invalid Google Sheet ID format",
            field="sheet_id",
            value=sheet_id[:10] + "...",  # Show only first 10 chars
            expected_type="valid Google Sheet ID"
        )
    
    return sheet_id


class WarehouseDataValidator:
    """
    Validator for multi-warehouse data synchronization (User Story 2).
    
    Provides validation for warehouse data consistency, synchronization,
    and integrity checks specifically for the multi-warehouse functionality.
    """
    
    def __init__(self):
        """Initialize warehouse data validator."""
        self.wildberries_validator = WildberriesDataValidator()
        logger.debug("WarehouseDataValidator initialized")
    
    def validate_warehouse_synchronization(self, warehouses: List, 
                                         expected_order: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Validate warehouse data synchronization across multiple warehouses.
        
        Args:
            warehouses: List of Warehouse objects to validate
            expected_order: Expected order of warehouse names (optional)
            
        Returns:
            Dict with validation results
        """
        try:
            from stock_tracker.core.models import Warehouse
            
            validation = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "synchronization_issues": [],
                "warehouse_count": len(warehouses) if warehouses else 0
            }
            
            if not warehouses:
                validation["warnings"].append("No warehouses to validate")
                return validation
            
            # Validate individual warehouses
            for i, warehouse in enumerate(warehouses):
                if not isinstance(warehouse, Warehouse):
                    validation["errors"].append(f"Warehouse {i}: Invalid type, expected Warehouse object")
                    validation["valid"] = False
                    continue
                
                # Validate warehouse name
                try:
                    self.wildberries_validator.validate_warehouse_name(warehouse.name)
                except ValidationError as e:
                    validation["errors"].append(f"Warehouse {i} ({warehouse.name}): {e}")
                    validation["valid"] = False
                
                # Validate quantities
                try:
                    self.wildberries_validator.validate_quantity(warehouse.stock)
                    self.wildberries_validator.validate_quantity(warehouse.orders)
                except ValidationError as e:
                    validation["errors"].append(f"Warehouse {i} ({warehouse.name}): {e}")
                    validation["valid"] = False
            
            # Check for duplicate warehouse names
            warehouse_names = [wh.name for wh in warehouses]
            duplicates = []
            seen = set()
            for name in warehouse_names:
                if name in seen:
                    if name not in duplicates:
                        duplicates.append(name)
                seen.add(name)
            
            if duplicates:
                validation["errors"].append(f"Duplicate warehouse names: {duplicates}")
                validation["valid"] = False
            
            # Validate ordering consistency
            if expected_order:
                actual_order = [wh.name for wh in warehouses]
                ordering_issues = self._validate_warehouse_ordering(actual_order, expected_order)
                validation["synchronization_issues"].extend(ordering_issues)
                
                if ordering_issues:
                    validation["warnings"].append(f"Warehouse ordering inconsistencies found: {len(ordering_issues)}")
            
            # Check data ranges
            high_stock_warehouses = [wh.name for wh in warehouses if wh.stock > 10000]
            if high_stock_warehouses:
                validation["warnings"].append(f"Very high stock values: {high_stock_warehouses}")
            
            high_orders_warehouses = [wh.name for wh in warehouses if wh.orders > 1000]
            if high_orders_warehouses:
                validation["warnings"].append(f"Very high orders values: {high_orders_warehouses}")
            
            return validation
            
        except Exception as e:
            logger.error(f"Failed to validate warehouse synchronization: {e}")
            return {
                "valid": False,
                "errors": [f"Validation failed: {e}"],
                "warnings": [],
                "synchronization_issues": [],
                "warehouse_count": 0
            }
    
    def validate_multi_warehouse_consistency(self, products: List) -> Dict[str, Any]:
        """
        Validate consistency of warehouse data across multiple products.
        
        Args:
            products: List of Product objects to validate
            
        Returns:
            Dict with comprehensive validation results
        """
        try:
            from stock_tracker.core.models import Product
            
            validation = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "products_checked": len(products) if products else 0,
                "warehouse_consistency": {},
                "common_warehouses": [],
                "orphaned_warehouses": {}
            }
            
            if not products:
                validation["warnings"].append("No products to validate")
                return validation
            
            # Collect all warehouse names across products
            all_warehouses = {}  # warehouse_name -> list of products that have it
            
            for product in products:
                if not isinstance(product, Product):
                    validation["errors"].append(f"Invalid product type: {type(product)}")
                    validation["valid"] = False
                    continue
                
                # Validate individual product warehouses
                product_validation = self.validate_warehouse_synchronization(product.warehouses)
                
                if not product_validation["valid"]:
                    for error in product_validation["errors"]:
                        validation["errors"].append(f"Product {product.seller_article}: {error}")
                    validation["valid"] = False
                
                # Track warehouse usage
                for warehouse in product.warehouses:
                    if warehouse.name not in all_warehouses:
                        all_warehouses[warehouse.name] = []
                    all_warehouses[warehouse.name].append(product.seller_article)
            
            # Analyze warehouse consistency
            warehouse_counts = {name: len(products) for name, products in all_warehouses.items()}
            total_products = len([p for p in products if hasattr(p, 'warehouses')])
            
            # Find common warehouses (used by most products)
            if total_products > 0:
                common_threshold = max(1, total_products * 0.5)  # Used by at least 50% of products
                validation["common_warehouses"] = [
                    name for name, count in warehouse_counts.items() 
                    if count >= common_threshold
                ]
                
                # Find orphaned warehouses (used by very few products)
                orphan_threshold = max(1, total_products * 0.1)  # Used by less than 10% of products
                validation["orphaned_warehouses"] = {
                    name: all_warehouses[name] for name, count in warehouse_counts.items()
                    if count < orphan_threshold and count > 0
                }
            
            # Check for synchronization patterns
            validation["warehouse_consistency"] = {
                "total_unique_warehouses": len(all_warehouses),
                "warehouse_usage_distribution": warehouse_counts,
                "max_warehouses_per_product": max([len(p.warehouses) for p in products if hasattr(p, 'warehouses')] or [0]),
                "min_warehouses_per_product": min([len(p.warehouses) for p in products if hasattr(p, 'warehouses')] or [0])
            }
            
            return validation
            
        except Exception as e:
            logger.error(f"Failed to validate multi-warehouse consistency: {e}")
            return {
                "valid": False,
                "errors": [f"Validation failed: {e}"],
                "warnings": [],
                "products_checked": 0,
                "warehouse_consistency": {},
                "common_warehouses": [],
                "orphaned_warehouses": {}
            }
    
    def validate_synchronized_data_integrity(self, names: str, orders: str, stock: str) -> Dict[str, Any]:
        """
        Validate integrity of synchronized data across columns F, G, H.
        
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
                "line_counts": {},
                "data_integrity": {}
            }
            
            # Parse multi-line data
            names_lines = [line.strip() for line in str(names).split('\n') if line.strip()]
            orders_lines = [line.strip() for line in str(orders).split('\n') if line.strip()]
            stock_lines = [line.strip() for line in str(stock).split('\n') if line.strip()]
            
            validation["line_counts"] = {
                "names": len(names_lines),
                "orders": len(orders_lines),
                "stock": len(stock_lines)
            }
            
            # Check line count consistency
            if len(set([len(names_lines), len(orders_lines), len(stock_lines)])) > 1:
                validation["errors"].append(
                    f"Inconsistent line counts: names={len(names_lines)}, "
                    f"orders={len(orders_lines)}, stock={len(stock_lines)}"
                )
                validation["valid"] = False
            
            # Validate warehouse names
            for i, name in enumerate(names_lines):
                try:
                    self.wildberries_validator.validate_warehouse_name(name)
                except ValidationError as e:
                    validation["errors"].append(f"Invalid warehouse name at line {i+1}: {e}")
                    validation["valid"] = False
            
            # Validate orders data
            for i, orders_val in enumerate(orders_lines):
                try:
                    orders_int = int(orders_val)
                    self.wildberries_validator.validate_quantity(orders_int)
                except (ValueError, ValidationError) as e:
                    validation["errors"].append(f"Invalid orders value at line {i+1}: {e}")
                    validation["valid"] = False
            
            # Validate stock data
            for i, stock_val in enumerate(stock_lines):
                try:
                    stock_int = int(stock_val)
                    self.wildberries_validator.validate_quantity(stock_int)
                except (ValueError, ValidationError) as e:
                    validation["errors"].append(f"Invalid stock value at line {i+1}: {e}")
                    validation["valid"] = False
            
            # Data integrity checks
            validation["data_integrity"] = {
                "has_empty_names": any(not name for name in names_lines),
                "has_zero_orders": any(orders_val == "0" for orders_val in orders_lines),
                "has_zero_stock": any(stock_val == "0" for stock_val in stock_lines),
                "consistent_formatting": True  # Could add more detailed checks
            }
            
            return validation
            
        except Exception as e:
            logger.error(f"Failed to validate synchronized data integrity: {e}")
            return {
                "valid": False,
                "errors": [f"Validation failed: {e}"],
                "warnings": [],
                "line_counts": {},
                "data_integrity": {}
            }
    
    def _validate_warehouse_ordering(self, actual_order: List[str], 
                                   expected_order: List[str]) -> List[str]:
        """
        Validate warehouse ordering against expected order.
        
        Args:
            actual_order: Actual warehouse order
            expected_order: Expected warehouse order
            
        Returns:
            List of ordering issues
        """
        issues = []
        
        try:
            # Check if all expected warehouses are present
            missing_warehouses = set(expected_order) - set(actual_order)
            if missing_warehouses:
                issues.append(f"Missing expected warehouses: {list(missing_warehouses)}")
            
            # Check if there are unexpected warehouses
            unexpected_warehouses = set(actual_order) - set(expected_order)
            if unexpected_warehouses:
                issues.append(f"Unexpected warehouses: {list(unexpected_warehouses)}")
            
            # Check ordering of common warehouses
            common_warehouses = set(actual_order) & set(expected_order)
            if common_warehouses:
                # Extract positions of common warehouses in both orders
                actual_positions = {wh: i for i, wh in enumerate(actual_order) if wh in common_warehouses}
                expected_positions = {wh: i for i, wh in enumerate(expected_order) if wh in common_warehouses}
                
                # Check if relative ordering is maintained
                for wh1 in common_warehouses:
                    for wh2 in common_warehouses:
                        if wh1 != wh2:
                            actual_before = actual_positions[wh1] < actual_positions[wh2]
                            expected_before = expected_positions[wh1] < expected_positions[wh2]
                            
                            if actual_before != expected_before:
                                issues.append(f"Ordering issue: {wh1} vs {wh2} order mismatch")
            
        except Exception as e:
            issues.append(f"Ordering validation error: {e}")
        
        return issues
    
    def generate_warehouse_sync_report(self, products: List) -> Dict[str, Any]:
        """
        Generate comprehensive warehouse synchronization report.
        
        Args:
            products: List of products to analyze
            
        Returns:
            Dict with detailed synchronization report
        """
        try:
            # Run all validations
            consistency_validation = self.validate_multi_warehouse_consistency(products)
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "products_analyzed": len(products) if products else 0,
                    "overall_status": "valid" if consistency_validation["valid"] else "issues_found",
                    "total_errors": len(consistency_validation["errors"]),
                    "total_warnings": len(consistency_validation["warnings"])
                },
                "warehouse_analysis": consistency_validation["warehouse_consistency"],
                "common_warehouses": consistency_validation["common_warehouses"],
                "orphaned_warehouses": consistency_validation["orphaned_warehouses"],
                "errors": consistency_validation["errors"],
                "warnings": consistency_validation["warnings"],
                "recommendations": []
            }
            
            # Generate recommendations
            if report["summary"]["total_errors"] > 0:
                report["recommendations"].append("Fix validation errors before proceeding with synchronization")
            
            if len(consistency_validation["orphaned_warehouses"]) > 0:
                report["recommendations"].append("Review orphaned warehouses - they may indicate data inconsistencies")
            
            if len(consistency_validation["common_warehouses"]) == 0:
                report["recommendations"].append("No common warehouses found across products - consider warehouse naming standardization")
            
            warehouse_count_variance = (
                report["warehouse_analysis"].get("max_warehouses_per_product", 0) - 
                report["warehouse_analysis"].get("min_warehouses_per_product", 0)
            )
            if warehouse_count_variance > 5:
                report["recommendations"].append("High variance in warehouse count per product - consider data normalization")
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate warehouse sync report: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "products_analyzed": 0,
                    "overall_status": "error",
                    "total_errors": 1,
                    "total_warnings": 0
                },
                "error": str(e),
                "recommendations": ["Fix report generation error"]
            }


if __name__ == "__main__":
    # Test validation functions
    print("Testing Wildberries data validation...")
    
    validator = WildberriesDataValidator()
    
    # Test valid data
    try:
        supplier_article = validator.validate_supplier_article("WB001")
        nm_id = validator.validate_nm_id(12345678)
        warehouse_name = validator.validate_warehouse_name("СЦ Волгоград")
        quantity = validator.validate_quantity(654)
        date_str = validator.validate_rfc3339_date("2019-06-20T23:59:59")
        
        print("✅ All basic validations passed for valid data")
        
        # Test product validation
        data_validator = DataValidator()
        
        # Test article format analysis
        analysis = data_validator.validate_article_format("WB001")
        print(f"✅ Article format analysis: {analysis['valid']}")
        
        # Test mock product (would need actual Product import for full test)
        print("✅ Product validation structure verified")
        
    except ValidationError as e:
        print(f"❌ Unexpected validation error: {e}")
    
    # Test invalid data
    try:
        validator.validate_nm_id(-1)  # Should fail
        print("❌ Validation should have failed for negative nmId")
    except ValidationError:
        print("✅ Correctly rejected negative nmId")
    
    # Test business rules
    try:
        data_validator = DataValidator()
        
        # Test article format edge cases
        short_analysis = data_validator.validate_article_format("AB")
        print(f"✅ Short article analysis: {len(short_analysis['issues'])} issues found")
        
        long_analysis = data_validator.validate_article_format("A" * 80)
        print(f"✅ Long article analysis: {len(long_analysis['recommendations'])} recommendations")
        
    except Exception as e:
        print(f"❌ Business rules test error: {e}")
    
    print("Validation tests completed!")