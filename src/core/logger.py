"""Logging setup with rotating file handler and UTF-8 support."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from src.core.config import ConfigManager


def setup_logger(
    name: str = "docx_bulk_editor",
    config: Optional[ConfigManager] = None,
    log_dir: Path = Path("logs"),
    log_file: str = "app.log"
) -> logging.Logger:
    """Configure application logger with rotating file handler.

    Creates a logger with both file and console handlers:
    - File handler: DEBUG level, rotating at 10MB, keeps 10 backups
    - Console handler: INFO level

    All handlers use UTF-8 encoding for Windows compatibility.

    Args:
        name: Logger name (default: "docx_bulk_editor")
        config: ConfigManager instance for reading log level (optional)
        log_dir: Directory for log files (default: "logs")
        log_file: Log filename (default: "app.log")

    Returns:
        Configured logger instance

    Examples:
        >>> logger = setup_logger()
        >>> logger.info("Application started")
        >>> logger.debug("Debug information")
    """
    # Create logs directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)

    # Get or create logger
    logger = logging.getLogger(name)

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Determine log level from config or use default
    log_level_str = "INFO"
    if config:
        log_level_str = config.get("logging.level", "INFO")

    # Convert string level to logging constant
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture all levels

    # Create formatter with timestamp
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler: DEBUG level, rotating at 10MB, UTF-8 encoding
    log_path = log_dir / log_file
    file_handler = RotatingFileHandler(
        filename=log_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler: configurable level (default INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str = "docx_bulk_editor") -> logging.Logger:
    """Get existing logger instance.

    Args:
        name: Logger name (default: "docx_bulk_editor")

    Returns:
        Existing logger instance or creates new one if not found
    """
    logger = logging.getLogger(name)

    # If logger has no handlers, set it up with defaults
    if not logger.handlers:
        logger = setup_logger(name)

    return logger
