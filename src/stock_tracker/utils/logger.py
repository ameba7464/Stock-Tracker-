"""
Logging configuration for Wildberries Stock Tracker.

Provides centralized logging setup with support for file and console logging,
colored output, and configurable log levels. Uses environment variables
for configuration.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

import colorlog


class StockTrackerLogger:
    """Centralized logger for the Stock Tracker application."""
    
    def __init__(self, name: str = "stock_tracker"):
        """Initialize logger with the given name."""
        self.name = name
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Setup logger with file and console handlers."""
        # Get configuration from environment
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        log_dir = os.getenv("LOG_DIR", "./logs")
        debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
        
        # Create logs directory if it doesn't exist
        Path(log_dir).mkdir(exist_ok=True)
        
        # Set log level
        self.logger.setLevel(getattr(logging, log_level, logging.INFO))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Setup console handler with colors
        self._setup_console_handler(debug_mode)
        
        # Setup file handler
        self._setup_file_handler(log_dir, debug_mode)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def _setup_console_handler(self, debug_mode: bool) -> None:
        """Setup colored console logging."""
        console_handler = colorlog.StreamHandler(sys.stdout)
        
        # Color format for console
        color_format = (
            "%(log_color)s%(asctime)s [%(levelname)8s] "
            "%(name)s.%(funcName)s:%(lineno)d - %(message)s"
        )
        
        if not debug_mode:
            # Simplified format for production
            color_format = (
                "%(log_color)s%(asctime)s [%(levelname)8s] "
                "%(name)s - %(message)s"
            )
        
        formatter = colorlog.ColoredFormatter(
            color_format,
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def _setup_file_handler(self, log_dir: str, debug_mode: bool) -> None:
        """Setup file logging with rotation."""
        log_file = os.path.join(log_dir, f"{self.name}.log")
        
        # Rotating file handler (5MB per file, keep 5 files)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # File format (no colors)
        file_format = (
            "%(asctime)s [%(levelname)8s] %(name)s.%(funcName)s:%(lineno)d - "
            "%(message)s"
        )
        
        if not debug_mode:
            # Simplified format for production
            file_format = (
                "%(asctime)s [%(levelname)8s] %(name)s - %(message)s"
            )
        
        formatter = logging.Formatter(
            file_format,
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance."""
        return self.logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance for the given name.
    
    Args:
        name: Logger name. If None, uses the caller's module name.
    
    Returns:
        Configured logger instance.
    """
    if name is None:
        # Get caller's module name
        frame = sys._getframe(1)
        name = frame.f_globals.get('__name__', 'stock_tracker')
    
    # Use the same logger configuration
    logger_manager = StockTrackerLogger(name)
    return logger_manager.get_logger()


def setup_logging() -> None:
    """
    Setup application-wide logging configuration.
    
    This should be called once at application startup.
    """
    # Setup root logger for the application
    root_logger = StockTrackerLogger("stock_tracker")
    
    # Log startup message
    logger = root_logger.get_logger()
    logger.info("Logging system initialized")
    logger.debug(f"Log level: {logger.level}")
    logger.debug(f"Handlers: {[h.__class__.__name__ for h in logger.handlers]}")


# Module-level logger for this file
logger = get_logger(__name__)


if __name__ == "__main__":
    # Test logging setup
    setup_logging()
    
    test_logger = get_logger("test")
    test_logger.debug("Debug message")
    test_logger.info("Info message")
    test_logger.warning("Warning message")
    test_logger.error("Error message")
    test_logger.critical("Critical message")