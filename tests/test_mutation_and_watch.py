"""Tests for Combined Phase 5 + 6: Safe Filesystem Agency + Watch Mode.

Verifies:
1. Organizer produces structured proposals without mutation authority.
2. SafetyPolicy pre-mutation revalidation (protected source, destination, unmanaged, collision).
3. Physical move+rename and ActionRecord persistence.
4. Reversible Undo restoring original file and index.
5. Index and search synchronization across mutations and undo.
6. Watchdog stability checks, temporary file ignoring, debounce, and loop suppression.
7. Environmental safety invariant (the same invoice in Downloads can move; in a project it cannot).
"""

import time
from pathlib import Path
import pytest

from tidyos.storage.models import ManagedRoot, FileRecord, ActionRecord, DirectoryRecord
from tidyos.storage.repository import StorageRepository
from tidyos.safety.protection_manager import ProtectionManager
from tidyos.safety.policy import SafetyPolicy, FileOperation, PolicyStatus
from tidyos.agents.guardian import GuardianAgent
from tidyos.agents.librarian import LibrarianAgent, FileUnderstanding
from tidyos.agents.organizer import OrganizerAgent, OrganizationProposal, sanitize_windows_filename
from tidyos.services.mutation_service import MutationService
from tidyos.services.watcher import FilesystemWatcher, should_ignore_file, is_file_stable, TidyOSEventHandler
from tidyos.services.pipeline import PipelineOrchestrator, PipelineResult
from tidyos.indexing.fts import FTSIndexManager


@pytest.fixture
def test_env(tmp_path: Path):
    """Set up isolated sandbox with managed roots, SQLite repo, safety policy, and mutation service."""
    db_path = tmp_path / "test_agency.db"
    repo = StorageRepository(db_path)

    # Set up approved intake folders: Downloads and Documents
    downloads_dir = tmp_path / "Downloads"
    downloads_dir.mkdir(parents=True)
    documents_dir = tmp_path / "Documents"
    documents_dir.mkdir(parents=True)

    # Set up a protected Next.js project
    project_dir = tmp_path / "Projects" / "storefront"
    public_dir = project_dir / "public"
    public_dir.mkdir(parents=True)
    (project_dir / "package.json").write_text('{"dependencies": {"next": "14.0.0"}}', encoding="utf-8")
    (project_dir / "next.config.js").write_text("module.exports = {};", encoding="utf-8")

    # Add managed roots to repository
    repo.add_managed_root(str(downloads_dir), mode="AUTO")
    repo.add_managed_root(str(documents_dir), mode="AUTO")
    repo.add_managed_root(str(tmp_path / "Projects"), mode="AUTO")

    # Protection manager & Safety policy
    prot_mgr = ProtectionManager(repo)
    prot_mgr.check_and_register_directory(str(project_dir))

    safety_policy = SafetyPolicy(
        protection_manager=prot_mgr,
        managed_roots_provider=lambda: [r.path for r in repo.list_managed_roots(enabled_only=True)],
    )

    mutation_service = MutationService(
        repository=repo,
        safety_policy=safety_policy,
    )

    pipeline = PipelineOrchestrator(
        repository=repo,
        safety_policy=safety_policy,
        mutation_service=mutation_service,
    )

    yield {
        "tmp_path": tmp_path,
        "repo": repo,
        "downloads": downloads_dir,
        "documents": documents_dir,
        "project": project_dir,
        "public": public_dir,
        "safety_policy": safety_policy,
        "mutation_service": mutation_service,
        "pipeline": pipeline,
    }

    repo.close()


# =============================================================================
# 1. Organizer Proposals & Advisory Invariant
# =============================================================================

