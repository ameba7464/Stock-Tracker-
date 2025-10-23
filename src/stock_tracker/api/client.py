"""
Wildberries API client implementation.

Provides authenticated access to Wildberries Analytics API v2 for stock tracking.
Migrated from v1 to v2 API with proper parameters for 7-day periods and all warehouse types.

CRITICAL: Uses Analytics API v2 endpoints with required parameters:
- currentPeriod: last 7 days 
- stockType: "" (all warehouses, no FBO/FBS separation)
- skipDeletedNm: true
- availabilityFilters: ["actual", "balanced", "deficient"] 
- orderBy: configurable sorting
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.config import get_config
from stock_tracker.utils.exceptions import (
    WildberriesAPIError, RateLimitError, TaskTimeoutError, 
    AuthenticationError, handle_api_error
)
from stock_tracker.utils.retry import retry_with_backoff, RetryConfig
from stock_tracker.utils.rate_limiting import (
    rate_limited, get_rate_limiter, configure_wildberries_rate_limits
)


logger = get_logger(__name__)


class WildberriesAPIClient:
    """
    Wildberries Analytics API v2 client for stock tracking.
    
    Supports:
    1. Analytics API v2: /api/v2/stocks-report/products/products
    2. Period-based queries with last 7 days
    3. All warehouse types (stockType="")
    4. Standard availability filters
    
    Replaces old v1 warehouse_remains and supplier/orders endpoints.
    """
    
    def __init__(self, api_key: Optional[str] = None, 
                 base_url: Optional[str] = None):
        """
        Initialize Wildberries Analytics API v2 client.
        
        Args:
            api_key: Wildberries API key for Analytics category
            base_url: Base URL for seller analytics API v2
        """
        self.config = get_config()
        
        self.api_key = api_key or self.config.wildberries.api_key
        # Use analytics API for v2 endpoints
        self.base_url = base_url or "https://seller-analytics-api.wildberries.ru"
        self.timeout = self.config.wildberries.timeout
        self.max_retries = self.config.wildberries.retry_count
        self.retry_delay = self.config.wildberries.retry_delay
        
        # Analytics API v2 has stricter rate limits: 3 requests/minute, 20 second intervals  
        rate_limit_config = configure_wildberries_rate_limits()
        self.rate_limiter = get_rate_limiter(rate_limit_config)
        
        # Setup session with basic retry logic
        self.session = requests.Session()
        
        # Configure retry strategy for v2 API
        retry_strategy = Retry(
            total=2,
            backoff_factor=self.retry_delay,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set headers for Analytics API v2
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "StockTracker/2.0"
        })
        
        logger.info("Initialized Wildberries Analytics API v2 client")
        logger.debug(f"Analytics Base URL: {self.base_url}")
        logger.debug(f"Rate limit: 3 req/min, 20 sec intervals")
    
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make HTTP request with error handling.
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request parameters
            
        Returns:
            Response object
            
        Raises:
            WildberriesAPIError: If request fails
        """
        try:
            # Set timeout if not provided
            kwargs.setdefault('timeout', self.timeout)
            
            logger.debug(f"Making {method} request to {url}")
            
            response = self.session.request(method, url, **kwargs)
            
            # Handle non-success status codes
            if not response.ok:
                handle_api_error(response, url)
            
            return response
            
        except requests.exceptions.Timeout:
            raise WildberriesAPIError(f"Request timeout after {self.timeout}s", endpoint=url)
        except requests.exceptions.ConnectionError:
            raise WildberriesAPIError(f"Connection failed to {url}", endpoint=url)
        except requests.exceptions.RequestException as e:
            raise WildberriesAPIError(f"Request failed: {e}", endpoint=url)
    
    def _get_last_week_period(self) -> Dict[str, str]:
        """
        Get period for last 7 days in required format.
        
        Returns:
            Dict with start and end dates in YYYY-MM-DD format
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        return {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d")
        }
    
    @retry_with_backoff(RetryConfig(
        max_retries=3,
        base_delay=20.0,  # 20 second intervals for analytics API
        retry_on_status_codes=(429, 500, 502, 503, 504),
        respect_retry_after=True
    ))
    @rate_limited("/api/v2/stocks-report/products/products", priority=1)
    async def get_product_stock_data(self, 
                                   nm_ids: Optional[List[int]] = None,
                                   subject_id: Optional[int] = None,
                                   brand_name: Optional[str] = None,
                                   tag_id: Optional[int] = None,
                                   order_by_field: str = "stockCount",
                                   order_by_mode: str = "desc",
                                   limit: int = 100,
                                   offset: int = 0) -> Dict[str, Any]:
        """
        Get product stock data from Analytics API v2.
        
        Uses /api/v2/stocks-report/products/products endpoint with:
        - Period: last 7 days
        - stockType: "" (all warehouses)
        - skipDeletedNm: true
        - availabilityFilters: ["actual", "balanced", "deficient"]
        
        Args:
            nm_ids: List of WB article IDs for filtering
            subject_id: Subject ID for filtering  
            brand_name: Brand name for filtering
            tag_id: Tag ID for filtering
            order_by_field: Field to sort by (default: stockCount)
            order_by_mode: Sort mode "asc" or "desc" (default: desc)
            limit: Number of products to return (max 1000)
            offset: Offset for pagination
            
        Returns:
            Dict with response data containing items array
            
        Raises:
            WildberriesAPIError: If request fails
        """
        url = urljoin(self.base_url, "/api/v2/stocks-report/products/products")
        
        # Build request body with required v2 parameters
        request_body = {
            "currentPeriod": self._get_last_week_period(),
            "stockType": "",  # All warehouses (no FBO/FBS separation)
            "skipDeletedNm": True,  # Hide deleted products
            "availabilityFilters": ["actual", "balanced", "deficient"],  # Standard filters
            "orderBy": {
                "field": order_by_field,
                "mode": order_by_mode
            },
            "limit": min(limit, 1000),  # API max limit
            "offset": offset
        }
        
        # Add optional filters
        if nm_ids:
            request_body["nmIDs"] = nm_ids
        if subject_id:
            request_body["subjectID"] = subject_id
        if brand_name:
            request_body["brandName"] = brand_name
        if tag_id:
            request_body["tagID"] = tag_id
        
        logger.info(f"Getting product stock data with {len(nm_ids or [])} nmIDs")
        logger.debug(f"Request body: {request_body}")
        
        try:
            response = self._make_request("POST", url, json=request_body)
            
            # Record response for rate limiter  
            self.rate_limiter.record_response(response.status_code, dict(response.headers))
            
            # Parse v2 API response
            data = response.json()
            
            if "data" not in data:
                raise WildberriesAPIError(
                    "Invalid v2 API response format: missing data field",
                    endpoint=url,
                    response_data=data
                )
            
            items = data["data"].get("items", [])
            logger.info(f"Retrieved {len(items)} product stock records")
            logger.debug(f"Sample record: {items[0] if items else 'No data'}")
            
            return data
            
        except Exception as e:
            if isinstance(e, WildberriesAPIError):
                raise
            raise WildberriesAPIError(f"Failed to get product stock data: {e}", endpoint=url)
    
    async def get_all_product_stock_data(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Get all product stock data with pagination.
        
        This method handles pagination automatically to retrieve all available data.
        
        Args:
            **kwargs: Arguments passed to get_product_stock_data
            
        Returns:
            List of all product stock records
        """
        all_items = []
        offset = 0
        limit = kwargs.get("limit", 100)
        
        logger.info("Starting paginated retrieval of all product stock data")
        
        while True:
            # Update offset in kwargs
            kwargs_with_offset = {**kwargs, "offset": offset, "limit": limit}
            
            # Get current page
            response = await self.get_product_stock_data(**kwargs_with_offset)
            items = response["data"].get("items", [])
            
            if not items:
                # No more data
                break
                
            all_items.extend(items)
            logger.debug(f"Retrieved page at offset {offset}, got {len(items)} items")
            
            # Check if we got fewer items than requested (last page)
            if len(items) < limit:
                break
                
            # Move to next page
            offset += limit
            
            # Respect rate limiting between requests
            await asyncio.sleep(20)  # 20 second intervals for v2 API
        
        logger.info(f"Retrieved total of {len(all_items)} product stock records")
        return all_items

    @retry_with_backoff(RetryConfig(
        max_retries=3,
        base_delay=30.0,  # 30 second intervals for warehouse remains API
        retry_on_status_codes=(429, 500, 502, 503, 504),
        respect_retry_after=True
    ))
    @rate_limited("/api/v1/warehouse_remains", priority=2)
    async def create_warehouse_remains_task(self, **params) -> str:
        """
        Create warehouse remains task using Analytics API v1.
        
        This method creates a task to get detailed warehouse data per urls.md specification.
        
        Args:
            **params: Task parameters like groupByNm, groupBySa, etc.
            
        Returns:
            Task ID for downloading results
            
        Raises:
            WildberriesAPIError: If task creation fails
        """
        url = "https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains"
        
        # Default parameters per urls.md
        task_params = {
            "locale": "ru",
            "groupByNm": True,  # To get nmId in response
            "groupBySa": True,  # To get supplierArticle
            **params
        }
        
        logger.info("Creating warehouse remains task with v1 API")
        logger.debug(f"Task parameters: {task_params}")
        
        try:
            response = self._make_request("GET", url, params=task_params)
            
            # Record response for rate limiter
            self.rate_limiter.record_response(response.status_code, dict(response.headers))
            
            data = response.json()
            
            if "data" not in data or "taskId" not in data["data"]:
                raise WildberriesAPIError(
                    "Invalid warehouse remains task response: missing taskId",
                    endpoint=url,
                    response_data=data
                )
            
            task_id = data["data"]["taskId"]
            logger.info(f"Created warehouse remains task: {task_id}")
            
            return task_id
            
        except Exception as e:
            if isinstance(e, WildberriesAPIError):
                raise
            raise WildberriesAPIError(f"Failed to create warehouse remains task: {e}", endpoint=url)

    @retry_with_backoff(RetryConfig(
        max_retries=5,
        base_delay=45.0,  # 45 second intervals for task download
        retry_on_status_codes=(429, 500, 502, 503, 504),
        respect_retry_after=True
    ))
    @rate_limited("/api/v1/warehouse_remains/tasks", priority=2)
    async def download_warehouse_remains(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Download warehouse remains data using task ID.
        
        Args:
            task_id: Task ID from create_warehouse_remains_task
            
        Returns:
            List of warehouse remains records with detailed warehouse breakdown
            
        Raises:
            WildberriesAPIError: If download fails
        """
        url = f"https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains/tasks/{task_id}/download"
        
        logger.info(f"Downloading warehouse remains data for task: {task_id}")
        
        try:
            response = self._make_request("GET", url)
            
            # Record response for rate limiter
            self.rate_limiter.record_response(response.status_code, dict(response.headers))
            
            data = response.json()
            
            if not isinstance(data, list):
                raise WildberriesAPIError(
                    "Invalid warehouse remains download response: expected array",
                    endpoint=url,
                    response_data=data
                )
            
            logger.info(f"Downloaded {len(data)} warehouse remains records")
            
            return data
            
        except Exception as e:
            if isinstance(e, WildberriesAPIError):
                raise
            raise WildberriesAPIError(f"Failed to download warehouse remains: {e}", endpoint=url)

    async def get_warehouse_remains_with_retry(self, max_wait_time: int = 900, **params) -> List[Dict[str, Any]]:
        """
        Get warehouse remains data with automatic task creation and polling.
        
        Implements proper timing according to WAREHOUSE_IMPROVEMENT_PROMPT.md:
        - Mandatory 60 second wait after task creation
        - 30-90 second polling intervals with exponential backoff
        - 15 minute maximum wait time
        - Proper interpretation of 404 as "task still processing"
        
        Args:
            max_wait_time: Maximum time to wait for task completion in seconds (default: 900 = 15 min)
            **params: Parameters for warehouse remains task
            
        Returns:
            List of warehouse remains records with real warehouse names
            
        Raises:
            WildberriesAPIError: If task fails or times out
        """
        logger.info("Starting warehouse remains data retrieval with improved task polling")
        
        # Create task
        task_id = await self.create_warehouse_remains_task(**params)
        
        # CRITICAL: Mandatory 60 second wait for WB to process the task
        logger.info(f"Task {task_id} created, waiting 60s for WB processing...")
        await asyncio.sleep(60)
        
        # Start polling with proper intervals
        start_time = time.time()
        poll_interval = 30  # Start with 30 seconds
        
        while time.time() - start_time < max_wait_time:
            try:
                # Try to download data
                data = await self.download_warehouse_remains(task_id)
                logger.info(f"✅ Successfully retrieved warehouse remains data: {len(data)} records")
                return data
                
            except WildberriesAPIError as e:
                # Check if task is not ready (404 means still processing on WB side)
                error_message = str(e).lower()
                if ("404" in error_message or 
                    "not found" in error_message or 
                    "not ready" in error_message or 
                    "processing" in error_message):
                    
                    elapsed = time.time() - start_time
                    logger.info(f"Task {task_id} still processing... waiting {poll_interval}s (elapsed: {elapsed:.1f}s)")
                    await asyncio.sleep(poll_interval)
                    
                    # Exponential backoff: increase poll interval gradually (30->60->90 seconds)
                    poll_interval = min(poll_interval + 30, 90)
                    continue
                else:
                    # Other error (authentication, rate limit, etc.), reraise
                    logger.error(f"Warehouse remains download failed with non-retriable error: {e}")
                    raise
        
        # Task timed out
        elapsed = time.time() - start_time
        raise TaskTimeoutError(
            f"Warehouse remains task {task_id} timed out after {elapsed:.1f} seconds (max: {max_wait_time}s)",
            endpoint="warehouse_remains_task",
            task_id=task_id
        )
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Wildberries Analytics API v2.
        
        Returns:
            Dict with connection test results.
        """
        try:
            logger.info("Testing Wildberries Analytics API v2 connection...")
            
            # Test with a simple product stock data request
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                response = loop.run_until_complete(
                    self.get_product_stock_data(limit=1)
                )
                
                result = {
                    "success": True,
                    "api_version": "v2",
                    "endpoint": "/api/v2/stocks-report/products/products",
                    "base_url": self.base_url,
                    "has_api_key": bool(self.api_key),
                    "sample_data": bool(response.get("data", {}).get("items"))
                }
                
                logger.info("✅ Wildberries Analytics API v2 connection test successful")
                return result
                
            finally:
                loop.close()
            
        except Exception as e:
            logger.error(f"❌ Wildberries Analytics API v2 connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "api_version": "v2",
                "base_url": self.base_url
            }
    
    def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            self.session.close()
        logger.debug("Closed Wildberries API client")


def create_wildberries_client(api_key: Optional[str] = None,
                             base_url: Optional[str] = None) -> WildberriesAPIClient:
    """
    Factory function to create a Wildberries Analytics API v2 client.
    
    Args:
        api_key: Wildberries API key for Analytics category
        base_url: Base URL for analytics API v2
        
    Returns:
        Configured WildberriesAPIClient instance.
    """
    return WildberriesAPIClient(
        api_key=api_key,
        base_url=base_url
    )


if __name__ == "__main__":
    # Test the Wildberries Analytics API v2 client
    def test_client():
        try:
            client = create_wildberries_client()
            result = client.test_connection()
            
            if result["success"]:
                print("✅ Wildberries Analytics API v2 connection successful!")
                print(f"🔑 Has API key: {result['has_api_key']}")
                print(f"📡 Base URL: {result['base_url']}")
                print(f"📊 API Version: {result['api_version']}")
                print(f"🛠️ Endpoint: {result['endpoint']}")
                print(f"📋 Sample data available: {result['sample_data']}")
            else:
                print(f"❌ Connection failed: {result['error']}")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
        finally:
            if 'client' in locals():
                client.close()
    
    # Run test
    test_client()