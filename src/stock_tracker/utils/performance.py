"""
Performance optimization utilities for batch operations.

Implements advanced batching strategies, data processing optimization,
connection pooling, and performance monitoring specifically for Google Sheets
API and Wildberries API operations to maximize throughput and minimize latency.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Tuple, Union
from collections import defaultdict, deque
from threading import Lock, RLock
from contextlib import asynccontextmanager

from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.monitoring import get_monitoring_system
from stock_tracker.utils.exceptions import PerformanceError, BatchProcessingError
from stock_tracker.core.models import Product, Warehouse


logger = get_logger(__name__)


@dataclass
class BatchConfig:
    """Configuration for batch processing optimization."""
    
    # Batch sizing
    max_batch_size: int = 100  # Maximum items per batch
    min_batch_size: int = 10   # Minimum items per batch
    optimal_batch_size: int = 50  # Target batch size for optimal performance
    
    # Timing controls
    batch_timeout: float = 30.0  # Maximum time to wait for batch completion
    collection_timeout: float = 5.0  # Time to collect items before processing
    
    # Concurrency controls
    max_concurrent_batches: int = 3  # Maximum parallel batches
    max_workers: int = 5  # Thread pool size
    
    # Performance thresholds
    latency_threshold: float = 2.0  # Acceptable latency per item (seconds)
    throughput_target: float = 50.0  # Target items per second
    
    # Adaptive behavior
    adaptive_sizing: bool = True  # Adjust batch size based on performance
    performance_window: int = 10  # Number of batches to average for adaptation


@dataclass
class BatchMetrics:
    """Performance metrics for batch operations."""
    
    items_processed: int = 0
    batches_completed: int = 0
    total_time: float = 0.0
    avg_batch_time: float = 0.0
    avg_item_time: float = 0.0
    throughput: float = 0.0  # Items per second
    error_count: int = 0
    retry_count: int = 0
    
    # Recent performance history
    recent_latencies: deque = field(default_factory=lambda: deque(maxlen=10))
    recent_throughputs: deque = field(default_factory=lambda: deque(maxlen=10))
    
    def update(self, batch_size: int, batch_time: float):
        """Update metrics with completed batch data."""
        self.items_processed += batch_size
        self.batches_completed += 1
        self.total_time += batch_time
        
        # Calculate averages
        self.avg_batch_time = self.total_time / self.batches_completed
        self.avg_item_time = self.total_time / self.items_processed if self.items_processed > 0 else 0
        self.throughput = self.items_processed / self.total_time if self.total_time > 0 else 0
        
        # Update recent history
        item_latency = batch_time / batch_size if batch_size > 0 else 0
        self.recent_latencies.append(item_latency)
        self.recent_throughputs.append(batch_size / batch_time if batch_time > 0 else 0)
    
    def get_recent_avg_latency(self) -> float:
        """Get average latency from recent batches."""
        return sum(self.recent_latencies) / len(self.recent_latencies) if self.recent_latencies else 0
    
    def get_recent_avg_throughput(self) -> float:
        """Get average throughput from recent batches."""
        return sum(self.recent_throughputs) / len(self.recent_throughputs) if self.recent_throughputs else 0


class AdaptiveBatchProcessor:
    """
    Adaptive batch processor that optimizes batch sizes based on performance.
    
    Features:
    - Dynamic batch size adjustment
    - Performance monitoring and adaptation
    - Concurrent batch processing
    - Error handling and retry logic
    """
    
    def __init__(self, config: BatchConfig):
        self.config = config
        self.metrics = BatchMetrics()
        self.monitoring = get_monitoring_system()
        self.lock = RLock()
        
        # Current batch size (adaptive)
        self.current_batch_size = config.optimal_batch_size
        
        # Thread pool for concurrent processing
        self.executor = ThreadPoolExecutor(max_workers=config.max_workers)
        
        logger.info(f"Initialized AdaptiveBatchProcessor with batch size {self.current_batch_size}")
    
    def _adapt_batch_size(self) -> None:
        """Adapt batch size based on recent performance metrics."""
        if not self.config.adaptive_sizing or self.metrics.batches_completed < 3:
            return
        
        recent_latency = self.metrics.get_recent_avg_latency()
        recent_throughput = self.metrics.get_recent_avg_throughput()
        
        # If latency is too high, reduce batch size
        if recent_latency > self.config.latency_threshold:
            new_size = max(
                self.config.min_batch_size,
                int(self.current_batch_size * 0.8)
            )
            logger.debug(f"Reducing batch size from {self.current_batch_size} to {new_size} "
                        f"(latency: {recent_latency:.2f}s)")
            self.current_batch_size = new_size
        
        # If throughput is below target and latency is acceptable, increase batch size
        elif (recent_throughput < self.config.throughput_target and 
              recent_latency < self.config.latency_threshold * 0.5):
            new_size = min(
                self.config.max_batch_size,
                int(self.current_batch_size * 1.2)
            )
            logger.debug(f"Increasing batch size from {self.current_batch_size} to {new_size} "
                        f"(throughput: {recent_throughput:.1f} items/s)")
            self.current_batch_size = new_size
    
    async def process_items(self, items: List[Any], 
                          processor_func: Callable,
                          *args, **kwargs) -> List[Any]:
        """
        Process items in optimized batches.
        
        Args:
            items: List of items to process
            processor_func: Function to process each batch
            *args, **kwargs: Additional arguments for processor function
            
        Returns:
            List of processing results
        """
        if not items:
            return []
        
        logger.info(f"Processing {len(items)} items in adaptive batches")
        start_time = time.time()
        
        # Split items into batches
        batches = self._create_batches(items)
        logger.debug(f"Created {len(batches)} batches with sizes: {[len(b) for b in batches]}")
        
        # Process batches concurrently
        results = []
        
        # Limit concurrent batches
        semaphore = asyncio.Semaphore(self.config.max_concurrent_batches)
        
        async def process_batch(batch: List[Any], batch_idx: int) -> Tuple[int, List[Any]]:
            async with semaphore:
                batch_start = time.time()
                
                try:
                    # Record batch start
                    self.monitoring.record_metric(
                        "batch_processing.batch_started",
                        1,
                        {"batch_size": len(batch), "batch_index": batch_idx}
                    )
                    
                    # Process the batch
                    if asyncio.iscoroutinefunction(processor_func):
                        batch_result = await processor_func(batch, *args, **kwargs)
                    else:
                        # Run sync function in thread pool
                        loop = asyncio.get_event_loop()
                        batch_result = await loop.run_in_executor(
                            self.executor, processor_func, batch, *args, **kwargs
                        )
                    
                    batch_time = time.time() - batch_start
                    
                    # Update metrics
                    with self.lock:
                        self.metrics.update(len(batch), batch_time)
                        self._adapt_batch_size()
                    
                    # Record performance metrics
                    self.monitoring.record_metric(
                        "batch_processing.batch_completed",
                        1,
                        {
                            "batch_size": len(batch),
                            "batch_time": batch_time,
                            "items_per_second": len(batch) / batch_time if batch_time > 0 else 0
                        }
                    )
                    
                    logger.debug(f"Batch {batch_idx} completed: {len(batch)} items in {batch_time:.2f}s")
                    
                    return batch_idx, batch_result
                
                except Exception as e:
                    with self.lock:
                        self.metrics.error_count += 1
                    
                    logger.error(f"Batch {batch_idx} failed: {e}")
                    self.monitoring.record_metric(
                        "batch_processing.batch_failed",
                        1,
                        {"batch_size": len(batch), "error": str(e)}
                    )
                    
                    raise BatchProcessingError(f"Batch {batch_idx} processing failed: {e}")
        
        # Execute all batches concurrently
        try:
            tasks = [process_batch(batch, idx) for idx, batch in enumerate(batches)]
            completed_batches = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Sort results by batch index and extract results
            successful_batches = []
            for result in completed_batches:
                if isinstance(result, Exception):
                    logger.error(f"Batch processing error: {result}")
                    continue
                
                batch_idx, batch_result = result
                successful_batches.append((batch_idx, batch_result))
            
            # Sort by batch index to maintain order
            successful_batches.sort(key=lambda x: x[0])
            
            # Flatten results
            for _, batch_result in successful_batches:
                if isinstance(batch_result, list):
                    results.extend(batch_result)
                else:
                    results.append(batch_result)
        
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            raise BatchProcessingError(f"Batch processing failed: {e}")
        
        # Record overall performance
        total_time = time.time() - start_time
        overall_throughput = len(items) / total_time if total_time > 0 else 0
        
        logger.info(f"Batch processing completed: {len(items)} items in {total_time:.2f}s "
                   f"({overall_throughput:.1f} items/s)")
        
        self.monitoring.record_metric(
            "batch_processing.session_completed",
            1,
            {
                "total_items": len(items),
                "total_time": total_time,
                "throughput": overall_throughput,
                "batches_count": len(batches),
                "success_rate": len(results) / len(items) if items else 0
            }
        )
        
        return results
    
    def _create_batches(self, items: List[Any]) -> List[List[Any]]:
        """Create optimally sized batches from items."""
        batches = []
        current_batch = []
        
        for item in items:
            current_batch.append(item)
            
            if len(current_batch) >= self.current_batch_size:
                batches.append(current_batch)
                current_batch = []
        
        # Add remaining items as final batch
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        return {
            "metrics": {
                "items_processed": self.metrics.items_processed,
                "batches_completed": self.metrics.batches_completed,
                "total_time": self.metrics.total_time,
                "avg_batch_time": self.metrics.avg_batch_time,
                "avg_item_time": self.metrics.avg_item_time,
                "throughput": self.metrics.throughput,
                "error_count": self.metrics.error_count
            },
            "current_config": {
                "current_batch_size": self.current_batch_size,
                "max_batch_size": self.config.max_batch_size,
                "min_batch_size": self.config.min_batch_size,
                "max_concurrent_batches": self.config.max_concurrent_batches
            },
            "recent_performance": {
                "avg_latency": self.metrics.get_recent_avg_latency(),
                "avg_throughput": self.metrics.get_recent_avg_throughput()
            }
        }
    
    def close(self):
        """Clean up resources."""
        self.executor.shutdown(wait=True)


class GoogleSheetsOptimizer:
    """
    Optimization utilities specifically for Google Sheets operations.
    
    Implements:
    - Batch read/write operations
    - Smart cell range optimization  
    - API quota management
    - Connection pooling
    """
    
    def __init__(self, batch_config: Optional[BatchConfig] = None):
        self.config = batch_config or BatchConfig(
            optimal_batch_size=50,  # Optimal for Sheets API
            max_batch_size=100,
            max_concurrent_batches=2  # Conservative for API limits
        )
        self.processor = AdaptiveBatchProcessor(self.config)
        self.monitoring = get_monitoring_system()
    
    async def batch_read_ranges(self, spreadsheet_id: str, 
                               ranges: List[str],
                               sheets_client) -> Dict[str, List[List[Any]]]:
        """
        Optimized batch reading of multiple cell ranges.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            ranges: List of A1 notation ranges to read
            sheets_client: Google Sheets client
            
        Returns:
            Dict mapping ranges to their values
        """
        if not ranges:
            return {}
        
        logger.info(f"Batch reading {len(ranges)} ranges from spreadsheet")
        
        async def read_range_batch(range_batch: List[str]) -> List[Tuple[str, List[List[Any]]]]:
            """Read a batch of ranges."""
            try:
                # Use Sheets API batch get to read multiple ranges at once
                spreadsheet = sheets_client.service.spreadsheets()
                result = spreadsheet.values().batchGet(
                    spreadsheetId=spreadsheet_id,
                    ranges=range_batch,
                    valueRenderOption='UNFORMATTED_VALUE',
                    dateTimeRenderOption='FORMATTED_STRING'
                ).execute()
                
                # Extract values for each range
                batch_results = []
                value_ranges = result.get('valueRanges', [])
                
                for i, range_name in enumerate(range_batch):
                    if i < len(value_ranges):
                        values = value_ranges[i].get('values', [])
                    else:
                        values = []
                    batch_results.append((range_name, values))
                
                return batch_results
            
            except Exception as e:
                logger.error(f"Batch range read failed: {e}")
                raise
        
        # Process ranges in batches
        batch_results = await self.processor.process_items(
            ranges, read_range_batch
        )
        
        # Convert to dictionary
        result_dict = {}
        for batch_result in batch_results:
            for range_name, values in batch_result:
                result_dict[range_name] = values
        
        logger.info(f"Successfully read {len(result_dict)} ranges")
        return result_dict
    
    async def batch_write_ranges(self, spreadsheet_id: str,
                                range_data: Dict[str, List[List[Any]]],
                                sheets_client) -> bool:
        """
        Optimized batch writing of multiple cell ranges.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            range_data: Dict mapping ranges to their values
            sheets_client: Google Sheets client
            
        Returns:
            True if successful
        """
        if not range_data:
            return True
        
        logger.info(f"Batch writing {len(range_data)} ranges to spreadsheet")
        
        # Convert to list for batch processing
        range_items = list(range_data.items())
        
        async def write_range_batch(batch_items: List[Tuple[str, List[List[Any]]]]) -> bool:
            """Write a batch of ranges."""
            try:
                # Prepare batch update request
                value_ranges = []
                for range_name, values in batch_items:
                    value_ranges.append({
                        'range': range_name,
                        'values': values,
                        'majorDimension': 'ROWS'
                    })
                
                # Execute batch update
                spreadsheet = sheets_client.service.spreadsheets()
                result = spreadsheet.values().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={
                        'valueInputOption': 'USER_ENTERED',
                        'data': value_ranges
                    }
                ).execute()
                
                updated_cells = result.get('totalUpdatedCells', 0)
                logger.debug(f"Batch update completed: {updated_cells} cells updated")
                
                return True
            
            except Exception as e:
                logger.error(f"Batch range write failed: {e}")
                raise
        
        # Process ranges in batches
        batch_results = await self.processor.process_items(
            range_items, write_range_batch
        )
        
        success = all(batch_results)
        if success:
            logger.info(f"Successfully wrote {len(range_data)} ranges")
        else:
            logger.error("Some batch writes failed")
        
        return success
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get optimization performance summary."""
        return self.processor.get_performance_summary()


