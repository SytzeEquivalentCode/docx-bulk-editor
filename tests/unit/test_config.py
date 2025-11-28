"""Unit tests for ConfigManager."""

import json
import tempfile
from pathlib import Path

import pytest

from src.core.config import ConfigManager


class TestConfigManager:
    """Test suite for ConfigManager class."""

    def test_load_save_utf8(self, tmp_path):
        """Test load/save with UTF-8 characters (emoji, Chinese)."""
        config_path = tmp_path / "test_config.json"
        config = ConfigManager(config_path)

        # Set values with Unicode characters
        config.set("test.emoji", "Hello 😀 World 🎉")
        config.set("test.chinese", "测试中文字符")
        config.set("test.mixed", "Émojis and 中文 together!")

        # Reload and verify
        config2 = ConfigManager(config_path)
        assert config2.get("test.emoji") == "Hello 😀 World 🎉"
        assert config2.get("test.chinese") == "测试中文字符"
        assert config2.get("test.mixed") == "Émojis and 中文 together!"

    def test_dot_notation_get(self, tmp_path):
        """Test get method with dot notation for nested keys."""
        config_path = tmp_path / "test_config.json"
        config = ConfigManager(config_path)

        # Test existing nested keys
        assert config.get("backup.retention_days") == 7
        assert config.get("backup.directory") == "./backups"
        assert config.get("processing.pool_size") is None
        assert config.get("ui.window_width") == 1000

        # Test with defaults
        assert config.get("nonexistent.key", "default") == "default"
        assert config.get("backup.nonexistent", 42) == 42

        # Test deeply nested
        assert config.get("nonexistent.deeply.nested.key", None) is None

    def test_dot_notation_set(self, tmp_path):
        """Test set method creating nested structures."""
        config_path = tmp_path / "test_config.json"
        config = ConfigManager(config_path)

        # Set new nested keys
        config.set("new.nested.key", "value1")
        config.set("another.deep.nested.value", 123)

        # Verify structure created
        assert config.get("new.nested.key") == "value1"
        assert config.get("another.deep.nested.value") == 123

        # Verify saved to file
        config2 = ConfigManager(config_path)
        assert config2.get("new.nested.key") == "value1"
        assert config2.get("another.deep.nested.value") == 123

    def test_defaults_generation(self, tmp_path):
        """Test default configuration generation with all required keys."""
        config_path = tmp_path / "new_config.json"
        config = ConfigManager(config_path)

        # Verify all top-level sections exist
        assert config.get("version") == "1.0.0"
        assert config.get("backup") is not None
        assert config.get("processing") is not None
        assert config.get("ui") is not None
        assert config.get("logging") is not None

        # Verify backup section
        assert config.get("backup.directory") == "./backups"
        assert config.get("backup.retention_days") == 7
        assert config.get("backup.auto_cleanup") is True
        assert config.get("backup.compress") is False

        # Verify processing section
        assert config.get("processing.pool_size") is None
        assert config.get("processing.timeout_per_file_seconds") == 60
        assert config.get("processing.max_file_size_mb") == 100
        assert config.get("processing.warn_large_files") is True
        assert config.get("processing.skip_locked_files") is True

        # Verify UI section
        assert config.get("ui.theme") == "system"
        assert config.get("ui.window_width") == 1000
        assert config.get("ui.window_height") == 700
        assert config.get("ui.remember_window_position") is True
        assert config.get("ui.show_tooltips") is True
        assert config.get("ui.progress_update_interval_ms") == 100

        # Verify logging section
        assert config.get("logging.level") == "INFO"
        assert config.get("logging.retention_days") == 30
        assert config.get("logging.max_file_size_mb") == 10
        assert config.get("logging.max_files") == 10

    def test_invalid_json(self, tmp_path):
        """Test handling of invalid JSON files."""
        config_path = tmp_path / "invalid.json"

        # Write invalid JSON
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write("{ invalid json }")

        # Should raise JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            ConfigManager(config_path)

    def test_nonexistent_file(self, tmp_path):
        """Test creation of defaults when file doesn't exist."""
        config_path = tmp_path / "nonexistent.json"

        # File should not exist initially
        assert not config_path.exists()

        # Creating ConfigManager should create the file with defaults
        config = ConfigManager(config_path)
        assert config_path.exists()
        assert config.get("version") == "1.0.0"
        assert config.get("backup.retention_days") == 7

    def test_modify_existing_values(self, tmp_path):
        """Test modifying existing configuration values."""
        config_path = tmp_path / "test_config.json"
        config = ConfigManager(config_path)

        # Modify existing values
        original_retention = config.get("backup.retention_days")
        config.set("backup.retention_days", 14)
        assert config.get("backup.retention_days") == 14
        assert config.get("backup.retention_days") != original_retention

        # Verify persisted
        config2 = ConfigManager(config_path)
        assert config2.get("backup.retention_days") == 14

    def test_get_with_non_dict_intermediate(self, tmp_path):
        """Test get method when intermediate value is not a dict."""
        config_path = tmp_path / "test_config.json"
        config = ConfigManager(config_path)

        # Set a non-dict value
        config.set("test.value", "string")

        # Try to access nested key under string value
        result = config.get("test.value.nested", "default")
        assert result == "default"

    def test_unicode_in_keys_and_values(self, tmp_path):
        """Test Unicode characters in both keys and values."""
        config_path = tmp_path / "unicode_test.json"
        config = ConfigManager(config_path)

        # Note: JSON keys should typically be ASCII, but values can be Unicode
        config.set("paths.测试", "C:/Users/测试/文档.docx")
        config.set("messages.greeting", "你好世界")

        # Verify retrieval
        assert config.get("paths.测试") == "C:/Users/测试/文档.docx"
        assert config.get("messages.greeting") == "你好世界"

        # Verify file is readable with UTF-8
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert data["paths"]["测试"] == "C:/Users/测试/文档.docx"

    def test_empty_key(self, tmp_path):
        """Test handling of empty key strings."""
        config_path = tmp_path / "test_config.json"
        config = ConfigManager(config_path)

        # Empty key should work with root config
        config.set("", "root_value")
        assert config.get("") == "root_value"

    def test_ensure_ascii_false(self, tmp_path):
        """Test that ensure_ascii=False is used for proper Unicode handling."""
        config_path = tmp_path / "test_config.json"
        config = ConfigManager(config_path)

        config.set("unicode.test", "日本語")

        # Read raw file content
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should contain actual Unicode characters, not escape sequences
        assert "日本語" in content
        assert "\\u" not in content  # No Unicode escape sequences


