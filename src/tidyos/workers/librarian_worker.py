"""Background worker for non-blocking semantic document analysis in PySide6."""

from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import QObject, QRunnable, Signal

from tidyos.agents.librarian import LibrarianAgent, FileUnderstanding
from tidyos.storage.repository import StorageRepository
from tidyos.logging_config import get_logger

logger = get_logger("workers.librarian_worker")


class LibrarianSignals(QObject):
    """Qt Signals emitted by background Librarian semantic understanding worker."""

    started = Signal(int)  # total_files
    progress = Signal(int, int, str, str)  # current_idx, total, filename, doc_type
    file_understood = Signal(str, str, str, float)  # path, doc_type, title, confidence
    batch_completed = Signal(int, int, float)  # processed, cached, duration_s
    error = Signal(str, str)  # file_path, error_msg


class LibrarianWorker(QRunnable):
    """QRunnable background worker executing semantic file understanding without blocking Qt UI."""

    def __init__(
        self,
        repository: StorageRepository,
        librarian_agent: Optional[LibrarianAgent] = None,
        target_files: Optional[List[str]] = None,
    ):
        super().__init__()
        self.repo = repository
        self.librarian = librarian_agent or LibrarianAgent(repository=repository)
        self.target_files = target_files
        self.signals = LibrarianSignals()
        self._is_cancelled = False
        self.setAutoDelete(True)

    def cancel(self):
        """Request worker cancellation."""
        self._is_cancelled = True
        logger.info("Cancellation requested for LibrarianWorker.")

    def run(self):
        """Analyze documents and images in background thread."""
        start_time = time.time()
        logger.info("LibrarianWorker background thread started.")

        try:
            files_to_process: List[str] = []
            if self.target_files is not None:
                files_to_process = self.target_files
            else:
                # Query candidate files from repository that have extractable extensions
                all_files = self.repo.list_files(limit=10000)
                for f in all_files:
                    if self.librarian.extractor.can_extract(f.path):
                        files_to_process.append(f.path)

            total = len(files_to_process)
            self.signals.started.emit(total)

            if total == 0:
                logger.info("No extractable files found for LibrarianWorker.")
                self.signals.batch_completed.emit(0, 0, 0.0)
                return

            processed = 0
            cached_hits = 0

            for idx, file_path in enumerate(files_to_process, 1):
                if self._is_cancelled:
                    logger.info("LibrarianWorker aborted due to cancellation.")
                    break

                try:
                    p = Path(file_path)
                    # Pre-check cache to track hit rate
                    existing = self.repo.get_file_understanding(file_path)
                    if existing and existing.analysis_source == "cached":
                        cached_hits += 1

                    understanding: FileUnderstanding = self.librarian.analyze_file(file_path)
                    processed += 1

                    self.signals.file_understood.emit(
                        understanding.file_path,
                        understanding.document_type,
                        understanding.title,
                        understanding.confidence,
                    )
                    self.signals.progress.emit(
                        idx,
                        total,
                        p.name,
                        understanding.document_type,
                    )
                except Exception as e:
                    logger.warning("Error analyzing file %s: %s", file_path, e)
                    self.signals.error.emit(str(file_path), str(e))

            duration = time.time() - start_time
            self.signals.batch_completed.emit(processed, cached_hits, duration)
            logger.info(
                f"LibrarianWorker completed: {processed}/{total} files ({cached_hits} cache hits) in {duration:.2f}s."
            )

        except Exception as e:
            logger.error(f"Fatal error in LibrarianWorker execution: {e}", exc_info=True)
            self.signals.error.emit("Global", str(e))
            self.signals.batch_completed.emit(0, 0, 0.0)
