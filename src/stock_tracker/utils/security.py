"""
Security utilities for secure credential storage and data protection.

Implements encryption, secure storage, configuration validation,
and security best practices for the Stock Tracker application.
Focuses on protecting sensitive data like API keys and service account credentials.
"""

import os
import json
import base64
import hashlib
import secrets
import keyring
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.exceptions import SecurityError, ConfigurationError
from stock_tracker.utils.monitoring import get_monitoring_system


logger = get_logger(__name__)


@dataclass
class SecurityConfig:
    """Configuration for security features."""
    
    # Encryption settings
    encryption_enabled: bool = True
    key_derivation_iterations: int = 100000  # PBKDF2 iterations
    salt_length: int = 32  # Salt length in bytes
    
    # Credential storage
    use_system_keyring: bool = True  # Use OS keyring when available
    fallback_to_file: bool = True   # Fallback to encrypted file storage
    credentials_file: str = "credentials.enc"
    
    # Security validation
    validate_permissions: bool = True
    min_password_entropy: float = 3.0  # Minimum entropy for passwords
    require_https: bool = True
    
    # Audit and logging
    audit_enabled: bool = True
    log_access_attempts: bool = True
    mask_sensitive_logs: bool = True


class CredentialEncryption:
    """
    Handles encryption and decryption of sensitive credentials.
    
    Uses Fernet (AES 128) with PBKDF2 key derivation for secure encryption.
    """
    
    def __init__(self, master_password: Optional[str] = None):
        """
        Initialize encryption with master password.
        
        Args:
            master_password: Master password for encryption (None to auto-generate)
        """
        self.monitoring = get_monitoring_system()
        self._master_password = master_password
        self._fernet_key: Optional[bytes] = None
        self._salt: Optional[bytes] = None
        
        if master_password:
            self._derive_key(master_password.encode())
    
    def _derive_key(self, password: bytes, salt: Optional[bytes] = None) -> None:
        """
        Derive encryption key from password using PBKDF2.
        
        Args:
            password: Master password as bytes
            salt: Salt for key derivation (generates new if None)
        """
        if salt is None:
            self._salt = secrets.token_bytes(SecurityConfig.salt_length)
        else:
            self._salt = salt
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=SecurityConfig.key_derivation_iterations,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self._fernet_key = key
        
        logger.debug("Encryption key derived successfully")
    
    def encrypt_data(self, data: Union[str, Dict[str, Any]]) -> Dict[str, str]:
        """
        Encrypt sensitive data.
        
        Args:
            data: Data to encrypt (string or dict)
            
        Returns:
            Dict with encrypted data and metadata
        """
        if self._fernet_key is None:
            raise SecurityError("Encryption not initialized")
        
        try:
            # Convert to JSON if dict
            if isinstance(data, dict):
                data_str = json.dumps(data, separators=(',', ':'))
            else:
                data_str = str(data)
            
            # Encrypt
            fernet = Fernet(self._fernet_key)
            encrypted_data = fernet.encrypt(data_str.encode())
            
            # Return with metadata
            result = {
                "encrypted_data": base64.b64encode(encrypted_data).decode(),
                "salt": base64.b64encode(self._salt).decode(),
                "version": "1.0",
                "algorithm": "fernet_pbkdf2"
            }
            
            self.monitoring.record_metric("security.encryption_success", 1)
            logger.debug("Data encrypted successfully")
            
            return result
            
        except Exception as e:
            self.monitoring.record_metric("security.encryption_failed", 1)
            logger.error(f"Encryption failed: {e}")
            raise SecurityError(f"Failed to encrypt data: {e}")
    
    def decrypt_data(self, encrypted_data: Dict[str, str]) -> Union[str, Dict[str, Any]]:
        """
        Decrypt sensitive data.
        
        Args:
            encrypted_data: Dict with encrypted data and metadata
            
        Returns:
            Decrypted data (attempts to parse as JSON)
        """
        if self._fernet_key is None:
            raise SecurityError("Encryption not initialized")
        
        try:
            # Extract components
            data_bytes = base64.b64decode(encrypted_data["encrypted_data"])
            
            # Decrypt
            fernet = Fernet(self._fernet_key)
            decrypted_bytes = fernet.decrypt(data_bytes)
            decrypted_str = decrypted_bytes.decode()
            
            # Try to parse as JSON
            try:
                result = json.loads(decrypted_str)
            except json.JSONDecodeError:
                result = decrypted_str
            
            self.monitoring.record_metric("security.decryption_success", 1)
            logger.debug("Data decrypted successfully")
            
            return result
            
        except Exception as e:
            self.monitoring.record_metric("security.decryption_failed", 1)
            logger.error(f"Decryption failed: {e}")
            raise SecurityError(f"Failed to decrypt data: {e}")
    
    @classmethod
    def from_password(cls, password: str) -> 'CredentialEncryption':
        """Create encryption instance from password."""
        return cls(password)
    
    @classmethod
    def from_encrypted_metadata(cls, password: str, metadata: Dict[str, str]) -> 'CredentialEncryption':
        """Create encryption instance from saved metadata."""
        instance = cls()
        salt = base64.b64decode(metadata["salt"])
        instance._derive_key(password.encode(), salt)
        return instance