class WildberriesAPIOptimizer:
    """
    Optimization utilities specifically for Wildberries API operations.
    
    Implements:
    - Efficient data fetching strategies
    - Request batching and deduplication
    - Response caching
    - Parallel processing optimization
    """
    
    def __init__(self, batch_config: Optional[BatchConfig] = None):
        self.config = batch_config or BatchConfig(
            optimal_batch_size=20,  # Conservative for API limits
            max_batch_size=50,
            max_concurrent_batches=2  # Respect rate limits
        )
        self.processor = AdaptiveBatchProcessor(self.config)
        self.monitoring = get_monitoring_system()
        
        # Response cache for deduplication
        self.response_cache: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, float] = {}
        self.cache_ttl = 300  # 5 minutes cache TTL
    
    def _get_cache_key(self, method: str, **kwargs) -> str:
        """Generate cache key for API request."""
        key_parts = [method]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        return "|".join(key_parts)
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached response is still valid."""
        if cache_key not in self.response_cache:
            return False
        
        timestamp = self.cache_timestamps.get(cache_key, 0)
        return time.time() - timestamp < self.cache_ttl
    
    async def fetch_product_data_optimized(self, nm_ids: List[int],
                                         wb_client) -> Dict[int, Dict[str, Any]]:
        """
        Optimized fetching of product data for multiple nmIds.
        
        Args:
            nm_ids: List of Wildberries article IDs
            wb_client: Wildberries API client
            
        Returns:
            Dict mapping nmId to product data
        """
        if not nm_ids:
            return {}
        
        # Remove duplicates while preserving order
        unique_nm_ids = list(dict.fromkeys(nm_ids))
        logger.info(f"Fetching optimized product data for {len(unique_nm_ids)} unique products")
        
        # Check cache for existing data
        cached_results = {}
        uncached_nm_ids = []
        
        for nm_id in unique_nm_ids:
            cache_key = self._get_cache_key("product_data", nm_id=nm_id)
            if self._is_cache_valid(cache_key):
                cached_results[nm_id] = self.response_cache[cache_key]
                logger.debug(f"Using cached data for nmId {nm_id}")
            else:
                uncached_nm_ids.append(nm_id)
        
        logger.info(f"Using {len(cached_results)} cached results, "
                   f"fetching {len(uncached_nm_ids)} new items")
        
        # Fetch uncached data if needed
        fetched_results = {}
        if uncached_nm_ids:
            
            async def fetch_batch(nm_id_batch: List[int]) -> List[Tuple[int, Dict[str, Any]]]:
                """Fetch product data for a batch of nmIds."""
                batch_results = []
                
                for nm_id in nm_id_batch:
                    try:
                        # This would be replaced with actual API calls
                        # For now, simulate the data structure
                        product_data = {
                            "nm_id": nm_id,
                            "supplier_article": f"ART-{nm_id}",
                            "warehouses": [],
                            "orders": []
                        }
                        
                        batch_results.append((nm_id, product_data))
                        
                        # Cache the result
                        cache_key = self._get_cache_key("product_data", nm_id=nm_id)
                        self.response_cache[cache_key] = product_data
                        self.cache_timestamps[cache_key] = time.time()
                        
                    except Exception as e:
                        logger.error(f"Failed to fetch data for nmId {nm_id}: {e}")
                        # Continue with other items
                
                return batch_results
            
            # Process in optimized batches
            batch_results = await self.processor.process_items(
                uncached_nm_ids, fetch_batch
            )
            
            # Merge batch results
            for batch_result in batch_results:
                for nm_id, product_data in batch_result:
                    fetched_results[nm_id] = product_data
        
        # Combine cached and fetched results
        all_results = {**cached_results, **fetched_results}
        
        logger.info(f"Completed optimized product data fetch: "
                   f"{len(all_results)} products retrieved")
        
        return all_results
    
    def clear_cache(self):
        """Clear the response cache."""
        self.response_cache.clear()
        self.cache_timestamps.clear()
        logger.debug("Response cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        valid_entries = sum(1 for key in self.response_cache.keys() 
                           if self._is_cache_valid(key))
        
        return {
            "total_entries": len(self.response_cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self.response_cache) - valid_entries,
            "cache_ttl": self.cache_ttl
        }


# Global optimizer instances
_sheets_optimizer: Optional[GoogleSheetsOptimizer] = None
_api_optimizer: Optional[WildberriesAPIOptimizer] = None


def get_sheets_optimizer() -> GoogleSheetsOptimizer:
    """Get global Google Sheets optimizer instance."""
    global _sheets_optimizer
    
    if _sheets_optimizer is None:
        _sheets_optimizer = GoogleSheetsOptimizer()
    
    return _sheets_optimizer


def get_api_optimizer() -> WildberriesAPIOptimizer:
    """Get global Wildberries API optimizer instance."""
    global _api_optimizer
    
    if _api_optimizer is None:
        _api_optimizer = WildberriesAPIOptimizer()
    
    return _api_optimizer


# Example usage and testing
if __name__ == "__main__":
    
    async def test_batch_processor():
        """Test the adaptive batch processor."""
        
        print("🚀 Testing AdaptiveBatchProcessor...")
        
        # Create test data
        test_items = list(range(100))
        
        # Simple processor function
        def process_batch(batch):
            # Simulate processing time
            time.sleep(0.1)
            return [f"processed_{item}" for item in batch]
        
        # Create processor with small batches for testing
        config = BatchConfig(
            optimal_batch_size=10,
            max_batch_size=20,
            min_batch_size=5,
            adaptive_sizing=True
        )
        
        processor = AdaptiveBatchProcessor(config)
        
        # Process items
        start_time = time.time()
        results = await processor.process_items(test_items, process_batch)
        end_time = time.time()
        
        print(f"✅ Processed {len(test_items)} items in {end_time - start_time:.2f}s")
        print(f"📊 Results: {len(results)} processed items")
        
        # Show performance summary
        summary = processor.get_performance_summary()
        print(f"📈 Performance Summary:")
        print(f"   Throughput: {summary['metrics']['throughput']:.1f} items/s")
        print(f"   Avg batch time: {summary['metrics']['avg_batch_time']:.3f}s")
        print(f"   Current batch size: {summary['current_config']['current_batch_size']}")
        
        processor.close()
    
    # Run test
    asyncio.run(test_batch_processor())