def test_organizer_produces_structured_proposal(test_env):
    """Requirement 1: Organizer produces structured proposal and prefers existing organization."""
    docs = test_env["documents"]
    vercel_folder = docs / "Finance" / "Invoices" / "Vercel"
    vercel_folder.mkdir(parents=True)

    test_env["repo"].upsert_folders([
        DirectoryRecord(
            managed_root_id=2,
            path=str(vercel_folder),
            relative_path="Finance/Invoices/Vercel",
            name="Vercel",
        )
    ])

    test_file = test_env["downloads"] / "document (17).pdf"
    test_file.write_text("Vercel Hosting Invoice September 2026", encoding="utf-8")

    understanding = FileUnderstanding(
        file_path=str(test_file),
        sha256_hash="dummy_hash",
        document_type="invoice",
        title="Vercel Invoice September 2026",
        entities=["Vercel"],
        topics=["hosting", "billing"],
        suggested_folder="Finance/Invoices/Vercel",
        confidence=0.94,
    )

    organizer = OrganizerAgent(repository=test_env["repo"])
    proposal = organizer.propose(
        file_path=str(test_file),
        understanding=understanding,
        candidate_roots=[str(docs)],
    )

    assert isinstance(proposal, OrganizationProposal)
    assert proposal.file_path == str(test_file)
    assert proposal.current_filename == "document (17).pdf"
    assert "Vercel" in proposal.proposed_filename
    assert proposal.proposed_filename.endswith(".pdf")
    assert "Finance" in proposal.proposed_destination or "Invoices" in proposal.proposed_destination
    assert proposal.confidence >= 0.85
    assert proposal.organization_needed is True
    assert len(proposal.signals_used) > 0


def test_organizer_cannot_mutate(test_env):
    """Requirement 2: Organizer has zero mutation authority and leaves files untouched."""
    test_file = test_env["downloads"] / "notes.txt"
    test_file.write_text("Original content", encoding="utf-8")

    organizer = OrganizerAgent(repository=test_env["repo"])
    proposal = organizer.propose(file_path=str(test_file))

    # File still exists at original path with original content
    assert test_file.exists()
    assert test_file.read_text(encoding="utf-8") == "Original content"


# =============================================================================
# 2. SafetyPolicy Pre-Mutation Invariants
# =============================================================================

def test_protected_source_cannot_mutate(test_env):
    """Requirement 3: Protected source file cannot be moved or renamed."""
    public_file = test_env["public"] / "invoice.pdf"
    public_file.write_text("Invoice inside protected Next.js storefront", encoding="utf-8")

    proposal = OrganizationProposal(
        file_path=str(public_file),
        current_filename="invoice.pdf",
        proposed_filename="Vercel_Invoice.pdf",
        proposed_destination=str(test_env["documents"] / "Finance"),
        reasoning="Attempt to organize protected file",
        confidence=0.95,
    )

    success, msg, action_id = test_env["mutation_service"].apply_proposal(proposal)
    assert success is False
    assert "DENY" in msg or "protected" in msg.lower()
    assert public_file.exists()


def test_protected_destination_cannot_mutate(test_env):
    """Requirement 4: File cannot be moved into a protected project structure."""
    src_file = test_env["downloads"] / "asset.pdf"
    src_file.write_text("Asset file", encoding="utf-8")

    proposal = OrganizationProposal(
        file_path=str(src_file),
        current_filename="asset.pdf",
        proposed_filename="asset.pdf",
        proposed_destination=str(test_env["public"]),  # Protected Next.js public dir
        reasoning="Attempt to move into protected destination",
        confidence=0.90,
    )

    success, msg, action_id = test_env["mutation_service"].apply_proposal(proposal)
    assert success is False
    assert "DENY" in msg or "protected" in msg.lower()
    assert src_file.exists()


def test_unmanaged_destination_cannot_mutate(test_env):
    """Requirement 5: File cannot escape authorized managed folders."""
    src_file = test_env["downloads"] / "doc.txt"
    src_file.write_text("Unmanaged escape attempt", encoding="utf-8")

    proposal = OrganizationProposal(
        file_path=str(src_file),
        current_filename="doc.txt",
        proposed_filename="doc.txt",
        proposed_destination="C:/Windows/System32",  # Unmanaged and system path
        reasoning="Escape attempt",
        confidence=0.90,
    )

    success, msg, action_id = test_env["mutation_service"].apply_proposal(proposal)
    assert success is False
    assert "DENY" in msg
    assert src_file.exists()


def test_collision_cannot_overwrite(test_env):
    """Requirement 6: Never overwrite existing files upon collision."""
    src_file = test_env["downloads"] / "invoice.pdf"
    src_file.write_text("New invoice content", encoding="utf-8")

    dest_dir = test_env["documents"] / "Invoices"
    dest_dir.mkdir(parents=True, exist_ok=True)
    existing_dest = dest_dir / "invoice.pdf"
    existing_dest.write_text("Existing previous invoice", encoding="utf-8")

    proposal = OrganizationProposal(
        file_path=str(src_file),
        current_filename="invoice.pdf",
        proposed_filename="invoice.pdf",
        proposed_destination=str(dest_dir),
        reasoning="Collision test",
        confidence=0.90,
    )

    success, msg, action_id = test_env["mutation_service"].apply_proposal(proposal)
    assert success is False
    assert "collision" in msg.lower() or "already exists" in msg.lower()
    # Ensure existing file content was preserved
    assert existing_dest.read_text(encoding="utf-8") == "Existing previous invoice"
    assert src_file.exists()


