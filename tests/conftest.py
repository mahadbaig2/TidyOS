"""Shared pytest fixtures and test configuration."""

import os
import sys
from pathlib import Path
import pytest

# Ensure src is in python path
src_dir = Path(__file__).parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Enable offscreen rendering for headless Qt testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp():
    """Create or retrieve QApplication instance for headless Qt tests."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])
    yield app
