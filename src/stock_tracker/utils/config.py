"""
Configuration management for Wildberries Stock Tracker.

Provides centralized configuration loading and validation using Pydantic models.
Supports environment variables, secure credential storage, and validates required 
settings for all services with enhanced security features.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

try:
    # For Pydantic v2
    from pydantic import BaseModel, Field
    from pydantic_settings import BaseSettings
    from pydantic import field_validator
    from pydantic import model_validator
    PYDANTIC_V2 = True
except ImportError:
    # For Pydantic v1
    from pydantic import BaseModel, Field, validator, root_validator
    from pydantic.env_settings import BaseSettings
    field_validator = None
    model_validator = None
    PYDANTIC_V2 = False

from stock_tracker.utils.logger import get_logger


logger = get_logger(__name__)


class WildberriesAPIConfig(BaseModel):
    """Wildberries API configuration."""
    
    api_key: str = Field(..., description="Wildberries API key")
    base_url: str = Field(
        default="https://seller-analytics-api.wildberries.ru",
        description="Wildberries API base URL"
    )
    statistics_base_url: str = Field(
        default="https://statistics-api.wildberries.ru",
        description="Wildberries Statistics API base URL"
    )
    timeout: int = Field(default=30, description="API request timeout in seconds")
    rate_limit: int = Field(default=60, description="API rate limit per minute")
    retry_count: int = Field(default=3, description="Number of retry attempts")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")
    max_concurrent_requests: int = Field(default=5, description="Max concurrent API requests")
    
    if PYDANTIC_V2:
        @field_validator('api_key')
        @classmethod
        def validate_api_key(cls, v):
            if not v or len(v.strip()) == 0:
                raise ValueError("Wildberries API key is required")
            return v.strip()
        
        @field_validator('timeout')
        @classmethod
        def validate_timeout(cls, v):
            if v <= 0:
                raise ValueError("Timeout must be positive")
            return v
    else:
        @validator('api_key')
        def validate_api_key(cls, v):
            if not v or len(v.strip()) == 0:
                raise ValueError("Wildberries API key is required")
            return v.strip()
        
        @validator('timeout')
        def validate_timeout(cls, v):
            if v <= 0:
                raise ValueError("Timeout must be positive")
            return v


class GoogleSheetsConfig(BaseModel):
    """Google Sheets API configuration."""
    
    service_account_key_path: str = Field(..., description="Path to service account JSON key")
    sheet_id: str = Field(..., description="Google Sheet ID")
    sheet_name: str = Field(default="Stock Tracker", description="Sheet name/tab")
    batch_size: int = Field(default=100, description="Batch size for operations")
    
    if PYDANTIC_V2:
        @field_validator('service_account_key_path')
        @classmethod
        def validate_service_account_path(cls, v):
            # Для Railway/Render: временный файл создается в __init__ StockTrackerConfig
            # Просто возвращаем путь без валидации существования
            return v
        
        @field_validator('sheet_id')
        @classmethod
        def validate_sheet_id(cls, v):
            if not v or len(v.strip()) == 0:
                raise ValueError("Google Sheet ID is required")
            return v.strip()
        
        @field_validator('batch_size')
        @classmethod
        def validate_batch_size(cls, v):
            if v <= 0:
                raise ValueError("Batch size must be positive")
            return v
    else:
        @validator('service_account_key_path')
        def validate_service_account_path(cls, v):
            # Для Railway/Render: временный файл создается в __init__ StockTrackerConfig
            # Просто возвращаем путь без валидации существования
            return v
        
        @validator('sheet_id')
        def validate_sheet_id(cls, v):
            if not v or len(v.strip()) == 0:
                raise ValueError("Google Sheet ID is required")
            return v.strip()
        
        @validator('batch_size')
        def validate_batch_size(cls, v):
            if v <= 0:
                raise ValueError("Batch size must be positive")
            return v


class ApplicationConfig(BaseModel):
    """General application configuration."""
    
    log_level: str = Field(default="INFO", description="Logging level")
    log_dir: str = Field(default="./logs", description="Log files directory")
    timezone: str = Field(default="UTC", description="Application timezone")
    debug_mode: bool = Field(default=False, description="Debug mode flag")
    dry_run: bool = Field(default=False, description="Dry run mode flag")
    mock_api: bool = Field(default=False, description="Mock API responses for testing")
    
    # Sync configuration
    sync_schedule: str = Field(default="0 0 * * *", description="Cron schedule for sync")
    auto_sync_enabled: bool = Field(default=True, description="Enable automatic sync")
    max_products_per_sync: int = Field(default=100, description="Max products per sync")
    
    if PYDANTIC_V2:
        @field_validator('log_level')
        @classmethod
        def validate_log_level(cls, v):
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if v.upper() not in valid_levels:
                raise ValueError(f"Log level must be one of: {valid_levels}")
            return v.upper()
        
        @field_validator('log_dir')
        @classmethod
        def validate_log_dir(cls, v):
            # Create log directory if it doesn't exist
            path = Path(v)
            path.mkdir(parents=True, exist_ok=True)
            return str(path.absolute())
        
        @field_validator('sync_schedule')
        @classmethod
        def validate_sync_schedule(cls, v):
            # Basic cron format validation (5 fields)
            parts = v.strip().split()
            if len(parts) != 5:
                raise ValueError("Sync schedule must be in cron format (5 fields)")
            return v.strip()
    else:
        @validator('log_level')
        def validate_log_level(cls, v):
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if v.upper() not in valid_levels:
                raise ValueError(f"Log level must be one of: {valid_levels}")
            return v.upper()
        
        @validator('log_dir')
        def validate_log_dir(cls, v):
            # Create log directory if it doesn't exist
            path = Path(v)
            path.mkdir(parents=True, exist_ok=True)
            return str(path.absolute())
        
        @validator('sync_schedule')
        def validate_sync_schedule(cls, v):
            # Basic cron format validation (5 fields)
            parts = v.strip().split()
            if len(parts) != 5:
                raise ValueError("Sync schedule must be in cron format (5 fields)")
            return v.strip()


class StockTrackerConfig(BaseSettings):
    """Main application configuration combining all sub-configurations."""
    
    # Load from environment with prefixes
    wildberries_api_key: str = Field(..., env="WILDBERRIES_API_KEY")
    wildberries_base_url: str = Field(
        default="https://seller-analytics-api.wildberries.ru",
        env="WILDBERRIES_BASE_URL"
    )
    wildberries_statistics_base_url: str = Field(
        default="https://statistics-api.wildberries.ru",
        env="WILDBERRIES_STATISTICS_BASE_URL"
    )
    wildberries_api_timeout: int = Field(default=30, env="WILDBERRIES_API_TIMEOUT")
    wildberries_rate_limit: int = Field(default=60, env="WILDBERRIES_RATE_LIMIT")
    
    google_service_account_key_path: Optional[str] = Field(default=None, env="GOOGLE_SERVICE_ACCOUNT_KEY_PATH")
    google_service_account: Optional[str] = Field(default=None, env="GOOGLE_SERVICE_ACCOUNT")
    google_sheet_id: str = Field(..., env="GOOGLE_SHEET_ID")
    google_sheet_name: str = Field(default="Stock Tracker", env="GOOGLE_SHEET_NAME")
    google_sheets_batch_size: int = Field(default=100, env="GOOGLE_SHEETS_BATCH_SIZE")
    
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_dir: str = Field(default="./logs", env="LOG_DIR")
    timezone: str = Field(default="UTC", env="TIMEZONE")
    debug_mode: bool = Field(default=False, env="DEBUG_MODE")
    dry_run: bool = Field(default=False, env="DRY_RUN")
    mock_api: bool = Field(default=False, env="MOCK_API")
    
    sync_schedule: str = Field(default="0 0 * * *", env="SYNC_SCHEDULE")
    auto_sync_enabled: bool = Field(default=True, env="AUTO_SYNC_ENABLED")
    max_products_per_sync: int = Field(default=100, env="MAX_PRODUCTS_PER_SYNC")
    
    # Optional fields from .env that are not always present
    api_retry_count: Optional[int] = Field(default=3, env="API_RETRY_COUNT")
    api_retry_delay: Optional[int] = Field(default=1, env="API_RETRY_DELAY") 
    max_concurrent_requests: Optional[int] = Field(default=5, env="MAX_CONCURRENT_REQUESTS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields but ignore them
    
    def model_post_init(self, __context):
        """Post-initialization hook for Pydantic v2."""
        # Поддержка GOOGLE_SERVICE_ACCOUNT как JSON строки (для Railway/Render)
        if self.google_service_account:
            try:
                service_account_json = json.loads(self.google_service_account)
                
                # Создаем временный файл с credentials
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w', 
                    delete=False, 
                    suffix='.json',
                    prefix='service-account-'
                )
                json.dump(service_account_json, temp_file)
                temp_file.close()
                
                # Устанавливаем путь через __dict__ чтобы обойти Pydantic validation
                object.__setattr__(self, 'google_service_account_key_path', temp_file.name)
                logger.info(f"✅ Создан временный файл service account: {temp_file.name}")
                logger.debug(f"🔍 google_service_account_key_path установлен в: {self.google_service_account_key_path}")
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Ошибка парсинга GOOGLE_SERVICE_ACCOUNT JSON: {e}")
                raise ValueError("GOOGLE_SERVICE_ACCOUNT должен быть валидным JSON")
            except Exception as e:
                logger.error(f"❌ Ошибка создания временного файла: {e}")
                raise
        
        # Проверка что есть путь к credentials
        if not self.google_service_account_key_path:
            raise ValueError(
                "Необходимо указать GOOGLE_SERVICE_ACCOUNT_KEY_PATH или GOOGLE_SERVICE_ACCOUNT"
            )
        
        logger.debug(f"🔍 Final google_service_account_key_path: {self.google_service_account_key_path}")
        
    @property
    def wildberries(self) -> WildberriesAPIConfig:
        """Get Wildberries API configuration."""
        return WildberriesAPIConfig(
            api_key=self.wildberries_api_key,
            base_url=self.wildberries_base_url,
            statistics_base_url=self.wildberries_statistics_base_url,
            timeout=self.wildberries_api_timeout,
            rate_limit=self.wildberries_rate_limit,
            retry_count=self.api_retry_count or 3,
            retry_delay=self.api_retry_delay or 1.0,
            max_concurrent_requests=self.max_concurrent_requests or 5
        )
        
    @property 
    def google_sheets(self) -> GoogleSheetsConfig:
        """Get Google Sheets configuration."""
        logger.debug(f"🔍 Creating GoogleSheetsConfig with path: {self.google_service_account_key_path}")
        return GoogleSheetsConfig(
            service_account_key_path=self.google_service_account_key_path,
            sheet_id=self.google_sheet_id,
            sheet_name=self.google_sheet_name,
            batch_size=self.google_sheets_batch_size
        )
        
    @property
    def app(self) -> ApplicationConfig:
        """Get Application configuration."""
        return ApplicationConfig(
            log_level=self.log_level,
            log_dir=self.log_dir,
            timezone=self.timezone,
            debug_mode=self.debug_mode,
            dry_run=self.dry_run,
            mock_api=self.mock_api,
            sync_schedule=self.sync_schedule,
            auto_sync_enabled=self.auto_sync_enabled,
            max_products_per_sync=self.max_products_per_sync
        )


# Global configuration instance
_config: Optional[StockTrackerConfig] = None


def get_config() -> StockTrackerConfig:
    """
    Get the global configuration instance.
    
    Returns:
        StockTrackerConfig: Validated configuration instance.
    
    Raises:
        ValueError: If configuration validation fails.
    """
    global _config
    
    if _config is None:
        try:
            _config = StockTrackerConfig()
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    return _config


def reload_config() -> StockTrackerConfig:
    """
    Reload configuration from environment variables.
    
    Returns:
        StockTrackerConfig: New validated configuration instance.
    """
    global _config
    _config = None
    return get_config()


def validate_configuration() -> Dict[str, Any]:
    """
    Validate current configuration and return status information.
    
    Returns:
        Dict containing validation results and configuration summary.
    """
    try:
        config = get_config()
        
        # Basic validation
        basic_result = {
            "valid": True,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "wildberries_api": {
                    "base_url": config.wildberries.base_url,
                    "timeout": config.wildberries.timeout,
                    "rate_limit": config.wildberries.rate_limit,
                    "has_api_key": bool(config.wildberries.api_key)
                },
                "google_sheets": {
                    "sheet_id": config.google_sheets.sheet_id,
                    "sheet_name": config.google_sheets.sheet_name,
                    "batch_size": config.google_sheets.batch_size,
                    "service_account_exists": Path(config.google_sheets.service_account_key_path).exists()
                },
                "application": {
                    "log_level": config.app.log_level,
                    "debug_mode": config.app.debug_mode,
                    "dry_run": config.app.dry_run,
                    "auto_sync_enabled": config.app.auto_sync_enabled,
                    "sync_schedule": config.app.sync_schedule
                }
            }
        }
        
        # Add security validation if available
        try:
            from stock_tracker.utils.security import SecurityValidator
            
            validator = SecurityValidator()
            
            # Convert config to dict for security validation
            config_dict = {
                "wildberries": config.wildberries.dict(),
                "google_sheets": config.google_sheets.dict(),
                "app": config.app.dict()
            }
            
            security_warnings = validator.validate_configuration(config_dict)
            basic_result["security"] = {
                "warnings": security_warnings,
                "secure": len(security_warnings) == 0
            }
            
            logger.info(f"Security validation completed: {len(security_warnings)} warnings found")
            
        except ImportError:
            logger.debug("Security module not available for validation")
        except Exception as e:
            logger.warning(f"Security validation failed: {e}")
            basic_result["security"] = {
                "error": str(e),
                "secure": False
            }
        
        return basic_result
    
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def get_secure_config(master_password: Optional[str] = None) -> 'StockTrackerConfig':
    """
    Get configuration with secure credential loading.
    
    Args:
        master_password: Master password for encrypted credentials
        
    Returns:
        Configuration with securely loaded credentials
    """
    try:
        # Load basic config first
        config = get_config()
        
        # Try to load secure credentials if available
        try:
            from stock_tracker.utils.security import get_credential_store
            
            store = get_credential_store()
            
            # Try to load Wildberries API key securely
            wb_api_key = store.retrieve_credential("wildberries_api_key", master_password)
            if wb_api_key:
                logger.info("Loaded Wildberries API key from secure storage")
                # Update config with secure credential
                config.wildberries.api_key = wb_api_key if isinstance(wb_api_key, str) else wb_api_key.get("key", config.wildberries.api_key)
            
            # Try to load Google Sheets credentials securely
            gs_credentials = store.retrieve_credential("google_sheets_service_account", master_password)
            if gs_credentials:
                logger.info("Loaded Google Sheets credentials from secure storage")
                # Handle service account JSON
                if isinstance(gs_credentials, dict):
                    # Save to temporary secure file
                    from stock_tracker.utils.security import secure_temporary_file
                    import json
                    
                    with secure_temporary_file(json.dumps(gs_credentials), ".json") as temp_file:
                        config.google_sheets.service_account_key_path = str(temp_file)
                elif isinstance(gs_credentials, str):
                    # Assume it's a file path
                    config.google_sheets.service_account_key_path = gs_credentials
            
        except ImportError:
            logger.debug("Security module not available, using standard config")
        except Exception as e:
            logger.warning(f"Failed to load secure credentials: {e}")
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to get secure config: {e}")
        # Fallback to standard config
        return get_config()


def setup_secure_credentials(master_password: str) -> bool:
    """
    Interactive setup for secure credential storage.
    
    Args:
        master_password: Master password for encryption
        
    Returns:
        True if setup successful
    """
    try:
        from stock_tracker.utils.security import get_credential_store
        
        store = get_credential_store()
        logger.info("Setting up secure credential storage...")
        
        # Setup Wildberries API key
        print("\n🔑 Wildberries API Key Setup")
        api_key = input("Enter your Wildberries API key: ").strip()
        if api_key:
            store.store_credential("wildberries_api_key", api_key, master_password)
            print("✅ Wildberries API key stored securely")
        
        # Setup Google Sheets service account
        print("\n📊 Google Sheets Service Account Setup")
        service_account_path = input("Enter path to service account JSON file: ").strip()
        
        if service_account_path and Path(service_account_path).exists():
            # Read and store the service account JSON
            with open(service_account_path, 'r') as f:
                service_account_data = json.load(f)
            
            store.store_credential("google_sheets_service_account", service_account_data, master_password)
            print("✅ Google Sheets service account stored securely")
        
        # Setup Google Sheets ID
        sheet_id = input("Enter your Google Sheets ID: ").strip()
        if sheet_id:
            store.store_credential("google_sheets_id", sheet_id, master_password)
            print("✅ Google Sheets ID stored securely")
        
        print("\n🎉 Secure credential setup completed!")
        return True
        
    except ImportError:
        logger.error("Security module not available")
        return False
    except Exception as e:
        logger.error(f"Secure credential setup failed: {e}")
        return False


if __name__ == "__main__":
    # Test configuration loading
    try:
        config = get_config()
        print("✅ Configuration loaded successfully!")
        
        validation_result = validate_configuration()
        if validation_result["valid"]:
            print("✅ Configuration validation passed!")
            print(f"📊 Summary: {validation_result['summary']}")
        else:
            print(f"❌ Configuration validation failed: {validation_result['error']}")
            
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")