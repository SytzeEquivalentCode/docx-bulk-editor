"""Unit tests for logger setup with UTF-8 support."""

import logging
import re
from pathlib import Path

import pytest

from src.core.config import ConfigManager
from src.core.logger import setup_logger, get_logger


class TestLoggerSetup:
    """Test suite for logger setup functionality."""

    def test_logger_creation(self, tmp_path):
        """Test logger creates log directory and file."""
        log_dir = tmp_path / "logs"
        logger = setup_logger(log_dir=log_dir)

        # Verify directory created
        assert log_dir.exists()
        assert log_dir.is_dir()

        # Verify log file created
        log_file = log_dir / "app.log"
        assert log_file.exists()

        # Verify logger is configured
        assert logger.name == "docx_bulk_editor"
        assert len(logger.handlers) == 2  # File and console handlers

    def test_log_file_creation(self, tmp_path):
        """Test that log file is created on first log message."""
        log_dir = tmp_path / "logs"
        logger = setup_logger(log_dir=log_dir)

        # Write a log message
        logger.info("Test message")

        # Verify file exists and contains message
        log_file = log_dir / "app.log"
        assert log_file.exists()

        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Test message" in content

    def test_utf8_encoding(self, tmp_path):
        """Test logging of UTF-8 characters (emoji, Chinese)."""
        log_dir = tmp_path / "logs"
        logger = setup_logger(log_dir=log_dir)

        # Log messages with Unicode characters
        test_messages = [
            "Hello 😀 World 🎉",
            "测试中文字符",
            "Émojis and 中文 together!"
        ]

        for msg in test_messages:
            logger.info(msg)

        # Read and verify UTF-8 encoding
        log_file = log_dir / "app.log"
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            for msg in test_messages:
                assert msg in content

    def test_log_levels(self, tmp_path):
        """Test different log levels are written to file."""
        log_dir = tmp_path / "logs"
        logger = setup_logger(log_dir=log_dir)

        # Write messages at different levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        # Read log file
        log_file = log_dir / "app.log"
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # All levels should be in file (file handler is DEBUG level)
        assert "DEBUG" in content
        assert "Debug message" in content
        assert "INFO" in content
        assert "Info message" in content
        assert "WARNING" in content
        assert "Warning message" in content
        assert "ERROR" in content
        assert "Error message" in content
        assert "CRITICAL" in content
        assert "Critical message" in content

    def test_formatter_correctness(self, tmp_path):
        """Test log message format includes timestamp and level."""
        log_dir = tmp_path / "logs"
        logger = setup_logger(log_dir=log_dir)

        test_message = "Test formatter message"
        logger.info(test_message)

        # Read log file
        log_file = log_dir / "app.log"
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verify format: YYYY-MM-DD HH:MM:SS - logger_name - LEVEL - message
        pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - docx_bulk_editor - INFO - Test formatter message'
        assert re.search(pattern, content) is not None

    def test_file_rotation(self, tmp_path):
        """Test file rotation when size limit is reached."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)  # Create directory first

        # Create logger with very small max size for testing
        logger = logging.getLogger("test_rotation")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)

        # Create handler with 1KB max size
        from logging.handlers import RotatingFileHandler
        log_file = log_dir / "test_rotation.log"
        handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=1024,  # 1KB for testing
            backupCount=10,
            encoding='utf-8'
        )
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Write enough data to trigger rotation
        large_message = "X" * 200  # 200 bytes per message
        for i in range(10):  # Write 2KB total
            logger.info(large_message)

        # Verify rotation occurred
        rotated_file = Path(str(log_file) + ".1")
        assert rotated_file.exists(), "Rotation file should exist"

    def test_config_integration(self, tmp_path):
        """Test logger respects ConfigManager log level setting."""
        log_dir = tmp_path / "logs"
        config_path = tmp_path / "test_config.json"

        # Create config with WARNING level
        config = ConfigManager(config_path)
        config.set("logging.level", "WARNING")

        # Setup logger with config
        logger = setup_logger(log_dir=log_dir, config=config)

        # Console handler should be set to WARNING
        console_handler = None
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.handlers.RotatingFileHandler):
                console_handler = handler
                break

        assert console_handler is not None
        assert console_handler.level == logging.WARNING

    def test_multiple_loggers(self, tmp_path):
        """Test creating multiple named loggers."""
        log_dir = tmp_path / "logs"

        logger1 = setup_logger(name="logger1", log_dir=log_dir, log_file="log1.log")
        logger2 = setup_logger(name="logger2", log_dir=log_dir, log_file="log2.log")

        logger1.info("Message from logger1")
        logger2.info("Message from logger2")

        # Verify separate log files
        log1_file = log_dir / "log1.log"
        log2_file = log_dir / "log2.log"

        assert log1_file.exists()
        assert log2_file.exists()

        with open(log1_file, 'r', encoding='utf-8') as f:
            content1 = f.read()
            assert "Message from logger1" in content1
            assert "Message from logger2" not in content1

        with open(log2_file, 'r', encoding='utf-8') as f:
            content2 = f.read()
            assert "Message from logger2" in content2
            assert "Message from logger1" not in content2

    def test_get_logger_function(self, tmp_path):
        """Test get_logger retrieves existing logger."""
        log_dir = tmp_path / "logs"

        # Setup logger
        logger1 = setup_logger(name="test_get", log_dir=log_dir)

        # Get same logger
        logger2 = get_logger(name="test_get")

        # Should be the same instance
        assert logger1 is logger2

    def test_no_duplicate_handlers(self, tmp_path):
        """Test that calling setup_logger multiple times doesn't duplicate handlers."""
        log_dir = tmp_path / "logs"

        # Setup same logger twice
        logger1 = setup_logger(name="test_dup", log_dir=log_dir)
        logger2 = setup_logger(name="test_dup", log_dir=log_dir)

        # Should have exactly 2 handlers (file and console)
        assert len(logger2.handlers) == 2

    def test_log_directory_nested(self, tmp_path):
        """Test logger creates nested log directories."""
        log_dir = tmp_path / "nested" / "log" / "directory"
        logger = setup_logger(log_dir=log_dir)

        # Verify nested directories created
        assert log_dir.exists()
        assert (log_dir / "app.log").exists()

    def test_windows_path_with_spaces(self, tmp_path):
        """Test logger handles paths with spaces (Windows compatibility)."""
        log_dir = tmp_path / "log directory with spaces"
        logger = setup_logger(log_dir=log_dir)

        logger.info("Test message in path with spaces")

        log_file = log_dir / "app.log"
        assert log_file.exists()

        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Test message in path with spaces" in content


