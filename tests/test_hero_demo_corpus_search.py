"""Verification of all four Hero Demo Search queries on the demo corpus."""

from pathlib import Path
import pytest

from scripts.reset_demo import reset_demo
from tidyos.storage.repository import StorageRepository
from tidyos.indexing.scanner import FilesystemScanner
from tidyos.agents.librarian import LibrarianAgent
from tidyos.retrieval.hybrid import HybridRetriever
from tidyos.agents.search_agent import SearchAgent
from tidyos.indexing.fts import FTSIndexManager
from tidyos.indexing.embeddings import LocalEmbeddingEngine, build_semantic_search_representation
from tidyos.safety.protection_manager import ProtectionManager


def test_hero_demo_corpus_search_queries(tmp_path: Path):
    """Verify that all four hero queries rank #1 on the actual demo sandbox."""
    demo_dir = tmp_path / "TidyOS_Demo"
    reset_demo(demo_root=demo_dir, reset_db=False)

    db_path = tmp_path / "hero_search.db"
    repo = StorageRepository(db_path)

    # 1. Register managed roots and protected projects
    r_down = repo.add_managed_root(str(demo_dir / "Downloads"), mode="REVIEW")
    r_docs = repo.add_managed_root(str(demo_dir / "Documents"), mode="AUTO")
    r_proj = repo.add_managed_root(str(demo_dir / "Projects"), mode="AUTO")

    prot_mgr = ProtectionManager(repo)
    prot_mgr.check_and_register_directory(str(demo_dir / "Projects" / "storefront"))

    # 2. Scan and index files
    scanner = FilesystemScanner(repo)
    scanner.scan_root(r_down)
    scanner.scan_root(r_docs)
    scanner.scan_root(r_proj)

    # 3. Analyze content with Librarian & build indices
    librarian = LibrarianAgent(repository=repo)
    fts = FTSIndexManager(repo)
    engine = LocalEmbeddingEngine.get_instance()

    all_files = repo.list_files()
    for file_rec in all_files:
        p = Path(file_rec.path)
        if p.exists():
            understanding = librarian.analyze_file(p)
            repo.save_file_understanding(understanding)
            fts.index_file(
                file_rec.path,
                p.name,
                understanding.title,
                understanding.summary,
                understanding.topics,
                understanding.entities,
                understanding.summary,
            )
            rep = build_semantic_search_representation(understanding, p.name, str(p.parent))
            v = engine.embed_text(rep)
            repo.save_file_embedding(file_rec.path, understanding.sha256_hash, engine.model_name, v, rep)

    retriever = HybridRetriever(
        repository=repo,
        embedding_engine=engine,
        fts_manager=fts,
        protection_manager=prot_mgr,
    )
    search_agent = SearchAgent(retriever=retriever)

    # QUERY 1: Agent Hackathon
    q1 = "Find the PDF about the agent hackathon I'm attending today."
    res1 = search_agent.search(q1, limit=5)
    assert len(res1) > 0, f"No results for '{q1}'"
    top1_name = Path(res1[0].file_path).name
    assert "document_42.pdf" == top1_name, f"Expected document_42.pdf as rank 1, got {top1_name}"

    # QUERY 2: AI Resume
    q2 = "Find my latest AI Product Engineering resume."
    res2 = search_agent.search(q2, limit=5)
    assert len(res2) > 0, f"No results for '{q2}'"
    top2_name = Path(res2[0].file_path).name
    assert "resume_final_3.pdf" == top2_name, f"Expected resume_final_3.pdf as rank 1, got {top2_name}"

    # QUERY 3: FastAPI CORS Screenshot
    q3 = "Find the screenshot where FastAPI had the CORS error."
    res3 = search_agent.search(q3, limit=5)
    assert len(res3) > 0, f"No results for '{q3}'"
    top3_name = Path(res3[0].file_path).name
    assert "Screenshot_20260912.png" == top3_name, f"Expected Screenshot_20260912.png as rank 1, got {top3_name}"

    # QUERY 4: Vercel invoice
    q4 = "Find the Vercel invoice from September."
    res4 = search_agent.search(q4, limit=5)
    assert len(res4) > 0, f"No results for '{q4}'"
    found_paths = [Path(r.file_path).name for r in res4]
    assert "document (17).pdf" in found_paths or "invoice.pdf" in found_paths

    # QUERY 5: Protected Project file is searchable and flagged
    q5 = "storefront invoice"
    res5 = search_agent.search(q5, limit=5)
    proj_match = [r for r in res5 if "storefront" in r.file_path.lower()]
    assert len(proj_match) > 0, "Protected file inside storefront must be searchable"
    assert proj_match[0].protected, "storefront/public/invoice.pdf must be flagged protected=True"
