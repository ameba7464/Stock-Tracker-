"""Конфигурация приложения."""
import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения из .env файла."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Telegram Bot
    bot_token: str
    
    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "tgstock"
    db_user: str = "postgres"
    db_password: str = ""
    database_url: str = ""  # Позволяет передать полный DATABASE_URL напрямую
    
    # Application
    google_sheet_url: str = ""
    google_drive_folder_id: str = ""
    admin_ids: str = ""
    
    # Logging
    log_level: str = "INFO"
    
    # Payment & Subscription Configuration
    payment_enabled: bool = False  # FALSE = MVP (бесплатный доступ для всех)
    payment_provider: str = "yookassa"
    payment_token: str = ""
    
    # Subscription Settings
    free_trial_days: int = 7  # Триальный период при payment_enabled=True
    subscription_price: int = 299  # Руб/мес (или другая валюта)
    
    def get_database_url(self) -> str:
        """Возвращает URL подключения к базе данных."""
        # Если передан полный DATABASE_URL через переменную окружения, используем его
        if self.database_url:
            # Заменяем postgresql:// на postgresql+asyncpg:// если нужно
            url = self.database_url
            if url.startswith("postgresql://") and "+asyncpg" not in url:
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
            
        # PostgreSQL - если указаны обязательные параметры
        if self.db_user and self.db_password and self.db_name:
            ssl_param = "?ssl=require" if "yandexcloud" in self.db_host or self.db_port == 6432 else ""
            return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}{ssl_param}"
        
        # SQLite (development) - fallback
        return f"sqlite+aiosqlite:///{self.db_name}"
    
    @property
    def admin_ids_list(self) -> List[int]:
        """Возвращает список ID администраторов."""
        if not self.admin_ids:
            return []
        
        return [
            int(admin_id.strip()) 
            for admin_id in self.admin_ids.split(",") 
            if admin_id.strip()
        ]


# Создаем глобальный экземпляр настроек
settings = Settings()
