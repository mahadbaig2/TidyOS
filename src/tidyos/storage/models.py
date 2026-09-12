"""Data models for TidyOS SQLite storage layer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    """Return current UTC timestamp formatted as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


class ManagedRoot(BaseModel):
    """Model representing an approved user filesystem root."""

    id: Optional[int] = None
    path: str
    mode: str = Field(default="AUTO")  # "AUTO" or "REVIEW"
    enabled: bool = True
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    exclusions: List[str] = Field(default_factory=list)


class DirectoryRecord(BaseModel):
    """Model representing a discovered directory within a managed root."""

    id: Optional[int] = None
    managed_root_id: int
    path: str
    relative_path: str
    name: str
    parent_path: Optional[str] = None
    depth: int = 0
    structural_markers: List[str] = Field(default_factory=list)
    is_present: bool = True
    indexed_at: str = Field(default_factory=utc_now_iso)


class FileRecord(BaseModel):
    """Model representing a discovered file within a managed root."""

    id: Optional[int] = None
    managed_root_id: int
    directory_id: Optional[int] = None
    path: str
    relative_path: str
    filename: str
    extension: str
    mime_type: Optional[str] = None
    size_bytes: int = 0
    created_at: str
    modified_at: str
    sha256_hash: Optional[str] = None
    is_present: bool = True
    indexed_at: str = Field(default_factory=utc_now_iso)


class ProtectedRoot(BaseModel):
    """Model representing a protected directory structure (e.g. Git, Next.js, Python)."""

    id: Optional[int] = None
    path: str
    project_type: str
    reason: str
    detected_markers: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class ActionRecord(BaseModel):
    """Model representing an auditable, reversible filesystem action."""

    id: Optional[int] = None
    source_path: str
    dest_path: str
    action_type: str = "MOVE"  # "MOVE" | "RENAME" | "MOVE_AND_RENAME"
    status: str = "PENDING"  # "PENDING" | "APPLIED" | "UNDONE" | "REJECTED" | "FAILED"
    agent_rationale: Optional[str] = None
    confidence: Optional[float] = None
    created_at: str = Field(default_factory=utc_now_iso)
    executed_at: Optional[str] = None
    undone_at: Optional[str] = None


class ReviewQueueItem(BaseModel):
    """Model representing an item in the human-in-the-loop review queue."""

    id: Optional[int] = None
    file_id: Optional[int] = None
    source_path: str = ""
    current_filename: str = ""
    suggested_filename: str
    suggested_destination: str
    confidence: float = 0.0
    reason: str = ""
    status: str = "PENDING"  # "PENDING" | "APPROVED" | "REJECTED" | "APPLIED"
    created_at: str = Field(default_factory=utc_now_iso)

