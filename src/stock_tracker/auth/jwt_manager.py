"""
JWT token management for authentication.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid

from jose import JWTError, jwt

from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class JWTManager:
    """
    Manages JWT token creation and verification.
    
    Uses RS256 (asymmetric) algorithm for better security in distributed systems.
    """
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 30
    ):
        """
        Initialize JWT manager.
        
        Args:
            secret_key: Secret key for signing tokens
            algorithm: Algorithm to use (HS256 or RS256)
            access_token_expire_minutes: Access token TTL in minutes
            refresh_token_expire_days: Refresh token TTL in days
        """
        self.secret_key = secret_key or os.getenv("SECRET_KEY")
        if not self.secret_key:
            raise ValueError("SECRET_KEY environment variable is required for JWT")
        
        self.algorithm = algorithm
        self.access_token_expire = timedelta(minutes=access_token_expire_minutes)
        self.refresh_token_expire = timedelta(days=refresh_token_expire_days)
        
        logger.info(f"Initialized JWT manager (algorithm={algorithm}, access_ttl={access_token_expire_minutes}m)")
    
    def create_access_token(
        self,
        user_id: str,
        tenant_id: str,
        role: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create access token for authenticated user.
        
        Args:
            user_id: User UUID
            tenant_id: Tenant UUID
            role: User role (owner, admin, user, viewer)
            additional_claims: Optional additional claims to include
            
        Returns:
            JWT access token string
        """
        now = datetime.utcnow()
        expires = now + self.access_token_expire
        
        payload = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "type": "access",
            "iat": now,
            "exp": expires,
            "jti": str(uuid.uuid4())  # Unique token ID
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.debug(f"Created access token for user {user_id} (expires in {self.access_token_expire})")
        
        return token
    
    def create_refresh_token(self, user_id: str) -> str:
        """
        Create refresh token for renewing access tokens.
        
        Args:
            user_id: User UUID
            
        Returns:
            JWT refresh token string
        """
        now = datetime.utcnow()
        expires = now + self.refresh_token_expire
        
        payload = {
            "sub": user_id,
            "type": "refresh",
            "iat": now,
            "exp": expires,
            "jti": str(uuid.uuid4())
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.debug(f"Created refresh token for user {user_id} (expires in {self.refresh_token_expire})")
        
        return token
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token string
            token_type: Expected token type (access or refresh)
            
        Returns:
            Decoded token payload
            
        Raises:
            JWTError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Verify token type
            if payload.get("type") != token_type:
                raise JWTError(f"Invalid token type: expected {token_type}, got {payload.get('type')}")
            
            return payload
            
        except JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            raise
    
    def decode_token_unsafe(self, token: str) -> Dict[str, Any]:
        """
        Decode token without verification (for debugging only).
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded payload (unverified)
        """
        return jwt.decode(
            token,
            options={"verify_signature": False}
        )


# Global JWT manager instance
_jwt_manager: Optional[JWTManager] = None


def get_jwt_manager() -> JWTManager:
    """Get or create global JWT manager instance."""
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager


def create_access_token(user_id: str, tenant_id: str, role: str) -> str:
    """Convenience function to create access token."""
    return get_jwt_manager().create_access_token(user_id, tenant_id, role)


def create_refresh_token(user_id: str) -> str:
    """Convenience function to create refresh token."""
    return get_jwt_manager().create_refresh_token(user_id)


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Convenience function to verify token."""
    return get_jwt_manager().verify_token(token, token_type)