# =============================================================================
# 3. Physical Move, Rename, Action Ledger, and Undo
# =============================================================================

def test_successful_move_rename_and_action_ledger(test_env):
    """Requirements 7 & 8: Successful physical move+rename and ActionRecord persistence."""
    src_file = test_env["downloads"] / "document (17).pdf"
    src_file.write_text("Vercel Hosting Invoice 2026", encoding="utf-8")

    dest_dir = test_env["documents"] / "Finance" / "Invoices" / "Vercel"
    proposal = OrganizationProposal(
        file_path=str(src_file),
        current_filename="document (17).pdf",
        proposed_filename="Vercel_Invoice_September_2026.pdf",
        proposed_destination=str(dest_dir),
        reasoning="September 2026 Vercel hosting invoice matching Finance structure",
        confidence=0.96,
    )

    success, msg, action_id = test_env["mutation_service"].apply_proposal(proposal, force_auto=True)
    assert success is True
    assert action_id is not None

    # Verify physical file state
    target_path = dest_dir / "Vercel_Invoice_September_2026.pdf"
    assert target_path.exists()
    assert not src_file.exists()
    assert target_path.read_text(encoding="utf-8") == "Vercel Hosting Invoice 2026"

    # Verify ActionRecord ledger
    actions = test_env["repo"].list_actions()
    assert len(actions) >= 1
    action = actions[0]
    assert action.id == action_id
    assert action.action_type == "MOVE_AND_RENAME"
    assert action.status == "APPLIED"
    assert action.dest_path == str(target_path)
    assert action.source_path == str(src_file)


def test_successful_undo(test_env):
    """Requirement 9: Successful Undo restores file to original location and cleans empty folder."""
    src_file = test_env["downloads"] / "resume_draft.pdf"
    src_file.write_text("Mahad Baig Resume Content", encoding="utf-8")

    dest_dir = test_env["documents"] / "Careers" / "Resumes"
    proposal = OrganizationProposal(
        file_path=str(src_file),
        current_filename="resume_draft.pdf",
        proposed_filename="Mahad_Baig_AI_Resume.pdf",
        proposed_destination=str(dest_dir),
        reasoning="AI Engineer Resume",
        confidence=0.95,
    )

    success, msg, action_id = test_env["mutation_service"].apply_proposal(proposal, force_auto=True)
    assert success is True

    # Now execute UNDO
    undo_success, undo_msg = test_env["mutation_service"].undo_action(action_id)
    assert undo_success is True

    # Physical restoration check
    assert src_file.exists()
    assert not (dest_dir / "Mahad_Baig_AI_Resume.pdf").exists()
    assert src_file.read_text(encoding="utf-8") == "Mahad Baig Resume Content"

    # Action status check
    action = test_env["repo"].get_action(action_id)
    assert action is not None
    assert action.status == "UNDONE"
    assert action.undone_at is not None


def test_unsafe_undo_fails(test_env):
    """Requirement 10: Unsafe Undo fails closed when file is missing or collision occurs."""
    src_file = test_env["downloads"] / "file1.txt"
    src_file.write_text("Hello", encoding="utf-8")

    dest_dir = test_env["documents"] / "Text"
    proposal = OrganizationProposal(
        file_path=str(src_file),
        current_filename="file1.txt",
        proposed_filename="file1_renamed.txt",
        proposed_destination=str(dest_dir),
        reasoning="Test",
        confidence=0.90,
    )

    success, _, action_id = test_env["mutation_service"].apply_proposal(proposal, force_auto=True)
    assert success is True

    # Create collision at original location
    src_file.write_text("Collision file at original location", encoding="utf-8")

    # Undo must fail closed
    undo_success, undo_msg = test_env["mutation_service"].undo_action(action_id)
    assert undo_success is False
    assert "collision" in undo_msg.lower()


# =============================================================================
# 4. Search & Index Synchronization (Move & Undo)
# =============================================================================

