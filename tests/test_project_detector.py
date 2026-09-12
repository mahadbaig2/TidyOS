"""Unit tests for deterministic ProjectRootDetector."""

import pytest
from pathlib import Path

from tidyos.safety import (
    ProjectRootDetector,
    DirectoryClassification,
)


def test_git_repository_detection(tmp_path: Path):
    """Test generic Git repository detection via .git marker."""
    git_dir = tmp_path / "my-repo"
    git_dir.mkdir()
    (git_dir / ".git").mkdir()

    detector = ProjectRootDetector()
    res = detector.detect(git_dir)

    assert res.classification == DirectoryClassification.PROTECTED
    assert res.project_type == "generic_git"
    assert ".git" in res.markers
    assert res.confidence == 1.0


def test_nextjs_project_detection(tmp_path: Path):
    """Test Next.js application detection via package.json and next.config.ts."""
    next_dir = tmp_path / "next-storefront"
    next_dir.mkdir()
    (next_dir / "package.json").write_text('{"name": "storefront"}', encoding="utf-8")
    (next_dir / "next.config.ts").write_text("export default {}", encoding="utf-8")
    (next_dir / "app").mkdir()
    (next_dir / "public").mkdir()

    detector = ProjectRootDetector()
    res = detector.detect(next_dir)

    assert res.classification == DirectoryClassification.PROTECTED
    assert res.project_type == "nextjs"
    assert "package.json" in res.markers
    assert "next.config.ts" in res.markers


def test_nextjs_detection_via_dependencies(tmp_path: Path):
    """Test Next.js detection via dependencies in package.json when config filename varies."""
    app_dir = tmp_path / "web-app"
    app_dir.mkdir()
    (app_dir / "package.json").write_text(
        '{"name": "web-app", "dependencies": {"next": "14.2.0", "react": "18.2.0"}}',
        encoding="utf-8",
    )

    detector = ProjectRootDetector()
    res = detector.detect(app_dir)

    assert res.classification == DirectoryClassification.PROTECTED
    assert res.project_type == "nextjs"
    assert "dependency:next" in res.markers


def test_node_project_detection(tmp_path: Path):
    """Test standard Node project detection via package.json and lockfile."""
    node_dir = tmp_path / "node-service"
    node_dir.mkdir()
    (node_dir / "package.json").write_text('{"name": "service"}', encoding="utf-8")
    (node_dir / "package-lock.json").write_text("{}", encoding="utf-8")

    detector = ProjectRootDetector()
    res = detector.detect(node_dir)

    assert res.classification == DirectoryClassification.PROTECTED
    assert res.project_type == "node"
    assert "package-lock.json" in res.markers


def test_python_project_detection(tmp_path: Path):
    """Test Python project detection via pyproject.toml and requirements.txt."""
    py_dir = tmp_path / "ai-agent"
    py_dir.mkdir()
    (py_dir / "pyproject.toml").write_text('[project]\nname = "agent"\n', encoding="utf-8")
    (py_dir / "requirements.txt").write_text("langchain>=0.2.0\n", encoding="utf-8")

    detector = ProjectRootDetector()
    res = detector.detect(py_dir)

    assert res.classification == DirectoryClassification.PROTECTED
    assert res.project_type == "python"
    assert "pyproject.toml" in res.markers
    assert "requirements.txt" in res.markers


def test_ordinary_folder_with_public_or_src_not_falsely_protected(tmp_path: Path):
    """Test that ordinary folder having 'public' or 'src' without project markers remains SAFE."""
    doc_dir = tmp_path / "UserPhotos"
    doc_dir.mkdir()
    (doc_dir / "public").mkdir()  # user happens to have a folder named 'public'
    (doc_dir / "src").mkdir()     # user happens to have a folder named 'src'
    (doc_dir / "photo.jpg").write_text("dummy photo", encoding="utf-8")

    detector = ProjectRootDetector()
    res = detector.detect(doc_dir)

    assert res.classification == DirectoryClassification.SAFE
    assert res.project_type is None


def test_nonexistent_directory_is_uncertain(tmp_path: Path):
    """Test that non-existent paths fail closed as UNCERTAIN."""
    detector = ProjectRootDetector()
    res = detector.detect(tmp_path / "does_not_exist")

    assert res.classification == DirectoryClassification.UNCERTAIN