class SecureCredentialStore:
    """
    Secure storage for sensitive credentials using multiple storage backends.
    
    Priority order:
    1. System keyring (if available and enabled)
    2. Encrypted file storage
    3. Environment variables (least secure, warnings issued)
    """
    
    def __init__(self, config: SecurityConfig = None):
        """
        Initialize secure credential store.
        
        Args:
            config: Security configuration
        """
        self.config = config or SecurityConfig()
        self.monitoring = get_monitoring_system()
        self._encryption: Optional[CredentialEncryption] = None
        self._credentials_path = Path(self.config.credentials_file)
        
        logger.info(f"Initialized SecureCredentialStore (keyring: {self.config.use_system_keyring}, "
                   f"file: {self.config.fallback_to_file})")
    
    def _init_encryption(self, master_password: str) -> None:
        """Initialize encryption if not already done."""
        if self._encryption is None:
            self._encryption = CredentialEncryption.from_password(master_password)
    
    def _get_keyring_service_name(self) -> str:
        """Get service name for keyring storage."""
        return "stock-tracker-wildberries"
    
    def store_credential(self, key: str, value: Union[str, Dict[str, Any]], 
                        master_password: Optional[str] = None) -> bool:
        """
        Store credential securely.
        
        Args:
            key: Credential identifier
            value: Credential data
            master_password: Master password for encryption
            
        Returns:
            True if stored successfully
        """
        try:
            self.monitoring.record_metric("security.credential_store_attempt", 1, {"key": key})
            
            # Try system keyring first
            if self.config.use_system_keyring:
                try:
                    # For keyring, store as JSON string
                    if isinstance(value, dict):
                        stored_value = json.dumps(value)
                    else:
                        stored_value = str(value)
                    
                    keyring.set_password(self._get_keyring_service_name(), key, stored_value)
                    
                    logger.info(f"Credential '{key}' stored in system keyring")
                    self.monitoring.record_metric("security.keyring_store_success", 1)
                    return True
                    
                except Exception as e:
                    logger.warning(f"Keyring storage failed for '{key}': {e}")
                    self.monitoring.record_metric("security.keyring_store_failed", 1)
            
            # Fallback to encrypted file storage
            if self.config.fallback_to_file:
                if not master_password:
                    raise SecurityError("Master password required for file encryption")
                
                self._init_encryption(master_password)
                
                # Load existing credentials
                existing_creds = self._load_encrypted_file(master_password)
                
                # Add/update credential
                existing_creds[key] = value
                
                # Save back to file
                self._save_encrypted_file(existing_creds, master_password)
                
                logger.info(f"Credential '{key}' stored in encrypted file")
                self.monitoring.record_metric("security.file_store_success", 1)
                return True
            
            raise SecurityError("No secure storage backend available")
            
        except Exception as e:
            logger.error(f"Failed to store credential '{key}': {e}")
            self.monitoring.record_metric("security.credential_store_failed", 1)
            raise SecurityError(f"Credential storage failed: {e}")
    
    def retrieve_credential(self, key: str, 
                          master_password: Optional[str] = None) -> Optional[Union[str, Dict[str, Any]]]:
        """
        Retrieve credential securely.
        
        Args:
            key: Credential identifier
            master_password: Master password for decryption
            
        Returns:
            Credential data or None if not found
        """
        try:
            self.monitoring.record_metric("security.credential_retrieve_attempt", 1, {"key": key})
            
            # Try system keyring first
            if self.config.use_system_keyring:
                try:
                    stored_value = keyring.get_password(self._get_keyring_service_name(), key)
                    if stored_value:
                        # Try to parse as JSON
                        try:
                            result = json.loads(stored_value)
                        except json.JSONDecodeError:
                            result = stored_value
                        
                        logger.debug(f"Retrieved credential '{key}' from system keyring")
                        self.monitoring.record_metric("security.keyring_retrieve_success", 1)
                        return result
                        
                except Exception as e:
                    logger.debug(f"Keyring retrieval failed for '{key}': {e}")
            
            # Try encrypted file storage
            if self.config.fallback_to_file and self._credentials_path.exists():
                if not master_password:
                    logger.warning(f"Master password required to retrieve '{key}' from encrypted file")
                    return None
                
                try:
                    credentials = self._load_encrypted_file(master_password)
                    if key in credentials:
                        logger.debug(f"Retrieved credential '{key}' from encrypted file")
                        self.monitoring.record_metric("security.file_retrieve_success", 1)
                        return credentials[key]
                
                except Exception as e:
                    logger.error(f"Failed to load from encrypted file: {e}")
            
            # Try environment variables as last resort
            env_key = f"STOCK_TRACKER_{key.upper()}"
            env_value = os.getenv(env_key)
            if env_value:
                logger.warning(f"Retrieved credential '{key}' from environment variable (least secure)")
                self.monitoring.record_metric("security.env_retrieve_success", 1)
                return env_value
            
            logger.debug(f"Credential '{key}' not found in any storage")
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve credential '{key}': {e}")
            self.monitoring.record_metric("security.credential_retrieve_failed", 1)
            return None
    
    def _load_encrypted_file(self, master_password: str) -> Dict[str, Any]:
        """Load credentials from encrypted file."""
        if not self._credentials_path.exists():
            return {}
        
        try:
            with open(self._credentials_path, 'r') as f:
                encrypted_data = json.load(f)
            
            encryption = CredentialEncryption.from_encrypted_metadata(
                master_password, encrypted_data
            )
            
            decrypted_data = encryption.decrypt_data(encrypted_data)
            return decrypted_data if isinstance(decrypted_data, dict) else {}
            
        except Exception as e:
            logger.error(f"Failed to load encrypted file: {e}")
            raise SecurityError(f"Could not load credentials file: {e}")
    
    def _save_encrypted_file(self, credentials: Dict[str, Any], master_password: str) -> None:
        """Save credentials to encrypted file."""
        try:
            # Ensure directory exists
            self._credentials_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize encryption
            self._init_encryption(master_password)
            
            # Encrypt data
            encrypted_data = self._encryption.encrypt_data(credentials)
            
            # Save to file
            with open(self._credentials_path, 'w') as f:
                json.dump(encrypted_data, f, indent=2)
            
            # Set restrictive permissions
            if self.config.validate_permissions:
                os.chmod(self._credentials_path, 0o600)  # Read/write for owner only
            
            logger.debug("Credentials saved to encrypted file")
            
        except Exception as e:
            logger.error(f"Failed to save encrypted file: {e}")
            raise SecurityError(f"Could not save credentials file: {e}")
    
    def list_stored_credentials(self, master_password: Optional[str] = None) -> List[str]:
        """
        List all stored credential keys.
        
        Args:
            master_password: Master password for file access
            
        Returns:
            List of credential keys
        """
        keys = set()
        
        # From encrypted file
        if self.config.fallback_to_file and self._credentials_path.exists() and master_password:
            try:
                credentials = self._load_encrypted_file(master_password)
                keys.update(credentials.keys())
            except Exception as e:
                logger.debug(f"Could not list file credentials: {e}")
        
        # From environment (scan known patterns)
        for env_key in os.environ:
            if env_key.startswith("STOCK_TRACKER_"):
                clean_key = env_key[14:].lower()  # Remove prefix and lowercase
                keys.add(clean_key)
        
        return sorted(list(keys))
    
    def delete_credential(self, key: str, master_password: Optional[str] = None) -> bool:
        """
        Delete stored credential.
        
        Args:
            key: Credential identifier
            master_password: Master password for file access
            
        Returns:
            True if deleted successfully
        """
        success = False
        
        # From keyring
        if self.config.use_system_keyring:
            try:
                keyring.delete_password(self._get_keyring_service_name(), key)
                success = True
                logger.info(f"Deleted credential '{key}' from keyring")
            except Exception as e:
                logger.debug(f"Keyring deletion failed: {e}")
        
        # From encrypted file
        if self.config.fallback_to_file and self._credentials_path.exists() and master_password:
            try:
                credentials = self._load_encrypted_file(master_password)
                if key in credentials:
                    del credentials[key]
                    self._save_encrypted_file(credentials, master_password)
                    success = True
                    logger.info(f"Deleted credential '{key}' from encrypted file")
            except Exception as e:
                logger.debug(f"File deletion failed: {e}")
        
        if success:
            self.monitoring.record_metric("security.credential_delete_success", 1)
        else:
            self.monitoring.record_metric("security.credential_delete_failed", 1)
        
        return success


