"""Central deterministic safety policy for TidyOS.

PROBABILISTIC INTELLIGENCE. DETERMINISTIC AUTHORITY.
All filesystem mutations must pass through this policy. No LLM or agent can override DENY.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from tidyos.storage.roots import normalize_root_path, is_path_in_managed_scope
from tidyos.safety.protection_manager import ProtectionManager
from tidyos.safety.project_detector import DirectoryClassification
from tidyos.logging_config import get_logger

logger = get_logger("safety.policy")


class PolicyStatus(str, Enum):
    """Decision outcomes from SafetyPolicy."""
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    DENY = "DENY"


class ReasonCode(str, Enum):
    """Machine-readable reason codes for policy evaluations."""
    VALID_SAFE_OPERATION = "VALID_SAFE_OPERATION"
    SOURCE_PROTECTED = "SOURCE_PROTECTED"
    DESTINATION_PROTECTED = "DESTINATION_PROTECTED"
    OUT_OF_SCOPE_SOURCE = "OUT_OF_SCOPE_SOURCE"
    OUT_OF_SCOPE_DESTINATION = "OUT_OF_SCOPE_DESTINATION"
    SYSTEM_PATH_DENIED = "SYSTEM_PATH_DENIED"
    DELETION_DENIED = "DELETION_DENIED"
    OVERWRITE_DENIED = "OVERWRITE_DENIED"
    INVALID_PATH = "INVALID_PATH"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    UNCERTAIN_DIRECTORY = "UNCERTAIN_DIRECTORY"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


class FileOperation(BaseModel):
    """Specification of an intended filesystem operation."""
    operation_type: str = "MOVE"  # "MOVE" | "RENAME" | "DELETE"
    source_path: str
    destination_path: Optional[str] = None
    managed_root: Optional[str] = None
    confidence: float = 1.0
    reason: Optional[str] = None


class PolicyDecision(BaseModel):
    """Evaluated policy outcome with machine-readable code and human explanation."""
    status: PolicyStatus
    reason_code: ReasonCode
    explanation: str
    details: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_allowed(self) -> bool:
        return self.status == PolicyStatus.ALLOW

    @property
    def requires_review(self) -> bool:
        return self.status == PolicyStatus.REVIEW

    @property
    def is_denied(self) -> bool:
        return self.status == PolicyStatus.DENY


class SafetyPolicy:
    """Central deterministic policy validator for all filesystem operations.

    HARD SAFETY INVARIANTS:
    1. An LLM cannot authorize a filesystem mutation.
    2. A descendant of a protected root cannot be autonomously moved or renamed.
    3. A path outside explicit managed scope cannot be mutated.
    4. UNCERTAIN never becomes automatic ALLOW.
    5. Failure of AI/network services cannot reduce filesystem protection.
    6. Protection takes precedence over semantic file classification.
    """

    def __init__(
        self,
        protection_manager: ProtectionManager,
        managed_roots_provider: Optional[callable] = None,
        confidence_threshold: float = 0.85,
    ):
        self.protection_manager = protection_manager
        self.managed_roots_provider = managed_roots_provider
        self.confidence_threshold = confidence_threshold

    def validate(self, op: FileOperation) -> PolicyDecision:
        """Validate an operation against deterministic safety invariants."""

        # Invariant: Permanent file deletion is strictly forbidden in MVP
        if op.operation_type.upper() in {"DELETE", "REMOVE", "UNLINK", "PERMANENT_DELETE"}:
            return PolicyDecision(
                status=PolicyStatus.DENY,
                reason_code=ReasonCode.DELETION_DENIED,
                explanation="Permanent deletion is disabled in TidyOS for safety.",
                details={"operation_type": op.operation_type},
            )

        # 1. Normalize and validate source path
        try:
            source_canon = normalize_root_path(op.source_path)
        except Exception as e:
            return PolicyDecision(
                status=PolicyStatus.DENY,
                reason_code=ReasonCode.INVALID_PATH,
                explanation=f"Source path cannot be resolved safely: {e}",
                details={"raw_source": op.source_path},
            )

        # Check system directory protection for source
        if self._is_system_path(source_canon):
            return PolicyDecision(
                status=PolicyStatus.DENY,
                reason_code=ReasonCode.SYSTEM_PATH_DENIED,
                explanation=f"Source is a protected Windows system path: {source_canon}",
                details={"path": source_canon},
            )

        # Verify source file exists
        if not Path(source_canon).exists():
            return PolicyDecision(
                status=PolicyStatus.DENY,
                reason_code=ReasonCode.SOURCE_NOT_FOUND,
                explanation=f"Source file does not exist: {source_canon}",
                details={"path": source_canon},
            )

        # 2. Check Managed Scope for Source
        active_managed_roots = self._get_active_managed_roots()
        in_scope, matched_root = is_path_in_managed_scope(source_canon, active_managed_roots)
        if not in_scope:
            return PolicyDecision(
                status=PolicyStatus.DENY,
                reason_code=ReasonCode.OUT_OF_SCOPE_SOURCE,
                explanation="Source path is outside user-approved managed folders.",
                details={"source_path": source_canon, "managed_roots": active_managed_roots},
            )

        # 3. Check Ancestor Protection for Source (Critical Invariant)
        is_prot, prot_record = self.protection_manager.is_protected(source_canon)
        if is_prot:
            prot_type = prot_record.project_type if prot_record else "structured codebase"
            prot_path = prot_record.path if prot_record else source_canon
            return PolicyDecision(
                status=PolicyStatus.DENY,
                reason_code=ReasonCode.SOURCE_PROTECTED,
                explanation=f"Source file is inside protected {prot_type} project: {prot_path}",
                details={
                    "source_path": source_canon,
                    "protected_root": prot_path,
                    "project_type": prot_type,
                },
            )

        # 4. Destination validation (if operation specifies a destination)
        if op.destination_path:
            try:
                dest_canon = normalize_root_path(op.destination_path)
            except Exception as e:
                return PolicyDecision(
                    status=PolicyStatus.DENY,
                    reason_code=ReasonCode.INVALID_PATH,
                    explanation=f"Destination path cannot be resolved safely: {e}",
                    details={"raw_destination": op.destination_path},
                )

            # Check system directory protection for destination
            if self._is_system_path(dest_canon):
                return PolicyDecision(
                    status=PolicyStatus.DENY,
                    reason_code=ReasonCode.SYSTEM_PATH_DENIED,
                    explanation=f"Destination is a protected Windows system path: {dest_canon}",
                    details={"path": dest_canon},
                )

            # Destination must be in managed scope
            dest_in_scope, dest_matched_root = is_path_in_managed_scope(dest_canon, active_managed_roots)
            if not dest_in_scope:
                return PolicyDecision(
                    status=PolicyStatus.DENY,
                    reason_code=ReasonCode.OUT_OF_SCOPE_DESTINATION,
                    explanation="Destination path escapes authorized managed folders.",
                    details={"destination_path": dest_canon, "managed_roots": active_managed_roots},
                )

            # Destination cannot be inside a protected project root
            dest_is_prot, dest_prot_rec = self.protection_manager.is_protected(dest_canon)
            if dest_is_prot:
                p_type = dest_prot_rec.project_type if dest_prot_rec else "structured codebase"
                p_path = dest_prot_rec.path if dest_prot_rec else dest_canon
                return PolicyDecision(
                    status=PolicyStatus.DENY,
                    reason_code=ReasonCode.DESTINATION_PROTECTED,
                    explanation=f"Destination is inside protected {p_type} project: {p_path}",
                    details={
                        "destination_path": dest_canon,
                        "protected_root": p_path,
                        "project_type": p_type,
                    },
                )

            # Prevent overwrite: destination must not already exist
            if Path(dest_canon).exists() and dest_canon.lower() != source_canon.lower():
                return PolicyDecision(
                    status=PolicyStatus.DENY,
                    reason_code=ReasonCode.OVERWRITE_DENIED,
                    explanation=f"Destination file already exists: {dest_canon}",
                    details={"destination_path": dest_canon},
                )

        # 5. Check Directory Uncertainty
        source_dir = str(Path(source_canon).parent)
        detect_res = self.protection_manager.detector.detect(source_dir)
        if detect_res.classification == DirectoryClassification.UNCERTAIN:
            return PolicyDecision(
                status=PolicyStatus.REVIEW,
                reason_code=ReasonCode.UNCERTAIN_DIRECTORY,
                explanation=f"Source folder has uncertain structural status: {detect_res.reason}",
                details={"source_directory": source_dir, "reason": detect_res.reason},
            )

        # 6. Check Agent Confidence Threshold
        if op.confidence < self.confidence_threshold:
            return PolicyDecision(
                status=PolicyStatus.REVIEW,
                reason_code=ReasonCode.LOW_CONFIDENCE,
                explanation=(
                    f"Agent confidence ({op.confidence:.0%}) is below threshold "
                    f"({self.confidence_threshold:.0%}); user review required."
                ),
                details={"confidence": op.confidence, "threshold": self.confidence_threshold},
            )

        # All deterministic checks passed
        return PolicyDecision(
            status=PolicyStatus.ALLOW,
            reason_code=ReasonCode.VALID_SAFE_OPERATION,
            explanation="Operation satisfies all deterministic safety policies.",
            details={
                "source": source_canon,
                "destination": op.destination_path,
                "managed_root": matched_root,
            },
        )

    def _get_active_managed_roots(self) -> List[str]:
        if self.managed_roots_provider:
            return self.managed_roots_provider()
        return [r.path for r in self.protection_manager.repository.list_managed_roots(enabled_only=True)]

    def _is_system_path(self, canonical_path: str) -> bool:
        """Check if path targets root drive or Windows system folder."""
        # Drive root check (e.g. C:\)
        if canonical_path.endswith(":\\") or canonical_path.endswith(":/") or len(canonical_path) <= 3:
            return True

        canon_lower = canonical_path.lower()
        win_dir = os.environ.get("WINDIR", "C:\\Windows").lower()
        prog_files = os.environ.get("ProgramFiles", "C:\\Program Files").lower()
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)").lower()

        return (
            canon_lower == win_dir
            or canon_lower.startswith(win_dir + "\\")
            or canon_lower == prog_files
            or canon_lower.startswith(prog_files + "\\")
            or canon_lower == prog_files_x86
            or canon_lower.startswith(prog_files_x86 + "\\")
        )
