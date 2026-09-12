"""End-to-end Pipeline Orchestrator for TidyOS.

Unifies:
  File Arrival -> Guardian -> (PROTECTED: Index only)
                           -> (SAFE / UNCERTAIN: Librarian -> Organizer -> SafetyPolicy -> [AUTO / REVIEW])
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from tidyos.storage.models import ReviewQueueItem
from tidyos.storage.repository import StorageRepository
from tidyos.safety.policy import SafetyPolicy, FileOperation, PolicyStatus
from tidyos.safety.protection_manager import ProtectionManager
from tidyos.agents.guardian import GuardianAgent, GuardianExplanation
from tidyos.agents.librarian import LibrarianAgent, FileUnderstanding
from tidyos.agents.organizer import OrganizerAgent, OrganizationProposal
from tidyos.services.mutation_service import MutationService
from tidyos.logging_config import get_logger

logger = get_logger("services.pipeline")


class PipelineResult:
    """Outcome of processing a single file through the TidyOS pipeline."""

    def __init__(
        self,
        file_path: str,
        is_protected: bool = False,
        proposal: Optional[OrganizationProposal] = None,
        review_item_id: Optional[int] = None,
        action_id: Optional[int] = None,
        status: str = "PROCESSED",
        message: str = "",
    ):
        self.file_path = file_path
        self.is_protected = is_protected
        self.proposal = proposal
        self.review_item_id = review_item_id
        self.action_id = action_id
        self.status = status
        self.message = message


class PipelineOrchestrator:
    """Coordinates Guardian, Librarian, Organizer, SafetyPolicy, and MutationService."""

    def __init__(
        self,
        repository: StorageRepository,
        safety_policy: Optional[SafetyPolicy] = None,
        mutation_service: Optional[MutationService] = None,
        guardian_agent: Optional[GuardianAgent] = None,
        librarian_agent: Optional[LibrarianAgent] = None,
        organizer_agent: Optional[OrganizerAgent] = None,
    ):
        self.repository = repository

        protection_mgr = ProtectionManager(repository)
        self.safety_policy = safety_policy or SafetyPolicy(
            protection_manager=protection_mgr,
            managed_roots_provider=lambda: [r.path for r in repository.list_managed_roots(enabled_only=True)],
        )
        self.mutation_service = mutation_service or MutationService(
            repository=repository,
            safety_policy=self.safety_policy,
        )
        self.guardian = guardian_agent or GuardianAgent(
            safety_policy=self.safety_policy,
            protection_manager=protection_mgr,
        )
        self.librarian = librarian_agent or LibrarianAgent(repository=repository)
        self.organizer = organizer_agent or OrganizerAgent(repository=repository)

    def process_file(
        self,
        file_path: str,
        auto_mode: bool = False,
        candidate_roots: Optional[list[str]] = None,
    ) -> PipelineResult:
        """Execute the full autonomous intelligence and safety pipeline on a file."""
        p = Path(file_path)
        if not p.exists():
            return PipelineResult(file_path=file_path, status="NOT_FOUND", message="File does not exist")

        # 1. Environmental Safety Assessment (Guardian)
        decision, explanation = self.guardian.inspect(file_path=str(p))

        if explanation.is_protected or decision.status == PolicyStatus.DENY:
            logger.info("File '%s' is PROTECTED (%s). Indexing semantically without reorganization.", p.name, explanation.explanation)
            try:
                # Still index content semantically so it is searchable!
                self.librarian.analyze_file(str(p))
            except Exception as e:
                logger.debug("Semantic indexing error for protected file '%s': %s", p.name, e)

            return PipelineResult(
                file_path=str(p),
                is_protected=True,
                status="PROTECTED_INDEXED",
                message=f"Protected: {explanation.explanation}",
            )

        # 2. Content Understanding (Librarian)
        try:
            understanding: FileUnderstanding = self.librarian.analyze_file(str(p))
        except Exception as e:
            logger.warning("Librarian understanding error for '%s': %s", p.name, e)
            understanding = FileUnderstanding(
                file_path=str(p),
                sha256_hash="",
                document_type="unknown",
                title=p.stem,
                confidence=0.5,
            )

        # 3. Destination & Filename Advisory Proposal (Organizer)
        proposal: OrganizationProposal = self.organizer.propose(
            file_path=str(p),
            understanding=understanding,
            candidate_roots=candidate_roots,
        )

        if not proposal.organization_needed:
            logger.info("File '%s' is already in optimal organizational location.", p.name)
            return PipelineResult(
                file_path=str(p),
                is_protected=False,
                proposal=proposal,
                status="ALREADY_OPTIMAL",
                message="File already in correct folder",
            )

        # 4. Deterministic Pre-Mutation Safety Revalidation (SafetyPolicy)
        target_full = Path(proposal.proposed_destination) / proposal.proposed_filename
        val_op = FileOperation(
            operation_type="MOVE",
            source_path=str(p),
            destination_path=str(target_full),
            confidence=proposal.confidence,
            reason=proposal.reasoning,
        )
        pre_decision = self.safety_policy.validate(val_op)

        if pre_decision.status == PolicyStatus.DENY:
            logger.warning("Proposal for '%s' rejected by SafetyPolicy: %s", p.name, pre_decision.explanation)
            return PipelineResult(
                file_path=str(p),
                is_protected=False,
                proposal=proposal,
                status="SAFETY_DENIED",
                message=f"SafetyPolicy rejected move: {pre_decision.explanation}",
            )

        # 5. Check if eligible for immediate AUTO-Move
        can_auto_move = (
            auto_mode
            and pre_decision.status == PolicyStatus.ALLOW
            and proposal.confidence >= 0.85
            and not proposal.requires_folder_creation
            and Path(proposal.proposed_destination).exists()
            and not target_full.exists()
        )

        if can_auto_move:
            success, msg, action_id = self.mutation_service.apply_proposal(proposal, force_auto=True)
            if success:
                logger.info("Auto-organized file '%s' -> '%s' (action #%s)", p.name, target_full, action_id)
                return PipelineResult(
                    file_path=str(p),
                    is_protected=False,
                    proposal=proposal,
                    action_id=action_id,
                    status="AUTO_ORGANIZED",
                    message="File automatically organized",
                )

        # 6. Default: Route to Human Review Queue
        review_item = ReviewQueueItem(
            source_path=str(p),
            current_filename=p.name,
            suggested_filename=proposal.proposed_filename,
            suggested_destination=proposal.proposed_destination,
            confidence=proposal.confidence,
            reason=proposal.reasoning,
            status="PENDING",
        )
        review_id = self.repository.add_review_item(review_item)
        logger.info("Queued proposal for '%s' into review queue (#%s)", p.name, review_id)

        return PipelineResult(
            file_path=str(p),
            is_protected=False,
            proposal=proposal,
            review_item_id=review_id,
            status="QUEUED_FOR_REVIEW",
            message="Queued for user review",
        )
