"""Application configuration management for TidyOS."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file if present
load_dotenv()


def get_default_data_dir() -> Path:
    """Return default local application data directory for Windows."""
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        path = Path(local_app_data) / "TidyOS"
    else:
        path = Path.home() / ".tidyos"
    path.mkdir(parents=True, exist_ok=True)
    return path


class AppConfig(BaseModel):
    """Configuration model for TidyOS runtime."""

    # Environment
    app_name: str = "TidyOS"
    version: str = "0.1.0"
    env: str = Field(default_factory=lambda: os.getenv("TIDYOS_ENV", "production"))

    # OpenAI API (Optional for offline local runs)
    openai_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )

    # Logging
    log_level: str = Field(default_factory=lambda: os.getenv("TIDYOS_LOG_LEVEL", "INFO"))
    log_to_console: bool = Field(
        default_factory=lambda: os.getenv("TIDYOS_LOG_TO_CONSOLE", "true").lower() == "true"
    )
    log_to_file: bool = Field(
        default_factory=lambda: os.getenv("TIDYOS_LOG_TO_FILE", "true").lower() == "true"
    )

    # Storage Paths
    data_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("TIDYOS_DATA_DIR", get_default_data_dir()))
    )

    # Agent & Watcher Behavior
    confidence_threshold: float = Field(
        default_factory=lambda: float(os.getenv("TIDYOS_CONFIDENCE_THRESHOLD", "0.85"))
    )
    watcher_enabled: bool = Field(
        default_factory=lambda: os.getenv("TIDYOS_WATCHER_ENABLED", "true").lower() == "true"
    )
    watcher_debounce_seconds: float = Field(
        default_factory=lambda: float(os.getenv("TIDYOS_WATCHER_DEBOUNCE_SECONDS", "2.0"))
    )

    @property
    def database_path(self) -> Path:
        """Return the path to the primary SQLite database."""
        return self.data_dir / "tidyos.db"

    @property
    def logs_dir(self) -> Path:
        """Return the directory where log files are stored."""
        path = self.data_dir / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path


# Singleton default configuration
config = AppConfig()
