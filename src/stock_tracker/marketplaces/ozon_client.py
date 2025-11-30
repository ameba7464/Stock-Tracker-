"""
Ozon marketplace client implementation (stub for future).
"""

from typing import List, Dict, Any, Optional

from stock_tracker.marketplaces.base import MarketplaceClient, OzonCredentials
from stock_tracker.core.models import Product
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class OzonMarketplaceClient(MarketplaceClient):
    """
    Ozon marketplace integration (FUTURE IMPLEMENTATION).
    
    Placeholder for Ozon API integration to be implemented in Q1 2026.
    """
    
    def __init__(self, credentials: OzonCredentials):
        """
        Initialize Ozon client.
        
        Args:
            credentials: Ozon API credentials
        """
        super().__init__(credentials)
        logger.info("Initialized Ozon marketplace client (stub)")
    
    async def fetch_products(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Product]:
        """Fetch products from Ozon (NOT YET IMPLEMENTED)."""
        raise NotImplementedError("Ozon integration coming in Q1 2026")
    
    async def fetch_stock(self, product_ids: Optional[List[str]] = None) -> Dict[str, int]:
        """Fetch stock from Ozon (NOT YET IMPLEMENTED)."""
        raise NotImplementedError("Ozon integration coming in Q1 2026")
    
    async def fetch_orders(
        self,
        date_from: str,
        date_to: Optional[str] = None
    ) -> Dict[str, int]:
        """Fetch orders from Ozon (NOT YET IMPLEMENTED)."""
        raise NotImplementedError("Ozon integration coming in Q1 2026")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Ozon API connection (NOT YET IMPLEMENTED)."""
        return {
            "success": False,
            "marketplace": "ozon",
            "error": "Ozon integration not yet implemented",
        }
    
    @property
    def marketplace_name(self) -> str:
        """Get marketplace name."""
        return "ozon"
