"""Structured logging setup for TidyOS."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

from tidyos.config import config


class SensitiveFilter(logging.Filter):
    """Filter to ensure sensitive credentials are not leaked in log output."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.msg)
        if "sk-" in msg:
            # Mask potential OpenAI secret key substrings
            import re
            record.msg = re.sub(r"sk-[a-zA-Z0-9_-]{20,}", "sk-[MASKED_KEY]", msg)
        return True


def setup_logging(
    level: Optional[str] = None,
    log_to_console: Optional[bool] = None,
    log_to_file: Optional[bool] = None,
) -> logging.Logger:
    """Initialize structured application logging.

    Args:
        level: Log level name (DEBUG, INFO, WARNING, ERROR).
        log_to_console: Whether to emit logs to stdout/stderr.
        log_to_file: Whether to write logs to rotating files on disk.

    Returns:
        The root 'tidyos' logger.
    """
    effective_level = level or config.log_level
    numeric_level = getattr(logging, effective_level.upper(), logging.INFO)

    root_logger = logging.getLogger("tidyos")
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()
    root_logger.addFilter(SensitiveFilter())

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    if log_to_console if log_to_console is not None else config.log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Rotating File Handler
    if log_to_file if log_to_file is not None else config.log_to_file:
        try:
            log_file = config.logs_dir / "tidyos.log"
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as err:
            # Fallback if file logging cannot be initialized
            root_logger.warning(f"Failed to initialize file logger: {err}")

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a scoped logger under the 'tidyos' hierarchy."""
    if not name.startswith("tidyos"):
        name = f"tidyos.{name}"
    return logging.getLogger(name)
