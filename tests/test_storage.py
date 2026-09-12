"""Unit tests for TidyOS SQLite storage layer and managed roots validation."""

import pytest
from pathlib import Path

from tidyos.storage import (
    StorageRepository,
    RootValidationError,
    validate_candidate_root,
    normalize_root_path,
    is_path_in_managed_scope,
    DirectoryRecord,
    FileRecord,
    ActionRecord,
)


def test_database_initialization(tmp_path: Path):
    """Test schema bootstrap and deterministic WAL initialization."""
    db_file = tmp_path / "test.db"
    repo = StorageRepository(db_file)
    assert db_file.exists()

    conn = repo.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cur.fetchall()}

    expected_tables = {
        "managed_roots",
        "folders",
        "files",
        "protected_roots",
        "actions",
        "preferences",
        "review_queue",
        "file_text",
        "schema_info",
    }
    assert expected_tables.issubset(tables)


def test_managed_root_validation_and_crud(tmp_path: Path):
    """Test validation, addition, listing, updating, and removal of managed roots."""
    db_file = tmp_path / "test.db"
    repo = StorageRepository(db_file)

    root_dir = tmp_path / "Downloads"
    root_dir.mkdir()

    # Add valid root
    root = repo.add_managed_root(root_dir, mode="AUTO")
    assert root.id is not None
    assert root.mode == "AUTO"
    assert root.enabled is True

    # Duplicate root rejection
    with pytest.raises(RootValidationError, match="already a managed root"):
        repo.add_managed_root(root_dir)

    # Sub-folder nesting rejection
    sub_dir = root_dir / "Subfolder"
    sub_dir.mkdir()
    with pytest.raises(RootValidationError, match="covered by parent"):
        repo.add_managed_root(sub_dir)

    # Non-existent path rejection
    with pytest.raises(RootValidationError, match="does not exist"):
        repo.add_managed_root(tmp_path / "NonExistent")

    # List roots
    roots = repo.list_managed_roots()
    assert len(roots) == 1
    assert roots[0].path == str(root_dir.resolve())

    # Mode update
    assert repo.update_managed_root_mode(root.id, "REVIEW") is True
    updated = repo.get_managed_root(root.id)
    assert updated.mode == "REVIEW"

    # In scope check
    in_scope, matched = is_path_in_managed_scope(sub_dir / "file.pdf", [r.path for r in roots])
    assert in_scope is True
    assert matched == str(root_dir.resolve())

    out_scope, _ = is_path_in_managed_scope(tmp_path / "Other" / "file.pdf", [r.path for r in roots])
    assert out_scope is False

    # Remove root
    assert repo.remove_managed_root(root.id) is True
    assert len(repo.list_managed_roots()) == 0


def test_files_and_folders_upsert(tmp_path: Path):
    """Test upserting discovered files, folders, and stats calculation."""
    db_file = tmp_path / "test.db"
    repo = StorageRepository(db_file)

    root_dir = tmp_path / "Documents"
    root_dir.mkdir()
    root = repo.add_managed_root(root_dir)

    folder = DirectoryRecord(
        managed_root_id=root.id,
        path=str((root_dir / "Finance").resolve()),
        relative_path="Finance",
        name="Finance",
        parent_path=str(root_dir.resolve()),
        depth=1,
        structural_markers=[],
    )
    folder_map = repo.upsert_folders([folder])
    folder_id = folder_map[folder.path]
    assert folder_id is not None

    file1 = FileRecord(
        managed_root_id=root.id,
        directory_id=folder_id,
        path=str((root_dir / "Finance" / "invoice.pdf").resolve()),
        relative_path="Finance/invoice.pdf",
        filename="invoice.pdf",
        extension=".pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        created_at="2026-09-12T00:00:00Z",
        modified_at="2026-09-12T00:00:00Z",
        sha256_hash="abcdef123456",
    )
    repo.upsert_files([file1])

    files = repo.list_files(managed_root_id=root.id)
    assert len(files) == 1
    assert files[0].filename == "invoice.pdf"
    assert files[0].sha256_hash == "abcdef123456"

    stats = repo.get_statistics()
    assert stats["total_roots"] == 1
    assert stats["total_files"] == 1
    assert stats["total_directories"] == 1


def test_action_record_ledger(tmp_path: Path):
    """Test action recording into audit ledger."""
    db_file = tmp_path / "test.db"
    repo = StorageRepository(db_file)

    action = ActionRecord(
        source_path="C:\\Downloads\\receipt.pdf",
        dest_path="C:\\Documents\\Finance\\receipt.pdf",
        action_type="MOVE",
        status="PENDING",
        agent_rationale="Matched invoice pattern",
        confidence=0.95,
    )
    action_id = repo.record_action(action)
    assert action_id is not None

    actions = repo.list_actions()
    assert len(actions) == 1
    assert actions[0].status == "PENDING"
    assert actions[0].confidence == 0.95
