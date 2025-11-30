"""
Wildberries marketplace client implementation.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from stock_tracker.marketplaces.base import MarketplaceClient, WildberriesCredentials
from stock_tracker.core.models import Product, Warehouse
from stock_tracker.api.client import WildberriesAPIClient
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class WildberriesMarketplaceClient(MarketplaceClient):
    """
    Wildberries marketplace integration.
    
    Wraps existing WildberriesAPIClient with marketplace interface.
    """
    
    def __init__(self, credentials: WildberriesCredentials):
        """
        Initialize Wildberries client.
        
        Args:
            credentials: Wildberries API credentials
        """
        super().__init__(credentials)
        self.api_client = WildberriesAPIClient(api_key=credentials.api_key)
        logger.info("Initialized Wildberries marketplace client")
    
    async def fetch_products(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Product]:
        """
        Fetch products from Wildberries Analytics API v2.
        
        Args:
            limit: Maximum products to fetch (default 1000)
            offset: Pagination offset
            filters: Additional filters (nm_ids, subject_id, etc.)
            
        Returns:
            List of Product objects
        """
        try:
            logger.info(f"Fetching products from Wildberries (limit={limit}, offset={offset})")
            
            # Prepare filters
            filter_params = filters or {}
            if limit:
                filter_params['limit'] = limit
            if offset:
                filter_params['offset'] = offset
            
            # Fetch from Analytics API v2
            response = await self.api_client.get_product_stock_data(**filter_params)
            
            items = response.get('data', {}).get('items', [])
            logger.info(f"Fetched {len(items)} products from Wildberries")
            
            # Convert to Product objects
            products = []
            for item in items:
                product = Product(
                    wildberries_article=item.get('nmID', 0),
                    seller_article=item.get('supplierArticle', ''),
                    total_orders=item.get('ordersCount', 0),
                    total_stock=item.get('stockCount', 0),
                )
                products.append(product)
            
            return products
            
        except Exception as e:
            logger.error(f"Failed to fetch products from Wildberries: {e}")
            raise
    
    async def fetch_stock(self, product_ids: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Fetch stock levels from Wildberries.
        
        Args:
            product_ids: List of nmID to filter (None = all)
            
        Returns:
            Dict mapping nmID -> stock_quantity
        """
        try:
            filters = {}
            if product_ids:
                filters['nm_ids'] = [int(pid) for pid in product_ids]
            
            response = await self.api_client.get_product_stock_data(**filters)
            items = response.get('data', {}).get('items', [])
            
            return {
                str(item.get('nmID')): item.get('stockCount', 0)
                for item in items
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch stock from Wildberries: {e}")
            raise
    
    async def fetch_orders(
        self,
        date_from: str,
        date_to: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Fetch orders from Wildberries.
        
        Args:
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            
        Returns:
            Dict mapping nmID -> order_count
        """
        try:
            # Wildberries API v2 uses last 7 days by default
            response = await self.api_client.get_product_stock_data()
            items = response.get('data', {}).get('items', [])
            
            return {
                str(item.get('nmID')): item.get('ordersCount', 0)
                for item in items
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch orders from Wildberries: {e}")
            raise
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Wildberries API connection."""
        try:
            result = self.api_client.test_connection()
            return {
                "success": result.get("success", False),
                "marketplace": "wildberries",
                "api_version": result.get("api_version", "unknown"),
            }
        except Exception as e:
            return {
                "success": False,
                "marketplace": "wildberries",
                "error": str(e),
            }
    
    @property
    def marketplace_name(self) -> str:
        """Get marketplace name."""
        return "wildberries"
