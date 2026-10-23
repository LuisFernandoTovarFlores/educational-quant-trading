"""
Secrets manager module.
Loads API keys and sensitive data from .env file.
"""

import os
from pathlib import Path
from typing import Optional


class SecretsManager:
    """Manages API keys and secrets from .env file."""

    _instance = None
    _loaded = False

    def __new__(cls):
        """Singleton pattern to ensure .env is loaded only once."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_env()
        return cls._instance

    def _load_env(self):
        """Load environment variables from .env without overriding real env vars."""
        if self._loaded:
            return

        env_path = Path(__file__).parent.parent / '.env'

        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue

                    if line.startswith('export '):
                        line = line[len('export ') :].strip()

                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key:
                        # Real environment variables take precedence over .env.
                        os.environ.setdefault(key, value)

        self._loaded = True

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get secret value.

        Args:
            key: Environment variable name
            default: Default value if not found

        Returns:
            Secret value or default
        """
        return os.environ.get(key, default)

    def get_required(self, key: str) -> str:
        """
        Get required secret value. Raises error if not found.

        Args:
            key: Environment variable name

        Returns:
            Secret value

        Raises:
            ValueError: If key not found in environment
        """
        value = self.get(key)
        if value is None:
            raise ValueError(f"Required secret '{key}' not found in .env file")
        return value

    def has(self, key: str) -> bool:
        """Check if a non-empty secret exists."""
        return bool(os.environ.get(key))


# Global secrets instance
secrets = SecretsManager()


def get_secrets() -> SecretsManager:
    """Get the global secrets instance."""
    return secrets
