"""
Helper functions for working with encrypted API keys.

Provides convenience methods for encrypting/decrypting API keys
when working with User models.
"""

from typing import Optional

from stock_tracker.database.models import User
from stock_tracker.utils.encryption import get_encryption_service
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


def get_api_key(user: User) -> Optional[str]:
    """
    Get decrypted API key for user.
    
    Tries encrypted field first, falls back to plaintext if available.
    
    Args:
        user: User model instance
    
    Returns:
        Decrypted API key or None if not set
    """
    if user.wb_api_key_encrypted:
        try:
            encryption_service = get_encryption_service()
            return encryption_service.decrypt(user.wb_api_key_encrypted)
        except Exception as e:
            logger.error(f"Failed to decrypt API key for user {user.id}: {e}")
            # Fall through to plaintext
    
    # Fallback to plaintext (for backward compatibility during migration)
    if user.wb_api_key:
        logger.warning(f"Using plaintext API key for user {user.id} - should be encrypted")
        return user.wb_api_key
    
    return None


def set_api_key(user: User, api_key: str) -> None:
    """
    Set encrypted API key for user.
    
    Encrypts the API key and stores in wb_api_key_encrypted field.
    Optionally clears plaintext field.
    
    Args:
        user: User model instance
        api_key: Plaintext API key to encrypt and store
    
    Raises:
        ValueError: If encryption fails
    """
    if not api_key or not api_key.strip():
        raise ValueError("API key cannot be empty")
    
    try:
        encryption_service = get_encryption_service()
        encrypted = encryption_service.encrypt(api_key)
        
        user.wb_api_key_encrypted = encrypted
        # Clear plaintext version for security
        user.wb_api_key = None
        
        logger.info(f"Set encrypted API key for user {user.id}")
        
    except Exception as e:
        logger.error(f"Failed to set encrypted API key for user {user.id}: {e}")
        raise ValueError(f"Failed to encrypt API key: {e}")


def has_api_key(user: User) -> bool:
    """
    Check if user has an API key configured (encrypted or plaintext).
    
    Args:
        user: User model instance
    
    Returns:
        True if user has API key, False otherwise
    """
    return bool(user.wb_api_key_encrypted or user.wb_api_key)


def rotate_api_key(user: User, new_api_key: str, db_session) -> None:
    """
    Rotate API key for user with audit logging.
    
    Args:
        user: User model instance
        new_api_key: New API key to set
        db_session: Database session for committing changes
    
    Raises:
        ValueError: If rotation fails
    """
    old_key_exists = has_api_key(user)
    
    try:
        set_api_key(user, new_api_key)
        db_session.commit()
        
        logger.info(
            f"API key rotated for user {user.id} "
            f"({'replaced' if old_key_exists else 'set initial'})"
        )
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to rotate API key for user {user.id}: {e}")
        raise


# For backward compatibility during migration period
def get_api_key_legacy(user: User) -> Optional[str]:
    """
    Legacy method - returns plaintext key if available.
    
    Use get_api_key() instead for automatic decryption.
    
    Args:
        user: User model instance
    
    Returns:
        Plaintext API key or None
    """
    return user.wb_api_key
