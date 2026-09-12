"""Unit tests for ProtectionManager and descendant boundary propagation."""

import pytest
from pathlib import Path

from tidyos.storage import StorageRepository
from tidyos.safety import (
    ProtectionManager,
    ProjectRootDetector,
    DirectoryClassification,
)


def test_descendant_protection_propagation(tmp_path: Path):
    """Test that all descendants of a protected root are unconditionally protected."""
    db_path = tmp_path / "test.db"
    repo = StorageRepository(db_path)

    project_root = tmp_path / "Projects" / "next-storefront"
    project_root.mkdir(parents=True)

    # Establish Next.js markers
    (project_root / "package.json").write_text('{"name": "storefront"}', encoding="utf-8")
    (project_root / "next.config.mjs").write_text("export default {};", encoding="utf-8")

    # Create deep nested structure
    public_dir = project_root / "public" / "images" / "nested"
    public_dir.mkdir(parents=True)
    logo_file = public_dir / "logo.png"
    logo_file.write_bytes(b"\x89PNG dummy")

    app_dir = project_root / "app" / "dashboard"
    app_dir.mkdir(parents=True)
    page_file = app_dir / "page.tsx"
    page_file.write_text("export default function Page() {}", encoding="utf-8")

    mgr = ProtectionManager(repo)

    # Detect and register project
    res = mgr.check_and_register_directory(project_root)
    assert res.classification == DirectoryClassification.PROTECTED
    assert res.project_type == "nextjs"

    # Verify project root is protected
    is_prot, prot = mgr.is_protected(project_root)
    assert is_prot is True
    assert prot.project_type == "nextjs"

    # CRITICAL INVARIANT: Descendants must be protected regardless of depth or name
    is_logo_prot, logo_prot = mgr.is_protected(logo_file)
    assert is_logo_prot is True
    assert logo_prot.path == str(project_root.resolve())

    is_page_prot, page_prot = mgr.is_protected(page_file)
    assert is_page_prot is True
    assert page_prot.path == str(project_root.resolve())

    # Path outside project is NOT protected
    outside_file = tmp_path / "Projects" / "other.pdf"
    outside_file.write_text("outside", encoding="utf-8")
    is_out_prot, _ = mgr.is_protected(outside_file)
    assert is_out_prot is False


def test_protected_roots_persisted_in_database(tmp_path: Path):
    """Test that detected protected roots are saved and reloaded across instances."""
    db_path = tmp_path / "test.db"
    repo = StorageRepository(db_path)

    py_root = tmp_path / "python-service"
    py_root.mkdir()
    (py_root / "pyproject.toml").write_text('[project]\nname="svc"\n', encoding="utf-8")

    mgr1 = ProtectionManager(repo)
    mgr1.check_and_register_directory(py_root)

    # Fresh instance reading from same SQLite DB
    mgr2 = ProtectionManager(repo)
    roots = mgr2.get_protected_roots()
    assert len(roots) == 1
    assert roots[0].project_type == "python"
    assert roots[0].path == str(py_root.resolve())
