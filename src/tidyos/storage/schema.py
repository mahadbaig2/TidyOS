"""Database schema definition and bootstrap migrations for TidyOS SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Union

SCHEMA_VERSION = 1

CREATE_TABLES_SQL = """
-- Managed user approved filesystem roots
CREATE TABLE IF NOT EXISTS managed_roots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    mode TEXT NOT NULL DEFAULT 'AUTO',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    exclusions TEXT NOT NULL DEFAULT '[]'
);

-- Folders discovered within managed roots
CREATE TABLE IF NOT EXISTS folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    managed_root_id INTEGER NOT NULL REFERENCES managed_roots(id) ON DELETE CASCADE,
    path TEXT UNIQUE NOT NULL,
    relative_path TEXT NOT NULL,
    name TEXT NOT NULL,
    parent_path TEXT,
    depth INTEGER NOT NULL DEFAULT 0,
    structural_markers TEXT NOT NULL DEFAULT '[]',
    is_present INTEGER NOT NULL DEFAULT 1,
    indexed_at TEXT NOT NULL
);

-- Discovered individual files
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    managed_root_id INTEGER NOT NULL REFERENCES managed_roots(id) ON DELETE CASCADE,
    directory_id INTEGER REFERENCES folders(id) ON DELETE SET NULL,
    path TEXT UNIQUE NOT NULL,
    relative_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    extension TEXT NOT NULL,
    mime_type TEXT,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    modified_at TEXT NOT NULL,
    sha256_hash TEXT,
    is_present INTEGER NOT NULL DEFAULT 1,
    indexed_at TEXT NOT NULL
);

-- Protected software and structured project roots
CREATE TABLE IF NOT EXISTS protected_roots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    project_type TEXT NOT NULL,
    reason TEXT NOT NULL,
    detected_markers TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Audit ledger for all file movements and renames (enables undo)
CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL,
    dest_path TEXT NOT NULL,
    action_type TEXT NOT NULL DEFAULT 'MOVE',
    status TEXT NOT NULL DEFAULT 'PENDING',
    agent_rationale TEXT,
    confidence REAL,
    created_at TEXT NOT NULL,
    executed_at TEXT,
    undone_at TEXT
);

-- User preferences and configuration overrides
CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Human-in-the-loop review queue
CREATE TABLE IF NOT EXISTS review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    source_path TEXT,
    current_filename TEXT,
    suggested_filename TEXT,
    suggested_destination TEXT,
    confidence REAL,
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TEXT NOT NULL
);

-- Content text and metadata representations for future search indexing
CREATE TABLE IF NOT EXISTS file_text (
    file_id INTEGER PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,
    extracted_text TEXT,
    summary TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    indexed_at TEXT NOT NULL
);

-- Semantic file understanding produced by Librarian Agent
CREATE TABLE IF NOT EXISTS file_understandings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    sha256_hash TEXT NOT NULL,
    document_type TEXT NOT NULL DEFAULT 'unknown',
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    entities TEXT NOT NULL DEFAULT '[]',
    topics TEXT NOT NULL DEFAULT '[]',
    suggested_folder TEXT,
    confidence REAL NOT NULL DEFAULT 0.0,
    extracted_chars INTEGER NOT NULL DEFAULT 0,
    is_truncated INTEGER NOT NULL DEFAULT 0,
    analysis_source TEXT NOT NULL DEFAULT 'local_heuristic',
    analyzed_at TEXT NOT NULL,
    UNIQUE(file_path, sha256_hash)
);

-- Local vector embeddings for semantic retrieval
CREATE TABLE IF NOT EXISTS file_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    sha256_hash TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_dimension INTEGER NOT NULL DEFAULT 384,
    embedding_blob BLOB NOT NULL,
    semantic_representation TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(file_path, sha256_hash, embedding_model)
);

-- Full-Text Search (FTS5) for keyword, phrase, and identifier retrieval
CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
    file_path UNINDEXED,
    filename,
    title,
    summary,
    topics,
    entities,
    extracted_text,
    tokenize = 'unicode61'
);

-- Schema metadata table for tracking version
CREATE TABLE IF NOT EXISTS schema_info (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- Indexes for high performance querying
CREATE INDEX IF NOT EXISTS idx_files_root ON files(managed_root_id);
CREATE INDEX IF NOT EXISTS idx_files_ext ON files(extension);
CREATE INDEX IF NOT EXISTS idx_files_filename ON files(filename);
CREATE INDEX IF NOT EXISTS idx_folders_root ON folders(managed_root_id);
CREATE INDEX IF NOT EXISTS idx_folders_parent ON folders(parent_path);
CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status);
CREATE INDEX IF NOT EXISTS idx_actions_created ON actions(created_at);
CREATE INDEX IF NOT EXISTS idx_protected_roots_path ON protected_roots(path);
CREATE INDEX IF NOT EXISTS idx_file_understandings_path ON file_understandings(file_path);
CREATE INDEX IF NOT EXISTS idx_file_understandings_hash ON file_understandings(sha256_hash);
CREATE INDEX IF NOT EXISTS idx_file_understandings_type ON file_understandings(document_type);
CREATE INDEX IF NOT EXISTS idx_file_embeddings_path ON file_embeddings(file_path);
CREATE INDEX IF NOT EXISTS idx_file_embeddings_hash ON file_embeddings(sha256_hash);
CREATE INDEX IF NOT EXISTS idx_file_embeddings_model ON file_embeddings(embedding_model);
"""


def init_db(db_path: Union[str, Path]) -> sqlite3.Connection:
    """Initialize SQLite database with WAL mode and schema."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row

    # Performance & integrity pragmas
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    # Execute table creation
    conn.executescript(CREATE_TABLES_SQL)

    # Migrations for existing databases
    for col in ("source_path", "current_filename"):
        try:
            conn.execute(f"ALTER TABLE review_queue ADD COLUMN {col} TEXT;")
        except Exception:
            pass

    # Record schema version if not recorded
    cur = conn.cursor()
    cur.execute("SELECT version FROM schema_info WHERE version = ?", (SCHEMA_VERSION,))
    if cur.fetchone() is None:
        from datetime import datetime, timezone

        cur.execute(
            "INSERT INTO schema_info (version, applied_at) VALUES (?, ?)",
            (SCHEMA_VERSION, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

    return conn
