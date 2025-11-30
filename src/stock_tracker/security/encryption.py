"""
Encryption utilities for securing sensitive credentials.

Uses Fernet symmetric encryption with master key rotation support.
"""

import os
import base64
from typing import Optional

from cryptography.fernet import Fernet, MultiFernet, InvalidToken

from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class CredentialEncryptor:
    """
    Encrypts and decrypts sensitive credentials using Fernet.
    
    Supports key rotation through MultiFernet for zero-downtime updates.
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryptor with master key.
        
        Args:
            master_key: Base64-encoded Fernet key. If None, loads from env.
        """
        self.master_key = master_key or os.getenv("ENCRYPTION_MASTER_KEY")
        
        if not self.master_key:
            raise ValueError(
                "ENCRYPTION_MASTER_KEY environment variable is required. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        
        # Support multiple keys for rotation
        self.keys = self._load_keys()
        self.fernet = MultiFernet([Fernet(key) for key in self.keys])
        
        logger.info(f"Initialized credential encryptor with {len(self.keys)} key(s)")
    
    def _load_keys(self) -> list[bytes]:
        """
        Load encryption keys from environment.
        
        Supports ENCRYPTION_MASTER_KEY (primary) and ENCRYPTION_SECONDARY_KEY (rotation).
        """
        keys = []
        
        # Primary key (required)
        primary = self.master_key.encode() if isinstance(self.master_key, str) else self.master_key
        keys.append(primary)
        
        # Secondary key for rotation (optional)
        secondary = os.getenv("ENCRYPTION_SECONDARY_KEY")
        if secondary:
            keys.append(secondary.encode() if isinstance(secondary, str) else secondary)
            logger.info("Secondary encryption key loaded for rotation")
        
        return keys
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")
        
        encrypted_bytes = self.fernet.encrypt(plaintext.encode())
        return encrypted_bytes.decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string.
        
        Args:
            ciphertext: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            InvalidToken: If decryption fails
        """
        if not ciphertext:
            raise ValueError("Cannot decrypt empty string")
        
        try:
            decrypted_bytes = self.fernet.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except InvalidToken as e:
            logger.error("Decryption failed - invalid token or corrupted data")
            raise
    
    def rotate_key(self, new_key: str) -> None:
        """
        Add new encryption key for rotation.
        
        Args:
            new_key: New Fernet key to add
        """
        new_key_bytes = new_key.encode() if isinstance(new_key, str) else new_key
        self.keys.insert(0, new_key_bytes)  # New key becomes primary
        self.fernet = MultiFernet([Fernet(key) for key in self.keys])
        
        logger.info(f"Key rotation complete - now using {len(self.keys)} keys")
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.
        
        Returns:
            Base64-encoded Fernet key
        """
        return Fernet.generate_key().decode()


# Global encryptor instance
_encryptor: Optional[CredentialEncryptor] = None


def get_encryptor() -> CredentialEncryptor:
    """Get or create global encryptor instance."""
    global _encryptor
    if _encryptor is None:
        _encryptor = CredentialEncryptor()
    return _encryptor


def encrypt_credential(plaintext: str) -> str:
    """Convenience function to encrypt credential."""
    return get_encryptor().encrypt(plaintext)


def decrypt_credential(ciphertext: str) -> str:
    """Convenience function to decrypt credential."""
    return get_encryptor().decrypt(ciphertext)
