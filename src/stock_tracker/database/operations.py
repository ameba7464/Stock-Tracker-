"""
CRUD operations for Google Sheets product management.

Provides comprehensive Create, Read, Update, Delete operations for managing
product inventory records in Google Sheets, with proper error handling,
data validation, and optimized batch processing for high-performance operations.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import asyncio

import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound

from stock_tracker.core.models import Product, SyncSession
from stock_tracker.core.formatter import ProductDataFormatter
from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.database.structure import SheetsTableStructure, ColumnDefinition
from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.exceptions import SyncError, ValidationError, DatabaseError
from stock_tracker.utils.performance import get_sheets_optimizer, BatchConfig
from stock_tracker.utils.monitoring import get_monitoring_system


logger = get_logger(__name__)


class SheetsOperations:
    """
    Optimized Google Sheets CRUD operations for product management.
    
    Handles all database-like operations on Google Sheets including:
    - Creating new product records
    - Reading existing products  
    - Updating product data
    - Deleting products
    - High-performance batch operations
    - Adaptive optimization based on data volume
    """
    
    def __init__(self, sheets_client: GoogleSheetsClient):
        """
        Initialize with Google Sheets client and performance optimization.
        
        Args:
            sheets_client: Authenticated Google Sheets client
        """
        self.sheets_client = sheets_client
        self.formatter = ProductDataFormatter()
        self.structure = SheetsTableStructure(sheets_client)
        self.optimizer = get_sheets_optimizer()
        self.monitoring = get_monitoring_system()
        
        logger.info("Initialized SheetsOperations with performance optimization")
        
    def get_or_create_worksheet(self, spreadsheet_id: str, 
                              worksheet_name: str = "Stock Tracker") -> gspread.Worksheet:
        """
        Get existing worksheet or create new one with proper structure.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            worksheet_name: Name of the worksheet (default: "Stock Tracker")
            
        Returns:
            Worksheet instance
            
        Raises:
            SyncError: If worksheet operations fail
        """
        try:
            spreadsheet = self.sheets_client.get_spreadsheet(spreadsheet_id)
            
            # Try to get existing worksheet
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
                logger.debug(f"Found existing worksheet: {worksheet_name}")
                
                # Ensure it has proper structure
                self._ensure_worksheet_structure(worksheet)
                return worksheet
                
            except WorksheetNotFound:
                # Check if there's a legacy worksheet with old name that we should rename
                if worksheet_name == "Stock Tracker":
                    try:
                        legacy_worksheet = spreadsheet.worksheet("Товары")
                        logger.info("Found legacy worksheet 'Товары', renaming to 'Stock Tracker'")
                        legacy_worksheet.update_title("Stock Tracker")
                        self._ensure_worksheet_structure(legacy_worksheet)
                        return legacy_worksheet
                    except WorksheetNotFound:
                        pass  # No legacy worksheet found, proceed with creation
                
                # Create new worksheet
                logger.info(f"Creating new worksheet: {worksheet_name}")
                worksheet = spreadsheet.add_worksheet(
                    title=worksheet_name,
                    rows=1000,  # Start with 1000 rows
                    cols=10      # 10 columns (added FBO/FBS columns I and J)
                )
                
                # Initialize structure
                self._initialize_worksheet_structure(worksheet)
                return worksheet
                
        except Exception as e:
            logger.error(f"Failed to get/create worksheet {worksheet_name}: {e}")
            raise SyncError(f"Worksheet operation failed: {e}")
    
    def _ensure_worksheet_structure(self, worksheet: gspread.Worksheet) -> None:
        """
        Ensure worksheet has proper headers and structure.
        
        Args:
            worksheet: Worksheet to check
        """
        try:
            # Check if headers exist
            headers = worksheet.row_values(1)
            expected_headers = self.structure.get_headers()
            
            if headers != expected_headers:
                logger.info("Updating worksheet headers")
                worksheet.update('A1:H1', [expected_headers])
                
        except Exception as e:
            logger.warning(f"Could not verify worksheet structure: {e}")
    
    def _initialize_worksheet_structure(self, worksheet: gspread.Worksheet) -> None:
        """
        Initialize new worksheet with headers and formatting.
        
        Args:
            worksheet: New worksheet to initialize
        """
        try:
            # Set headers
            headers = self.structure.get_headers()
            worksheet.update('A1:H1', [headers])
            
            # Apply basic formatting
            self.structure.apply_header_formatting(worksheet)
            
            logger.info(f"Initialized worksheet structure")
            
        except Exception as e:
            logger.error(f"Failed to initialize worksheet structure: {e}")
    
    def rename_worksheet_from_legacy(self, spreadsheet_id: str, 
                                   old_name: str = "Товары", 
                                   new_name: str = "Stock Tracker") -> bool:
        """
        Rename existing worksheet from legacy name to new name.
        
        This function helps migrate from old Russian worksheet names 
        to new English names for better internationalization.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            old_name: Old worksheet name to find and rename
            new_name: New worksheet name
            
        Returns:
            True if renamed successfully, False if old worksheet not found
            
        Raises:
            SyncError: If rename operation fails
        """
        try:
            spreadsheet = self.sheets_client.get_spreadsheet(spreadsheet_id)
            
            logger.info(f"Looking for worksheet '{old_name}' to rename to '{new_name}'")
            
            try:
                # Find worksheet with old name
                old_worksheet = spreadsheet.worksheet(old_name)
                
                # Check if new name already exists
                try:
                    spreadsheet.worksheet(new_name)
                    logger.warning(f"Worksheet '{new_name}' already exists. Cannot rename.")
                    return False
                except WorksheetNotFound:
                    pass  # Good, new name doesn't exist
                
                # Rename the worksheet
                old_worksheet.update_title(new_name)
                
                logger.info(f"✅ Successfully renamed worksheet '{old_name}' to '{new_name}'")
                return True
                
            except WorksheetNotFound:
                logger.info(f"Worksheet '{old_name}' not found. Nothing to rename.")
                return False
                
        except Exception as e:
            logger.error(f"Failed to rename worksheet: {e}")
            raise SyncError(f"Worksheet rename failed: {e}")
    
    # CREATE operations
    
    def create_product(self, spreadsheet_id: str, product: Product,
                      worksheet_name: str = "Stock Tracker") -> int:
        """
        Create new product record in Google Sheets.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            product: Product instance to create
            worksheet_name: Target worksheet name
            
        Returns:
            Row number where product was created
            
        Raises:
            SyncError: If creation fails
            ValidationError: If product data is invalid
        """
        try:
            worksheet = self.get_or_create_worksheet(spreadsheet_id, worksheet_name)
            
            # Check if product already exists
            existing_row = self._find_product_row(worksheet, product.seller_article)
            if existing_row is not None:
                raise ValidationError(
                    f"Product already exists at row {existing_row}",
                    field="seller_article",
                    value=product.seller_article
                )
            
            # Format product data
            row_data = self.formatter.format_product_for_sheets(product)
            
            # Find next empty row
            next_row = self._find_next_empty_row(worksheet)
            
            # Ensure sheet has enough capacity for the new row
            try:
                self.sheets_client.ensure_sheet_capacity(next_row, len(row_data))
                logger.debug(f"Sheet capacity ensured for row {next_row}")
            except Exception as capacity_error:
                logger.warning(f"Could not ensure sheet capacity: {capacity_error}")
                # Continue anyway, let the actual update fail if needed
            
            # Insert product data
            range_name = f"A{next_row}:H{next_row}"
            worksheet.update(range_name, [row_data])
            
            logger.info(f"Created product {product.seller_article} at row {next_row}")
            return next_row
            
        except Exception as e:
            logger.error(f"Failed to create product {product.seller_article}: {e}")
            
            # Check if it's a capacity issue
            if "недостаточно места" in str(e).lower() or "insufficient space" in str(e).lower():
                logger.error("Google Sheets capacity error detected - trying to expand sheet")
                try:
                    # Try to expand and retry
                    next_row = self._find_next_empty_row(worksheet)
                    self.sheets_client.ensure_sheet_capacity(next_row + 100, 8)
                    worksheet.update(range_name, [row_data])
                    logger.info(f"Created product {product.seller_article} after sheet expansion")
                    return next_row
                except Exception as retry_error:
                    logger.error(f"Failed even after sheet expansion: {retry_error}")
                    raise SyncError(f"Sheet capacity issue: {retry_error}")
            
            if isinstance(e, (ValidationError, SyncError)):
                raise
            raise SyncError(f"Product creation failed: {e}")
    
    def create_products_batch(self, spreadsheet_id: str, products: List[Product],
                            worksheet_name: str = "Stock Tracker") -> List[int]:
        """
        Create multiple products in batch operation.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            products: List of Product instances
            worksheet_name: Target worksheet name
            
        Returns:
            List of row numbers where products were created
            
        Raises:
            SyncError: If batch creation fails
        """
        try:
            worksheet = self.get_or_create_worksheet(spreadsheet_id, worksheet_name)
            
            # Check for duplicates
            existing_articles = self._get_all_seller_articles(worksheet)
            new_products = []
            for product in products:
                if product.seller_article not in existing_articles:
                    new_products.append(product)
                else:
                    logger.warning(f"Skipping duplicate product: {product.seller_article}")
            
            if not new_products:
                logger.info("No new products to create")
                return []
            
            # Format all products
            batch_data = self.formatter.format_products_batch(new_products)
            
            # Find insertion point
            start_row = self._find_next_empty_row(worksheet)
            end_row = start_row + len(batch_data) - 1
            
            # Ensure sheet has enough capacity for batch data
            try:
                self.sheets_client.ensure_sheet_capacity(end_row, 8)
                logger.debug(f"Sheet capacity ensured for batch: rows {start_row}-{end_row}")
            except Exception as capacity_error:
                logger.warning(f"Could not ensure sheet capacity for batch: {capacity_error}")
            
            # Batch update
            range_name = f"A{start_row}:H{end_row}"
            worksheet.update(range_name, batch_data)
            
            created_rows = list(range(start_row, end_row + 1))
            logger.info(f"Created {len(new_products)} products in batch (rows {start_row}-{end_row})")
            
            return created_rows
            
        except Exception as e:
            logger.error(f"Failed to create products batch: {e}")
            raise SyncError(f"Batch creation failed: {e}")
    
    # READ operations
    
    def read_product(self, spreadsheet_id: str, seller_article: str,
                    worksheet_name: str = "Stock Tracker") -> Optional[Product]:
        """
        Read single product by seller article.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            seller_article: Product seller article to find
            worksheet_name: Source worksheet name
            
        Returns:
            Product instance or None if not found
            
        Raises:
            SyncError: If read operation fails
        """
        try:
            worksheet = self.get_or_create_worksheet(spreadsheet_id, worksheet_name)
            
            # Find product row
            row_number = self._find_product_row(worksheet, seller_article)
            if row_number is None:
                logger.debug(f"Product not found: {seller_article}")
                return None
            
            # Get row data
            row_data = worksheet.row_values(row_number)
            
            # Parse product
            product = self.formatter.parse_product_from_sheets_row(row_data, row_number)
            if product:
                logger.debug(f"Read product {seller_article} from row {row_number}")
            
            return product
            
        except Exception as e:
            logger.error(f"Failed to read product {seller_article}: {e}")
            raise SyncError(f"Product read failed: {e}")
    
    def read_all_products(self, spreadsheet_id: str,
                         worksheet_name: str = "Stock Tracker",
                         use_optimization: bool = True) -> List[Product]:
        """
        Read all products from worksheet with optional performance optimization.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            worksheet_name: Source worksheet name
            use_optimization: Whether to use optimized batch operations
            
        Returns:
            List of Product instances
            
        Raises:
            SyncError: If read operation fails
        """
        if use_optimization:
            # Use async optimized version - run in sync context
            import asyncio
            
            try:
                # Check if we're already in an event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context, create a task
                    task = asyncio.create_task(
                        self.batch_read_products_optimized(spreadsheet_id, worksheet_name)
                    )
                    return asyncio.run_coroutine_threadsafe(task, loop).result()
                else:
                    # We're in sync context, run directly
                    return asyncio.run(
                        self.batch_read_products_optimized(spreadsheet_id, worksheet_name)
                    )
            except Exception as e:
                logger.warning(f"Optimized read failed, falling back to standard method: {e}")
                # Fall through to standard method
        
        # Standard synchronous method (fallback)
        try:
            worksheet = self.get_or_create_worksheet(spreadsheet_id, worksheet_name)
            
            # Get all data (skip header row)
            all_data = worksheet.get_all_values()
            if len(all_data) <= 1:
                logger.info("No products found in worksheet")
                return []
            
            # Parse all products
            products = []
            for i, row_data in enumerate(all_data[1:], start=2):  # Start from row 2
                product = self.formatter.parse_product_from_sheets_row(row_data, i)
                if product:
                    products.append(product)
            
            logger.info(f"Read {len(products)} products from worksheet")
            return products
            
        except Exception as e:
            logger.error(f"Failed to read all products: {e}")
            raise SyncError(f"Products read failed: {e}")
    
    def search_products(self, spreadsheet_id: str, search_criteria: Dict[str, Any],
                       worksheet_name: str = "Stock Tracker") -> List[Tuple[Product, int]]:
        """
        Search products by various criteria.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            search_criteria: Dict with search parameters
            worksheet_name: Source worksheet name
            
        Returns:
            List of (Product, row_number) tuples
            
        Example:
            search_criteria = {
                'seller_article': 'WB001',
                'wildberries_article': 12345678,
                'min_stock': 100,
                'warehouse_name': 'Москва'
            }
        """
        try:
            all_products = self.read_all_products(spreadsheet_id, worksheet_name)
            results = []
            
            for i, product in enumerate(all_products, start=2):  # Row numbers start from 2
                if self._matches_criteria(product, search_criteria):
                    results.append((product, i))
            
            logger.info(f"Found {len(results)} products matching criteria")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search products: {e}")
            raise SyncError(f"Product search failed: {e}")
    
    # UPDATE operations
    
    def update_product(self, spreadsheet_id: str, seller_article: str, 
                      updated_product: Product,
                      worksheet_name: str = "Stock Tracker") -> bool:
        """
        Update existing product record.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            seller_article: Seller article of product to update
            updated_product: New product data
            worksheet_name: Target worksheet name
            
        Returns:
            True if updated successfully, False if product not found
            
        Raises:
            SyncError: If update operation fails
        """
        try:
            worksheet = self.get_or_create_worksheet(spreadsheet_id, worksheet_name)
            
            # Find product row
            row_number = self._find_product_row(worksheet, seller_article)
            if row_number is None:
                logger.warning(f"Product not found for update: {seller_article}")
                return False
            
            # Format updated data
            row_data = self.formatter.format_product_for_sheets(updated_product)
            
            # Update row
            range_name = f"A{row_number}:H{row_number}"
            worksheet.update(range_name, [row_data])
            
            logger.info(f"Updated product {seller_article} at row {row_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update product {seller_article}: {e}")
            raise SyncError(f"Product update failed: {e}")
    
    def update_products_batch(self, spreadsheet_id: str, 
                            updates: List[Tuple[str, Product]],
                            worksheet_name: str = "Stock Tracker") -> int:
        """
        Update multiple products in batch.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            updates: List of (seller_article, updated_product) tuples
            worksheet_name: Target worksheet name
            
        Returns:
            Number of products successfully updated
            
        Raises:
            SyncError: If batch update fails
        """
        try:
            worksheet = self.get_or_create_worksheet(spreadsheet_id, worksheet_name)
            updated_count = 0
            
            for seller_article, updated_product in updates:
                try:
                    if self.update_product(spreadsheet_id, seller_article, 
                                         updated_product, worksheet_name):
                        updated_count += 1
                except Exception as e:
                    logger.warning(f"Failed to update product {seller_article}: {e}")
                    continue
            
            logger.info(f"Updated {updated_count}/{len(updates)} products in batch")
            return updated_count
            
        except Exception as e:
            logger.error(f"Failed to update products batch: {e}")
            raise SyncError(f"Batch update failed: {e}")
    
    # DELETE operations
    
    def delete_product(self, spreadsheet_id: str, seller_article: str,
                      worksheet_name: str = "Stock Tracker") -> bool:
        """
        Delete product record.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            seller_article: Seller article of product to delete
            worksheet_name: Target worksheet name
            
        Returns:
            True if deleted successfully, False if product not found
            
        Raises:
            SyncError: If delete operation fails
        """
        try:
            worksheet = self.get_or_create_worksheet(spreadsheet_id, worksheet_name)
            
            # Find product row
            row_number = self._find_product_row(worksheet, seller_article)
            if row_number is None:
                logger.warning(f"Product not found for deletion: {seller_article}")
                return False
            
            # Delete row
            worksheet.delete_rows(row_number)
            
            logger.info(f"Deleted product {seller_article} from row {row_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete product {seller_article}: {e}")
            raise SyncError(f"Product deletion failed: {e}")
    
    def clear_all_products(self, spreadsheet_id: str,
                          worksheet_name: str = "Stock Tracker") -> int:
        """
        Clear all product data (keep headers).
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            worksheet_name: Target worksheet name
            
        Returns:
            Number of products cleared
            
        Raises:
            SyncError: If clear operation fails
        """
        try:
            worksheet = self.get_or_create_worksheet(spreadsheet_id, worksheet_name)
            
            # Count existing products
            all_data = worksheet.get_all_values()
            product_count = max(0, len(all_data) - 1)  # Exclude header
            
            if product_count == 0:
                logger.info("No products to clear")
                return 0
            
            # ИСПРАВЛЕНО 28.10.2025: Удаляем строки вместо очистки содержимого
            # batch_clear оставляет пустые строки, что приводит к записи данных 
            # с неправильной позиции (например строка 36 вместо строки 2)
            if len(all_data) > 1:
                # Удаляем все строки с данными (строки 2 и далее)
                # delete_rows удаляет строки физически, а не просто очищает
                num_rows_to_delete = len(all_data) - 1  # Все кроме заголовка
                worksheet.delete_rows(2, num_rows_to_delete + 1)  # delete_rows(start, end)
            
            logger.info(f"Cleared {product_count} products (deleted rows 2-{len(all_data)})")
            return product_count
            
        except Exception as e:
            logger.error(f"Failed to clear products: {e}")
            raise SyncError(f"Product clear failed: {e}")
    
    def create_or_update_product(self, spreadsheet_id: str, product: Product,
                                worksheet_name: str = "Stock Tracker",
                                skip_existence_check: bool = False) -> bool:
        """
        Create a new product or update existing one.
        
        If product exists (by seller_article), updates it.
        If product doesn't exist, creates new one.
        
        Args:
            spreadsheet_id: Google Spreadsheet ID
            product: Product data to create/update
            worksheet_name: Worksheet name (default: "Stock Tracker")
            skip_existence_check: Skip existence check and directly create product.
                                 Useful after clear_all_products() to avoid unnecessary API calls.
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # If skip_existence_check is True, directly create the product
            if skip_existence_check:
                logger.debug(f"Creating product (skipping existence check): {product.seller_article}")
                return self.create_product(
                    spreadsheet_id=spreadsheet_id,
                    product=product,
                    worksheet_name=worksheet_name
                )
            
            # Try to read existing product
            existing_product = self.read_product(spreadsheet_id, product.seller_article, worksheet_name)
            
            if existing_product:
                # Product exists - update it
                logger.debug(f"Updating existing product: {product.seller_article}")
                return self.update_product(
                    spreadsheet_id=spreadsheet_id,
                    seller_article=product.seller_article,
                    updated_product=product,
                    worksheet_name=worksheet_name
                )
            else:
                # Product doesn't exist - create it
                logger.debug(f"Creating new product: {product.seller_article}")
                return self.create_product(
                    spreadsheet_id=spreadsheet_id,
                    product=product,
                    worksheet_name=worksheet_name
                )
                
        except Exception as e:
            logger.error(f"Failed to create/update product {product.seller_article}: {e}")
            return False
    
    # Warehouse synchronization methods for User Story 2
    
    def synchronize_warehouse_data_ordering(self, spreadsheet_id: str, 
                                          seller_article: str,
                                          reference_order: Optional[List[str]] = None,
                                          worksheet_name: str = "Stock Tracker") -> bool:
        """
        Synchronize warehouse data ordering for columns F, G, H.
        
        Ensures that warehouse names (F), orders (G), and stock (H) maintain
        consistent ordering as required by User Story 2.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            seller_article: Product to synchronize
            reference_order: Desired warehouse order (None for alphabetical)
            worksheet_name: Target worksheet name
            
        Returns:
            True if synchronized successfully, False if product not found
            
        Raises:
            SyncError: If synchronization fails
        """
        try:
            logger.debug(f"Synchronizing warehouse data for {seller_article}")
            
            # Read current product
            product = self.read_product(spreadsheet_id, seller_article, worksheet_name)
            if not product:
                logger.warning(f"Product not found for synchronization: {seller_article}")
                return False
            
            if not product.warehouses:
                logger.debug(f"No warehouses to synchronize for {seller_article}")
                return True
            
            # Apply synchronization using reference order
            from stock_tracker.api.warehouses import WarehouseSynchronizer
            synchronizer = WarehouseSynchronizer()
            
            synchronized_product = synchronizer.synchronize_product_warehouses(
                product, reference_order
            )
            
            # Update the product in sheets
            success = self.update_product(spreadsheet_id, seller_article, synchronized_product, worksheet_name)
            
            if success:
                logger.info(f"Synchronized warehouse data for {seller_article}")
            else:
                logger.error(f"Failed to update synchronized data for {seller_article}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to synchronize warehouse data for {seller_article}: {e}")
            raise SyncError(f"Warehouse synchronization failed: {e}")
    
    def synchronize_all_warehouse_data(self, spreadsheet_id: str,
                                     global_reference_order: Optional[List[str]] = None,
                                     worksheet_name: str = "Stock Tracker") -> Dict[str, Any]:
        """
        Synchronize warehouse data ordering for all products.
        
        Ensures consistent warehouse ordering across all products in the sheet.
        This is particularly useful for maintaining data integrity across
        columns F, G, H for User Story 2.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            global_reference_order: Global warehouse order to apply to all products
            worksheet_name: Target worksheet name
            
        Returns:
            Dict with synchronization results
            
        Raises:
            SyncError: If synchronization fails
        """
        try:
            logger.info("Starting global warehouse data synchronization")
            
            # Read all products
            products = self.read_all_products(spreadsheet_id, worksheet_name)
            if not products:
                logger.info("No products found for synchronization")
                return {
                    "synchronized_count": 0,
                    "failed_count": 0,
                    "total_products": 0,
                    "errors": []
                }
            
            # Determine reference order if not provided
            if global_reference_order is None:
                from stock_tracker.api.warehouses import WarehouseSynchronizer
                synchronizer = WarehouseSynchronizer()
                global_reference_order = synchronizer.get_consistent_warehouse_order(products)
                logger.info(f"Determined global warehouse order: {global_reference_order}")
            
            # Synchronize each product
            synchronized_count = 0
            failed_count = 0
            errors = []
            
            for product in products:
                try:
                    success = self.synchronize_warehouse_data_ordering(
                        spreadsheet_id, 
                        product.seller_article, 
                        global_reference_order,
                        worksheet_name
                    )
                    
                    if success:
                        synchronized_count += 1
                    else:
                        failed_count += 1
                        errors.append(f"Failed to synchronize {product.seller_article}")
                        
                except Exception as e:
                    failed_count += 1
                    error_msg = f"Error synchronizing {product.seller_article}: {e}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
            
            result = {
                "synchronized_count": synchronized_count,
                "failed_count": failed_count,
                "total_products": len(products),
                "errors": errors,
                "global_reference_order": global_reference_order
            }
            
            logger.info(f"Global synchronization completed: {synchronized_count}/{len(products)} products synchronized")
            return result
            
        except Exception as e:
            logger.error(f"Failed to synchronize all warehouse data: {e}")
            raise SyncError(f"Global warehouse synchronization failed: {e}")
    
    def validate_warehouse_data_consistency(self, spreadsheet_id: str,
                                          worksheet_name: str = "Stock Tracker") -> Dict[str, Any]:
        """
        Validate consistency of warehouse data across all products.
        
        Checks for synchronization issues in columns F, G, H across all products
        and provides detailed validation report for User Story 2.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            worksheet_name: Target worksheet name
            
        Returns:
            Dict with validation results
        """
        try:
            logger.debug("Validating warehouse data consistency")
            
            worksheet = self.get_or_create_worksheet(spreadsheet_id, worksheet_name)
            all_data = worksheet.get_all_values()
            
            if len(all_data) <= 1:
                return {
                    "valid": True,
                    "products_checked": 0,
                    "consistency_issues": [],
                    "warnings": ["No products found to validate"]
                }
            
            validation_results = {
                "valid": True,
                "products_checked": 0,
                "consistency_issues": [],
                "warnings": [],
                "warehouse_orders": {}
            }
            
            # Check each product row
            for row_idx, row_data in enumerate(all_data[1:], start=2):  # Skip header
                if len(row_data) < 8:
                    continue
                
                seller_article = row_data[0] if row_data[0] else f"Row {row_idx}"
                validation_results["products_checked"] += 1
                
                # Validate warehouse data columns F, G, H
                names_cell = row_data[5] if len(row_data) > 5 else ""
                orders_cell = row_data[6] if len(row_data) > 6 else ""
                stock_cell = row_data[7] if len(row_data) > 7 else ""
                
                # Use formatter to validate data integrity
                cell_validation = self.formatter.validate_synchronized_data_integrity(
                    names_cell, orders_cell, stock_cell
                )
                
                if not cell_validation["valid"]:
                    validation_results["valid"] = False
                    for error in cell_validation["errors"]:
                        validation_results["consistency_issues"].append(
                            f"{seller_article} (row {row_idx}): {error}"
                        )
                
                for warning in cell_validation["warnings"]:
                    validation_results["warnings"].append(
                        f"{seller_article} (row {row_idx}): {warning}"
                    )
                
                # Track warehouse ordering patterns
                if names_cell:
                    warehouse_names = [name.strip() for name in names_cell.split('\n') if name.strip()]
                    validation_results["warehouse_orders"][seller_article] = warehouse_names
            
            # Check for consistent ordering across products
            all_warehouse_orders = list(validation_results["warehouse_orders"].values())
            if all_warehouse_orders:
                # Find products with inconsistent warehouse ordering
                from collections import Counter
                order_patterns = []
                for order in all_warehouse_orders:
                    if len(order) > 1:
                        order_patterns.append(tuple(order))
                
                if order_patterns:
                    pattern_counts = Counter(order_patterns)
                    if len(pattern_counts) > 1:
                        validation_results["warnings"].append(
                            f"Inconsistent warehouse ordering patterns found: {len(pattern_counts)} different patterns"
                        )
            
            logger.info(f"Validated {validation_results['products_checked']} products, "
                       f"valid: {validation_results['valid']}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Failed to validate warehouse data consistency: {e}")
            return {
                "valid": False,
                "error": str(e),
                "products_checked": 0,
                "consistency_issues": [f"Validation failed: {e}"],
                "warnings": []
            }
    
    # Helper methods
    
    def _find_product_row(self, worksheet: gspread.Worksheet, 
                         seller_article: str) -> Optional[int]:
        """
        Find row number for product by seller article.
        
        Args:
            worksheet: Worksheet to search
            seller_article: Seller article to find
            
        Returns:
            Row number or None if not found
        """
        try:
            # Get all seller articles (column A)
            seller_articles = worksheet.col_values(1)
            
            # Search for match (case-insensitive)
            for i, article in enumerate(seller_articles):
                if article.strip().lower() == seller_article.strip().lower():
                    return i + 1  # Convert to 1-based row number
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to find product row: {e}")
            return None
    
    def _find_next_empty_row(self, worksheet: gspread.Worksheet) -> int:
        """
        Find next empty row for insertion.
        
        Args:
            worksheet: Worksheet to check
            
        Returns:
            Next available row number
        """
        try:
            # Get all data to find last used row
            all_data = worksheet.get_all_values()
            return len(all_data) + 1
            
        except Exception:
            # Fallback: assume row 2 if data fetch fails
            return 2
    
    def _get_all_seller_articles(self, worksheet: gspread.Worksheet) -> set:
        """
        Get set of all existing seller articles.
        
        Args:
            worksheet: Worksheet to read
            
        Returns:
            Set of seller articles
        """
        try:
            seller_articles = worksheet.col_values(1)
            # Skip header and filter empty values
            return {article.strip() for article in seller_articles[1:] if article.strip()}
            
        except Exception:
            return set()
    
    def _matches_criteria(self, product: Product, criteria: Dict[str, Any]) -> bool:
        """
        Check if product matches search criteria.
        
        Args:
            product: Product to check
            criteria: Search criteria dict
            
        Returns:
            True if product matches all criteria
        """
        try:
            for key, value in criteria.items():
                if key == "seller_article":
                    if product.seller_article.lower() != str(value).lower():
                        return False
                elif key == "wildberries_article":
                    if product.wildberries_article != int(value):
                        return False
                elif key == "min_stock":
                    if product.total_stock < int(value):
                        return False
                elif key == "max_stock":
                    if product.total_stock > int(value):
                        return False
                elif key == "min_orders":
                    if product.total_orders < int(value):
                        return False
                elif key == "warehouse_name":
                    warehouse_names = [w.name.lower() for w in product.warehouses]
                    if str(value).lower() not in warehouse_names:
                        return False
                elif key == "min_turnover":
                    if product.turnover < float(value):
                        return False
                # Add more criteria as needed
            
            return True
            
        except Exception:
            return False
    
    def get_sync_status(self, spreadsheet_id: str, 
                       worksheet_name: str = "Stock Tracker") -> Dict[str, Any]:
        """
        Get sync status and statistics.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            worksheet_name: Target worksheet name
            
        Returns:
            Dict with sync status information
        """
        try:
            products = self.read_all_products(spreadsheet_id, worksheet_name)
            
            total_stock = sum(p.total_stock for p in products)
            total_orders = sum(p.total_orders for p in products)
            avg_turnover = sum(p.turnover for p in products) / len(products) if products else 0
            
            return {
                "products_count": len(products),
                "total_stock": total_stock,
                "total_orders": total_orders,
                "avg_turnover": round(avg_turnover, 3),
                "last_check": datetime.now().isoformat(),
                "status": "healthy"
            }
            
        except Exception as e:
            logger.error(f"Failed to get sync status: {e}")
            return {
                "products_count": 0,
                "status": "error",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }
    
    # ========== PERFORMANCE-OPTIMIZED BATCH OPERATIONS ==========
    
    async def batch_read_products_optimized(self, spreadsheet_id: str,
                                          worksheet_name: str = "Stock Tracker",
                                          chunk_size: int = 500) -> List[Product]:
        """
        High-performance batch reading of all products using optimized range operations.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            worksheet_name: Target worksheet name
            chunk_size: Number of rows to read per batch
            
        Returns:
            List of Product objects
        """
        try:
            worksheet = self.get_or_create_worksheet(spreadsheet_id, worksheet_name)
            
            # Get total row count
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:  # Only header or empty
                return []
            
            total_rows = len(all_values)
            logger.info(f"Optimized batch reading {total_rows-1} products in chunks of {chunk_size}")
            
            # Create range batches for optimal API usage
            ranges = []
            for start_row in range(2, total_rows + 1, chunk_size):
                end_row = min(start_row + chunk_size - 1, total_rows)
                range_name = f"{worksheet_name}!A{start_row}:H{end_row}"
                ranges.append(range_name)
            
            # Use optimized batch reading
            range_data = await self.optimizer.batch_read_ranges(
                spreadsheet_id, ranges, self.sheets_client
            )
            
            # Process all data
            products = []
            processed_rows = 0
            
            for range_name, values in range_data.items():
                for row in values:
                    try:
                        product = self.formatter.row_to_product(row)
                        products.append(product)
                        processed_rows += 1
                    except Exception as e:
                        logger.warning(f"Failed to parse row: {e}")
                        continue
            
            # Record performance metrics
            self.monitoring.record_metric(
                "database.batch_read_completed",
                1,
                {
                    "products_count": len(products),
                    "total_rows": total_rows - 1,
                    "success_rate": len(products) / max(1, total_rows - 1),
                    "batch_count": len(ranges)
                }
            )
            
            logger.info(f"Batch read completed: {len(products)} products processed from {processed_rows} rows")
            return products
            
        except Exception as e:
            logger.error(f"Optimized batch read failed: {e}")
            self.monitoring.record_metric("database.batch_read_failed", 1, {"error": str(e)})
            raise SyncError(f"Batch read operation failed: {e}")
    
    async def batch_write_products_optimized(self, products: List[Product],
                                           spreadsheet_id: str,
                                           worksheet_name: str = "Stock Tracker",
                                           mode: str = "append") -> bool:
        """
        High-performance batch writing of products using optimized range operations.
        
        Args:
            products: List of products to write
            spreadsheet_id: Google Sheets spreadsheet ID
            worksheet_name: Target worksheet name
            mode: Write mode - "append", "replace", or "update"
            
        Returns:
            True if successful
        """
        if not products:
            return True
        
        try:
            worksheet = self.get_or_create_worksheet(spreadsheet_id, worksheet_name)
            logger.info(f"Optimized batch writing {len(products)} products (mode: {mode})")
            
            # Prepare data for batch writing
            if mode == "replace":
                # Clear existing data (keep headers)
                worksheet.clear()
                self._initialize_worksheet_structure(worksheet)
                start_row = 2
            elif mode == "append":
                start_row = self._find_next_empty_row(worksheet)
            else:  # update mode
                # This would require more complex logic to match existing rows
                # For now, use append behavior
                start_row = self._find_next_empty_row(worksheet)
            
            # Prepare range data
            range_data = {}
            
            # Format all products to rows
            rows_data = []
            for product in products:
                try:
                    row = self.formatter.product_to_row(product)
                    rows_data.append(row)
                except Exception as e:
                    logger.warning(f"Failed to format product {product.seller_article}: {e}")
                    continue
            
            if not rows_data:
                logger.warning("No valid product data to write")
                return False
            
            # Create batch ranges for optimal performance
            batch_size = 100  # Optimal for Sheets API
            
            for i in range(0, len(rows_data), batch_size):
                batch_rows = rows_data[i:i + batch_size]
                batch_start_row = start_row + i
                batch_end_row = batch_start_row + len(batch_rows) - 1
                
                range_name = f"{worksheet_name}!A{batch_start_row}:H{batch_end_row}"
                range_data[range_name] = batch_rows
            
            # Execute optimized batch write
            success = await self.optimizer.batch_write_ranges(
                spreadsheet_id, range_data, self.sheets_client
            )
            
            if success:
                # Record performance metrics
                self.monitoring.record_metric(
                    "database.batch_write_completed",
                    1,
                    {
                        "products_count": len(products),
                        "rows_written": len(rows_data),
                        "mode": mode,
                        "batch_count": len(range_data)
                    }
                )
                
                logger.info(f"Batch write completed: {len(rows_data)} rows written")
                return True
            else:
                logger.error("Batch write operation failed")
                self.monitoring.record_metric("database.batch_write_failed", 1, {"mode": mode})
                return False
        
        except Exception as e:
            logger.error(f"Optimized batch write failed: {e}")
            self.monitoring.record_metric("database.batch_write_failed", 1, {"error": str(e)})
            raise SyncError(f"Batch write operation failed: {e}")
    
    async def batch_update_products_optimized(self, products: List[Product],
                                            spreadsheet_id: str,
                                            worksheet_name: str = "Stock Tracker") -> Dict[str, int]:
        """
        High-performance batch updating of existing products.
        
        Args:
            products: List of products to update
            spreadsheet_id: Google Sheets spreadsheet ID
            worksheet_name: Target worksheet name
            
        Returns:
            Dict with update statistics
        """
        if not products:
            return {"updated": 0, "not_found": 0, "errors": 0}
        
        try:
            # First, read all existing products to build index
            existing_products = await self.batch_read_products_optimized(
                spreadsheet_id, worksheet_name
            )
            
            # Build index by seller_article for fast lookup
            existing_index = {
                product.seller_article: i + 2  # +2 for header and 1-based indexing
                for i, product in enumerate(existing_products)
            }
            
            logger.info(f"Built index for {len(existing_index)} existing products")
            
            # Prepare updates
            range_data = {}
            stats = {"updated": 0, "not_found": 0, "errors": 0}
            
            for product in products:
                try:
                    if product.seller_article in existing_index:
                        row_number = existing_index[product.seller_article]
                        row_data = self.formatter.product_to_row(product)
                        
                        range_name = f"{worksheet_name}!A{row_number}:H{row_number}"
                        range_data[range_name] = [row_data]
                        
                        stats["updated"] += 1
                    else:
                        stats["not_found"] += 1
                        logger.debug(f"Product not found for update: {product.seller_article}")
                
                except Exception as e:
                    stats["errors"] += 1
                    logger.warning(f"Failed to prepare update for {product.seller_article}: {e}")
            
            # Execute batch update if there are changes
            if range_data:
                success = await self.optimizer.batch_write_ranges(
                    spreadsheet_id, range_data, self.sheets_client
                )
                
                if not success:
                    logger.error("Batch update operation failed")
                    stats["errors"] += stats["updated"]
                    stats["updated"] = 0
            
            # Record performance metrics
            self.monitoring.record_metric(
                "database.batch_update_completed",
                1,
                {
                    "total_products": len(products),
                    "updated": stats["updated"],
                    "not_found": stats["not_found"],
                    "errors": stats["errors"],
                    "success_rate": stats["updated"] / max(1, len(products))
                }
            )
            
            logger.info(f"Batch update completed: {stats}")
            return stats
        
        except Exception as e:
            logger.error(f"Optimized batch update failed: {e}")
            self.monitoring.record_metric("database.batch_update_failed", 1, {"error": str(e)})
            raise SyncError(f"Batch update operation failed: {e}")
    
    def refresh_table_data(self, spreadsheet_id: str, 
                          worksheet_name: str = "Stock Tracker",
                          clear_existing: bool = True) -> Dict[str, Any]:
        """
        Обновить таблицу свежими данными из Wildberries API.
        
        Получает актуальные данные о товарах и остатках со складов Wildberries
        и обновляет Google Sheets таблицу. Может использоваться при запуске
        для обновления всех данных.
        
        Args:
            spreadsheet_id: ID Google Sheets документа
            worksheet_name: Название листа для обновления
            clear_existing: Очистить существующие данные перед обновлением
            
        Returns:
            Dict с результатами обновления
            
        Raises:
            SyncError: Если обновление не удалось
        """
        try:
            logger.info(f"Starting table data refresh for worksheet '{worksheet_name}'")
            
            # Импортируем здесь чтобы избежать циклических импортов
            from stock_tracker.services.product_service import ProductService
            from stock_tracker.api.client import WildberriesAPIClient
            from stock_tracker.utils.config import get_config
            from datetime import datetime, timedelta
            
            # Инициализируем сервисы
            config = get_config()
            product_service = ProductService(config)
            wb_client = product_service.wb_client
            
            # Получаем worksheet
            worksheet = self.get_or_create_worksheet(spreadsheet_id, worksheet_name)
            
            # Очищаем существующие данные если требуется
            if clear_existing:
                logger.info("Clearing existing data...")
                self.clear_all_products(spreadsheet_id, worksheet_name)
            
            # Запускаем синхронизацию с API
            logger.info("🏭 Fetching fresh data from Wildberries API with intelligent warehouse system...")
            
            # Получаем все данные о продуктах через Analytics API v2
            import asyncio
            import threading
            import concurrent.futures
            
            def run_async_api_call():
                """Запуск асинхронного API вызова в отдельном потоке."""
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(wb_client.get_all_product_stock_data())
                finally:
                    new_loop.close()
            
            # Запускаем в отдельном потоке
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async_api_call)
                all_stock_data = future.result(timeout=300)  # 5 минут таймаут
            logger.info(f"Downloaded {len(all_stock_data)} products from Analytics API v2")
            
            # 🏭 НОВАЯ ПРИОРИТЕТНАЯ СИСТЕМА СКЛАДОВ согласно WAREHOUSE_IMPROVEMENT_PROMPT.md
            logger.info("🏭 Starting intelligent warehouse data processing...")
            
            from stock_tracker.utils.warehouse_cache import get_warehouse_cache, cache_real_warehouses
            from stock_tracker.core.calculator import WildberriesCalculator
            
            warehouse_cache_entry = None
            products = None
            
            # ПРИОРИТЕТ 1: Попытка получить реальные данные по складам через Warehouse API v1
            logger.info("📦 PRIORITY 1: Attempting to get real warehouse data from Warehouse API v1...")
            
            def run_warehouse_api_call():
                """Запуск получения данных по складам в отдельном потоке."""
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(wb_client.get_warehouse_remains_with_retry(max_wait_time=900))
                finally:
                    new_loop.close()
            
            # Запускаем в отдельном потоке
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_warehouse_api_call)
                try:
                    warehouse_data = future.result(timeout=900)  # 15 минут таймаут для warehouse API
                    logger.info(f"✅ SUCCESS: Downloaded {len(warehouse_data)} warehouse records from API v1")
                    
                    # Кэшируем реальные названия складов
                    real_warehouses = cache_real_warehouses(warehouse_data, source="warehouse_api")
                    if real_warehouses:
                        logger.info(f"✅ Cached {len(real_warehouses)} real warehouse names")
                        warehouse_cache_entry = get_warehouse_cache().get_warehouses(prefer_source="warehouse_api")
                    
                    # Обрабатываем комбинированные данные (ПРИОРИТЕТ 1: реальные склады)
                    products = WildberriesCalculator.process_combined_api_data(all_stock_data, warehouse_data)
                    logger.info(f"✅ PRIORITY 1 SUCCESS: Processed {len(products)} products with REAL warehouse data")
                    
                except Exception as warehouse_error:
                    logger.warning(f"⚠️ PRIORITY 1 FAILED: Warehouse API v1 error: {warehouse_error}")
                    
                    # ПРИОРИТЕТ 2: ТОЛЬКО реальные кэшированные данные из Warehouse API v1
                    logger.info("📊 PRIORITY 2: Checking for REAL cached warehouse data from API v1...")
                    
                    cache = get_warehouse_cache()
                    warehouse_cache_entry = cache.get_warehouses(prefer_source="warehouse_api")
                    
                    if warehouse_cache_entry and warehouse_cache_entry.source == "warehouse_api":
                        logger.info(f"✅ Found REAL warehouse data from API v1 cache "
                                   f"(age: {warehouse_cache_entry.age_hours():.1f}h)")
                        products = WildberriesCalculator.process_analytics_v2_data(all_stock_data, warehouse_cache_entry)
                        logger.info(f"✅ PRIORITY 2 SUCCESS: Processed {len(products)} products with REAL warehouse data")
                    else:
                        # NO FAKE DATA! Show totals only when real data unavailable
                        logger.warning("⚠️ PRIORITY 2 FAILED: No REAL warehouse data available")
                        logger.info("� SHOWING TOTALS ONLY: Analytics API v2 data without warehouse breakdown...")
                        
                        products = WildberriesCalculator.process_analytics_v2_data(all_stock_data, None)
                        logger.warning(f"⚠️ LIMITED DATA: Processed {len(products)} products with totals only (no warehouse details)")
            
            # Логирование качества данных по складам
            if warehouse_cache_entry and warehouse_cache_entry.source == "warehouse_api":
                data_quality = "REAL WAREHOUSE DATA"
                warehouse_count = len(warehouse_cache_entry.warehouse_names)
                cache_age = warehouse_cache_entry.age_hours()
                logger.info(f"📊 Final Data Quality: {data_quality} ({warehouse_count} warehouses, age: {cache_age:.1f}h)")
            else:
                logger.warning("⚠️ Final Data Quality: TOTALS ONLY (Warehouse API v1 required for detailed breakdown)")
                
            if not products:
                raise DatabaseError("Failed to process any data through available sources")
            
            # Записываем продукты в таблицу батчами
            if products:
                created_rows = self.create_products_batch(
                    spreadsheet_id, 
                    products, 
                    worksheet_name
                )
                
                logger.info(f"Successfully updated table with {len(products)} products")
                
                # Подготавливаем статистику
                total_stock = sum(p.total_stock for p in products)
                total_orders = sum(p.total_orders for p in products)
                avg_turnover = sum(p.turnover for p in products) / len(products) if products else 0
                
                result = {
                    "success": True,
                    "products_updated": len(products),
                    "rows_created": len(created_rows),
                    "total_stock": total_stock,
                    "total_orders": total_orders,
                    "avg_turnover": round(avg_turnover, 3),
                    "warehouses_found": len(set(
                        wh.name for product in products for wh in product.warehouses
                    )),
                    "update_time": datetime.now().isoformat(),
                    "cleared_existing": clear_existing
                }
                
                logger.info(f"Table refresh completed successfully: {result}")
                return result
            
            else:
                logger.warning("No products received from API")
                return {
                    "success": False,
                    "error": "No products received from API",
                    "products_updated": 0,
                    "update_time": datetime.now().isoformat()
                }
        
        except Exception as e:
            logger.error(f"Failed to refresh table data: {e}")
            return {
                "success": False,
                "error": str(e),
                "products_updated": 0,
                "update_time": datetime.now().isoformat()
            }
    
    def update_table_on_startup(self, spreadsheet_id: str,
                               worksheet_name: str = "Stock Tracker") -> bool:
        """
        Обновить таблицу при запуске приложения.
        
        Удобная функция для обновления данных при старте приложения.
        Автоматически очищает старые данные и загружает свежие.
        
        Args:
            spreadsheet_id: ID Google Sheets документа
            worksheet_name: Название листа
            
        Returns:
            True если обновление прошло успешно, False иначе
        """
        try:
            logger.info("Starting table update on application startup")
            
            result = self.refresh_table_data(
                spreadsheet_id=spreadsheet_id,
                worksheet_name=worksheet_name,
                clear_existing=True
            )
            
            if result.get("success", False):
                logger.info(f"Startup table update completed: {result['products_updated']} products updated")
                return True
            else:
                logger.error(f"Startup table update failed: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update table on startup: {e}")
            return False
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive performance summary for database operations.
        
        Returns:
            Performance metrics and optimization statistics
        """
        try:
            # Get optimizer performance
            optimizer_stats = self.optimizer.get_optimization_summary()
            
            # Add database-specific metrics
            summary = {
                "optimization": optimizer_stats,
                "database_metrics": {
                    "client_type": "google_sheets",
                    "formatter_active": self.formatter is not None,
                    "structure_version": self.structure.version if hasattr(self.structure, 'version') else "1.0"
                },
                "last_updated": datetime.now().isoformat()
            }
            
            return summary
        
        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {
                "error": str(e),
                "last_updated": datetime.now().isoformat()
            }


if __name__ == "__main__":
    # Test CRUD operations
    print("Testing CRUD operations...")
    
    # This would require actual Google Sheets credentials and spreadsheet
    # For testing, we'll just validate the class structure
    
    from stock_tracker.database.sheets import GoogleSheetsClient
    from stock_tracker.core.models import Product, Warehouse
    
    # Mock testing (would need real credentials for actual testing)
    try:
        # sheets_client = GoogleSheetsClient("path/to/service_account.json")
        # operations = SheetsOperations(sheets_client)
        
        # Create test product
        product = Product(seller_article="TEST001", wildberries_article=87654321)
        warehouse = Warehouse(name="Тест склад", orders=10, stock=50)
        product.add_warehouse(warehouse)
        
        print(f"✅ Created test product: {product.seller_article}")
        print(f"   Warehouses: {len(product.warehouses)}")
        print(f"   Total stock: {product.total_stock}")
        
    except Exception as e:
        print(f"Note: Full testing requires Google Sheets credentials: {e}")
    
    print("CRUD operations tests completed!")

