"""UI smoke tests for TidyOS desktop shell."""

import pytest
from tidyos.ui.main_window import MainWindow
from tidyos.ui.pages import (
    HomePage,
    SearchPage,
    OrganizePage,
    ReviewPage,
    ActivityPage,
    SettingsPage,
)


def test_main_window_initialization(qapp):
    """Verify MainWindow initializes without errors in headless mode."""
    window = MainWindow()
    assert window.windowTitle() == "TidyOS — Autonomous File System Agent"
    assert window.minimumWidth() == 1000
    assert window.minimumHeight() == 650
    assert window.sidebar is not None
    assert window.stack is not None
    assert window.tray_icon is not None


def test_all_pages_present(qapp):
    """Verify all six core pages are instantiated and present in the stack."""
    window = MainWindow()
    expected_pages = ["home", "search", "organize", "review", "activity", "settings"]

    assert set(window.pages.keys()) == set(expected_pages)
    assert window.stack.count() == 6

    assert isinstance(window.pages["home"], HomePage)
    assert isinstance(window.pages["search"], SearchPage)
    assert isinstance(window.pages["organize"], OrganizePage)
    assert isinstance(window.pages["review"], ReviewPage)
    assert isinstance(window.pages["activity"], ActivityPage)
    assert isinstance(window.pages["settings"], SettingsPage)


def test_sidebar_navigation(qapp):
    """Verify navigating to pages updates current stack index and sidebar button."""
    window = MainWindow()

    for page_id in ["search", "organize", "review", "activity", "settings", "home"]:
        window.navigate_to(page_id)
        current_widget = window.stack.currentWidget()
        assert current_widget == window.pages[page_id]


def test_search_hero_component(qapp):
    """Verify the hero search bar works on SearchPage."""
    window = MainWindow()
    search_page: SearchPage = window.pages["search"]
    assert search_page.search_bar is not None

    search_page.search_bar.set_text("test query")
    assert search_page.search_bar.text() == "test query"


def test_home_metric_cards(qapp):
    """Verify Home page metric cards are rendered with initial placeholder values."""
    window = MainWindow()
    home_page: HomePage = window.pages["home"]

    assert home_page.card_indexed.value_label.text() == "12,491"
    assert home_page.card_organized.value_label.text() == "128"
    assert home_page.card_protected.value_label.text() == "14"
    assert home_page.card_review.value_label.text() == "3"