class SecurityValidator:
    """
    Validates security configuration and practices.
    """
    
    def __init__(self, config: SecurityConfig = None):
        self.config = config or SecurityConfig()
        self.monitoring = get_monitoring_system()
    
    def validate_configuration(self, config_data: Dict[str, Any]) -> List[str]:
        """
        Validate configuration for security issues.
        
        Args:
            config_data: Configuration dictionary
            
        Returns:
            List of security warnings/issues
        """
        warnings = []
        
        try:
            # Check for hardcoded credentials
            sensitive_keys = ['api_key', 'secret', 'password', 'token', 'credential']
            for key, value in self._flatten_dict(config_data).items():
                if isinstance(value, str) and any(sk in key.lower() for sk in sensitive_keys):
                    if len(value) > 10:  # Likely a real credential
                        warnings.append(f"Potential hardcoded credential in config: {key}")
            
            # Check for insecure URLs
            if self.config.require_https:
                url_keys = ['url', 'endpoint', 'host', 'server']
                for key, value in self._flatten_dict(config_data).items():
                    if isinstance(value, str) and any(uk in key.lower() for uk in url_keys):
                        if value.startswith('http://'):
                            warnings.append(f"Insecure HTTP URL in config: {key}")
            
            # Check file permissions
            if self.config.validate_permissions:
                config_files = ['config.json', 'credentials.json', '.env']
                for filename in config_files:
                    if Path(filename).exists():
                        stat = os.stat(filename)
                        if stat.st_mode & 0o077:  # Check if group/others have access
                            warnings.append(f"Insecure file permissions: {filename}")
            
            self.monitoring.record_metric("security.validation_completed", 1, 
                                        {"warnings_count": len(warnings)})
            
            return warnings
            
        except Exception as e:
            logger.error(f"Security validation failed: {e}")
            return [f"Security validation error: {e}"]
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '') -> Dict[str, Any]:
        """Flatten nested dictionary for easier searching."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def check_password_strength(self, password: str) -> Dict[str, Any]:
        """
        Check password strength and entropy.
        
        Args:
            password: Password to check
            
        Returns:
            Dict with strength analysis
        """
        import math
        from collections import Counter
        
        # Calculate entropy
        char_counts = Counter(password)
        entropy = -sum((count / len(password)) * math.log2(count / len(password)) 
                      for count in char_counts.values())
        
        # Check criteria
        criteria = {
            "length": len(password) >= 12,
            "uppercase": any(c.isupper() for c in password),
            "lowercase": any(c.islower() for c in password),
            "digits": any(c.isdigit() for c in password),
            "special": any(not c.isalnum() for c in password),
            "entropy": entropy >= self.config.min_password_entropy
        }
        
        strength_score = sum(criteria.values()) / len(criteria)
        
        if strength_score >= 0.8:
            strength = "strong"
        elif strength_score >= 0.6:
            strength = "medium"
        else:
            strength = "weak"
        
        return {
            "strength": strength,
            "score": strength_score,
            "entropy": entropy,
            "criteria": criteria,
            "recommendations": self._get_password_recommendations(criteria)
        }
    
    def _get_password_recommendations(self, criteria: Dict[str, bool]) -> List[str]:
        """Get password improvement recommendations."""
        recommendations = []
        
        if not criteria["length"]:
            recommendations.append("Use at least 12 characters")
        if not criteria["uppercase"]:
            recommendations.append("Include uppercase letters")
        if not criteria["lowercase"]:
            recommendations.append("Include lowercase letters")
        if not criteria["digits"]:
            recommendations.append("Include numbers")
        if not criteria["special"]:
            recommendations.append("Include special characters")
        if not criteria["entropy"]:
            recommendations.append("Increase character variety for higher entropy")
        
        return recommendations


# Global secure credential store
_credential_store: Optional[SecureCredentialStore] = None


def get_credential_store(config: SecurityConfig = None) -> SecureCredentialStore:
    """Get global secure credential store instance."""
    global _credential_store
    
    if _credential_store is None:
        _credential_store = SecureCredentialStore(config)
    
    return _credential_store


@contextmanager
def secure_temporary_file(content: str = "", suffix: str = ".tmp"):
    """
    Context manager for creating secure temporary files.
    
    Args:
        content: Initial content for the file
        suffix: File suffix
        
    Yields:
        Path to the temporary file
    """
    import tempfile
    
    # Create secure temporary file
    fd, temp_path = tempfile.mkstemp(suffix=suffix)
    temp_file = Path(temp_path)
    
    try:
        # Set restrictive permissions
        os.chmod(temp_path, 0o600)
        
        # Write initial content
        if content:
            with os.fdopen(fd, 'w') as f:
                f.write(content)
        else:
            os.close(fd)
        
        yield temp_file
        
    finally:
        # Secure cleanup
        if temp_file.exists():
            # Overwrite with random data before deletion
            try:
                file_size = temp_file.stat().st_size
                with open(temp_file, 'wb') as f:
                    f.write(secrets.token_bytes(file_size))
                temp_file.unlink()
            except Exception as e:
                logger.warning(f"Secure file cleanup failed: {e}")
                # Fallback to regular deletion
                try:
                    temp_file.unlink()
                except Exception:
                    pass


# Example usage and testing
if __name__ == "__main__":
    
    def test_credential_encryption():
        """Test credential encryption functionality."""
        
        print("🔐 Testing Credential Encryption...")
        
        # Test data
        test_credentials = {
            "api_key": "test_api_key_12345",
            "service_account": {
                "type": "service_account",
                "project_id": "test-project",
                "private_key": "-----BEGIN PRIVATE KEY-----\ntest_key\n-----END PRIVATE KEY-----\n"
            }
        }
        
        # Test encryption
        encryption = CredentialEncryption.from_password("test_master_password")
        
        encrypted_data = encryption.encrypt_data(test_credentials)
        print(f"✅ Encrypted data: {len(encrypted_data['encrypted_data'])} bytes")
        
        # Test decryption
        decrypted_data = encryption.decrypt_data(encrypted_data)
        print(f"✅ Decrypted data matches: {decrypted_data == test_credentials}")
        
        return True
    
    def test_secure_storage():
        """Test secure credential storage."""
        
        print("🗄️ Testing Secure Storage...")
        
        config = SecurityConfig(
            use_system_keyring=False,  # Disable for testing
            fallback_to_file=True
        )
        
        store = SecureCredentialStore(config)
        
        # Store credential
        test_key = "test_api_key"
        test_value = {"key": "secret_value", "endpoint": "https://api.test.com"}
        
        success = store.store_credential(test_key, test_value, "test_password")
        print(f"✅ Storage success: {success}")
        
        # Retrieve credential
        retrieved = store.retrieve_credential(test_key, "test_password")
        print(f"✅ Retrieved matches: {retrieved == test_value}")
        
        # List credentials
        keys = store.list_stored_credentials("test_password")
        print(f"✅ Found keys: {keys}")
        
        # Clean up
        store.delete_credential(test_key, "test_password")
        
        return True
    
    def test_security_validation():
        """Test security validation."""
        
        print("🛡️ Testing Security Validation...")
        
        validator = SecurityValidator()
        
        # Test config validation
        test_config = {
            "api_key": "hardcoded_api_key_12345",
            "database": {
                "url": "http://insecure.example.com",
                "password": "weak"
            }
        }
        
        warnings = validator.validate_configuration(test_config)
        print(f"✅ Found {len(warnings)} security warnings")
        
        # Test password strength
        passwords = ["weak", "StrongPassword123!", "Sup3r_S3cur3_P@ssw0rd!"]
        
        for password in passwords:
            strength = validator.check_password_strength(password)
            print(f"✅ Password '{password}' strength: {strength['strength']}")
        
        return True
    
    # Run tests
    try:
        test_credential_encryption()
        test_secure_storage()
        test_security_validation()
        print("🎉 All security tests completed!")
        
    except Exception as e:
        print(f"❌ Security test failed: {e}")