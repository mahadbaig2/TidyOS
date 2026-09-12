"""End-to-end verification of Hero Demo and Environmental Contrast."""

import os
import shutil
from pathlib import Path
import pymupdf

from tidyos.storage.models import ManagedRoot, FileRecord, DirectoryRecord
from tidyos.storage.repository import StorageRepository
from tidyos.safety.protection_manager import ProtectionManager
from tidyos.safety.policy import SafetyPolicy, FileOperation
from tidyos.agents.guardian import GuardianAgent
from tidyos.agents.librarian import LibrarianAgent
from tidyos.agents.organizer import OrganizerAgent
from tidyos.services.mutation_service import MutationService
from tidyos.services.pipeline import PipelineOrchestrator
from tidyos.indexing.fts import FTSIndexManager


def make_pdf(path: Path, content: str):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), content)
    doc.save(str(path))
    doc.close()


def run_hero_demo():
    print("==================================================")
    print("TIDYOS HERO DEMO & ENVIRONMENTAL INVARIANT TEST")
    print("==================================================")

    base = Path("c:/Mahad/Projects/tidyos/sandbox_demo")
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)

    db_path = base / "demo.db"
    repo = StorageRepository(db_path)

    downloads = base / "Downloads"
    documents = base / "Documents"
    projects = base / "Projects"
    storefront = projects / "storefront"
    storefront_public = storefront / "public"

    downloads.mkdir()
    documents.mkdir()
    storefront_public.mkdir(parents=True)

    # Make storefront a Next.js project
    (storefront / "package.json").write_text('{"dependencies": {"next": "14.0.0"}}', encoding="utf-8")
    (storefront / "next.config.js").write_text("module.exports = {};", encoding="utf-8")

    # Set up existing organized folder in Documents
    existing_vercel_folder = documents / "Finance" / "Invoices" / "Vercel"
    existing_vercel_folder.mkdir(parents=True)

    # Register managed roots
    r1 = repo.add_managed_root(str(downloads), mode="REVIEW")
    r2 = repo.add_managed_root(str(documents), mode="AUTO")
    r3 = repo.add_managed_root(str(projects), mode="AUTO")

    # Register existing folder in DB
    repo.upsert_folders([
        DirectoryRecord(
            managed_root_id=r2.id,
            path=str(existing_vercel_folder),
            relative_path="Finance/Invoices/Vercel",
            name="Vercel",
        )
    ])

    # Protection Manager & Policy
    prot_mgr = ProtectionManager(repo)
    prot_mgr.check_and_register_directory(str(storefront))

    safety_policy = SafetyPolicy(
        protection_manager=prot_mgr,
        managed_roots_provider=lambda: [r.path for r in repo.list_managed_roots(enabled_only=True)],
    )

    mutation_service = MutationService(repository=repo, safety_policy=safety_policy)
    guardian = GuardianAgent(safety_policy=safety_policy, protection_manager=prot_mgr)
    librarian = LibrarianAgent(repository=repo)
    organizer = OrganizerAgent(repository=repo)

    pipeline = PipelineOrchestrator(
        repository=repo,
        guardian_agent=guardian,
        librarian_agent=librarian,
        organizer_agent=organizer,
        mutation_service=mutation_service,
        safety_policy=safety_policy,
    )

    print("\n--- STAGE 1: File Appears in Downloads ---")
    file1 = downloads / "document (17).pdf"
    make_pdf(file1, "Vercel Inc. Hosting Invoice #INV-2026-09 Amount: $20.00 Date: September 2026")
    print(f"Created intake file: {file1}")

    print("\n--- STAGE 2: Pipeline Processes File ---")
    res = pipeline.process_file(str(file1))
    print(f"Pipeline Result Status: {res.status}")
    print(f"Is Protected: {res.is_protected}")
    assert not res.is_protected, "Intake file in Downloads must NOT be protected"
    assert res.proposal is not None, "Organizer should produce a proposal"
    print(f"Organizer Proposed Path: {res.proposal.proposed_full_path}")
    print(f"Organizer Proposed Destination: {res.proposal.proposed_destination}")
    print(f"Organizer Proposed Name: {res.proposal.proposed_filename}")
    assert "Finance" in res.proposal.proposed_destination or "Invoices" in res.proposal.proposed_destination, "Should match existing Finance/Invoices folder"

    # Index the file in FTS so we can demonstrate search
    fts = FTSIndexManager(repo)
    fts.index_file(str(file1), file1.name, "Vercel Inc Hosting Invoice September 2026")

    print("\n--- STAGE 3: Review Queue Approval & Mutation ---")
    success, msg, action_id = mutation_service.apply_proposal(res.proposal)
    assert success, f"apply_proposal failed: {msg}"
    print(f"Applied Action ID: {action_id}")
    print(f"Original Path Exists: {file1.exists()} (Expected: False)")
    assert not file1.exists(), "Original file must be gone"
    dest_path = Path(res.proposal.proposed_full_path)
    print(f"New Destination Exists: {dest_path.exists()} (Expected: True)")
    assert dest_path.exists(), "New file must exist"

    print("\n--- STAGE 4: Search Sync to New Location ---")
    search_res = fts.search("Vercel invoice")
    print(f"Search results for 'Vercel invoice': {list(search_res.keys())}")
    assert any(str(dest_path).lower() == p.lower() for p in search_res.keys()), "Search must return new destination"

    print("\n--- STAGE 5: Safe Undo Restoration ---")
    undo_ok, undo_msg = mutation_service.undo_action(action_id)
    print(f"Undo success: {undo_ok} ({undo_msg})")
    assert undo_ok, "Undo must succeed"
    print(f"Restored Original Path Exists: {file1.exists()} (Expected: True)")
    assert file1.exists(), "Original file must be restored"
    print(f"Destination Path Exists: {dest_path.exists()} (Expected: False)")
    assert not dest_path.exists(), "Destination file must be removed"

    print("\n--- STAGE 6: Search Sync to Restored Location ---")
    search_res2 = fts.search("Vercel invoice")
    print(f"Search results after undo: {list(search_res2.keys())}")
    assert any(str(file1).lower() == p.lower() for p in search_res2.keys()), "Search must return restored original location"

    print("\n--- STAGE 7: Environmental Contrast Demonstration ---")
    project_invoice = storefront_public / "invoice.pdf"
    make_pdf(project_invoice, "Vercel Inc. Hosting Invoice #INV-2026-09 Amount: $20.00 Date: September 2026")
    print(f"Created identical file inside Next.js project: {project_invoice}")

    res_proj = pipeline.process_file(str(project_invoice))
    print(f"Project File Pipeline Status: {res_proj.status}")
    print(f"Project File is_protected: {res_proj.is_protected}")
    assert res_proj.is_protected, "Project file must be classified as PROTECTED"
    assert res_proj.proposal is None, "Organizer must NOT propose moving protected file"

    # Index project invoice in FTS
    fts.index_file(str(project_invoice), project_invoice.name, "Vercel Inc Hosting Invoice September 2026")
    search_proj = fts.search("Vercel invoice")
    print(f"Search finds protected file: {list(search_proj.keys())}")
    assert any(str(project_invoice).lower() == p.lower() for p in search_proj.keys()), "Protected file must still be searchable"

    # Verify SafetyPolicy rejects any mutation attempt
    decision = safety_policy.validate(
        FileOperation(
            operation_type="MOVE",
            source_path=str(project_invoice),
            destination_path=str(existing_vercel_folder / "invoice.pdf"),
        )
    )
    print(f"SafetyPolicy Decision for project file move: status={decision.status}, reason={decision.reason_code}")
    assert decision.is_denied, "SafetyPolicy must strictly reject moving project file"

    # Clean up
    try:
        shutil.rmtree(base, ignore_errors=True)
    except Exception:
        pass
    print("\n==================================================")
    print("ALL 7 HERO DEMO STAGES PASSED FLAWLESSLY!")
    print("==================================================")


if __name__ == "__main__":
    run_hero_demo()
