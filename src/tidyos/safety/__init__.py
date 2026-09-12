"""TidyOS Safety, Protection, and Policy Engine."""

from tidyos.safety.project_detector import (
    DirectoryClassification,
    DetectionResult,
    ProjectRootDetector,
    GENERIC_GIT_MARKERS,
    NEXTJS_CONFIG_MARKERS,
    NODE_LOCK_OR_DIR_MARKERS,
    PYTHON_ROOT_MARKERS,
    TOOLING_MARKERS,
)
from tidyos.safety.protection_manager import ProtectionManager
from tidyos.safety.policy import (
    PolicyStatus,
    ReasonCode,
    FileOperation,
    PolicyDecision,
    SafetyPolicy,
)

__all__ = [
    "DirectoryClassification",
    "DetectionResult",
    "ProjectRootDetector",
    "GENERIC_GIT_MARKERS",
    "NEXTJS_CONFIG_MARKERS",
    "NODE_LOCK_OR_DIR_MARKERS",
    "PYTHON_ROOT_MARKERS",
    "TOOLING_MARKERS",
    "ProtectionManager",
    "PolicyStatus",
    "ReasonCode",
    "FileOperation",
    "PolicyDecision",
    "SafetyPolicy",
]
