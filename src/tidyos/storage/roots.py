"""Managed roots domain validation and path normalization."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, List, Tuple


class RootValidationError(ValueError):
    """Raised when a candidate managed filesystem root is invalid."""
    pass


def normalize_root_path(raw_path: str | Path) -> str:
    """Normalize and resolve a path to its canonical absolute representation."""
    if not raw_path:
        raise RootValidationError("Path cannot be empty.")

    p = Path(raw_path).expanduser().resolve()
    canonical = os.path.normpath(str(p))

    # Normalize Windows drive letter to uppercase (e.g. 'c:\' -> 'C:\')
    if len(canonical) >= 2 and canonical[1] == ":" and canonical[0].islower():
        canonical = canonical[0].upper() + canonical[1:]

    return canonical


def validate_candidate_root(
    raw_path: str | Path,
    existing_roots: Optional[List[str]] = None,
) -> str:
    """Validate that a path is eligible to be added as a managed root.

    Returns the normalized canonical path if valid, or raises RootValidationError.
    """
    canonical = normalize_root_path(raw_path)
    p = Path(canonical)

    if not p.exists():
        raise RootValidationError(f"Directory does not exist: {canonical}")

    if not p.is_dir():
        raise RootValidationError(f"Path is not a directory: {canonical}")

    # Prevent managing entire Windows drive root (e.g. 'C:\')
    if canonical.endswith(":\\") or canonical.endswith(":/") or len(canonical) <= 3:
        raise RootValidationError(
            f"Cannot manage entire drive root ({canonical}). Please select a specific folder."
        )

    # Prevent system critical directories (e.g. Windows, Program Files)
    win_dir = os.environ.get("WINDIR", "C:\\Windows").lower()
    prog_files = os.environ.get("ProgramFiles", "C:\\Program Files").lower()
    prog_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)").lower()

    canon_lower = canonical.lower()
    if (
        canon_lower == win_dir
        or canon_lower.startswith(win_dir + "\\")
        or canon_lower == prog_files
        or canon_lower.startswith(prog_files + "\\")
        or canon_lower == prog_files_x86
        or canon_lower.startswith(prog_files_x86 + "\\")
    ):
        raise RootValidationError(
            f"Cannot manage system directory ({canonical}) for safety."
        )

    # Prevent duplicate or overlapping roots
    if existing_roots:
        for exist in existing_roots:
            exist_norm = normalize_root_path(exist)
            if exist_norm.lower() == canon_lower:
                raise RootValidationError(f"Directory is already a managed root: {canonical}")
            # Check nesting
            if canon_lower.startswith(exist_norm.lower() + os.sep):
                raise RootValidationError(
                    f"Directory is already covered by parent managed root: {exist_norm}"
                )
            if exist_norm.lower().startswith(canon_lower + os.sep):
                raise RootValidationError(
                    f"Directory contains an existing managed root: {exist_norm}. Remove it first."
                )

    return canonical


def is_path_in_managed_scope(path: str | Path, managed_roots: List[str]) -> Tuple[bool, Optional[str]]:
    """Check whether a given path is located inside any active managed root.

    Returns (in_scope, matching_managed_root).
    """
    try:
        norm = normalize_root_path(path).lower()
    except Exception:
        return False, None

    for root in managed_roots:
        try:
            r_norm = normalize_root_path(root).lower()
            if norm == r_norm or norm.startswith(r_norm + os.sep):
                return True, root
        except Exception:
            continue

    return False, None
