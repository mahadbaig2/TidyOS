"""Basic import and configuration tests."""

import pytest


def test_tidyos_package_import():
    """Verify tidyos package and version are available."""
    import tidyos

    assert hasattr(tidyos, "__version__")
    assert tidyos.__version__ == "0.1.0"


def test_config_initialization():
    """Verify AppConfig loads defaults without errors."""
    from tidyos.config import AppConfig

    cfg = AppConfig()
    assert cfg.app_name == "TidyOS"
    assert cfg.confidence_threshold == 0.85
    assert cfg.watcher_enabled is True
    assert cfg.data_dir.exists()


def test_logging_setup():
    """Verify structured logger initializes correctly."""
    from tidyos.logging_config import setup_logging, get_logger

    logger = setup_logging(level="DEBUG", log_to_console=False, log_to_file=False)
    assert logger.name == "tidyos"

    child_logger = get_logger("test")
    assert child_logger.name == "tidyos.test"


def test_pyside6_available():
    """Verify PySide6 core and widgets can be imported."""
    from PySide6 import QtCore, QtGui, QtWidgets

    assert QtCore is not None
    assert QtGui is not None
    assert QtWidgets is not None


def test_subpackages_importable():
    """Verify all architectural subpackages exist and import."""
    import tidyos.agents
    import tidyos.safety
    import tidyos.search
    import tidyos.indexing
    import tidyos.storage
    import tidyos.tools
    import tidyos.workers
    import tidyos.ui

    assert tidyos.agents is not None
    assert tidyos.safety is not None
    assert tidyos.search is not None
    assert tidyos.indexing is not None
    assert tidyos.storage is not None
    assert tidyos.tools is not None
    assert tidyos.workers is not None
    assert tidyos.ui is not None
