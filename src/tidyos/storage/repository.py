"""Storage repository for local SQLite database operations."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

from tidyos.storage.models import (
    ManagedRoot,
    DirectoryRecord,
    FileRecord,
    ProtectedRoot,
    ActionRecord,
    utc_now_iso,
)
from tidyos.storage.schema import init_db
from tidyos.storage.roots import validate_candidate_root, normalize_root_path
from tidyos.logging_config import get_logger

logger = get_logger("storage.repository")


class StorageRepository:
    """Thread-safe SQLite storage repository."""

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self._local = threading.local()
        # Initialize schema once at instantiation
        init_db(self.db_path).close()
        logger.info(f"StorageRepository initialized for database: {self.db_path}")

    def get_connection(self) -> sqlite3.Connection:
        """Get or create thread-local database connection with WAL mode."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            self._local.conn = conn
        return self._local.conn

    def close(self):
        """Close thread-local connection if open."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None

    # -------------------------------------------------------------------------
    # Managed Roots
    # -------------------------------------------------------------------------

    def add_managed_root(
        self,
        raw_path: str | Path,
        mode: str = "AUTO",
        exclusions: Optional[List[str]] = None,
    ) -> ManagedRoot:
        """Validate, normalize, and insert a new managed root."""
        existing_roots = [r.path for r in self.list_managed_roots()]
        canonical_path = validate_candidate_root(raw_path, existing_roots=existing_roots)

        excl = exclusions or []
        excl_json = json.dumps(excl)
        now = utc_now_iso()

        conn = self.get_connection()
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO managed_roots (path, mode, enabled, created_at, updated_at, exclusions)
                VALUES (?, ?, 1, ?, ?, ?)
                """,
                (canonical_path, mode.upper(), now, now, excl_json),
            )
            root_id = cur.lastrowid

        logger.info(f"Added managed root: id={root_id}, path='{canonical_path}', mode={mode}")
        return ManagedRoot(
            id=root_id,
            path=canonical_path,
            mode=mode.upper(),
            enabled=True,
            created_at=now,
            updated_at=now,
            exclusions=excl,
        )

    def list_managed_roots(self, enabled_only: bool = False) -> List[ManagedRoot]:
        """Return list of managed roots."""
        conn = self.get_connection()
        query = "SELECT * FROM managed_roots"
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY id ASC"

        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()

        results = []
        for r in rows:
            try:
                excl = json.loads(r["exclusions"])
            except Exception:
                excl = []
            results.append(
                ManagedRoot(
                    id=r["id"],
                    path=r["path"],
                    mode=r["mode"],
                    enabled=bool(r["enabled"]),
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                    exclusions=excl,
                )
            )
        return results

    def get_managed_root(self, root_id: int) -> Optional[ManagedRoot]:
        """Fetch managed root by ID."""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM managed_roots WHERE id = ?", (root_id,))
        r = cur.fetchone()
        if not r:
            return None
        try:
            excl = json.loads(r["exclusions"])
        except Exception:
            excl = []
        return ManagedRoot(
            id=r["id"],
            path=r["path"],
            mode=r["mode"],
            enabled=bool(r["enabled"]),
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            exclusions=excl,
        )

    def get_managed_root_by_path(self, raw_path: str | Path) -> Optional[ManagedRoot]:
        """Fetch managed root matching path."""
        try:
            canonical = normalize_root_path(raw_path)
        except Exception:
            return None

        for root in self.list_managed_roots():
            if root.path.lower() == canonical.lower():
                return root
        return None

    def update_managed_root_mode(self, root_id: int, mode: str) -> bool:
        """Update operation mode (AUTO/REVIEW) for a managed root."""
        conn = self.get_connection()
        now = utc_now_iso()
        with conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE managed_roots SET mode = ?, updated_at = ? WHERE id = ?",
                (mode.upper(), now, root_id),
            )
            return cur.rowcount > 0

    def update_managed_root_enabled(self, root_id: int, enabled: bool) -> bool:
        """Enable or disable watching/scanning on a managed root."""
        conn = self.get_connection()
        now = utc_now_iso()
        with conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE managed_roots SET enabled = ?, updated_at = ? WHERE id = ?",
                (1 if enabled else 0, now, root_id),
            )
            return cur.rowcount > 0

    def remove_managed_root(self, root_id: int) -> bool:
        """Remove a managed root and all associated files/folders."""
        conn = self.get_connection()
        with conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM managed_roots WHERE id = ?", (root_id,))
            removed = cur.rowcount > 0
        if removed:
            logger.info(f"Removed managed root id={root_id}")
        return removed

    # -------------------------------------------------------------------------
    # Folders & Directories
    # -------------------------------------------------------------------------

    def upsert_folders(self, folders: List[DirectoryRecord]) -> Dict[str, int]:
        """Insert or update directory records. Returns mapping of path -> id."""
        if not folders:
            return {}

        conn = self.get_connection()
        path_to_id: Dict[str, int] = {}

        with conn:
            cur = conn.cursor()
            for f in folders:
                markers_json = json.dumps(f.structural_markers)
                cur.execute(
                    """
                    INSERT INTO folders (
                        managed_root_id, path, relative_path, name,
                        parent_path, depth, structural_markers, is_present, indexed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                    ON CONFLICT(path) DO UPDATE SET
                        relative_path = excluded.relative_path,
                        name = excluded.name,
                        parent_path = excluded.parent_path,
                        depth = excluded.depth,
                        structural_markers = excluded.structural_markers,
                        is_present = 1,
                        indexed_at = excluded.indexed_at
                    RETURNING id, path
                    """,
                    (
                        f.managed_root_id,
                        f.path,
                        f.relative_path,
                        f.name,
                        f.parent_path,
                        f.depth,
                        markers_json,
                        f.indexed_at,
                    ),
                )
                row = cur.fetchone()
                if row:
                    path_to_id[row["path"]] = row["id"]

        return path_to_id

    def list_folders(self, managed_root_id: Optional[int] = None) -> List[DirectoryRecord]:
        """List folders, optionally filtered by managed root."""
        conn = self.get_connection()
        cur = conn.cursor()
        if managed_root_id is not None:
            cur.execute(
                "SELECT * FROM folders WHERE managed_root_id = ? AND is_present = 1 ORDER BY depth ASC, path ASC",
                (managed_root_id,),
            )
        else:
            cur.execute("SELECT * FROM folders WHERE is_present = 1 ORDER BY depth ASC, path ASC")

        rows = cur.fetchall()
        results = []
        for r in rows:
            try:
                markers = json.loads(r["structural_markers"])
            except Exception:
                markers = []
            results.append(
                DirectoryRecord(
                    id=r["id"],
                    managed_root_id=r["managed_root_id"],
                    path=r["path"],
                    relative_path=r["relative_path"],
                    name=r["name"],
                    parent_path=r["parent_path"],
                    depth=r["depth"],
                    structural_markers=markers,
                    is_present=bool(r["is_present"]),
                    indexed_at=r["indexed_at"],
                )
            )
        return results

    # -------------------------------------------------------------------------
    # Files
    # -------------------------------------------------------------------------

    def upsert_files(self, files: List[FileRecord]):
        """Batch insert or update file records."""
        if not files:
            return

        conn = self.get_connection()
        with conn:
            cur = conn.cursor()
            for f in files:
                cur.execute(
                    """
                    INSERT INTO files (
                        managed_root_id, directory_id, path, relative_path,
                        filename, extension, mime_type, size_bytes,
                        created_at, modified_at, sha256_hash, is_present, indexed_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                    ON CONFLICT(path) DO UPDATE SET
                        directory_id = excluded.directory_id,
                        relative_path = excluded.relative_path,
                        filename = excluded.filename,
                        extension = excluded.extension,
                        mime_type = excluded.mime_type,
                        size_bytes = excluded.size_bytes,
                        created_at = excluded.created_at,
                        modified_at = excluded.modified_at,
                        sha256_hash = excluded.sha256_hash,
                        is_present = 1,
                        indexed_at = excluded.indexed_at
                    """,
                    (
                        f.managed_root_id,
                        f.directory_id,
                        f.path,
                        f.relative_path,
                        f.filename,
                        f.extension,
                        f.mime_type,
                        f.size_bytes,
                        f.created_at,
                        f.modified_at,
                        f.sha256_hash,
                        f.indexed_at,
                    ),
                )

    def list_files(
        self,
        managed_root_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[FileRecord]:
        """List files with optional pagination and root filter."""
        conn = self.get_connection()
        cur = conn.cursor()
        if managed_root_id is not None:
            cur.execute(
                """
                SELECT * FROM files
                WHERE managed_root_id = ? AND is_present = 1
                ORDER BY modified_at DESC
                LIMIT ? OFFSET ?
                """,
                (managed_root_id, limit, offset),
            )
        else:
            cur.execute(
                """
                SELECT * FROM files
                WHERE is_present = 1
                ORDER BY modified_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )

        rows = cur.fetchall()
        return [
            FileRecord(
                id=r["id"],
                managed_root_id=r["managed_root_id"],
                directory_id=r["directory_id"],
                path=r["path"],
                relative_path=r["relative_path"],
                filename=r["filename"],
                extension=r["extension"],
                mime_type=r["mime_type"],
                size_bytes=r["size_bytes"],
                created_at=r["created_at"],
                modified_at=r["modified_at"],
                sha256_hash=r["sha256_hash"],
                is_present=bool(r["is_present"]),
                indexed_at=r["indexed_at"],
            )
            for r in rows
        ]

    def mark_missing_items(self, managed_root_id: int, seen_file_paths: set[str], seen_folder_paths: set[str]):
        """Mark files and folders that were previously indexed but no longer present as is_present=0."""
        conn = self.get_connection()
        with conn:
            cur = conn.cursor()
            # Fetch existing active paths
            cur.execute("SELECT id, path FROM files WHERE managed_root_id = ? AND is_present = 1", (managed_root_id,))
            for row in cur.fetchall():
                if row["path"] not in seen_file_paths:
                    conn.execute("UPDATE files SET is_present = 0 WHERE id = ?", (row["id"],))

            cur.execute("SELECT id, path FROM folders WHERE managed_root_id = ? AND is_present = 1", (managed_root_id,))
            for row in cur.fetchall():
                if row["path"] not in seen_folder_paths:
                    conn.execute("UPDATE folders SET is_present = 0 WHERE id = ?", (row["id"],))

    # -------------------------------------------------------------------------
    # Protected Roots
    # -------------------------------------------------------------------------

    def upsert_protected_root(self, prot: ProtectedRoot):
        """Insert or update a protected structure record."""
        conn = self.get_connection()
        markers_json = json.dumps(prot.detected_markers)
        now = utc_now_iso()
        with conn:
            conn.execute(
                """
                INSERT INTO protected_roots (path, project_type, reason, detected_markers, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    project_type = excluded.project_type,
                    reason = excluded.reason,
                    detected_markers = excluded.detected_markers,
                    updated_at = excluded.updated_at
                """,
                (prot.path, prot.project_type, prot.reason, markers_json, prot.created_at, now),
            )

    def list_protected_roots(self) -> List[ProtectedRoot]:
        """Return list of protected directory roots."""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM protected_roots ORDER BY path ASC")
        rows = cur.fetchall()
        results = []
        for r in rows:
            try:
                markers = json.loads(r["detected_markers"])
            except Exception:
                markers = []
            results.append(
                ProtectedRoot(
                    id=r["id"],
                    path=r["path"],
                    project_type=r["project_type"],
                    reason=r["reason"],
                    detected_markers=markers,
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
            )
        return results

    # -------------------------------------------------------------------------
    # Actions (Audit / Undo ledger)
    # -------------------------------------------------------------------------

    def record_action(self, action: ActionRecord) -> int:
        """Record an action into the audit ledger."""
        conn = self.get_connection()
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO actions (
                    source_path, dest_path, action_type, status,
                    agent_rationale, confidence, created_at, executed_at, undone_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action.source_path,
                    action.dest_path,
                    action.action_type,
                    action.status,
                    action.agent_rationale,
                    action.confidence,
                    action.created_at,
                    action.executed_at,
                    action.undone_at,
                ),
            )
            return cur.lastrowid

    def list_actions(self, limit: int = 50) -> List[ActionRecord]:
        """Fetch recent actions from the ledger."""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM actions ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        return [
            ActionRecord(
                id=r["id"],
                source_path=r["source_path"],
                dest_path=r["dest_path"],
                action_type=r["action_type"],
                status=r["status"],
                agent_rationale=r["agent_rationale"],
                confidence=r["confidence"],
                created_at=r["created_at"],
                executed_at=r["executed_at"],
                undone_at=r["undone_at"],
            )
            for r in rows
        ]

    # -------------------------------------------------------------------------
    # Overall System Statistics
    # -------------------------------------------------------------------------

    def get_statistics(self) -> Dict[str, int]:
        """Return counts of managed roots, indexed files, folders, and protected structures."""
        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM managed_roots WHERE enabled = 1")
        total_roots = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM files WHERE is_present = 1")
        total_files = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM folders WHERE is_present = 1")
        total_dirs = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM protected_roots")
        total_protected = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM actions WHERE status = 'APPLIED'")
        total_organized = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM review_queue WHERE status = 'PENDING'")
        total_review = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM file_understandings")
        total_understood = cur.fetchone()[0]

        return {
            "total_roots": total_roots,
            "total_files": total_files,
            "total_directories": total_dirs,
            "total_protected": total_protected,
            "total_organized": total_organized,
            "total_review": total_review,
            "total_understood": total_understood,
        }

    # -------------------------------------------------------------------------
    # Semantic File Understandings (Librarian Cache & Search)
    # -------------------------------------------------------------------------

    def save_file_understanding(self, understanding: Any) -> int:
        """Persist or update semantic understanding for a file."""
        conn = self.get_connection()
        entities_json = json.dumps(understanding.entities or [])
        topics_json = json.dumps(understanding.topics or [])
        analyzed_at_iso = understanding.analyzed_at.isoformat() if hasattr(understanding.analyzed_at, "isoformat") else str(understanding.analyzed_at)

        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO file_understandings (
                    file_path, sha256_hash, document_type, title, summary,
                    entities, topics, suggested_folder, confidence,
                    extracted_chars, is_truncated, analysis_source, analyzed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path, sha256_hash) DO UPDATE SET
                    document_type = excluded.document_type,
                    title = excluded.title,
                    summary = excluded.summary,
                    entities = excluded.entities,
                    topics = excluded.topics,
                    suggested_folder = excluded.suggested_folder,
                    confidence = excluded.confidence,
                    extracted_chars = excluded.extracted_chars,
                    is_truncated = excluded.is_truncated,
                    analysis_source = excluded.analysis_source,
                    analyzed_at = excluded.analyzed_at
                """,
                (
                    str(understanding.file_path),
                    understanding.sha256_hash,
                    understanding.document_type,
                    understanding.title,
                    understanding.summary,
                    entities_json,
                    topics_json,
                    understanding.suggested_folder,
                    float(understanding.confidence),
                    int(understanding.extracted_chars),
                    1 if understanding.is_truncated else 0,
                    understanding.analysis_source,
                    analyzed_at_iso,
                ),
            )
            return cur.lastrowid

    def get_file_understanding(
        self, file_path: str, sha256_hash: Optional[str] = None
    ) -> Optional[Any]:
        """Fetch cached semantic understanding for a file, optionally verifying hash."""
        from datetime import datetime
        from tidyos.agents.librarian import FileUnderstanding

        conn = self.get_connection()
        cur = conn.cursor()

        if sha256_hash:
            cur.execute(
                """
                SELECT * FROM file_understandings
                WHERE file_path = ? AND sha256_hash = ?
                LIMIT 1
                """,
                (str(file_path), sha256_hash),
            )
        else:
            cur.execute(
                """
                SELECT * FROM file_understandings
                WHERE file_path = ?
                ORDER BY id DESC LIMIT 1
                """,
                (str(file_path),),
            )

        row = cur.fetchone()
        if not row:
            return None

        entities = json.loads(row["entities"]) if row["entities"] else []
        topics = json.loads(row["topics"]) if row["topics"] else []

        try:
            analyzed_at = datetime.fromisoformat(row["analyzed_at"])
        except Exception:
            analyzed_at = datetime.utcnow()

        return FileUnderstanding(
            file_path=row["file_path"],
            sha256_hash=row["sha256_hash"],
            document_type=row["document_type"],
            title=row["title"],
            summary=row["summary"],
            entities=entities,
            topics=topics,
            suggested_folder=row["suggested_folder"],
            confidence=float(row["confidence"]),
            extracted_chars=int(row["extracted_chars"]),
            is_truncated=bool(row["is_truncated"]),
            analysis_source=row["analysis_source"],
            analyzed_at=analyzed_at,
        )

    def list_file_understandings(
        self, document_type: Optional[str] = None, limit: int = 100
    ) -> List[Any]:
        """List recently analyzed file understandings."""
        from datetime import datetime
        from tidyos.agents.librarian import FileUnderstanding

        conn = self.get_connection()
        cur = conn.cursor()

        if document_type:
            cur.execute(
                """
                SELECT * FROM file_understandings
                WHERE document_type = ?
                ORDER BY id DESC LIMIT ?
                """,
                (document_type, limit),
            )
        else:
            cur.execute(
                """
                SELECT * FROM file_understandings
                ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            )

        results = []
        for row in cur.fetchall():
            entities = json.loads(row["entities"]) if row["entities"] else []
            topics = json.loads(row["topics"]) if row["topics"] else []
            try:
                analyzed_at = datetime.fromisoformat(row["analyzed_at"])
            except Exception:
                analyzed_at = datetime.utcnow()

            results.append(
                FileUnderstanding(
                    file_path=row["file_path"],
                    sha256_hash=row["sha256_hash"],
                    document_type=row["document_type"],
                    title=row["title"],
                    summary=row["summary"],
                    entities=entities,
                    topics=topics,
                    suggested_folder=row["suggested_folder"],
                    confidence=float(row["confidence"]),
                    extracted_chars=int(row["extracted_chars"]),
                    is_truncated=bool(row["is_truncated"]),
                    analysis_source=row["analysis_source"],
                    analyzed_at=analyzed_at,
                )
            )
        return results