class TestConfigManagerIntegration:
    """Integration tests for ConfigManager."""

    def test_concurrent_access(self, tmp_path):
        """Test concurrent access with a single shared config instance.

        Note: Using multiple ConfigManager instances to write to the same file
        concurrently is not supported and will cause file corruption. Applications
        should use a single shared instance with proper synchronization.
        """
        import threading

        config_path = tmp_path / "concurrent_config.json"
        config = ConfigManager(config_path)

        # Use a lock for thread-safe writes with shared instance
        lock = threading.Lock()

        def writer1():
            for i in range(10):
                with lock:
                    config.set(f"thread1.value{i}", i)

        def writer2():
            for i in range(10):
                with lock:
                    config.set(f"thread2.value{i}", i * 2)

        thread1 = threading.Thread(target=writer1)
        thread2 = threading.Thread(target=writer2)

        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # Reload and verify all values exist
        config2 = ConfigManager(config_path)
        # All values from both threads should exist
        for i in range(10):
            assert config2.get(f"thread1.value{i}") == i
            assert config2.get(f"thread2.value{i}") == i * 2

    def test_windows_paths_with_spaces(self, tmp_path):
        """Test handling of Windows paths with spaces and Unicode."""
        config_path = tmp_path / "paths_config.json"
        config = ConfigManager(config_path)

        # Windows paths with spaces and Unicode
        test_paths = [
            "C:/Program Files/My App/file.docx",
            "C:/Users/用户/Documents/test.docx",
            "\\\\server\\share\\folder name\\file.docx"
        ]

        for i, path in enumerate(test_paths):
            config.set(f"paths.test{i}", path)

        # Verify all paths preserved correctly
        for i, path in enumerate(test_paths):
            assert config.get(f"paths.test{i}") == path
