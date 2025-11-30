"""Настройка логирования."""
import logging
import sys
from pathlib import Path

from app.config import settings


def setup_logger(name: str = "tgstock") -> logging.Logger:
    """
    Настраивает и возвращает логгер.
    
    Args:
        name: Имя логгера
        
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Форматирование
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Консольный handler с UTF-8 для Windows
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    # Устанавливаем UTF-8 для консоли в Windows
    if sys.platform == 'win32':
        try:
            # Пытаемся установить UTF-8 для консольного вывода
            sys.stdout.reconfigure(encoding='utf-8')
        except (AttributeError, OSError):
            # Если не получилось, используем fallback без эмодзи в консоли
            pass
    logger.addHandler(console_handler)
    
    # Файловый handler с UTF-8
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    file_handler = logging.FileHandler(
        log_dir / "bot.log",
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# Создаем глобальный логгер
logger = setup_logger()
