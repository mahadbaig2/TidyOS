"""Central Mutation Service for TidyOS.

DETERMINISTIC MUTATION AUTHORITY.
This is the ONLY production component authorized to physically move, rename,
or create folders on the filesystem.

All operations must pass SafetyPolicy validation immediately prior to execution.
Records actions into the audit ledger and synchronizes search indices.
"""

from __future__ import annotations

import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from tidyos.storage.models import ActionRecord, ReviewQueueItem, utc_now_iso
from tidyos.storage.repository import StorageRepository
from tidyos.safety.policy import SafetyPolicy, FileOperation, PolicyStatus, PolicyDecision
from tidyos.agents.organizer import OrganizationProposal
from tidyos.logging_config import get_logger

logger = get_logger("services.mutation_service")


class MutationService:
    """The central authority for physical filesystem mutations in TidyOS."""

    def __init__(
        self,
        repository: StorageRepository,
        safety_policy: SafetyPolicy,
    ):
        self.repository = repository
        self.safety_policy = safety_policy

        # Self-mutation event suppression for Watchdog (thread-safe with timestamps)
        self._suppressed_paths: Dict[str, float] = {}
        self._suppressed_lock = threading.Lock()

        # Folders created by TidyOS that can be safely pruned during Undo if empty
        self._created_folders: Set[str] = set()

    # -------------------------------------------------------------------------
    # Watchdog Suppression Tracking
    # -------------------------------------------------------------------------

    def suppress_path(self, path: str, duration_seconds: float = 10.0):
        """Mark a path as mutated by TidyOS to prevent watchdog feedback loops."""
        try:
            norm = str(Path(path).resolve()).lower()
            with self._suppressed_lock:
                self._suppressed_paths[norm] = time.time() + duration_seconds
        except Exception:
            pass

    def is_suppressed(self, path: str) -> bool:
        """Check if a filesystem event path was caused by TidyOS."""
        try:
            norm = str(Path(path).resolve()).lower()
            now = time.time()
            with self._suppressed_lock:
                # Clean expired entries
                expired = [k for k, exp in self._suppressed_paths.items() if exp < now]
                for k in expired:
                    del self._suppressed_paths[k]

                return norm in self._suppressed_paths
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Proposal Execution
    # -------------------------------------------------------------------------

    def apply_proposal(
        self,
        proposal: OrganizationProposal,
        force_auto: bool = False,
    ) -> Tuple[bool, str, Optional[int]]:
        """Validate and execute an advisory organization proposal.

        Returns:
            Tuple[bool, str, Optional[int]]: (success, message, action_id)
        """
        source_path = Path(proposal.file_path)
        dest_dir = Path(proposal.proposed_destination)
        dest_full = dest_dir / proposal.proposed_filename

        # 1. Source existence check
        if not source_path.exists():
            return False, f"Source file does not exist: {source_path}", None

        # 2. Collision check (Never overwrite)
        if dest_full.exists() and dest_full.resolve() != source_path.resolve():
            return False, f"Destination collision: file already exists at {dest_full}", None

        # 3. Determine operation type
        is_rename = proposal.proposed_filename.lower() != proposal.current_filename.lower()
        is_move = str(dest_dir.resolve()).lower() != str(source_path.parent.resolve()).lower() if source_path.parent.exists() else True

        if is_move and is_rename:
            op_type = "MOVE_AND_RENAME"
        elif is_rename:
            op_type = "RENAME"
        else:
            op_type = "MOVE"

        # 4. Mandatory SafetyPolicy Pre-Mutation Revalidation
        file_op = FileOperation(
            operation_type="MOVE",
            source_path=str(source_path),
            destination_path=str(dest_full),
            confidence=proposal.confidence,
            reason=proposal.reasoning,
        )

        decision: PolicyDecision = self.safety_policy.validate(file_op)

        if decision.status == PolicyStatus.DENY:
            logger.warning("Mutation rejected by SafetyPolicy: %s", decision.explanation)
            return False, f"SafetyPolicy DENY: {decision.explanation}", None

        if decision.status == PolicyStatus.REVIEW and not force_auto:
            logger.info("Mutation routed to REVIEW by SafetyPolicy: %s", decision.explanation)
            return False, f"Requires user review: {decision.explanation}", None

        # 5. Safe directory creation if required
        folder_was_created = False
        if not dest_dir.exists():
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                folder_was_created = True
                self._created_folders.add(str(dest_dir.resolve()).lower())
                logger.info("Created approved destination directory: %s", dest_dir)
            except Exception as e:
                logger.error("Failed to create destination directory '%s': %s", dest_dir, e)
                return False, f"Could not create folder: {e}", None

        # 6. Suppress watchdog events
        self.suppress_path(str(source_path))
        self.suppress_path(str(dest_full))

        # 7. Physical filesystem move / rename
        try:
            shutil.move(str(source_path), str(dest_full))
            logger.info("Physically executed %s: %s -> %s", op_type, source_path, dest_full)
        except Exception as e:
            logger.error("Physical file mutation failed (%s -> %s): %s", source_path, dest_full, e)
            # If we created the folder but the move failed, prune it
            if folder_was_created:
                try:
                    if not any(dest_dir.iterdir()):
                        dest_dir.rmdir()
                except Exception:
                    pass
            return False, f"Filesystem error: {e}", None

        # 8. Record in Action Ledger
        action = ActionRecord(
            source_path=str(source_path),
            dest_path=str(dest_full),
            action_type=op_type,
            status="APPLIED",
            agent_rationale=proposal.reasoning,
            confidence=proposal.confidence,
            executed_at=utc_now_iso(),
        )
        action_id = self.repository.record_action(action)

        # 9. Search and Database Index Synchronization
        try:
            # If a stale record already exists at the destination (from a prior run),
            # remove it first to avoid UNIQUE constraint violations.
            try:
                self.repository.delete_file_record(str(dest_full))
            except Exception:
                pass  # No stale record — that's fine
            self.repository.relocate_file_record(
                old_path=str(source_path),
                new_path=str(dest_full),
                new_filename=proposal.proposed_filename,
            )
            logger.info("Synchronized database index and FTS search for: %s", dest_full)
        except Exception as e:
            logger.warning("Failed to synchronize index for relocated file: %s", e)

        return True, "File organized successfully", action_id

    # -------------------------------------------------------------------------
    # Undo Capability (P0 Reversible Agency)
    # -------------------------------------------------------------------------

    def undo_action(self, action_id: int) -> Tuple[bool, str]:
        """Physically reverse a previously executed move/rename action.

        Returns:
            Tuple[bool, str]: (success, message)
        """
        action = self.repository.get_action(action_id)
        if not action:
            return False, f"Action #{action_id} not found in ledger"

        if action.status == "UNDONE":
            return False, f"Action #{action_id} has already been undone"

        if action.status != "APPLIED":
            return False, f"Cannot undo action #{action_id} with status '{action.status}'"

        current_path = Path(action.dest_path)
        orig_path = Path(action.source_path)

        # 1. Verify current file exists
        if not current_path.exists():
            return False, f"Cannot undo: file no longer exists at current location: {current_path}"

        # 2. Verify original location has no collision
        if orig_path.exists() and orig_path.resolve() != current_path.resolve():
            return False, f"Cannot undo: destination collision at original location: {orig_path}"

        # 3. SafetyPolicy validation for the reversal
        rev_op = FileOperation(
            operation_type="MOVE",
            source_path=str(current_path),
            destination_path=str(orig_path),
            confidence=1.0,
            reason="User requested Undo reversal",
        )
        decision = self.safety_policy.validate(rev_op)
        if decision.status == PolicyStatus.DENY:
            logger.warning("Undo blocked by SafetyPolicy: %s", decision.explanation)
            return False, f"Undo denied by safety policy: {decision.explanation}"

        # 4. Ensure original parent directory exists
        if not orig_path.parent.exists():
            try:
                orig_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return False, f"Could not restore original parent directory: {e}"

        # 5. Suppress watchdog events
        self.suppress_path(str(current_path))
        self.suppress_path(str(orig_path))

        # 6. Physical reversal move
        try:
            shutil.move(str(current_path), str(orig_path))
            logger.info("Physically executed UNDO: %s -> %s", current_path, orig_path)
        except Exception as e:
            logger.error("Physical reversal failed (%s -> %s): %s", current_path, orig_path, e)
            return False, f"Filesystem error during undo: {e}"

        # 7. Safely clean up destination folder if TidyOS created it and it is now empty
        dest_dir = current_path.parent
        norm_dest_dir = str(dest_dir.resolve()).lower()
        if norm_dest_dir in self._created_folders:
            try:
                if dest_dir.exists() and not any(dest_dir.iterdir()):
                    dest_dir.rmdir()
                    self._created_folders.discard(norm_dest_dir)
                    logger.info("Pruned empty TidyOS-created directory during undo: %s", dest_dir)
            except Exception as e:
                logger.debug("Could not prune directory during undo: %s", e)

        # 8. Update Action status in ledger
        self.repository.update_action_status(action_id, status="UNDONE", undone_at=utc_now_iso())

        # 9. Synchronize Search & Database Index back to original location
        try:
            self.repository.relocate_file_record(
                old_path=str(current_path),
                new_path=str(orig_path),
                new_filename=orig_path.name,
            )
            logger.info("Synchronized database index and FTS search back to: %s", orig_path)
        except Exception as e:
            logger.warning("Failed to synchronize index during undo: %s", e)

        return True, f"Successfully restored {orig_path.name} to original location"
