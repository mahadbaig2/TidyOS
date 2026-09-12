"""Background worker for non-blocking embedding generation and FTS indexing."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, List, Optional
from PySide6.QtCore import QObject, QRunnable, Signal

from tidyos.indexing.embeddings import LocalEmbeddingEngine, build_semantic_search_representation
from tidyos.indexing.fts import FTSIndexManager
from tidyos.storage.repository import StorageRepository
from tidyos.logging_config import get_logger

logger = get_logger("workers.indexer_worker")


class IndexerSignals(QObject):
    """Qt Signals emitted by background vector and FTS indexing worker."""

    started = Signal(int)  # total_files
    progress = Signal(int, int, str)  # current_idx, total, filename
    indexing_completed = Signal(int, float)  # total_indexed, duration_s
    error = Signal(str, str)  # file_path, error_msg


class IndexerWorker(QRunnable):
    """QRunnable background worker generating embeddings and FTS entries without blocking Qt UI."""

    def __init__(
        self,
        repository: StorageRepository,
        embedding_engine: Optional[LocalEmbeddingEngine] = None,
        fts_manager: Optional[FTSIndexManager] = None,
    ):
        super().__init__()
        self.repo = repository
        self.embedding_engine = embedding_engine or LocalEmbeddingEngine.get_instance()
        self.fts = fts_manager or FTSIndexManager(repository)
        self.signals = IndexerSignals()
        self._is_cancelled = False
        self.setAutoDelete(True)

    def cancel(self):
        """Request worker cancellation."""
        self._is_cancelled = True
        logger.info("Cancellation requested for IndexerWorker.")

    def run(self):
        """Index semantic representations into vector store and FTS5."""
        start_time = time.time()
        logger.info("IndexerWorker background thread started.")

        try:
            understandings = self.repo.list_file_understandings(limit=10000)
            total = len(understandings)
            self.signals.started.emit(total)

            if total == 0:
                logger.info("No file understandings to index.")
                self.signals.indexing_completed.emit(0, 0.0)
                return

            indexed_count = 0

            for idx, u in enumerate(understandings, 1):
                if self._is_cancelled:
                    logger.info("IndexerWorker aborted due to cancellation.")
                    break

                try:
                    p = Path(u.file_path)
                    if not p.exists():
                        continue

                    # 1. Update FTS index
                    self.fts.index_file(
                        file_path=u.file_path,
                        filename=p.name,
                        title=u.title,
                        summary=u.summary,
                        topics=u.topics,
                        entities=u.entities,
                        extracted_text=u.summary,
                    )

                    # 2. Check if embedding is already cached for this hash
                    existing_emb = self.repo.get_file_embedding(
                        u.file_path,
                        sha256_hash=u.sha256_hash,
                        embedding_model=self.embedding_engine.model_name,
                    )

                    if existing_emb is None:
                        rep = build_semantic_search_representation(
                            understanding=u,
                            filename=p.name,
                            path_context=str(p.parent),
                        )
                        vec = self.embedding_engine.embed_text(rep)
                        self.repo.save_file_embedding(
                            file_path=u.file_path,
                            sha256_hash=u.sha256_hash,
                            embedding_model=self.embedding_engine.model_name,
                            vector=vec,
                            semantic_representation=rep,
                        )

                    indexed_count += 1
                    self.signals.progress.emit(idx, total, p.name)

                except Exception as e:
                    logger.warning("Error indexing file %s: %s", u.file_path, e)
                    self.signals.error.emit(str(u.file_path), str(e))

            duration = time.time() - start_time
            self.signals.indexing_completed.emit(indexed_count, duration)
            logger.info("IndexerWorker finished: %d files indexed in %.2fs", indexed_count, duration)

        except Exception as e:
            logger.error("Fatal error in IndexerWorker execution: %s", e, exc_info=True)
            self.signals.error.emit("Global", str(e))
            self.signals.indexing_completed.emit(0, 0.0)
