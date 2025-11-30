"""
Tenant credentials helper for extracting marketplace credentials from database.
"""

import json
from typing import Dict, Any

from stock_tracker.database.models import Tenant
from stock_tracker.security.encryption import CredentialEncryptor
from stock_tracker.marketplaces.base import WildberriesCredentials, OzonCredentials
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

# Lazy initialization of encryptor to avoid import-time errors
_encryptor = None


def _get_encryptor() -> CredentialEncryptor:
    """Get or create global encryptor instance."""
    global _encryptor
    if _encryptor is None:
        _encryptor = CredentialEncryptor()
    return _encryptor


def get_wildberries_credentials(tenant: Tenant) -> WildberriesCredentials:
    """
    Extract Wildberries credentials from tenant.
    
    Args:
        tenant: Tenant model instance
        
    Returns:
        WildberriesCredentials object
        
    Raises:
        ValueError: If credentials not configured
    """
    if not tenant.credentials_encrypted:
        raise ValueError(f"Tenant {tenant.id} has no Wildberries credentials configured")
    
    try:
        # credentials_encrypted is JSONB dict: {"encrypted": "base64_string"}
        encrypted_str = tenant.credentials_encrypted.get("encrypted")
        if not encrypted_str:
            raise ValueError("No encrypted data found")
        
        # Decrypt credentials
        decrypted = _get_encryptor().decrypt(encrypted_str)
        credentials_dict = json.loads(decrypted)
        
        # Extract API key
        api_key = credentials_dict.get("api_key")
        if not api_key:
            raise ValueError("API key not found in credentials")
        
        return WildberriesCredentials(api_key=api_key)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse credentials for tenant {tenant.id}: {e}")
        raise ValueError("Invalid credentials format")
    except Exception as e:
        logger.error(f"Failed to decrypt credentials for tenant {tenant.id}: {e}")
        raise ValueError("Failed to decrypt credentials")


def get_ozon_credentials(tenant: Tenant) -> OzonCredentials:
    """
    Extract Ozon credentials from tenant.
    
    Args:
        tenant: Tenant model instance
        
    Returns:
        OzonCredentials object
        
    Raises:
        ValueError: If credentials not configured
    """
    if not tenant.credentials_encrypted:
        raise ValueError(f"Tenant {tenant.id} has no Ozon credentials configured")
    
    try:
        # credentials_encrypted is JSONB dict: {"encrypted": "base64_string"}
        encrypted_str = tenant.credentials_encrypted.get("encrypted")
        if not encrypted_str:
            raise ValueError("No encrypted data found")
        
        # Decrypt credentials
        decrypted = _get_encryptor().decrypt(encrypted_str)
        credentials_dict = json.loads(decrypted)
        
        # Extract Ozon credentials
        client_id = credentials_dict.get("ozon_client_id")
        api_key = credentials_dict.get("ozon_api_key")
        
        if not client_id or not api_key:
            raise ValueError("Ozon credentials not complete")
        
        return OzonCredentials(client_id=client_id, api_key=api_key)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Ozon credentials for tenant {tenant.id}: {e}")
        raise ValueError("Invalid credentials format")
    except Exception as e:
        logger.error(f"Failed to decrypt Ozon credentials for tenant {tenant.id}: {e}")
        raise ValueError("Failed to decrypt credentials")


def update_wildberries_credentials(tenant: Tenant, api_key: str) -> None:
    """
    Update Wildberries API key for tenant.
    
    Args:
        tenant: Tenant model instance
        api_key: New Wildberries API key
    """
    # Get existing credentials or create new
    credentials_dict = {}
    
    if tenant.credentials_encrypted:
        try:
            encrypted_str = tenant.credentials_encrypted.get("encrypted")
            if encrypted_str:
                decrypted = _get_encryptor().decrypt(encrypted_str)
                credentials_dict = json.loads(decrypted)
        except:
            logger.warning(f"Failed to load existing credentials for tenant {tenant.id}, creating new")
            credentials_dict = {}
    
    # Update API key
    credentials_dict["api_key"] = api_key
    
    # Encrypt and save as JSONB: {"encrypted": "base64_string"}
    encrypted_str = _get_encryptor().encrypt(json.dumps(credentials_dict))
    tenant.credentials_encrypted = {"encrypted": encrypted_str}
    
    logger.info(f"Updated Wildberries credentials for tenant {tenant.id}")


def update_google_credentials(
    tenant: Tenant, 
    sheet_id: str, 
    credentials_json: str,
    db_session=None
) -> None:
    """
    Update Google Sheets credentials for tenant.
    
    Args:
        tenant: Tenant model instance
        sheet_id: Google Sheet ID (optional if only updating credentials)
        credentials_json: Service account JSON credentials
        db_session: Optional database session to commit changes
    """
    # Update sheet ID if provided
    if sheet_id:
        tenant.google_sheet_id = sheet_id
    
    # Encrypt service account JSON and store in dedicated field
    encrypted_str = _get_encryptor().encrypt(credentials_json)
    tenant.google_service_account_encrypted = encrypted_str
    
    logger.info(f"Updated Google credentials for tenant {tenant.id}")
    
    # Commit if session provided
    if db_session:
        db_session.commit()


def get_encryptor() -> CredentialEncryptor:
    """Get global encryptor instance."""
    return _get_encryptor()
