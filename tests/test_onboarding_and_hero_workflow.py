"""End-to-end verification of Onboarding Wizard data flow, Fix My Mess, and Hero actions."""

from pathlib import Path
import pytest
from tidyos.storage.repository import StorageRepository
from tidyos.safety.policy import SafetyPolicy
from tidyos.services.mutation_service import MutationService
from tidyos.agents.organizer import OrganizerAgent
from tidyos.agents.search_agent import SearchAgent
from tidyos.retrieval.hybrid import HybridRetriever
from tidyos.indexing.scanner import FilesystemScanner
from tidyos.indexing.fts import FTSIndexManager
from tidyos.safety.protection_manager import ProtectionManager
from tidyos.agents.librarian import LibrarianAgent
from tidyos.storage.models import FileRecord


def test_onboarding_data_and_fix_my_mess_end_to_end(tmp_path: Path):
    db_path = tmp_path / "tidyos_test.db"
    repo = StorageRepository(db_path)
    prot_mgr = ProtectionManager(repo)
    safety_policy = SafetyPolicy(
        protection_manager=prot_mgr,
        managed_roots_provider=lambda: [r.path for r in repo.list_managed_roots(enabled_only=True)],
    )
    mutation_service = MutationService(repo, safety_policy)
    librarian = LibrarianAgent(repository=repo)
    retriever = HybridRetriever(repo)
    search_agent = SearchAgent(retriever)
    organizer = OrganizerAgent(repo)

    # 1. Verify First-Run status
    assert not repo.is_first_run_completed()

    # 2. Setup mock environment
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    docs = tmp_path / "Documents"
    docs.mkdir()
    projects = tmp_path / "Projects"
    projects.mkdir()
    storefront = projects / "storefront"
    storefront.mkdir()
    (storefront / "package.json").write_text('{"dependencies": {"next": "14.0.0"}}', encoding="utf-8")
    public_dir = storefront / "public"
    public_dir.mkdir()
    protected_invoice = public_dir / "invoice.pdf"

    import pymupdf
    doc_prot = pymupdf.open()
    doc_prot.new_page().insert_text((50, 72), "Project internal invoice asset")
    doc_prot.save(str(protected_invoice))
    doc_prot.close()

    # Target mess file
    mess_file = downloads / "document (17).pdf"
    doc_mess = pymupdf.open()
    doc_mess.new_page().insert_text((50, 72), "Invoice from Vercel Inc. Date: September 2026. Total Amount: $20.00. Hosting & Edge Network.")
    doc_mess.save(str(mess_file))
    doc_mess.close()

    # 3. Add managed roots
    root_dl = repo.add_managed_root(str(downloads), mode="AUTO")
    root_doc = repo.add_managed_root(str(docs), mode="AUTO")
    root_prj = repo.add_managed_root(str(projects), mode="AUTO")

    # 4. Scanner step
    scanner = FilesystemScanner(repo)
    scanner.scan_root(root_dl)
    scanner.scan_root(root_doc)
    scanner.scan_root(root_prj)

    # 5. Protection detection
    prot_mgr.check_and_register_directory(str(storefront))
    assert prot_mgr.is_protected(str(protected_invoice))

    # 6. Analyze mess file with Librarian
    meta = librarian.analyze_file(mess_file)
    meta.entities = ["Vercel"]
    meta.document_type = "Invoice"
    meta.title = "Vercel Invoice"
    meta.summary = "Vercel hosting invoice for September 2026"

    # Index for search
    file_rec = next(f for f in repo.list_files() if f.path == str(mess_file))
    repo.save_file_understanding(meta)
    fts = FTSIndexManager(repo)
    fts.index_file(
        file_rec.path,
        mess_file.name,
        meta.title,
        meta.summary,
        meta.topics,
        meta.entities,
        meta.summary,
    )

    # 6. Generate Fix My Mess proposal
    p = organizer.propose(str(mess_file), understanding=meta)
    assert "Vercel_Invoice" in p.proposed_filename
    assert "document (17)" not in p.proposed_filename.lower()

    # 7. Approve proposal (Fix My Mess)
    success, msg, action_id = mutation_service.apply_proposal(p, force_auto=True)
    assert success is True
    assert not mess_file.exists()
    assert Path(p.proposed_full_path).exists()
    assert Path(p.proposed_full_path).name == p.proposed_filename

    # 8. Search finds relocated file
    res = search_agent.search("Vercel invoice September", limit=5)
    assert len(res) >= 1
    assert res[0].file_path == p.proposed_full_path

    # 9. Undo restores mess file
    undo_success, undo_msg = mutation_service.undo_action(action_id)
    assert undo_success is True
    assert mess_file.exists()
    assert not Path(p.proposed_full_path).exists()

    # 10. Complete onboarding
    repo.set_first_run_completed(True)
    assert repo.is_first_run_completed()
