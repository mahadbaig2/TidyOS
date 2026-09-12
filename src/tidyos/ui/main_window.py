"""Main application window for TidyOS desktop shell."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List
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
from tidyos.workers.librarian_worker import LibrarianWorker
from tidyos.workers.indexer_worker import IndexerWorker
from tidyos.workers.watcher_worker import WatcherServiceManager
from tidyos.safety.protection_manager import ProtectionManager
from tidyos.safety.policy import SafetyPolicy
from tidyos.services.mutation_service import MutationService
from tidyos.services.pipeline import PipelineOrchestrator
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
from tidyos.ui.onboarding.wizard import OnboardingWizard
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
        self.active_librarian_worker: Optional[LibrarianWorker] = None
        self.active_indexer_worker: Optional[IndexerWorker] = None
        self._indexing_in_progress: bool = False  # Guard against concurrent index runs

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

        # Initialize Safety, Mutation & Pipeline Services
        self.protection_manager = ProtectionManager(self.repository)
        self.safety_policy = SafetyPolicy(
            protection_manager=self.protection_manager,
            managed_roots_provider=lambda: [r.path for r in self.repository.list_managed_roots(enabled_only=True)],
        )
        self.mutation_service = MutationService(
            repository=self.repository,
            safety_policy=self.safety_policy,
        )
        self.pipeline = PipelineOrchestrator(
            repository=self.repository,
            safety_policy=self.safety_policy,
            mutation_service=self.mutation_service,
        )

        self.home_page = HomePage(repository=self.repository)
        self.search_page = SearchPage(repository=self.repository)
        self.organize_page = OrganizePage(repository=self.repository, mutation_service=self.mutation_service, pipeline=self.pipeline)
        self.review_page = ReviewPage(repository=self.repository, mutation_service=self.mutation_service)
        self.activity_page = ActivityPage(repository=self.repository, mutation_service=self.mutation_service)
        self.settings_page = SettingsPage(repository=self.repository)

        self.pages: dict[str, QWidget] = {
            "home": self.home_page,
            "search": self.search_page,
            "organize": self.organize_page,
            "review": self.review_page,
            "activity": self.activity_page,
            "settings": self.settings_page,
        }

        for page in self.pages.values():
            self.stack.addWidget(page)

        root_layout.addWidget(self.stack, 1)

        # Connect navigation
        self.sidebar.page_changed.connect(self.navigate_to)
        self.organize_page.navigate_requested.connect(self.navigate_to)

        # Connect cross-page synchronization
        self.review_page.proposal_applied.connect(self.activity_page.refresh_ledger)
        self.review_page.proposal_applied.connect(self.organize_page.refresh_page)
        self.review_page.proposal_applied.connect(self.home_page.refresh_metrics)

        self.activity_page.action_undone.connect(self.review_page.refresh_queue)
        self.activity_page.action_undone.connect(self.organize_page.refresh_page)
        self.activity_page.action_undone.connect(self.home_page.refresh_metrics)

        # Connect scan triggers and root change updates
        self.settings_page.scan_requested.connect(self.start_scan)
        self.settings_page.roots_changed.connect(self.home_page.refresh_metrics)
        # When a new root is added, immediately scan + understand + index it
        self.settings_page.roots_changed.connect(self._on_roots_changed)

        # Global Shortcut: Ctrl+K / Cmd+K to jump to search
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        self.search_shortcut.activated.connect(self._on_search_shortcut)

        # Initialize System Tray
        self._setup_system_tray()

        # Initialize Live Filesystem Watcher
        self.watcher_manager = WatcherServiceManager(
            repository=self.repository,
            pipeline=self.pipeline,
            parent=self,
        )
        self.watcher_manager.signals.review_needed.connect(self._on_watch_review_needed)
        self.watcher_manager.signals.file_organized.connect(self._on_watch_file_organized)
        # Auto-index search whenever the watcher finishes processing any file
        self.watcher_manager.signals.file_processed.connect(self._on_watch_file_processed)

        if config.watcher_enabled:
            self.watcher_manager.start_watching()

        # Initialize Onboarding Wizard
        self.onboarding_wizard = OnboardingWizard(
            repository=self.repository,
            safety_policy=self.safety_policy,
            mutation_service=self.mutation_service,
            parent=self,
        )
        self.stack.addWidget(self.onboarding_wizard)
        self.onboarding_wizard.completed.connect(self._on_onboarding_completed)
        self.settings_page.reset_demo_requested.connect(self._on_reset_demo_requested)

        # First Run check
        if not self.repository.is_first_run_completed():
            self.sidebar.hide()
            self.stack.setCurrentWidget(self.onboarding_wizard)
        else:
            self.sidebar.show()
            self.navigate_to("search")  # Search is the main screen

        logger.info("MainWindow initialized with real SQLite storage repository, mutation service, and watcher.")

        # Auto-process on startup: pick up any files added while the app was closed
        if self.repository.is_first_run_completed():
            roots = self.repository.list_managed_roots(enabled_only=True)
            if roots:
                logger.info("Auto-scanning %d managed root(s) on startup...", len(roots))
                self.start_scan()

    def _on_onboarding_completed(self):
        """User completed first-run onboarding — land on Search as main screen."""
        self.sidebar.show()
        self.navigate_to("search")  # Search is the main experience
        self.home_page.refresh_metrics()
        self.review_page.refresh_queue()
        self.organize_page.refresh_page()
        self.activity_page.refresh_ledger()
        if config.watcher_enabled and not self.watcher_manager.is_watching():
            self.watcher_manager.start_watching()

    def _on_reset_demo_requested(self):
        """Reset onboarding state and re-launch onboarding wizard."""
        self.repository.set_first_run_completed(False)
        self.sidebar.hide()
        self.stack.setCurrentWidget(self.onboarding_wizard)
        self.onboarding_wizard.stack.setCurrentIndex(0)

    def _on_watch_review_needed(self, filename: str, dest: str):
        """Notification when watcher routes an arrived file to the review queue."""
        logger.info("Watch Mode review required for '%s' -> '%s'", filename, dest)
        self.review_page.refresh_queue()
        self.organize_page.refresh_page()
        if self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "TidyOS Review Needed",
                f"New file ready for review: {filename}",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

    def _on_watch_file_organized(self, old_path: str, new_path: str):
        """Notification when watcher autonomously organizes an arrived file."""
        logger.info("Watch Mode organized file: %s -> %s", old_path, new_path)
        self.activity_page.refresh_ledger()
        self.organize_page.refresh_page()
        self.home_page.refresh_metrics()
        if self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "TidyOS File Organized",
                f"Organized: {Path(new_path).name}",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

    def _on_watch_file_processed(self, file_path: str, status: str, message: str):
        """Called after the watcher pipeline processes any arriving file.

        Automatically re-indexes the search vector/FTS store so newly arrived
        (and semantically analysed) files are immediately findable without any
        manual button press.
        """
        logger.debug("Watch: file processed '%s' status=%s — scheduling search index update", file_path, status)
        # Only index if the file was actually analysed (not an error or suppressed)
        if status not in ("ERROR",):
            self.start_indexing()

    def _on_roots_changed(self):
        """Called when the user adds or removes a managed root in Settings.

        Immediately kicks off scan → understand → index so the new folder
        appears in search without any manual step. Also restarts the watcher
        so the new root is picked up by Watch Mode.
        """
        logger.info("Managed roots changed — auto-scanning new roots and restarting watcher.")
        self.start_scan()
        # Restart watcher to pick up any newly added roots
        if config.watcher_enabled:
            self.watcher_manager.stop_watching()
            self.watcher_manager.start_watching()

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
        # Automatically trigger background Librarian semantic understanding for discovered files
        if total_files > 0:
            self.start_understanding()

    def start_understanding(self, target_files: Optional[List[str]] = None):
        """Start non-blocking Librarian semantic analysis across files."""
        logger.info("Initiating background Librarian semantic understanding...")
        worker = LibrarianWorker(self.repository, target_files=target_files)
        self.active_librarian_worker = worker

        worker.signals.progress.connect(self.home_page.show_understanding_progress)
        worker.signals.batch_completed.connect(self._on_understanding_completed)
        worker.signals.error.connect(self._on_understanding_error)

        self.thread_pool.start(worker)

    def _on_understanding_completed(self, processed: int, cached: int, duration_s: float):
        """Handle completion of background Librarian analysis."""
        logger.info(f"Librarian analysis finished: {processed} files ({cached} cached) in {duration_s:.2f}s")
        self.home_page.hide_understanding_progress(processed, cached, duration_s)
        self.settings_page.show_status_message(
            f"Librarian analyzed {processed:,} files ({cached} cached) in {duration_s:.1f}s."
        )
        # Trigger background vector and FTS indexing for newly understood files
        if processed > 0:
            self.start_indexing()

    def start_indexing(self):
        """Start non-blocking vector and FTS indexing across understood files.

        Guarded: if indexing is already running the call is a no-op — the
        in-flight worker will pick up any files queued in the meantime.
        """
        if self._indexing_in_progress:
            logger.debug("Indexing already in progress — skipping duplicate trigger.")
            return
        self._indexing_in_progress = True
        logger.info("Initiating background vector and FTS indexing...")
        worker = IndexerWorker(self.repository)
        self.active_indexer_worker = worker
        worker.signals.indexing_completed.connect(self._on_indexing_completed)
        self.thread_pool.start(worker)

    def _on_indexing_completed(self, total_indexed: int, duration_s: float):
        """Handle completion of background indexing."""
        self._indexing_in_progress = False
        logger.info(f"Indexing completed: {total_indexed} files in {duration_s:.2f}s")
        self.settings_page.show_status_message(
            f"Search index updated: {total_indexed} files indexed in {duration_s:.1f}s."
        )

    def _on_understanding_error(self, file_path: str, error_message: str):
        """Handle background Librarian error without crashing."""
        logger.warning(f"Librarian reported error for '{file_path}': {error_message}")

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

    def closeEvent(self, event):
        """Cleanly stop watcher on window close."""
        if hasattr(self, "watcher_manager"):
            self.watcher_manager.stop_watching()
        event.accept()
