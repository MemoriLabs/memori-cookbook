"""Configuration management for the contributor assistant."""

import json
import uuid
from pathlib import Path


class Config:
    """Manage configuration for the contributor assistant."""

    def __init__(self) -> None:
        """Initialize configuration manager."""
        self.config_dir = Path.home() / ".memori_contributor"
        self.config_file = self.config_dir / "config.json"
        self.db_path = self.config_dir / "memori.db"
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Ensure configuration directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        """Load configuration from file."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                return json.load(f)
        return {}

    def save(self, config: dict) -> None:
        """Save configuration to file."""
        self._ensure_dir()
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)

    def initialize(
        self,
        contribution_type: str,
        areas_of_interest: list[str],
        llm_provider: str = "anthropic",
    ) -> dict:
        """Initialize configuration with user preferences."""
        config = {
            "entity_id": f"contributor-{uuid.uuid4().hex[:8]}",
            "process_id": "memori-contributor",
            "database_path": str(self.db_path),
            "default_provider": llm_provider,
            "contribution_type": contribution_type,
            "areas_of_interest": areas_of_interest,
            "initialized": True,
        }
        self.save(config)
        return config

    def is_initialized(self) -> bool:
        """Check if configuration is initialized."""
        config = self.load()
        return config.get("initialized", False)

    def get(self, key: str, default=None):
        """Get a configuration value."""
        config = self.load()
        return config.get(key, default)

    def reset(self) -> None:
        """Reset configuration."""
        if self.config_file.exists():
            self.config_file.unlink()
        if self.db_path.exists():
            self.db_path.unlink()
