"""
Marketplace abstraction layer for Stock Tracker.

Provides unified interface for different marketplace platforms.
"""

from .base import (
    MarketplaceClient,
    MarketplaceCredentials,
    WildberriesCredentials,
    OzonCredentials,
)
from .wildberries_client import WildberriesMarketplaceClient
from .ozon_client import OzonMarketplaceClient
# factory is imported separately to avoid circular imports

__all__ = [
    "MarketplaceClient",
    "MarketplaceCredentials",
    "WildberriesCredentials",
    "OzonCredentials",
    "WildberriesMarketplaceClient",
    "OzonMarketplaceClient",
]
