"""Read-only recursive filesystem scanner and metadata extractor for TidyOS."""

from __future__ import annotations

import hashlib
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Set, List, Dict, Tuple, Any

from tidyos.storage.models import (
    DirectoryRecord,
    FileRecord,
    ManagedRoot,
    utc_now_iso,
)
from tidyos.storage.roots import normalize_root_path
from tidyos.storage.repository import StorageRepository
from tidyos.logging_config import get_logger

logger = get_logger("indexing.scanner")

# Initialize MIME types database
mimetypes.init()

# Known structural project markers
STRUCTURAL_MARKERS: Set[str] = {
    ".git",
    "package.json",
    "next.config.js",
    "next.config.mjs",
    "next.config.ts",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "node_modules",
    "pyproject.toml",
    "requirements.txt",
    "Pipfile",
    "setup.py",
    ".venv",
    "venv",
    "Dockerfile",
    "docker-compose.yml",
    ".github",
    "src",
    "app",
    "pages",
    "public",
}

# Max file size to compute hash synchronously during scan (25 MB)
MAX_HASH_FILE_SIZE_BYTES = 25 * 1024 * 1024


def compute_sha256(file_path: Path, max_size: int = MAX_HASH_FILE_SIZE_BYTES) -> Optional[str]:
    """Compute SHA-256 hash of a file safely in 64KB chunks.

    Returns None if file is larger than max_size or unreadable.
    """
    try:
        size = file_path.stat().st_size
        if size > max_size:
            return None

        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (PermissionError, FileNotFoundError, OSError) as e:
        logger.debug(f"Could not compute hash for {file_path}: {e}")
        return None


def detect_mime_type(file_path: Path) -> Optional[str]:
    """Determine MIME type from filename and system mimetypes."""
    mime, _ = mimetypes.guess_type(str(file_path))
    if mime:
        return mime

    # Fallback heuristics for common modern file extensions
    ext = file_path.suffix.lower()
    custom_map = {
        ".ts": "application/typescript",
        ".tsx": "application/typescript",
        ".jsx": "text/javascript",
        ".json": "application/json",
        ".md": "text/markdown",
        ".log": "text/plain",
        ".env": "text/plain",
        ".yaml": "text/yaml",
        ".yml": "text/yaml",
        ".toml": "text/toml",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }
    return custom_map.get(ext, "application/octet-stream")


class ScanResult:
    """Summary of a filesystem scan execution."""

    def __init__(self, root_path: str):
        self.root_path = root_path
        self.total_files: int = 0
        self.total_directories: int = 0
        self.errors: List[str] = []
        self.duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_path": self.root_path,
            "total_files": self.total_files,
            "total_directories": self.total_directories,
            "errors": self.errors,
            "duration_seconds": round(self.duration_seconds, 2),
        }


