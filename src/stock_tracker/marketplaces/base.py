"""
Abstract base class for marketplace API clients.

Provides unified interface for different marketplaces (Wildberries, Ozon, etc.)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from stock_tracker.core.models import Product


@dataclass
class MarketplaceCredentials:
    """Base credentials for marketplace authentication."""
    pass


@dataclass
class WildberriesCredentials(MarketplaceCredentials):
    """Wildberries API credentials."""
    api_key: str


@dataclass
class OzonCredentials(MarketplaceCredentials):
    """Ozon API credentials."""
    client_id: str
    api_key: str
    seller_id: str


class MarketplaceClient(ABC):
    """
    Abstract marketplace client interface.
    
    All marketplace integrations must implement this interface
    to ensure consistent behavior across different platforms.
    """
    
    def __init__(self, credentials: MarketplaceCredentials):
        """
        Initialize marketplace client with credentials.
        
        Args:
            credentials: Marketplace-specific credentials
        """
        self.credentials = credentials
    
    @abstractmethod
    async def fetch_products(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Product]:
        """
        Fetch products from marketplace.
        
        Args:
            limit: Maximum number of products to fetch
            offset: Offset for pagination
            filters: Additional filters (marketplace-specific)
            
        Returns:
            List of Product objects
        """
        pass
    
    @abstractmethod
    async def fetch_stock(self, product_ids: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Fetch stock levels for products.
        
        Args:
            product_ids: List of product IDs (None = all products)
            
        Returns:
            Dict mapping product_id -> stock_quantity
        """
        pass
    
    @abstractmethod
    async def fetch_orders(
        self,
        date_from: str,
        date_to: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Fetch orders for products in date range.
        
        Args:
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD), defaults to today
            
        Returns:
            Dict mapping product_id -> order_count
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test API connectivity and credentials.
        
        Returns:
            Dict with connection test results
        """
        pass
    
    @property
    @abstractmethod
    def marketplace_name(self) -> str:
        """Get marketplace name."""
        pass
