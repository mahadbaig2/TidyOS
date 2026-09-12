"""Protection manager enforcing ancestor protection propagation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Tuple, Set, Dict

from tidyos.storage.models import ProtectedRoot
from tidyos.storage.repository import StorageRepository
from tidyos.storage.roots import normalize_root_path
from tidyos.safety.project_detector import (
    ProjectRootDetector,
    DirectoryClassification,
    DetectionResult,
)
from tidyos.logging_config import get_logger

logger = get_logger("safety.protection_manager")


class ProtectionManager:
    """Manages and enforces structured directory boundary protection.

    CRITICAL INVARIANT:
    Ancestor protection takes absolute precedence over individual file semantics.
    If an ancestor directory is protected, every descendant file and folder is unconditionally protected.
    """

    def __init__(
        self,
        repository: StorageRepository,
        detector: Optional[ProjectRootDetector] = None,
    ):
        self.repository = repository
        self.detector = detector or ProjectRootDetector()
        self._cached_roots: Optional[List[ProtectedRoot]] = None

    def refresh_cache(self) -> List[ProtectedRoot]:
        """Reload known protected roots from storage repository."""
        self._cached_roots = self.repository.list_protected_roots()
        return self._cached_roots

    def get_protected_roots(self) -> List[ProtectedRoot]:
        """Return cached or freshly loaded protected roots."""
        if self._cached_roots is None:
            return self.refresh_cache()
        return self._cached_roots

    def is_protected(self, path: str | Path) -> Tuple[bool, Optional[ProtectedRoot]]:
        """Determine if a path is inside or identical to a protected project root.

        Evaluates the path against all registered protected roots in O(N).
        Returns:
            (True, matching_protected_root) if protected
            (False, None) if not protected
        """
        try:
            norm_target = normalize_root_path(path).lower()
        except Exception:
            # If path cannot be normalized, fail safe closed
            return True, None

        for prot in self.get_protected_roots():
            try:
                prot_norm = normalize_root_path(prot.path).lower()
                # Exact match or child descendant
                if norm_target == prot_norm or norm_target.startswith(prot_norm + os.sep):
                    return True, prot
            except Exception:
                continue

        return False, None

    def check_and_register_directory(
        self,
        dir_path: str | Path,
        entries: Optional[Set[str]] = None,
    ) -> DetectionResult:
        """Inspect a directory, classify it, and register it if detected as protected."""
        canonical = normalize_root_path(dir_path)

        # First, check if already covered by an ancestor protected root
        is_prot, ancestor_prot = self.is_protected(canonical)
        if is_prot and ancestor_prot and normalize_root_path(ancestor_prot.path).lower() != canonical.lower():
            # Already covered by ancestor
            return DetectionResult(
                path=canonical,
                classification=DirectoryClassification.PROTECTED,
                project_type=ancestor_prot.project_type,
                confidence=1.0,
                markers=ancestor_prot.detected_markers,
                reason=f"Descendant of protected {ancestor_prot.project_type} project: {ancestor_prot.path}",
            )

        # Run detector
        result = self.detector.detect(canonical, entries=entries)

        if result.classification == DirectoryClassification.PROTECTED:
            prot_record = ProtectedRoot(
                path=canonical,
                project_type=result.project_type or "generic_codebase",
                reason=result.reason,
                detected_markers=result.markers,
            )
            self.repository.upsert_protected_root(prot_record)
            self.refresh_cache()
            logger.info(
                f"Registered protected root: '{canonical}' [{prot_record.project_type}] - {result.reason}"
            )

        return result
