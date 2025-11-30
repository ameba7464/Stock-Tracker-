"""
Unit tests for authentication and security
"""
import pytest
from datetime import datetime, timedelta
from jose import jwt

from stock_tracker.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from stock_tracker.core.config import get_settings


class TestPasswordHashing:
    """Test password hashing functionality"""
    
    def test_hash_password(self):
        """Test password hashing"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt prefix
    
    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        assert verify_password("WrongPassword!", hashed) is False
    
    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes (salt)"""
        password = "TestPassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestJWTTokens:
    """Test JWT token creation and validation"""
    
    def test_create_access_token(self):
        """Test access token creation"""
        data = {"sub": "test@example.com", "tenant_id": "test-tenant-123"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_refresh_token(self):
        """Test refresh token creation"""
        data = {"sub": "test@example.com"}
        token = create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_valid_token(self):
        """Test decoding valid token"""
        data = {"sub": "test@example.com", "tenant_id": "test-tenant-123"}
        token = create_access_token(data)
        
        decoded = decode_token(token)
        
        assert decoded["sub"] == "test@example.com"
        assert decoded["tenant_id"] == "test-tenant-123"
        assert "exp" in decoded
    
    def test_decode_expired_token(self):
        """Test decoding expired token"""
        settings = get_settings()
        data = {"sub": "test@example.com"}
        expires = datetime.utcnow() - timedelta(minutes=1)  # Expired
        
        token = jwt.encode(
            {**data, "exp": expires},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        with pytest.raises(Exception):  # Should raise JWTError
            decode_token(token)
    
    def test_decode_invalid_token(self):
        """Test decoding invalid token"""
        with pytest.raises(Exception):
            decode_token("invalid.token.here")
    
    def test_token_contains_expiration(self):
        """Test that token contains expiration time"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        decoded = decode_token(token)
        
        assert "exp" in decoded
        exp_time = datetime.fromtimestamp(decoded["exp"])
        assert exp_time > datetime.utcnow()


class TestEncryption:
    """Test data encryption/decryption"""
    
    def test_encrypt_decrypt_credentials(self):
        """Test encryption and decryption of credentials"""
        from stock_tracker.core.encryption import encrypt_data, decrypt_data
        
        original = "my-secret-api-key-12345"
        encrypted = encrypt_data(original)
        
        assert encrypted != original
        assert len(encrypted) > 0
        
        decrypted = decrypt_data(encrypted)
        assert decrypted == original
    
    def test_encrypt_empty_string(self):
        """Test encryption of empty string"""
        from stock_tracker.core.encryption import encrypt_data, decrypt_data
        
        original = ""
        encrypted = encrypt_data(original)
        decrypted = decrypt_data(encrypted)
        
        assert decrypted == original
    
    def test_encrypt_unicode_characters(self):
        """Test encryption of unicode characters"""
        from stock_tracker.core.encryption import encrypt_data, decrypt_data
        
        original = "Тестовый ключ API 🔑"
        encrypted = encrypt_data(original)
        decrypted = decrypt_data(encrypted)
        
        assert decrypted == original