class FilesystemScanner:
    """Read-only recursive scanner for managed filesystem roots.

    HARD SAFETY RULE: All operations are strictly read-only.
    No file is renamed, moved, deleted, or overwritten.
    """

    def __init__(
        self,
        repository: StorageRepository,
        batch_size: int = 250,
    ):
        self.repo = repository
        self.batch_size = batch_size

    def scan_root(
        self,
        root: ManagedRoot,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> ScanResult:
        """Perform recursive read-only scan of a single managed root."""
        import time

        start_time = time.time()
        result = ScanResult(root.path)
        canonical_root = normalize_root_path(root.path)
        root_path_obj = Path(canonical_root)

        if not root_path_obj.exists() or not root_path_obj.is_dir():
            err = f"Managed root directory missing or inaccessible: {canonical_root}"
            logger.error(err)
            result.errors.append(err)
            result.duration_seconds = time.time() - start_time
            return result

        logger.info(f"Starting read-only scan of managed root: {canonical_root} (mode={root.mode})")

        seen_file_paths: Set[str] = set()
        seen_folder_paths: Set[str] = set()

        # Batch buffers for database upsert
        folder_buffer: List[DirectoryRecord] = []
        file_buffer: List[FileRecord] = []

        # Maintain map of folder path -> folder id in database
        folder_id_map: Dict[str, int] = {}

        # First, ensure root folder itself is recorded
        now_iso = utc_now_iso()
        root_dir_record = DirectoryRecord(
            managed_root_id=root.id,
            path=canonical_root,
            relative_path=".",
            name=root_path_obj.name,
            parent_path=None,
            depth=0,
            structural_markers=[],
            indexed_at=now_iso,
        )
        folder_id_map.update(self.repo.upsert_folders([root_dir_record]))
        seen_folder_paths.add(canonical_root)
        result.total_directories += 1

        # Recursive traversal using os.walk with followlinks=False to avoid symlink cycles
        for dirpath, dirnames, filenames in os.walk(canonical_root, followlinks=False):
            if cancel_check and cancel_check():
                logger.warning(f"Scan cancelled by user for root: {canonical_root}")
                break

            current_dir_path = normalize_root_path(dirpath)
            seen_folder_paths.add(current_dir_path)

            # Check exclusions
            if self._is_excluded(current_dir_path, root.exclusions):
                dirnames.clear()  # Do not recurse into excluded directory
                continue

            # Detect structural markers inside this directory
            entries_in_dir = set(dirnames) | set(filenames)
            detected_markers = sorted(list(entries_in_dir.intersection(STRUCTURAL_MARKERS)))

            # Calculate relative path and depth
            rel_dir = os.path.relpath(current_dir_path, canonical_root)
            depth = 0 if rel_dir == "." else len(Path(rel_dir).parts)

            parent_path = str(Path(current_dir_path).parent) if current_dir_path != canonical_root else None

            # Add directory record to buffer (if not root directory already created)
            if current_dir_path != canonical_root:
                dir_record = DirectoryRecord(
                    managed_root_id=root.id,
                    path=current_dir_path,
                    relative_path=rel_dir.replace("\\", "/"),
                    name=os.path.basename(current_dir_path),
                    parent_path=parent_path,
                    depth=depth,
                    structural_markers=detected_markers,
                    indexed_at=utc_now_iso(),
                )
                folder_buffer.append(dir_record)
                result.total_directories += 1

            # Flush folder buffer periodically to have folder IDs available
            if len(folder_buffer) >= self.batch_size:
                upserted = self.repo.upsert_folders(folder_buffer)
                folder_id_map.update(upserted)
                folder_buffer.clear()

            # Ensure current directory has an ID in the database
            current_dir_id = folder_id_map.get(current_dir_path)
            if current_dir_id is None and folder_buffer:
                # Flush to get ID
                upserted = self.repo.upsert_folders(folder_buffer)
                folder_id_map.update(upserted)
                folder_buffer.clear()
                current_dir_id = folder_id_map.get(current_dir_path)

            # Process files in current directory
            for filename in filenames:
                if cancel_check and cancel_check():
                    break

                file_path = os.path.join(current_dir_path, filename)
                try:
                    canon_file = normalize_root_path(file_path)
                except Exception as e:
                    logger.debug(f"Skipping unnormalizable filename '{filename}': {e}")
                    continue

                seen_file_paths.add(canon_file)

                # Skip exclusions
                if self._is_excluded(canon_file, root.exclusions):
                    continue

                # Collect file metadata safely
                try:
                    f_stat = os.stat(file_path, follow_symlinks=False)
                except (PermissionError, FileNotFoundError, OSError) as e:
                    logger.debug(f"Permission or missing error reading '{file_path}': {e}")
                    result.errors.append(f"Cannot access file {filename}: {str(e)}")
                    continue

                size = f_stat.st_size
                mtime = datetime.fromtimestamp(f_stat.st_mtime, tz=timezone.utc).isoformat()
                ctime = datetime.fromtimestamp(
                    getattr(f_stat, "st_birthtime", f_stat.st_ctime), tz=timezone.utc
                ).isoformat()

                rel_file = os.path.relpath(canon_file, canonical_root).replace("\\", "/")
                ext = os.path.splitext(filename)[1].lower()
                mime = detect_mime_type(Path(file_path))

                # Compute hash for files <= 25MB
                sha_hash = compute_sha256(Path(file_path))

                file_record = FileRecord(
                    managed_root_id=root.id,
                    directory_id=current_dir_id,
                    path=canon_file,
                    relative_path=rel_file,
                    filename=filename,
                    extension=ext,
                    mime_type=mime,
                    size_bytes=size,
                    created_at=ctime,
                    modified_at=mtime,
                    sha256_hash=sha_hash,
                    indexed_at=utc_now_iso(),
                )
                file_buffer.append(file_record)
                result.total_files += 1

                # Flush file buffer
                if len(file_buffer) >= self.batch_size:
                    self.repo.upsert_files(file_buffer)
                    file_buffer.clear()

                # Report progress
                if progress_callback:
                    try:
                        progress_callback(canon_file, result.total_files, result.total_directories)
                    except Exception as e:
                        logger.debug(f"Progress callback error: {e}")

        # Flush remaining buffers
        if folder_buffer:
            self.repo.upsert_folders(folder_buffer)
            folder_buffer.clear()

        if file_buffer:
            self.repo.upsert_files(file_buffer)
            file_buffer.clear()

        # Update presence status for missing/deleted items
        self.repo.mark_missing_items(root.id, seen_file_paths, seen_folder_paths)

        result.duration_seconds = time.time() - start_time
        logger.info(
            f"Completed scan of '{canonical_root}' in {result.duration_seconds:.2f}s: "
            f"{result.total_files} files, {result.total_directories} directories, {len(result.errors)} errors."
        )
        return result

    def _is_excluded(self, path: str, exclusions: List[str]) -> bool:
        """Check if path matches any exclusion rule."""
        if not exclusions:
            return False
        path_lower = path.lower()
        for excl in exclusions:
            if excl.lower() in path_lower:
                return True
        return False
