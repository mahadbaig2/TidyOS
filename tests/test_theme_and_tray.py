"""Tests for theme generation, logging masking, and system tray."""

import pytest
from tidyos.ui.theme import get_application_stylesheet, COLORS
from tidyos.logging_config import setup_logging
from tidyos.ui.main_window import MainWindow, create_fallback_tray_icon


def test_theme_stylesheet_generation():
    """Verify QSS stylesheet is generated and contains core design tokens."""
    qss = get_application_stylesheet()
    assert COLORS.app_bg in qss
    assert COLORS.surface in qss
    assert COLORS.sidebar_bg in qss
    assert "HeroSearchInput" in qss
    assert "Card" in qss


def test_sensitive_logging_mask(caplog):
    """Verify that sensitive API keys are masked by SensitiveFilter."""
    import logging

    logger = setup_logging(level="INFO", log_to_console=False, log_to_file=False)
    with caplog.at_level(logging.INFO):
        logger.info("Connecting with key sk-abcdef123456789012345678 to service")

    assert "sk-[MASKED_KEY]" in caplog.text
    assert "sk-abcdef123456789012345678" not in caplog.text


def test_system_tray_menu(qapp):
    """Verify system tray icon is populated with expected menu actions."""
    window = MainWindow()
    tray = window.tray_icon
    assert tray is not None

    menu = tray.contextMenu()
    assert menu is not None

    action_texts = [action.text() for action in menu.actions() if not action.isSeparator()]
    assert "Show TidyOS" in action_texts
    assert "Pause Watching" in action_texts
    assert "Exit" in action_texts


def test_fallback_tray_icon_generation():
    """Verify the programmatic fallback tray icon can be generated without crashing."""
    icon = create_fallback_tray_icon()
    assert not icon.isNull()
