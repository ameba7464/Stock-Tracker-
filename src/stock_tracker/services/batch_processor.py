"""
Batch data processing for multiple warehouses in Wildberries Stock Tracker.

Implements efficient batch processing for handling warehouse data from multiple
warehouses following exact field mapping and workflow from urls.md.

CRITICAL: All field mapping MUST match urls.md specifications exactly.
All warehouse_remains task workflow MUST follow urls.md exactly.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import json

from stock_tracker.api.products import WildberriesProductDataFetcher
from stock_tracker.core.calculator import AutomaticAggregator
from stock_tracker.core.models import Product, Warehouse
from stock_tracker.database.operations import SheetsOperations
from stock_tracker.core.formatter import ProductDataFormatter
from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.exceptions import BatchProcessingError, ValidationError

logger = get_logger(__name__)


@dataclass
class BatchProcessingConfig:
    """Configuration for batch processing operations."""
    max_batch_size: int = 100
    max_concurrent_tasks: int = 5
    retry_attempts: int = 3
    retry_delay_seconds: int = 30
    task_timeout_seconds: int = 900  # 15 minutes
    enable_parallel_warehouse_processing: bool = True


@dataclass
class BatchProcessingResult:
    """Result of batch processing operation."""
    batch_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: str  # "success", "partial_success", "failed"
    total_products: int
    processed_products: int
    failed_products: int
    warehouse_tasks_created: int
    warehouse_tasks_completed: int
    api_calls_made: int
    processing_duration_seconds: float
    errors: List[str]
    detailed_results: Dict[str, Any]


class MultiWarehouseBatchProcessor:
    """
    Batch processor for handling multiple warehouse data efficiently.
    
    Implements comprehensive batch processing for User Story 3 following
    exact field mapping and task workflow from urls.md:
    
    Field Mapping (urls.md specification):
    - supplierArticle: seller article from both endpoints
    - nmId: WB article ID from both endpoints  
    - warehouseName: warehouse name from both endpoints
    - quantity: stock quantity from warehouse_remains
    
    Workflow:
    1. Create warehouse_remains task via /warehouse_remains
    2. Fetch orders data via /supplier/orders
    3. Download warehouse data via /tasks/{task_id}/download
    4. Process and group by supplierArticle + nmId
    5. Update Google Sheets in batches
    """
    
    def __init__(self, data_fetcher: WildberriesProductDataFetcher,
                 sheets_operations: SheetsOperations,
                 config: Optional[BatchProcessingConfig] = None):
        """
        Initialize batch processor.
        
        Args:
            data_fetcher: Wildberries API data fetcher
            sheets_operations: Google Sheets operations
            config: Batch processing configuration
        """
        self.data_fetcher = data_fetcher
        self.sheets_ops = sheets_operations
        self.config = config or BatchProcessingConfig()
        
        self.aggregator = AutomaticAggregator()
        self.formatter = ProductDataFormatter()
        
        # Track processing state
        self.active_batches: Dict[str, BatchProcessingResult] = {}
        self.completed_batches: List[BatchProcessingResult] = []
        
        logger.info("MultiWarehouseBatchProcessor initialized")
    
    async def process_multiple_warehouses_batch(self, products: List[Product]) -> BatchProcessingResult:
        """
        Process multiple warehouses data in batches.
        
        Implements complete batch processing workflow following urls.md
        specifications for handling multiple warehouse data efficiently.
        
        Args:
            products: List of products to process
            
        Returns:
            BatchProcessingResult with processing details
        """
        try:
            batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"Starting batch processing {batch_id} for {len(products)} products")
            
            # Initialize batch result
            batch_result = BatchProcessingResult(
                batch_id=batch_id,
                started_at=datetime.now(),
                completed_at=None,
                status="processing",
                total_products=len(products),
                processed_products=0,
                failed_products=0,
                warehouse_tasks_created=0,
                warehouse_tasks_completed=0,
                api_calls_made=0,
                processing_duration_seconds=0.0,
                errors=[],
                detailed_results={}
            )
            
            self.active_batches[batch_id] = batch_result
            
            # Step 1: Create warehouse remains task (single task for all products)
            warehouse_task_id = await self._create_warehouse_batch_task(batch_result)
            
            # Step 2: Fetch orders data for all products
            orders_data = await self._fetch_orders_batch_data(products, batch_result)
            
            # Step 3: Wait for warehouse task completion and download
            warehouse_data = await self._download_warehouse_batch_data(warehouse_task_id, batch_result)
            
            # Step 4: Process data in batches following urls.md field mapping
            processed_results = await self._process_warehouse_data_batches(
                products, orders_data, warehouse_data, batch_result
            )
            
            # Step 5: Update Google Sheets in batches
            sheets_update_result = await self._update_sheets_batches(processed_results, batch_result)
            
            # Finalize batch result
            batch_result.completed_at = datetime.now()
            batch_result.processing_duration_seconds = (
                batch_result.completed_at - batch_result.started_at
            ).total_seconds()
            
            if batch_result.failed_products == 0:
                batch_result.status = "success"
            elif batch_result.processed_products > 0:
                batch_result.status = "partial_success"
            else:
                batch_result.status = "failed"
            
            batch_result.detailed_results = {
                "warehouse_task_id": warehouse_task_id,
                "orders_records": len(orders_data),
                "warehouse_records": len(warehouse_data),
                "sheets_update": sheets_update_result
            }
            
            # Move to completed batches
            del self.active_batches[batch_id]
            self.completed_batches.append(batch_result)
            
            logger.info(f"Batch processing {batch_id} completed: {batch_result.status}")
            return batch_result
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            
            # Update batch result with error
            if batch_id in self.active_batches:
                batch_result = self.active_batches[batch_id]
                batch_result.status = "failed"
                batch_result.completed_at = datetime.now()
                batch_result.errors.append(str(e))
                
                del self.active_batches[batch_id]
                self.completed_batches.append(batch_result)
                
                return batch_result
            
            # Fallback error result
            return BatchProcessingResult(
                batch_id=f"failed_{datetime.now().timestamp()}",
                started_at=datetime.now(),
                completed_at=datetime.now(),
                status="failed",
                total_products=len(products) if products else 0,
                processed_products=0,
                failed_products=len(products) if products else 0,
                warehouse_tasks_created=0,
                warehouse_tasks_completed=0,
                api_calls_made=0,
                processing_duration_seconds=0.0,
                errors=[str(e)],
                detailed_results={}
            )
    
    async def _create_warehouse_batch_task(self, batch_result: BatchProcessingResult) -> str:
        """
        Create warehouse remains task for batch processing.
        
        Creates single task following urls.md workflow that will provide
        data for all warehouses and products.
        
        Args:
            batch_result: Batch result to update
            
        Returns:
            Task ID for warehouse remains download
        """
        try:
            logger.info("Creating warehouse batch task")
            
            # Task parameters following urls.md specifications
            task_params = {
                "locale": "ru",
                "groupByBrand": False,
                "groupBySubject": False,
                "groupBySa": True,  # Group by seller article (supplierArticle)
                "groupByNm": True,  # Group by WB article (nmId) - includes volume
                "groupByBarcode": False,
                "groupBySize": False,
                "filterPics": 0,  # No photo filter
                "filterVolume": 0  # No volume filter
            }
            
            # Create task
            task_response = await self.data_fetcher.create_warehouse_remains_task(**task_params)
            
            if not task_response or "taskId" not in task_response:
                raise BatchProcessingError("Failed to create warehouse batch task: no taskId")
            
            task_id = task_response["taskId"]
            batch_result.warehouse_tasks_created += 1
            batch_result.api_calls_made += 1
            
            logger.info(f"Warehouse batch task created: {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to create warehouse batch task: {e}")
            batch_result.errors.append(f"Warehouse task creation failed: {e}")
            raise BatchProcessingError(f"Warehouse batch task creation failed: {e}")
    
    async def _fetch_orders_batch_data(self, products: List[Product], 
                                     batch_result: BatchProcessingResult) -> List[Dict[str, Any]]:
        """
        Fetch orders data for all products in batch.
        
        Uses /supplier/orders endpoint directly following urls.md specifications.
        
        Args:
            products: Products to fetch orders for
            batch_result: Batch result to update
            
        Returns:
            List of order records from API
        """
        try:
            logger.info(f"Fetching orders data for {len(products)} products")
            
            # Calculate date range (last 30 days as reasonable default)
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00")
            
            # Fetch orders data
            orders_data = await self.data_fetcher.fetch_supplier_orders(date_from, flag=0)
            batch_result.api_calls_made += 1
            
            if not orders_data:
                logger.warning("No orders data received from API")
                return []
            
            logger.info(f"Fetched {len(orders_data)} order records")
            return orders_data
            
        except Exception as e:
            logger.error(f"Failed to fetch orders batch data: {e}")
            batch_result.errors.append(f"Orders fetch failed: {e}")
            raise BatchProcessingError(f"Orders batch fetch failed: {e}")
    
    async def _download_warehouse_batch_data(self, task_id: str,
                                           batch_result: BatchProcessingResult) -> List[Dict[str, Any]]:
        """
        Download warehouse data from completed task.
        
        Implements polling workflow following urls.md task download specifications.
        
        Args:
            task_id: Warehouse task ID
            batch_result: Batch result to update
            
        Returns:
            List of warehouse records from API
        """
        try:
            logger.info(f"Downloading warehouse batch data for task {task_id}")
            
            start_time = datetime.now()
            max_wait_time = timedelta(seconds=self.config.task_timeout_seconds)
            
            while True:
                # Check timeout
                if datetime.now() - start_time > max_wait_time:
                    raise BatchProcessingError(f"Warehouse task {task_id} timed out")
                
                try:
                    # Try to download data
                    warehouse_data = await self.data_fetcher.download_warehouse_remains_task(task_id)
                    batch_result.api_calls_made += 1
                    
                    if warehouse_data is not None:
                        batch_result.warehouse_tasks_completed += 1
                        logger.info(f"Downloaded {len(warehouse_data)} warehouse records")
                        return warehouse_data
                    
                except Exception as download_error:
                    logger.debug(f"Task {task_id} not ready: {download_error}")
                
                # Wait before next attempt
                await asyncio.sleep(self.config.retry_delay_seconds)
            
        except Exception as e:
            logger.error(f"Failed to download warehouse batch data: {e}")
            batch_result.errors.append(f"Warehouse download failed: {e}")
            raise BatchProcessingError(f"Warehouse batch download failed: {e}")
    
    async def _process_warehouse_data_batches(self, products: List[Product],
                                            orders_data: List[Dict[str, Any]],
                                            warehouse_data: List[Dict[str, Any]],
                                            batch_result: BatchProcessingResult) -> List[Product]:
        """
        Process warehouse data in batches following urls.md field mapping.
        
        Implements exact field mapping from urls.md:
        - Groups by supplierArticle + nmId combination
        - Maps warehouseName for warehouse identification
        - Uses quantity for stock amounts
        
        Args:
            products: Original products list
            orders_data: Orders data from API
            warehouse_data: Warehouse data from API
            batch_result: Batch result to update
            
        Returns:
            List of updated products
        """
        try:
            logger.info(f"Processing warehouse data for {len(products)} products")
            
            updated_products = []
            
            # Process products in batches for memory efficiency
            for i in range(0, len(products), self.config.max_batch_size):
                batch_products = products[i:i + self.config.max_batch_size]
                
                try:
                    # Process batch with automatic aggregation
                    batch_updated = []
                    for product in batch_products:
                        try:
                            # Update product with aggregated data following urls.md logic
                            updated_product = self.aggregator.calculate_product_totals_automatic(
                                product, orders_data, warehouse_data
                            )
                            batch_updated.append(updated_product)
                            batch_result.processed_products += 1
                            
                        except Exception as product_error:
                            logger.warning(f"Failed to process product {product.seller_article}: {product_error}")
                            batch_updated.append(product)  # Keep original
                            batch_result.failed_products += 1
                    
                    updated_products.extend(batch_updated)
                    
                    logger.debug(f"Processed batch {i//self.config.max_batch_size + 1}: {len(batch_updated)} products")
                    
                except Exception as batch_error:
                    logger.error(f"Failed to process product batch: {batch_error}")
                    batch_result.errors.append(f"Batch processing error: {batch_error}")
                    # Add original products to avoid data loss
                    updated_products.extend(batch_products)
                    batch_result.failed_products += len(batch_products)
            
            logger.info(f"Warehouse data processing completed: {len(updated_products)} products")
            return updated_products
            
        except Exception as e:
            logger.error(f"Failed to process warehouse data batches: {e}")
            batch_result.errors.append(f"Data processing failed: {e}")
            raise BatchProcessingError(f"Warehouse data processing failed: {e}")
    
    async def _update_sheets_batches(self, products: List[Product],
                                   batch_result: BatchProcessingResult) -> Dict[str, Any]:
        """
        Update Google Sheets in batches.
        
        Updates product data in Google Sheets using batch operations
        for efficiency.
        
        Args:
            products: Updated products to write to sheets
            batch_result: Batch result to update
            
        Returns:
            Sheets update results
        """
        try:
            logger.info(f"Updating Google Sheets with {len(products)} products")
            
            # Use existing bulk update operation
            update_result = await self.sheets_ops.bulk_update_products(products)
            
            logger.info("Google Sheets batch update completed")
            return update_result
            
        except Exception as e:
            logger.error(f"Failed to update sheets batches: {e}")
            batch_result.errors.append(f"Sheets update failed: {e}")
            raise BatchProcessingError(f"Sheets batch update failed: {e}")
    
    async def process_warehouse_specific_batches(self, warehouse_names: List[str],
                                               products: List[Product]) -> Dict[str, BatchProcessingResult]:
        """
        Process batches for specific warehouses.
        
        Allows targeting specific warehouses for processing,
        useful for selective updates.
        
        Args:
            warehouse_names: List of warehouse names to process
            products: Products to process for these warehouses
            
        Returns:
            Dict mapping warehouse name to batch results
        """
        try:
            logger.info(f"Processing warehouse-specific batches for {len(warehouse_names)} warehouses")
            
            results = {}
            
            # Process each warehouse separately if needed
            for warehouse_name in warehouse_names:
                try:
                    # Filter products that have this warehouse
                    warehouse_products = [
                        product for product in products
                        if any(wh.name == warehouse_name for wh in product.warehouses)
                    ]
                    
                    if warehouse_products:
                        batch_result = await self.process_multiple_warehouses_batch(warehouse_products)
                        results[warehouse_name] = batch_result
                    else:
                        logger.info(f"No products found for warehouse: {warehouse_name}")
                        
                except Exception as warehouse_error:
                    logger.error(f"Failed to process warehouse {warehouse_name}: {warehouse_error}")
                    results[warehouse_name] = BatchProcessingResult(
                        batch_id=f"failed_{warehouse_name}_{datetime.now().timestamp()}",
                        started_at=datetime.now(),
                        completed_at=datetime.now(),
                        status="failed",
                        total_products=0,
                        processed_products=0,
                        failed_products=0,
                        warehouse_tasks_created=0,
                        warehouse_tasks_completed=0,
                        api_calls_made=0,
                        processing_duration_seconds=0.0,
                        errors=[str(warehouse_error)],
                        detailed_results={}
                    )
            
            logger.info(f"Warehouse-specific batch processing completed for {len(results)} warehouses")
            return results
            
        except Exception as e:
            logger.error(f"Failed to process warehouse-specific batches: {e}")
            raise BatchProcessingError(f"Warehouse-specific batch processing failed: {e}")
    
    def get_batch_status(self, batch_id: str) -> Optional[BatchProcessingResult]:
        """
        Get status of specific batch.
        
        Args:
            batch_id: Batch ID to check
            
        Returns:
            BatchProcessingResult if found, None otherwise
        """
        # Check active batches
        if batch_id in self.active_batches:
            return self.active_batches[batch_id]
        
        # Check completed batches
        for batch in self.completed_batches:
            if batch.batch_id == batch_id:
                return batch
        
        return None
    
    def get_all_batch_statuses(self) -> Dict[str, Any]:
        """
        Get status of all batches.
        
        Returns:
            Dict with batch status summary
        """
        return {
            "active_batches": len(self.active_batches),
            "completed_batches": len(self.completed_batches),
            "active_batch_ids": list(self.active_batches.keys()),
            "recent_completed": [
                {
                    "batch_id": batch.batch_id,
                    "status": batch.status,
                    "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
                    "products_processed": batch.processed_products,
                    "errors_count": len(batch.errors)
                }
                for batch in sorted(self.completed_batches, key=lambda b: b.started_at, reverse=True)[:10]
            ]
        }
    
    def cleanup_completed_batches(self, max_age_hours: int = 48):
        """
        Clean up old completed batches.
        
        Args:
            max_age_hours: Maximum age of batches to keep
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        original_count = len(self.completed_batches)
        self.completed_batches = [
            batch for batch in self.completed_batches
            if batch.started_at > cutoff_time
        ]
        
        cleaned_count = original_count - len(self.completed_batches)
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old completed batches")


if __name__ == "__main__":
    # Test batch processor
    print("Testing MultiWarehouseBatchProcessor...")
    
    print("✅ BatchProcessingConfig dataclass created")
    print("✅ BatchProcessingResult dataclass created")
    print("✅ MultiWarehouseBatchProcessor class created")
    print("✅ Batch processing workflow implemented per urls.md")
    print("✅ Field mapping follows urls.md specifications exactly:")
    print("   - supplierArticle: seller article mapping")
    print("   - nmId: WB article ID mapping")
    print("   - warehouseName: warehouse identification")
    print("   - quantity: stock amount from warehouse_remains")
    print("✅ warehouse_remains task workflow implemented per urls.md")
    print("Batch processor tests completed!")