class TestLoggerIntegration:
    """Integration tests for logger with ConfigManager."""

    def test_full_config_integration(self, tmp_path):
        """Test complete integration with ConfigManager settings."""
        log_dir = tmp_path / "logs"
        config_path = tmp_path / "config.json"

        # Create config with custom logging settings
        config = ConfigManager(config_path)
        config.set("logging.level", "DEBUG")
        config.set("logging.retention_days", 30)
        config.set("logging.max_file_size_mb", 10)
        config.set("logging.max_files", 10)

        # Setup logger with config
        logger = setup_logger(log_dir=log_dir, config=config)

        # Test logging at various levels
        logger.debug("Debug log with config")
        logger.info("Info log with config")

        # Verify logs written
        log_file = log_dir / "app.log"
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Debug log with config" in content
            assert "Info log with config" in content

    def test_dynamic_config_change(self, tmp_path):
        """Test that changing config requires new logger setup."""
        log_dir = tmp_path / "logs"
        config_path = tmp_path / "config.json"

        config = ConfigManager(config_path)
        config.set("logging.level", "INFO")

        # Setup logger with INFO level
        logger1 = setup_logger(name="dynamic_test", log_dir=log_dir, config=config)

        # Change config to DEBUG
        config.set("logging.level", "DEBUG")

        # Setup new logger with updated config
        logger2 = setup_logger(name="dynamic_test", log_dir=log_dir, config=config)

        # New logger should have DEBUG level on console handler
        console_handler = None
        for handler in logger2.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.handlers.RotatingFileHandler):
                console_handler = handler
                break

        assert console_handler is not None
        assert console_handler.level == logging.DEBUG
