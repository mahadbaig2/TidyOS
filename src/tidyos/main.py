"""Application entry point for TidyOS desktop application."""

from __future__ import annotations

import sys
import traceback
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from tidyos.config import config
from tidyos.logging_config import setup_logging, get_logger
from tidyos.ui.theme import get_application_stylesheet
from tidyos.ui.main_window import MainWindow, create_fallback_tray_icon

logger = get_logger("main")


def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception hook to ensure crashes are logged cleanly."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical(
        "Uncaught exception encountered in application loop:",
        exc_info=(exc_type, exc_value, exc_traceback),
    )


def create_application() -> tuple[QApplication, MainWindow]:
    """Create and configure the QApplication and MainWindow instances."""
    # Setup structured logging
    setup_logging(
        level=config.log_level,
        log_to_console=config.log_to_console,
        log_to_file=config.log_to_file,
    )
    logger.info(f"Starting {config.app_name} v{config.version} in environment '{config.env}'")

    # Install global exception handler
    sys.excepthook = handle_exception

    # Enable Qt High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName(config.app_name)
    app.setOrganizationName("TidyOS")
    app.setWindowIcon(create_fallback_tray_icon())

    # Apply global dark theme stylesheet
    app.setStyleSheet(get_application_stylesheet())

    # Initialize main window
    window = MainWindow()

    return app, window


def main() -> int:
    """Main CLI entry point."""
    app, window = create_application()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
