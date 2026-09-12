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
from PySide6.QtCore import Qt, QThreadPool

from tidyos.config import config
from tidyos.storage import StorageRepository, ManagedRoot
from tidyos.workers.scanner_worker import ScannerWorker
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

    def __init__(self, repository: Optional[StorageRepository] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TidyOS — Autonomous File System Agent")
        self.resize(1200, 780)
        self.setMinimumSize(1000, 650)

        self.repository = repository or StorageRepository(config.database_path)
        self.thread_pool = QThreadPool.globalInstance()
        self.active_worker: Optional[ScannerWorker] = None

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

        self.home_page = HomePage(repository=self.repository)
        self.settings_page = SettingsPage(repository=self.repository)

        self.pages: dict[str, QWidget] = {
            "home": self.home_page,
            "search": SearchPage(),
            "organize": OrganizePage(),
            "review": ReviewPage(),
            "activity": ActivityPage(),
            "settings": self.settings_page,
        }

        for page in self.pages.values():
            self.stack.addWidget(page)

        root_layout.addWidget(self.stack, 1)

        # Connect navigation
        self.sidebar.page_changed.connect(self.navigate_to)

        # Connect scan triggers and root change updates
        self.settings_page.scan_requested.connect(self.start_scan)
        self.settings_page.roots_changed.connect(self.home_page.refresh_metrics)

        # Global Shortcut: Ctrl+K / Cmd+K to jump to search
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        self.search_shortcut.activated.connect(self._on_search_shortcut)

        # Initialize System Tray
        self._setup_system_tray()

        logger.info("MainWindow initialized with real SQLite storage repository and background scanner.")

    def navigate_to(self, page_id: str):
        """Switch current view to the specified page."""
        if page_id in self.pages:
            widget = self.pages[page_id]
            self.stack.setCurrentWidget(widget)
            self.sidebar.set_active_page(page_id)
            logger.debug(f"Navigated to page: {page_id}")

    def start_scan(self, target_root: Optional[ManagedRoot] = None):
        """Start non-blocking filesystem scan in background QThreadPool."""
        roots_to_scan = [target_root] if target_root is not None else None
        target_name = target_root.path if target_root else "all approved folders"
        logger.info(f"Initiating background scan for: {target_name}")

        worker = ScannerWorker(self.repository, roots_to_scan=roots_to_scan)
        self.active_worker = worker

        worker.signals.scan_started.connect(
            lambda root_p: self.settings_page.show_status_message(f"Scanning started: {root_p}")
        )
        worker.signals.progress.connect(self.home_page.show_scan_progress)
        worker.signals.scan_completed.connect(self._on_scan_completed)
        worker.signals.scan_failed.connect(self._on_scan_failed)

        self.home_page.show_scan_progress("Initializing...", 0, 0)
        self.thread_pool.start(worker)

    def _on_scan_completed(self, total_files: int, total_dirs: int, duration_s: float):
        """Handle background scan completion signal."""
        logger.info(f"Scan finished signal received: {total_files} files in {duration_s:.2f}s")
        self.home_page.hide_scan_progress(total_files, total_dirs, duration_s)
        self.settings_page.show_status_message(
            f"Scan completed: {total_files:,} files and {total_dirs:,} folders indexed in {duration_s:.1f}s."
        )

    def _on_scan_failed(self, root_path: str, error_message: str):
        """Handle background scan failure signal without crashing."""
        logger.warning(f"Scan reported error for '{root_path}': {error_message}")
        self.settings_page.show_status_message(f"Warning on {root_path}: {error_message}")

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
