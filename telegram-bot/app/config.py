"""Конфигурация приложения."""
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
    db_password: str
    
    # Application
    google_sheet_url: str
    google_drive_folder_id: str = ""
    admin_ids: str = ""
    
    # Logging
    log_level: str = "INFO"
    
    # Payment (заглушка)
    payment_enabled: bool = False
    payment_provider: str = "yookassa"
    payment_token: str = ""
    
    @property
    def database_url(self) -> str:
        """Возвращает URL подключения к базе данных."""
        # PostgreSQL (production)
        if self.db_host != "localhost" or self.db_port != 5432:
            return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        
        # SQLite (development - будет использован позже)
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
