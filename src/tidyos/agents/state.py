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

    # Future agents state stubs
    extracted_text: Optional[str]
    file_type: Optional[str]
    summary: Optional[str]
    tags: List[str]
    suggested_filename: Optional[str]
    suggested_destination: Optional[str]
    confidence: float
    requires_review: bool

    # Pipeline outcome status
    status: str
    errors: List[str]
