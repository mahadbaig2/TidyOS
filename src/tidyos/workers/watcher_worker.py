"""PySide6 background worker bridging FilesystemWatcher and PipelineOrchestrator."""

from __future__ import annotations

from typing import List, Optional
from PySide6.QtCore import QObject, Signal

from tidyos.storage.repository import StorageRepository
from tidyos.services.watcher import FilesystemWatcher
from tidyos.services.pipeline import PipelineOrchestrator, PipelineResult
from tidyos.logging_config import get_logger

logger = get_logger("workers.watcher_worker")


class WatcherSignals(QObject):
    """Signals emitted by watcher pipeline to update PySide6 UI."""

    file_detected = Signal(str)  # filename/path
    file_processed = Signal(str, str, str)  # path, status, message
    review_needed = Signal(str, str)  # filename, suggested_destination
    file_organized = Signal(str, str)  # old_path, new_path
    watcher_state_changed = Signal(bool, list)  # is_running, watched_roots


class WatcherServiceManager(QObject):
    """Manages active watcher lifecycle and connects events to PipelineOrchestrator."""

    def __init__(
        self,
        repository: StorageRepository,
        pipeline: Optional[PipelineOrchestrator] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.repository = repository
        self.pipeline = pipeline or PipelineOrchestrator(repository=repository)
        self.signals = WatcherSignals()

        self.watcher = FilesystemWatcher(
            on_file_detected=self._on_file_arrived,
            is_suppressed_callback=self.pipeline.mutation_service.is_suppressed,
            debounce_seconds=2.0,
        )

    def is_running(self) -> bool:
        return self.watcher.is_running

    def start_watching(self, roots_to_watch: Optional[List[str]] = None):
        """Start monitoring enabled managed roots."""
        if roots_to_watch is None:
            roots_to_watch = [r.path for r in self.repository.list_managed_roots(enabled_only=True)]

        if not roots_to_watch:
            logger.warning("No enabled roots available to watch.")
            return

        self.watcher.start(roots_to_watch)
        self.signals.watcher_state_changed.emit(self.watcher.is_running, roots_to_watch)

    def stop_watching(self):
        """Stop monitoring."""
        self.watcher.stop()
        self.signals.watcher_state_changed.emit(False, [])

    def _on_file_arrived(self, file_path: str):
        """Dispatched when a stable new file appears in a watched root."""
        self.signals.file_detected.emit(file_path)

        # Run pipeline
        try:
            res: PipelineResult = self.pipeline.process_file(file_path, auto_mode=False)
            self.signals.file_processed.emit(file_path, res.status, res.message)

            if res.status == "QUEUED_FOR_REVIEW" and res.proposal:
                self.signals.review_needed.emit(
                    res.proposal.current_filename,
                    res.proposal.proposed_destination,
                )
            elif res.status == "AUTO_ORGANIZED" and res.proposal:
                self.signals.file_organized.emit(
                    res.proposal.file_path,
                    res.proposal.proposed_full_path,
                )
        except Exception as e:
            logger.error("Error processing arrived file '%s': %s", file_path, e, exc_info=True)
            self.signals.file_processed.emit(file_path, "ERROR", str(e))
