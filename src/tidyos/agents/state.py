"""Typed shared state for TidyOS LangGraph multi-agent orchestration."""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict


class TidyOSState(TypedDict, total=False):
    """Shared state dictionary passed across LangGraph nodes."""

    # File and location context
    file_path: str
    managed_root: Optional[str]
    parent_directory: Optional[str]

    # Deterministic safety and protection
    protected: bool
    protection_reason: Optional[str]
    project_type: Optional[str]
    detected_markers: List[str]

    # Policy validation
    policy_status: str  # "ALLOW" | "REVIEW" | "DENY"
    policy_reason_code: Optional[str]
    policy_explanation: Optional[str]

    # Guardian contextual explanation
    guardian_explanation: Optional[str]
    suggested_routing: Optional[str]  # "STOP_PROTECTED" | "REVIEW" | "ELIGIBLE"

    # Librarian semantic analysis state
    document_type: Optional[str]
    title: Optional[str]
    summary: Optional[str]
    entities: List[str]
    topics: List[str]
    suggested_folder: Optional[str]
    analysis_source: Optional[str]
    extracted_chars: int
    is_truncated: bool
    confidence: float
    requires_review: bool

    # Organizer proposal state
    proposed_filename: Optional[str]
    proposed_destination: Optional[str]
    organization_reasoning: Optional[str]
    organization_confidence: Optional[float]
    organization_needed: Optional[bool]
    requires_folder_creation: Optional[bool]
    signals_used: Optional[List[str]]
    action_status: Optional[str]
    action_id: Optional[int]

    # Pipeline outcome status
    status: str
    errors: List[str]

