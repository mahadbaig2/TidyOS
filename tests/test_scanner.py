"""Unit tests for read-only filesystem scanner."""

import os
import pytest
from pathlib import Path

from tidyos.storage import StorageRepository
from tidyos.indexing import FilesystemScanner, compute_sha256, detect_mime_type


def test_empty_directory_scan(tmp_path: Path):
    """Test scanner behavior on an empty managed directory."""
    db_path = tmp_path / "test.db"
    repo = StorageRepository(db_path)

    empty_dir = tmp_path / "EmptyFolder"
    empty_dir.mkdir()
    root = repo.add_managed_root(empty_dir)

    scanner = FilesystemScanner(repo)
    result = scanner.scan_root(root)

    assert result.total_files == 0
    assert result.total_directories == 1  # The root directory itself
    assert len(result.errors) == 0

    stats = repo.get_statistics()
    assert stats["total_files"] == 0
    assert stats["total_directories"] == 1


def test_nested_directory_and_metadata_extraction(tmp_path: Path):
    """Test recursive directory scanning, metadata collection, and hash calculation."""
    db_path = tmp_path / "test.db"
    repo = StorageRepository(db_path)

    managed_dir = tmp_path / "ManagedIntake"
    managed_dir.mkdir()

    # Create subfolders
    finance_dir = managed_dir / "Finance"
    finance_dir.mkdir()
    taxes_dir = finance_dir / "2026"
    taxes_dir.mkdir()

    # Create files
    file1 = managed_dir / "readme.txt"
    file1.write_text("Hello TidyOS", encoding="utf-8")

    file2 = taxes_dir / "w2_form.pdf"
    file2.write_bytes(b"%PDF-1.4 dummy pdf content for scanner testing")

    # Record hashes and mtimes before scan to verify READ-ONLY invariant
    hash1_before = compute_sha256(file1)
    hash2_before = compute_sha256(file2)
    mtime1_before = file1.stat().st_mtime
    mtime2_before = file2.stat().st_mtime

    root = repo.add_managed_root(managed_dir)
    scanner = FilesystemScanner(repo)

    progress_events = []

    def on_progress(p, f_count, d_count):
        progress_events.append((p, f_count, d_count))

    result = scanner.scan_root(root, progress_callback=on_progress)

    assert result.total_files == 2
    assert result.total_directories >= 3
    assert len(progress_events) == 2

    # Verify database contents
    files = repo.list_files(managed_root_id=root.id)
    assert len(files) == 2

    filenames = {f.filename for f in files}
    assert "readme.txt" in filenames
    assert "w2_form.pdf" in filenames

    pdf_rec = next(f for f in files if f.filename == "w2_form.pdf")
    assert pdf_rec.extension == ".pdf"
    assert pdf_rec.mime_type == "application/pdf"
    assert pdf_rec.sha256_hash == hash2_before
    assert pdf_rec.relative_path == "Finance/2026/w2_form.pdf"

    # STRICT READ-ONLY CHECK: Ensure files were not modified
    assert compute_sha256(file1) == hash1_before
    assert compute_sha256(file2) == hash2_before
    assert file1.stat().st_mtime == mtime1_before
    assert file2.stat().st_mtime == mtime2_before


def test_structural_markers_preservation(tmp_path: Path):
    """Test that scanner identifies directory structural markers like Next.js and Git."""
    db_path = tmp_path / "test.db"
    repo = StorageRepository(db_path)

    project_dir = tmp_path / "Workspace" / "next-app"
    project_dir.mkdir(parents=True)

    # Add project markers
    (project_dir / "package.json").write_text('{"name": "test-app"}', encoding="utf-8")
    (project_dir / "next.config.ts").write_text("export default {}", encoding="utf-8")
    (project_dir / ".git").mkdir()
    (project_dir / "app").mkdir()

    root = repo.add_managed_root(tmp_path / "Workspace")
    scanner = FilesystemScanner(repo)
    result = scanner.scan_root(root)

    assert result.total_files >= 2

    # Check directory records
    folders = repo.list_folders(managed_root_id=root.id)
    next_folder = next(f for f in folders if f.name == "next-app")
    assert ".git" in next_folder.structural_markers
    assert "package.json" in next_folder.structural_markers
    assert "next.config.ts" in next_folder.structural_markers
    assert "app" in next_folder.structural_markers


def test_missing_or_inaccessible_root_handling(tmp_path: Path):
    """Test scanner behavior when root directory is deleted or inaccessible."""
    db_path = tmp_path / "test.db"
    repo = StorageRepository(db_path)

    temp_root = tmp_path / "WillDisappear"
    temp_root.mkdir()
    root = repo.add_managed_root(temp_root)

    # Delete the directory to simulate external disconnection / disappearance
    temp_root.rmdir()

    scanner = FilesystemScanner(repo)
    result = scanner.scan_root(root)

    assert len(result.errors) > 0
    assert result.total_files == 0


def test_symlink_safety_and_cycle_avoidance(tmp_path: Path):
    """Test that scanner ignores symlink recursion and does not enter infinite loops."""
    db_path = tmp_path / "test.db"
    repo = StorageRepository(db_path)

    base = tmp_path / "SymlinkTest"
    base.mkdir()
    (base / "actual_file.txt").write_text("Hello Symlink", encoding="utf-8")

    sub = base / "subdir"
    sub.mkdir()

    # Try creating a recursive symlink if supported by OS permissions
    try:
        os.symlink(str(base), str(sub / "loop_link"), target_is_directory=True)
    except (OSError, NotImplementedError):
        # On Windows without Developer Mode, creating directory symlinks requires elevation
        pytest.skip("Symlink creation not permitted in this Windows environment")

    root = repo.add_managed_root(base)
    scanner = FilesystemScanner(repo)
    result = scanner.scan_root(root)

    # If os.walk followlinks=False, it does not recurse into loop_link
    assert result.total_files == 1
    stats = repo.get_statistics()
    assert stats["total_files"] == 1

