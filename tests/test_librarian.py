"""Tests for Librarian Agent and LibrarianWorker."""

from pathlib import Path
import pytest
import pymupdf
from PIL import Image

from tidyos.agents.librarian import LibrarianAgent, FileUnderstanding, compute_file_sha256
from tidyos.storage.repository import StorageRepository
from tidyos.workers.librarian_worker import LibrarianWorker


def test_compute_file_sha256(tmp_path: Path):
    test_file = tmp_path / "hash_test.txt"
    test_file.write_text("Unique content for hashing", encoding="utf-8")
    hash1 = compute_file_sha256(test_file)
    assert len(hash1) == 64
    assert hash1 == compute_file_sha256(test_file)

    # Modification alters hash
    test_file.write_text("Changed content", encoding="utf-8")
    hash2 = compute_file_sha256(test_file)
    assert hash1 != hash2


def test_librarian_analyze_file_and_cache(tmp_path: Path):
    db_path = tmp_path / "test.db"
    repo = StorageRepository(db_path)
    librarian = LibrarianAgent(repository=repo)

    # Create a test PDF invoice
    pdf_file = tmp_path / "invoice_999.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Invoice #999 from Beta Corp. Total Amount: $450.00")
    doc.save(str(pdf_file))
    doc.close()

    # First analysis (computed via local heuristic)
    u1 = librarian.analyze_file(pdf_file)
    assert u1.document_type == "invoice"
    assert u1.confidence > 0.0
    assert "Beta Corp" in u1.entities or len(u1.topics) > 0
    assert u1.analysis_source == "local_heuristic"

    # Second analysis (should hit SQLite cache)
    u2 = librarian.analyze_file(pdf_file)
    assert u2.document_type == "invoice"
    assert u2.title == u1.title
    assert u2.sha256_hash == u1.sha256_hash

    # Check database statistics
    stats = repo.get_statistics()
    assert stats["total_understood"] == 1
    repo.close()


def test_librarian_image_understanding_offline(tmp_path: Path):
    img_file = tmp_path / "screenshot_2026.png"
    img = Image.new("RGB", (200, 200), color="red")
    img.save(img_file, format="PNG")

    librarian = LibrarianAgent()
    understanding = librarian.analyze_file(img_file)

    assert understanding.document_type in ("screenshot", "image", "photo")
    assert understanding.is_truncated is False
    assert understanding.confidence > 0.0


def test_librarian_worker_execution(qapp, tmp_path: Path):
    """Test LibrarianWorker non-blocking execution across candidate files."""
    db_path = tmp_path / "test_worker.db"
    repo = StorageRepository(db_path)

    # Register managed root and insert files into database
    root_dir = tmp_path / "Docs"
    root_dir.mkdir()
    managed_root = repo.add_managed_root(root_dir)

    file1 = root_dir / "notes.md"
    file1.write_text("# Meeting Notes\nDiscussion on project architecture.", encoding="utf-8")

    file2 = root_dir / "receipt.txt"
    file2.write_text("Receipt from Coffee Shop\nTotal: $4.50\nPaid by Card", encoding="utf-8")

    from tidyos.indexing.scanner import FilesystemScanner
    scanner = FilesystemScanner(repo)
    scanner.scan_root(managed_root)

    worker = LibrarianWorker(repo)

    progress_events = []
    completed_events = []

    worker.signals.progress.connect(lambda idx, total, name, dt: progress_events.append((idx, total, name, dt)))
    worker.signals.batch_completed.connect(lambda p, c, dur: completed_events.append((p, c, dur)))

    # Run synchronously
    worker.run()

    assert len(progress_events) == 2
    assert len(completed_events) == 1
    processed, cached, duration = completed_events[0]
    assert processed == 2
    assert duration >= 0.0

    stats = repo.get_statistics()
    assert stats["total_understood"] == 2
    repo.close()


def test_librarian_zero_mutation_invariant(tmp_path: Path):
    """Verify that Librarian never moves, renames, or modifies original files."""
    test_file = tmp_path / "original_file.txt"
    content = "Immutable content"
    test_file.write_text(content, encoding="utf-8")
    orig_mtime = test_file.stat().st_mtime

    librarian = LibrarianAgent()
    understanding = librarian.analyze_file(test_file)

    # File must still exist at original path, unchanged
    assert test_file.exists()
    assert test_file.read_text(encoding="utf-8") == content
    assert test_file.stat().st_mtime == orig_mtime
    assert understanding.document_type is not None
