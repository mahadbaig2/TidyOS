"""Main application window for TidyOS desktop shell."""

from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QStackedWidget,
    QSystemTrayIcon,
    QMenu,
    QApplication,
)
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QKeySequence, QShortcut
from PySide6.QtCore import Qt

from tidyos.ui.theme.tokens import COLORS
from tidyos.ui.components.sidebar import Sidebar
from tidyos.ui.pages import (
    HomePage,
    SearchPage,
    OrganizePage,
    ReviewPage,
    ActivityPage,
    SettingsPage,
)
from tidyos.logging_config import get_logger

logger = get_logger("ui.main_window")


def create_fallback_tray_icon() -> QIcon:
    """Generate a clean dark-mode icon pixmap for system tray."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Outer circle
    painter.setBrush(QColor(COLORS.surface_raised))
    painter.setPen(QColor(COLORS.border))
    painter.drawRoundedRect(2, 2, 28, 28, 6, 6)

    # Inner active dot
    painter.setBrush(QColor(COLORS.success))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(11, 11, 10, 10)

    painter.end()
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    """TidyOS Primary Desktop Window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TidyOS — Autonomous File System Agent")
        self.resize(1200, 780)
        self.setMinimumSize(1000, 650)

        # Root container
        root_widget = QWidget()
        root_widget.setObjectName("AppCanvas")
        self.setCentralWidget(root_widget)

        root_layout = QHBoxLayout(root_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Left Sidebar
        self.sidebar = Sidebar()
        root_layout.addWidget(self.sidebar)

        # Right Stacked Pages
        self.stack = QStackedWidget()
        self.stack.setObjectName("MainContentArea")

        self.pages: dict[str, QWidget] = {
            "home": HomePage(),
            "search": SearchPage(),
            "organize": OrganizePage(),
            "review": ReviewPage(),
            "activity": ActivityPage(),
            "settings": SettingsPage(),
        }

        for page in self.pages.values():
            self.stack.addWidget(page)

        root_layout.addWidget(self.stack, 1)

        # Connect navigation
        self.sidebar.page_changed.connect(self.navigate_to)

        # Global Shortcut: Ctrl+K / Cmd+K to jump to search
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        self.search_shortcut.activated.connect(self._on_search_shortcut)

        # Initialize System Tray
        self._setup_system_tray()

        logger.info("MainWindow initialized with all 6 pages and system tray skeleton.")

    def navigate_to(self, page_id: str):
        """Switch current view to the specified page."""
        if page_id in self.pages:
            widget = self.pages[page_id]
            self.stack.setCurrentWidget(widget)
            self.sidebar.set_active_page(page_id)
            logger.debug(f"Navigated to page: {page_id}")

    def _on_search_shortcut(self):
        """Handle Ctrl+K shortcut: switch to search page and focus input."""
        self.navigate_to("search")
        search_page = self.pages["search"]
        if hasattr(search_page, "search_bar"):
            search_page.search_bar.set_focus()

    def _setup_system_tray(self):
        """Create system tray icon and contextual menu."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(create_fallback_tray_icon())
        self.tray_icon.setToolTip("TidyOS — Autonomous File System Agent (Watching)")

        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show TidyOS")
        show_action.triggered.connect(self._show_and_raise)

        pause_action = tray_menu.addAction("Pause Watching")
        pause_action.setCheckable(True)

        tray_menu.addSeparator()

        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(QApplication.instance().quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_and_raise()

    def _show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()
