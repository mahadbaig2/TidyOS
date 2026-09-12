"""Background worker for non-blocking filesystem scanning in PySide6."""

from __future__ import annotations

import time
from typing import List, Optional
from PySide6.QtCore import QObject, QRunnable, Signal

from tidyos.storage.models import ManagedRoot
from tidyos.storage.repository import StorageRepository
from tidyos.indexing.scanner import FilesystemScanner, ScanResult
from tidyos.logging_config import get_logger

logger = get_logger("workers.scanner_worker")


class ScannerSignals(QObject):
    """Qt Signals emitted by background filesystem scanner worker."""

    scan_started = Signal(str)  # root_path
    progress = Signal(str, int, int)  # current_path, files_found, dirs_found
    root_completed = Signal(str, int, int)  # root_path, files_found, dirs_found
    scan_completed = Signal(int, int, float)  # total_files, total_dirs, duration_s
    scan_failed = Signal(str, str)  # root_path, error_message


class ScannerWorker(QRunnable):
    """QRunnable background worker executing filesystem scans without blocking Qt UI."""

    def __init__(
        self,
        repository: StorageRepository,
        roots_to_scan: Optional[List[ManagedRoot]] = None,
    ):
        super().__init__()
        self.repo = repository
        self.roots_to_scan = roots_to_scan
        self.signals = ScannerSignals()
        self._is_cancelled = False
        self.setAutoDelete(True)

    def cancel(self):
        """Request cancellation of the active scan."""
        self._is_cancelled = True
        logger.info("Cancellation requested for ScannerWorker.")

    def run(self):
        """Execute scan across specified or enabled roots in background thread."""
        start_time = time.time()
        logger.info("ScannerWorker background thread started.")

        try:
            # If no explicit roots provided, scan all enabled roots
            roots = self.roots_to_scan
            if roots is None:
                roots = self.repo.list_managed_roots(enabled_only=True)

            if not roots:
                logger.info("No enabled roots to scan.")
                self.signals.scan_completed.emit(0, 0, 0.0)
                return

            scanner = FilesystemScanner(self.repo)
            total_files = 0
            total_dirs = 0

            for root in roots:
                if self._is_cancelled:
                    logger.info("Scan loop aborted due to cancellation.")
                    break

                self.signals.scan_started.emit(root.path)

                def on_progress(current_path: str, f_count: int, d_count: int):
                    self.signals.progress.emit(
                        current_path,
                        total_files + f_count,
                        total_dirs + d_count,
                    )

                def cancel_check() -> bool:
                    return self._is_cancelled

                try:
                    result: ScanResult = scanner.scan_root(
                        root,
                        progress_callback=on_progress,
                        cancel_check=cancel_check,
                    )
                    total_files += result.total_files
                    total_dirs += result.total_directories

                    if result.errors:
                        for err in result.errors:
                            self.signals.scan_failed.emit(root.path, err)

                    self.signals.root_completed.emit(
                        root.path,
                        result.total_files,
                        result.total_directories,
                    )
                except Exception as e:
                    logger.error(f"Scan failed unexpectedly for root '{root.path}': {e}", exc_info=True)
                    self.signals.scan_failed.emit(root.path, str(e))

            total_duration = time.time() - start_time
            self.signals.scan_completed.emit(total_files, total_dirs, total_duration)
            logger.info(
                f"ScannerWorker finished: {total_files} files, {total_dirs} directories in {total_duration:.2f}s."
            )

        except Exception as e:
            logger.error(f"Fatal error in ScannerWorker execution: {e}", exc_info=True)
            self.signals.scan_failed.emit("Global", str(e))
            self.signals.scan_completed.emit(0, 0, 0.0)
