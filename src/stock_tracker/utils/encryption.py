"""
Encryption utilities for sensitive data (API keys, tokens).

Uses Fernet (symmetric encryption) from cryptography library.
Encryption key should be stored in environment variables, never in code.
"""

import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class EncryptionService:
    """
    Service for encrypting/decrypting sensitive data.
    
    Uses Fernet symmetric encryption (AES 128 in CBC mode).
    Automatically handles base64 encoding/decoding.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption service.
        
        Args:
            encryption_key: Base64-encoded 32-byte key. If None, reads from env.
        
        Raises:
            ValueError: If encryption key is not provided or invalid.
        """
        # Get encryption key from parameter or environment
        key = encryption_key or os.getenv("ENCRYPTION_KEY")
        
        if not key:
            raise ValueError(
                "ENCRYPTION_KEY not found. Generate with: "
                "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        
        try:
            # Validate key format
            if isinstance(key, str):
                key_bytes = key.encode('utf-8')
            else:
                key_bytes = key
            
            # Fernet key must be 44 bytes (32 bytes after base64 decode)
            if len(key_bytes) != 44:
                raise ValueError(
                    f"Invalid ENCRYPTION_KEY length: {len(key_bytes)} bytes. "
                    f"Expected 44 bytes. Generate a new key with: "
                    f"python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )
            
            # Validate and create Fernet instance
            self.cipher = Fernet(key_bytes)
            logger.info("Encryption service initialized successfully")
        except ValueError:
            # Re-raise ValueError with our custom message
            raise
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise ValueError(f"Invalid ENCRYPTION_KEY format: {e}")
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.
        
        Args:
            plaintext: String to encrypt (e.g., API key)
        
        Returns:
            Base64-encoded encrypted string
        
        Raises:
            ValueError: If plaintext is empty
        """
        if not plaintext or not plaintext.strip():
            raise ValueError("Cannot encrypt empty string")
        
        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode('utf-8'))
            encrypted_str = encrypted_bytes.decode('utf-8')
            logger.debug("Successfully encrypted data")
            return encrypted_str
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt encrypted string.
        
        Args:
            encrypted: Base64-encoded encrypted string
        
        Returns:
            Original plaintext string
        
        Raises:
            ValueError: If decryption fails (wrong key or corrupted data)
        """
        if not encrypted or not encrypted.strip():
            raise ValueError("Cannot decrypt empty string")
        
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted.encode('utf-8'))
            plaintext = decrypted_bytes.decode('utf-8')
            logger.debug("Successfully decrypted data")
            return plaintext
        except InvalidToken:
            logger.error("Decryption failed: Invalid token or wrong encryption key")
            raise ValueError("Decryption failed: Invalid token or wrong key")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_api_key(self, api_key: str) -> str:
        """
        Encrypt API key (convenience method with validation).
        
        Args:
            api_key: Wildberries or other marketplace API key
        
        Returns:
            Encrypted API key as base64 string
        """
        if len(api_key) < 10:
            raise ValueError("API key seems too short, check input")
        
        return self.encrypt(api_key)
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """
        Decrypt API key (convenience method).
        
        Args:
            encrypted_key: Encrypted API key
        
        Returns:
            Original API key
        """
        return self.decrypt(encrypted_key)


# Global singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Get global encryption service instance (singleton pattern).
    
    Returns:
        EncryptionService instance
    
    Raises:
        ValueError: If ENCRYPTION_KEY not configured
    """
    global _encryption_service
    
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    
    return _encryption_service


def encrypt_data(plaintext: str) -> str:
    """
    Convenience function to encrypt data.
    
    Args:
        plaintext: String to encrypt
    
    Returns:
        Encrypted string
    """
    service = get_encryption_service()
    return service.encrypt(plaintext)


def decrypt_data(encrypted: str) -> str:
    """
    Convenience function to decrypt data.
    
    Args:
        encrypted: Encrypted string
    
    Returns:
        Decrypted plaintext
    """
    service = get_encryption_service()
    return service.decrypt(encrypted)


def generate_encryption_key() -> str:
    """
    Generate new encryption key for ENCRYPTION_KEY environment variable.
    
    Returns:
        Base64-encoded 32-byte key
    
    Example:
        >>> key = generate_encryption_key()
        >>> print(f"Add to .env: ENCRYPTION_KEY={key}")
    """
    key = Fernet.generate_key()
    return key.decode('utf-8')


if __name__ == "__main__":
    # Generate key for setup
    print("=" * 60)
    print("ENCRYPTION KEY GENERATOR")
    print("=" * 60)
    key = generate_encryption_key()
    print(f"\nAdd this to your .env file:")
    print(f"ENCRYPTION_KEY={key}")
    print("\n" + "=" * 60)
    print("KEEP THIS KEY SECURE! Loss = data loss")
    print("=" * 60)
