"""Tests verifying the integrated LangGraph pipeline with Guardian and Librarian agents."""

from pathlib import Path
import pytest
import pymupdf

from tidyos.safety import SafetyPolicy, ProtectionManager
from tidyos.agents.guardian import GuardianAgent
from tidyos.agents.librarian import LibrarianAgent
from tidyos.agents.graph import create_safety_graph
from tidyos.storage.repository import StorageRepository


def test_langgraph_contrasting_invoice_routing(tmp_path: Path):
    """Test the core hackathon thesis:
    A file's surrounding environment changes what an autonomous agent should do.
    Downloads/invoice.pdf -> SAFE_FOR_ORGANIZATION
    Projects/next-app/public/invoice.pdf -> PROTECTED_SEMANTICALLY_INDEXED
    """
    db_path = tmp_path / "test_tidyos.db"
    repo = StorageRepository(db_path)

    # 1. Setup Downloads root with an invoice
    downloads_dir = tmp_path / "Downloads"
    downloads_dir.mkdir(parents=True)
    safe_invoice = downloads_dir / "invoice.pdf"

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Acme Corporation Invoice #10293. Total Due: $1,250.00")
    doc.save(str(safe_invoice))
    doc.close()

    # 2. Setup Next.js project with a static asset invoice
    projects_dir = tmp_path / "Projects"
    next_project = projects_dir / "storefront"
    public_dir = next_project / "public"
    public_dir.mkdir(parents=True)
    (next_project / "package.json").write_text('{"dependencies": {"next": "14.0.0"}}')
    (next_project / "next.config.js").write_text('module.exports = {};')
    protected_invoice = public_dir / "invoice.pdf"

    doc2 = pymupdf.open()
    page2 = doc2.new_page()
    page2.insert_text((50, 72), "Acme Corporation Invoice #10293. Total Due: $1,250.00")
    doc2.save(str(protected_invoice))
    doc2.close()

    # 3. Register managed roots and setup protection manager
    repo.add_managed_root(downloads_dir)
    repo.add_managed_root(projects_dir)

    prot_mgr = ProtectionManager(repo)
    prot_mgr.check_and_register_directory(next_project)

    policy = SafetyPolicy(
        protection_manager=prot_mgr,
        managed_roots_provider=lambda: [r.path for r in repo.list_managed_roots()],
        confidence_threshold=0.85,
    )
    guardian = GuardianAgent(safety_policy=policy, protection_manager=prot_mgr)
    librarian = LibrarianAgent(repository=repo)

    graph = create_safety_graph(guardian_agent=guardian, librarian_agent=librarian)

    # 4. Invoke for Safe Downloads file
    safe_state = graph.invoke({
        "file_path": str(safe_invoice),
        "managed_root": str(downloads_dir),
        "parent_directory": str(downloads_dir),
        "confidence": 0.95,
    })

    assert safe_state["protected"] is False
    assert safe_state["status"] == "SAFE_FOR_ORGANIZATION"
    assert safe_state["document_type"] == "invoice"
    assert "finance" in safe_state["topics"] or "billing" in safe_state["topics"]
    assert safe_state["requires_review"] is False

    # 5. Invoke for Protected Next.js file
    protected_state = graph.invoke({
        "file_path": str(protected_invoice),
        "managed_root": str(projects_dir),
        "parent_directory": str(public_dir),
        "confidence": 0.95,
    })

    assert protected_state["protected"] is True
    assert protected_state["project_type"] in ("nextjs", "node_next")
    assert protected_state["status"] == "PROTECTED_SEMANTICALLY_INDEXED"
    # Even though protected from mutation, it WAS semantically understood!
    assert protected_state["document_type"] == "invoice"
    assert protected_state["requires_review"] is False

    # Verify repository saved understandings
    stats = repo.get_statistics()
    assert stats["total_understood"] == 2
    repo.close()
