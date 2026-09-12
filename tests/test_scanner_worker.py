"""Unit tests for background ScannerWorker and Qt signals."""

import pytest
from pathlib import Path
from PySide6.QtCore import QThreadPool

from tidyos.storage import StorageRepository
from tidyos.workers.scanner_worker import ScannerWorker
from tidyos.testing.demo_corpus import create_demo_corpus


def test_scanner_worker_signals_and_execution(qapp, tmp_path: Path):
    """Test that ScannerWorker runs cleanly and emits appropriate Qt signals."""
    corpus = create_demo_corpus(tmp_path / "DemoCorpus")
    db_path = tmp_path / "test.db"
    repo = StorageRepository(db_path)

    root = repo.add_managed_root(corpus["downloads"])

    worker = ScannerWorker(repo, roots_to_scan=[root])

    started_roots = []
    progress_events = []
    completed_scans = []
    failed_scans = []

    worker.signals.scan_started.connect(started_roots.append)
    worker.signals.progress.connect(lambda p, f, d: progress_events.append((p, f, d)))
    worker.signals.scan_completed.connect(lambda f, d, dur: completed_scans.append((f, d, dur)))
    worker.signals.scan_failed.connect(lambda r, err: failed_scans.append((r, err)))

    # Run worker synchronously for test verification
    worker.run()

    assert len(started_roots) == 1
    assert started_roots[0] == root.path
    assert len(completed_scans) == 1
    total_files, total_dirs, duration = completed_scans[0]
    assert total_files == 3  # document (17).pdf, Screenshot_2026.png, random_notes.txt
    assert total_dirs >= 1
    assert len(failed_scans) == 0

    stats = repo.get_statistics()
    assert stats["total_files"] == 3


def test_scanner_worker_cancellation(qapp, tmp_path: Path):
    """Test that cancel() stops scanner loop safely."""
    corpus = create_demo_corpus(tmp_path / "DemoCorpus")
    db_path = tmp_path / "test.db"
    repo = StorageRepository(db_path)

    root1 = repo.add_managed_root(corpus["downloads"])
    root2 = repo.add_managed_root(corpus["projects"])

    worker = ScannerWorker(repo, roots_to_scan=[root1, root2])

    completed = []
    worker.signals.scan_completed.connect(lambda f, d, dur: completed.append(True))

    # Cancel immediately
    worker.cancel()
    worker.run()

    assert len(completed) == 1
