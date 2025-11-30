"""
Password hashing and verification utilities.
"""

import bcrypt

from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class PasswordManager:
    """
    Manages password hashing and verification using bcrypt.
    """
    
    def __init__(self):
        """Initialize password manager."""
        self.rounds = 12  # Balance between security and performance
    
    def hash(self, password: str) -> str:
        """
        Hash a plaintext password.
        
        Args:
            password: Plaintext password
            
        Returns:
            Hashed password string
        """
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        
        # Bcrypt only accepts up to 72 bytes
        password_bytes = password.encode('utf-8')[:72]
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plaintext password to verify
            hashed_password: Hashed password to compare against
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            password_bytes = plain_password.encode('utf-8')[:72]
            hashed_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False
    
    def needs_rehash(self, hashed_password: str) -> bool:
        """
        Check if password hash needs to be updated.
        
        Args:
            hashed_password: Hashed password to check
            
        Returns:
            True if hash should be updated
        """
        # Simple check: if rounds is different, needs rehash
        try:
            return bcrypt.gensalt(rounds=self.rounds) != hashed_password[:29].encode('utf-8')
        except:
            return False


# Global password manager instance
_password_manager = PasswordManager()


def hash_password(password: str) -> str:
    """Convenience function to hash password."""
    return _password_manager.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Convenience function to verify password."""
    return _password_manager.verify(plain_password, hashed_password)
