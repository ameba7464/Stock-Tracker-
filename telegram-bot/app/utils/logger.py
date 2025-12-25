"""Настройка логирования."""
import logging
import sys
import os
from pathlib import Path

from app.config import settings

# Устанавливаем UTF-8 для Windows перед импортом других модулей
if sys.platform == 'win32':
    # Устанавливаем переменные окружения для UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    
    # Настраиваем консоль Windows
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)  # UTF-8 input
        kernel32.SetConsoleOutputCP(65001)  # UTF-8 output
    except:
        pass


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
    
    # Форматирование без emoji для Windows консоли
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Консольный handler с UTF-8
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Устанавливаем UTF-8 для консоли
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, OSError):
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
