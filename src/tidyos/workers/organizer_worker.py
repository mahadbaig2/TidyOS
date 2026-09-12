"""Background worker for batch file organization analysis in PySide6."""

from __future__ import annotations

import time
from typing import List, Optional
from PySide6.QtCore import QObject, QRunnable, Signal

from tidyos.storage.repository import StorageRepository
from tidyos.services.pipeline import PipelineOrchestrator, PipelineResult
from tidyos.logging_config import get_logger

logger = get_logger("workers.organizer_worker")


class OrganizerSignals(QObject):
    """Qt Signals emitted by background organizer worker."""

    started = Signal(int)  # total_files
    progress = Signal(int, int, str)  # current, total, filename
    completed = Signal(int, int, float)  # organized_or_queued, total, duration_s
    error = Signal(str, str)  # file_path, error_msg


class OrganizerWorker(QRunnable):
    """QRunnable background worker executing organization proposals across managed roots."""

    def __init__(
        self,
        repository: StorageRepository,
        pipeline: Optional[PipelineOrchestrator] = None,
        target_files: Optional[List[str]] = None,
    ):
        super().__init__()
        self.repository = repository
        self.pipeline = pipeline or PipelineOrchestrator(repository=repository)
        self.target_files = target_files
        self.signals = OrganizerSignals()
        self._is_cancelled = False
        self.setAutoDelete(True)

    def cancel(self):
        self._is_cancelled = True
        logger.info("Cancellation requested for OrganizerWorker.")

    def run(self):
        start_time = time.time()
        logger.info("OrganizerWorker background thread started.")

        try:
            files_to_process = self.target_files
            if files_to_process is None:
                # Query present files from repository
                db_files = self.repository.list_files(limit=500)
                files_to_process = [f.path for f in db_files if f.is_present]

            total = len(files_to_process)
            self.signals.started.emit(total)

            queued_or_applied = 0
            for idx, file_path in enumerate(files_to_process, start=1):
                if self._is_cancelled:
                    logger.info("OrganizerWorker cancelled.")
                    break

                self.signals.progress.emit(idx, total, file_path)

                try:
                    res: PipelineResult = self.pipeline.process_file(file_path, auto_mode=False)
                    if res.status in {"QUEUED_FOR_REVIEW", "AUTO_ORGANIZED"}:
                        queued_or_applied += 1
                except Exception as e:
                    logger.warning("Error organizing file '%s': %s", file_path, e)
                    self.signals.error.emit(file_path, str(e))

            duration = time.time() - start_time
            self.signals.completed.emit(queued_or_applied, total, duration)
            logger.info("OrganizerWorker completed: %d/%d processed in %.2fs", queued_or_applied, total, duration)
        except Exception as e:
            logger.error("Fatal error in OrganizerWorker: %s", e, exc_info=True)
