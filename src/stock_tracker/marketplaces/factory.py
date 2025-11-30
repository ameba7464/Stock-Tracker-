"""
Factory for creating marketplace clients based on tenant configuration.
"""

from typing import Dict, Any

from stock_tracker.marketplaces.base import MarketplaceClient
from stock_tracker.marketplaces.wildberries_client import WildberriesMarketplaceClient
from stock_tracker.marketplaces.ozon_client import OzonMarketplaceClient
from stock_tracker.database.models import Tenant
from stock_tracker.services.tenant_credentials import (
    get_wildberries_credentials,
    get_ozon_credentials
)
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


def create_marketplace_client(tenant: Tenant) -> MarketplaceClient:
    """
    Create marketplace client based on tenant's marketplace type.
    
    Extracts encrypted credentials from database and creates appropriate client.
    This is the main entry point for getting marketplace clients that will use
    the API key provided by seller through Telegram bot.
    
    Args:
        tenant: Tenant model instance with encrypted credentials
        
    Returns:
        Appropriate MarketplaceClient implementation
        
    Raises:
        ValueError: If marketplace type not supported or credentials missing
    """
    if tenant.marketplace_type == "wildberries":
        # Extract Wildberries credentials from encrypted field
        credentials = get_wildberries_credentials(tenant)
        logger.info(f"Creating Wildberries client for tenant {tenant.id}")
        return WildberriesMarketplaceClient(credentials)
    
    elif tenant.marketplace_type == "ozon":
        # Extract Ozon credentials from encrypted field
        credentials = get_ozon_credentials(tenant)
        logger.info(f"Creating Ozon client for tenant {tenant.id}")
        return OzonMarketplaceClient(credentials)
    
    else:
        raise ValueError(f"Unsupported marketplace type: {tenant.marketplace_type}")
