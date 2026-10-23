"""
Config loader module.
Loads settings from config/settings.yaml and provides access to configuration values.
"""

from pathlib import Path
from typing import Any, Dict

import yaml


class ConfigLoader:
    """Loads and manages configuration from settings.yaml."""

    _instance = None
    _config = None

    def __new__(cls):
        """Singleton pattern to ensure config is loaded only once."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Load configuration from settings.yaml."""
        config_path = Path(__file__).parent / 'settings.yaml'

        if not config_path.exists():
            raise FileNotFoundError(f'Configuration file not found: {config_path}')

        with open(config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key_path: Dot-separated path (e.g., 'project.name', 'costs.commission_pct')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            config.get('costs.commission_pct')  # Returns 0.20
        """
        keys = key_path.split('.')
        value = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration dictionary."""
        return self._config.copy()

    def reload(self):
        """Reload configuration from file."""
        self._load_config()


# Global config instance
config = ConfigLoader()


def get_config() -> ConfigLoader:
    """Get the global config instance."""
    return config
