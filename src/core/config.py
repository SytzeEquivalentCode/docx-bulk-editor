"""Configuration management with UTF-8 support for Windows compatibility."""

import json
from pathlib import Path
from typing import Any, Dict


class ConfigManager:
    """Thread-safe configuration manager with UTF-8 encoding.

    Supports dot-notation access (e.g., config.get('backup.retention_days'))
    and automatic default configuration generation.
    """

    def __init__(self, config_path: Path = Path('config.json')):
        """Initialize ConfigManager.

        Args:
            config_path: Path to configuration file (default: config.json)
        """
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from JSON file with UTF-8 encoding.

        If the file doesn't exist, generates default configuration
        and saves it to disk.
        """
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        else:
            self._config = self._get_defaults()
            self.save()

    def save(self) -> None:
        """Save configuration to JSON file with UTF-8 encoding.

        Uses ensure_ascii=False to properly handle Unicode characters.
        """
        # Create parent directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with dot notation support.

        Args:
            key: Configuration key (supports dot notation like 'backup.retention_days')
            default: Default value if key not found

        Returns:
            Configuration value or default if not found

        Examples:
            >>> config.get('backup.retention_days')
            7
            >>> config.get('nonexistent.key', 'default_value')
            'default_value'
        """
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value and save.

        Supports dot notation for nested keys. Creates intermediate
        dictionaries as needed.

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set

        Examples:
            >>> config.set('backup.retention_days', 14)
            >>> config.set('new.nested.key', 'value')
        """
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            config = config.setdefault(k, {})
        config[keys[-1]] = value
        self.save()

    @staticmethod
    def _get_defaults() -> Dict[str, Any]:
        """Return default configuration from PRD Section 9.

        Returns:
            Dictionary with complete default configuration
        """
        return {
            "version": "1.0.0",
            "backup": {
                "directory": "./backups",
                "retention_days": 7,
                "auto_cleanup": True,
                "compress": False
            },
            "processing": {
                "pool_size": None,
                "timeout_per_file_seconds": 60,
                "max_file_size_mb": 100,
                "warn_large_files": True,
                "skip_locked_files": True
            },
            "ui": {
                "theme": "system",
                "window_width": 1000,
                "window_height": 700,
                "remember_window_position": True,
                "show_tooltips": True,
                "progress_update_interval_ms": 100
            },
            "logging": {
                "level": "INFO",
                "retention_days": 30,
                "max_file_size_mb": 10,
                "max_files": 10
            }
        }
