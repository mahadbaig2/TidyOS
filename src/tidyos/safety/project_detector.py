"""Deterministic project root detector for TidyOS safety system."""

from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set, Dict, Any
from pydantic import BaseModel, Field

from tidyos.storage.roots import normalize_root_path
from tidyos.logging_config import get_logger

logger = get_logger("safety.project_detector")


class DirectoryClassification(str, Enum):
    """Classification states for filesystem directories."""
    SAFE = "SAFE"
    PROTECTED = "PROTECTED"
    UNCERTAIN = "UNCERTAIN"


class DetectionResult(BaseModel):
    """Structured detection outcome from ProjectRootDetector."""
    path: str
    classification: DirectoryClassification
    project_type: Optional[str] = None
    confidence: float = 1.0
    markers: List[str] = Field(default_factory=list)
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "classification": self.classification.value,
            "project_type": self.project_type,
            "confidence": self.confidence,
            "markers": self.markers,
            "reason": self.reason,
        }


# Strong individual project root indicators
GENERIC_GIT_MARKERS = {".git"}

NEXTJS_CONFIG_MARKERS = {
    "next.config.js",
    "next.config.mjs",
    "next.config.ts",
    "next.config.cjs",
}

NODE_LOCK_OR_DIR_MARKERS = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lockb",
    "node_modules",
}

PYTHON_ROOT_MARKERS = {
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "poetry.lock",
    ".venv",
    "venv",
}

TOOLING_MARKERS = {
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "Makefile",
    ".github",
}


class ProjectRootDetector:
    """Deterministic detector for software and structured project boundaries.

    HARD SAFETY RULE: Probabilistic intelligence never overrides deterministic authority.
    This detector uses concrete filesystem evidence to protect structured codebases.
    """

    def detect(self, dir_path: str | Path, entries: Optional[Set[str]] = None) -> DetectionResult:
        """Evaluate a directory path and return its deterministic classification.

        Parameters
        ----------
        dir_path : str | Path
            Directory path to inspect.
        entries : Optional[Set[str]]
            Pre-scanned list of entry names inside this directory (optional optimization).
        """
        canonical_path = normalize_root_path(dir_path)
        path_obj = Path(canonical_path)

        if not path_obj.exists() or not path_obj.is_dir():
            return DetectionResult(
                path=canonical_path,
                classification=DirectoryClassification.UNCERTAIN,
                confidence=0.5,
                markers=[],
                reason=f"Path does not exist or is not a directory: {canonical_path}",
            )

        # Gather directory entries if not provided
        if entries is None:
            try:
                entries = set(os.listdir(canonical_path))
            except (PermissionError, OSError) as e:
                logger.warning(f"Cannot read directory {canonical_path} for project detection: {e}")
                return DetectionResult(
                    path=canonical_path,
                    classification=DirectoryClassification.UNCERTAIN,
                    confidence=0.0,
                    markers=[],
                    reason=f"Permission denied or read error: {e}",
                )

        found_markers: List[str] = []

        # 1. Check Next.js Project (High priority specialization of Node)
        has_pkg_json = "package.json" in entries
        next_config_matches = entries.intersection(NEXTJS_CONFIG_MARKERS)

        if has_pkg_json and next_config_matches:
            found_markers.append("package.json")
            found_markers.extend(sorted(list(next_config_matches)))
            if ".git" in entries:
                found_markers.append(".git")
            for m in entries.intersection(NODE_LOCK_OR_DIR_MARKERS | {"app", "pages", "src", "public"}):
                found_markers.append(m)

            return DetectionResult(
                path=canonical_path,
                classification=DirectoryClassification.PROTECTED,
                project_type="nextjs",
                confidence=1.0,
                markers=sorted(list(set(found_markers))),
                reason="Detected Next.js application project root (package.json + next.config)",
            )

        # Check package.json contents for 'next' dependency if config file isn't explicitly top-level
        if has_pkg_json:
            try:
                pkg_file = path_obj / "package.json"
                if pkg_file.is_file() and pkg_file.stat().st_size < 500_000:
                    data = json.loads(pkg_file.read_text(encoding="utf-8", errors="ignore"))
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    if "next" in deps:
                        found_markers.append("package.json")
                        found_markers.append("dependency:next")
                        if ".git" in entries:
                            found_markers.append(".git")
                        return DetectionResult(
                            path=canonical_path,
                            classification=DirectoryClassification.PROTECTED,
                            project_type="nextjs",
                            confidence=1.0,
                            markers=sorted(list(set(found_markers))),
                            reason="Detected Next.js project root via package.json dependencies",
                        )
            except Exception as e:
                logger.debug(f"Could not parse package.json at {canonical_path}: {e}")

        # 2. Check Node / Package-Managed Project
        node_lock_matches = entries.intersection(NODE_LOCK_OR_DIR_MARKERS)
        if has_pkg_json and (node_lock_matches or "tsconfig.json" in entries):
            found_markers.append("package.json")
            found_markers.extend(sorted(list(node_lock_matches)))
            if ".git" in entries:
                found_markers.append(".git")
            return DetectionResult(
                path=canonical_path,
                classification=DirectoryClassification.PROTECTED,
                project_type="node",
                confidence=1.0,
                markers=sorted(list(set(found_markers))),
                reason="Detected Node.js / JavaScript project root",
            )

        # 3. Check Python Project
        py_matches = entries.intersection(PYTHON_ROOT_MARKERS)
        if py_matches:
            found_markers.extend(sorted(list(py_matches)))
            if ".git" in entries:
                found_markers.append(".git")
            return DetectionResult(
                path=canonical_path,
                classification=DirectoryClassification.PROTECTED,
                project_type="python",
                confidence=1.0,
                markers=sorted(list(set(found_markers))),
                reason=f"Detected Python project root (markers: {', '.join(sorted(py_matches))})",
            )

        # 4. Check Generic Git Repository
        if ".git" in entries:
            found_markers.append(".git")
            # Collect secondary markers if present
            found_markers.extend(sorted(list(entries.intersection(TOOLING_MARKERS))))
            return DetectionResult(
                path=canonical_path,
                classification=DirectoryClassification.PROTECTED,
                project_type="generic_git",
                confidence=1.0,
                markers=sorted(list(set(found_markers))),
                reason="Detected Git repository root (.git)",
            )

        # 5. Check Docker / Tooling Project Root
        tool_matches = entries.intersection(TOOLING_MARKERS)
        if len(tool_matches) >= 2 or ("Dockerfile" in tool_matches and ("src" in entries or "app" in entries)):
            found_markers.extend(sorted(list(tool_matches)))
            return DetectionResult(
                path=canonical_path,
                classification=DirectoryClassification.PROTECTED,
                project_type="docker_tooling",
                confidence=0.95,
                markers=sorted(list(set(found_markers))),
                reason=f"Detected structured project tooling ({', '.join(sorted(tool_matches))})",
            )

        # IMPORTANT: "src" or "public" alone WITHOUT project markers is NOT a project root.
        # It's an ordinary directory (e.g. Pictures/public or user created folder).
        return DetectionResult(
            path=canonical_path,
            classification=DirectoryClassification.SAFE,
            project_type=None,
            confidence=1.0,
            markers=[],
            reason="Ordinary directory without project root markers",
        )