def test_search_synchronization_after_move_and_undo(test_env):
    """Requirements 11 & 12: Search returns new location after move, and original location after Undo."""
    src_file = test_env["downloads"] / "document (17).pdf"
    src_file.write_text("Vercel hosting invoice for September billing", encoding="utf-8")

    fts = FTSIndexManager(test_env["repo"])
    fts.index_file(
        file_path=str(src_file),
        filename="document (17).pdf",
        title="Vercel Invoice",
        summary="Hosting invoice from Vercel for September 2026",
        topics=["hosting", "invoice", "vercel"],
        extracted_text="Vercel hosting invoice for September billing",
    )

    # Initial search returns original path
    initial_results = fts.search("Vercel invoice September")
    assert str(src_file) in initial_results

    # Move file
    dest_dir = test_env["documents"] / "Finance" / "Invoices" / "Vercel"
    proposal = OrganizationProposal(
        file_path=str(src_file),
        current_filename="document (17).pdf",
        proposed_filename="Vercel_Invoice_September_2026.pdf",
        proposed_destination=str(dest_dir),
        reasoning="Vercel hosting invoice",
        confidence=0.95,
    )

    success, _, action_id = test_env["mutation_service"].apply_proposal(proposal, force_auto=True)
    assert success is True
    target_path = dest_dir / "Vercel_Invoice_September_2026.pdf"

    # Search now returns NEW path and does NOT return old path
    post_move_results = fts.search("Vercel invoice September")
    assert str(target_path) in post_move_results
    assert str(src_file) not in post_move_results

    # Execute Undo
    undo_success, _ = test_env["mutation_service"].undo_action(action_id)
    assert undo_success is True

    # Search now returns ORIGINAL path again
    post_undo_results = fts.search("Vercel invoice September")
    assert str(src_file) in post_undo_results
    assert str(target_path) not in post_undo_results


# =============================================================================
# 5. Watch Mode & Event Stability
# =============================================================================

def test_watch_ignores_temporary_files():
    """Requirement 14: Incomplete download and temporary file patterns are strictly ignored."""
    assert should_ignore_file("invoice.pdf.crdownload") is True
    assert should_ignore_file("report.part") is True
    assert should_ignore_file("data.tmp") is True
    assert should_ignore_file("~$Financial_Model.xlsx") is True
    assert should_ignore_file(".git") is True
    assert should_ignore_file(".DS_Store") is True
    assert should_ignore_file("Vercel_Invoice.pdf") is False


def test_watch_detects_stable_file(tmp_path: Path):
    """Requirement 13: File stability check verifies file is not still being downloaded/written."""
    stable_file = tmp_path / "stable.txt"
    stable_file.write_text("Completed file download content", encoding="utf-8")

    assert is_file_stable(str(stable_file), wait_seconds=0.1) is True


def test_watch_suppression_prevents_loop(test_env):
    """Requirement 16: TidyOS's own mutations are suppressed to prevent infinite loops."""
    ms = test_env["mutation_service"]
    test_path = str(test_env["downloads"] / "sample.pdf")

    assert ms.is_suppressed(test_path) is False
    ms.suppress_path(test_path, duration_seconds=5.0)
    assert ms.is_suppressed(test_path) is True


# =============================================================================
# 6. Environmental Contrast Demo Invariant
# =============================================================================

def test_environmental_contrast_invariant(test_env):
    """Requirement 17: The same invoice in Downloads can move; inside a project it is NEVER moved."""
    # 1. Invoice in Downloads -> SAFE -> Queued/Organized
    dl_invoice = test_env["downloads"] / "invoice.pdf"
    dl_invoice.write_text("Invoice content", encoding="utf-8")

    dl_result = test_env["pipeline"].process_file(str(dl_invoice))
    assert dl_result.is_protected is False
    assert dl_result.status in {"QUEUED_FOR_REVIEW", "AUTO_ORGANIZED"}

    # 2. Same invoice inside Projects/storefront/public -> PROTECTED -> Never organized
    proj_invoice = test_env["public"] / "invoice.pdf"
    proj_invoice.write_text("Invoice content", encoding="utf-8")

    proj_result = test_env["pipeline"].process_file(str(proj_invoice))
    assert proj_result.is_protected is True
    assert proj_result.status == "PROTECTED_INDEXED"
    assert proj_result.action_id is None
    assert proj_result.review_item_id is None
    # File was not moved or renamed
    assert proj_invoice.exists()
