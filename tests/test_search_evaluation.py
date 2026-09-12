"""Retrieval evaluation benchmark suite testing Hit@1, Hit@3, and MRR."""

from pathlib import Path
import pytest

from tidyos.testing.demo_corpus import create_demo_corpus
from tidyos.storage.repository import StorageRepository
from tidyos.indexing.scanner import FilesystemScanner
from tidyos.indexing.embeddings import LocalEmbeddingEngine, build_semantic_search_representation
from tidyos.indexing.fts import FTSIndexManager
from tidyos.safety.protection_manager import ProtectionManager
from tidyos.retrieval.hybrid import HybridRetriever
from tidyos.agents.librarian import LibrarianAgent, FileUnderstanding
from tidyos.agents.search_agent import SearchAgent


BENCHMARK_PAIRS = [
    {
        "query": "Find the PDF about the agent hackathon I'm attending today.",
        "expected_filename": "document_17.pdf",
    },
    {
        "query": "Find my latest AI Product Engineering resume.",
        "expected_filename": "resume_ai_engineer.pdf",
    },
    {
        "query": "Find the Vercel invoice from September.",
        "expected_filename": "billing_03.pdf",
    },
    {
        "query": "Find the screenshot where FastAPI had the CORS error.",
        "expected_filename": "screenshot_fastapi_cors.png",
    },
    {
        "query": "Find the notes about LangGraph and agents.",
        "expected_filename": "notes_draft.md",
    },
]


def test_semantic_retrieval_benchmark_evaluation(tmp_path: Path):
    """Evaluate Hit@1, Hit@3, and MRR on realistic human memory search queries."""
    corpus = create_demo_corpus(tmp_path / "Corpus", include_benchmarks=True)
    db_path = tmp_path / "eval.db"
    repo = StorageRepository(db_path)

    # 1. Register managed roots and protected projects
    root_dl = repo.add_managed_root(corpus["downloads"])
    root_proj = repo.add_managed_root(corpus["projects"])
    prot_mgr = ProtectionManager(repo)
    prot_mgr.check_and_register_directory(corpus["next_demo"])
    prot_mgr.check_and_register_directory(corpus["python_demo"])

    # 2. Scan filesystem to index files
    scanner = FilesystemScanner(repo)
    scanner.scan_root(root_dl)
    scanner.scan_root(root_proj)

    # 3. Perform Librarian semantic analysis
    librarian = LibrarianAgent(repository=repo)
    all_files = repo.list_files(limit=100)
    for f in all_files:
        p = Path(f.path)
        if librarian.extractor.can_extract(p):
            librarian.analyze_file(p)

    # Specific enrichment for benchmark screenshot if analyzed heuristically
    sc_path = corpus["downloads"] / "screenshot_fastapi_cors.png"
    u_sc = FileUnderstanding(
        file_path=str(sc_path),
        sha256_hash="sc_cors_hash",
        document_type="screenshot",
        title="FastAPI CORS Error",
        summary="VS Code and browser showing a FastAPI CORS error during local development.",
        topics=["FastAPI", "CORS", "Python", "debugging", "screenshot"],
        entities=["FastAPI"],
        confidence=0.92,
    )
    repo.save_file_understanding(u_sc)

    # 4. Generate Embeddings and FTS5 Index
    fts = FTSIndexManager(repo)
    engine = LocalEmbeddingEngine.get_instance()

    for f in all_files:
        p_str = f.path
        p = Path(p_str)
        u = repo.get_file_understanding(p_str)
        if u:
            fts.index_file(p_str, p.name, u.title, u.summary, u.topics, u.entities, u.summary)
            rep = build_semantic_search_representation(u, p.name, str(p.parent))
            v = engine.embed_text(rep)
            repo.save_file_embedding(p_str, u.sha256_hash, engine.model_name, v, rep)

    # 5. Initialize Retriever and Search Agent
    retriever = HybridRetriever(
        repository=repo,
        embedding_engine=engine,
        fts_manager=fts,
        protection_manager=prot_mgr,
    )
    agent = SearchAgent(retriever=retriever)

    # 6. Execute Benchmark Suite
    hits_at_1 = 0
    hits_at_3 = 0
    reciprocal_ranks = []

    print("\n--- RETRIEVAL EVALUATION RESULTS ---")
    for pair in BENCHMARK_PAIRS:
        q = pair["query"]
        expected = pair["expected_filename"]
        results = agent.search(q, limit=10)

        rank = None
        for idx, res in enumerate(results):
            if res.filename == expected:
                rank = idx + 1
                break

        if rank is not None:
            rr = 1.0 / rank
            reciprocal_ranks.append(rr)
            if rank == 1:
                hits_at_1 += 1
            if rank <= 3:
                hits_at_3 += 1
            print(f"PASS: Query '{q}' -> Rank #{rank} ({expected})")
        else:
            reciprocal_ranks.append(0.0)
            print(f"FAIL: Query '{q}' -> Expected {expected} not in top 10")

    total_q = len(BENCHMARK_PAIRS)
    hit_1_rate = hits_at_1 / total_q
    hit_3_rate = hits_at_3 / total_q
    mrr = sum(reciprocal_ranks) / total_q

    print(f"\nBenchmark Metrics (Total Queries: {total_q}):")
    print(f"Hit@1 Rate: {hit_1_rate * 100:.1f}%")
    print(f"Hit@3 Rate: {hit_3_rate * 100:.1f}%")
    print(f"MRR:        {mrr:.4f}")

    assert hit_1_rate >= 0.80, f"Hit@1 rate {hit_1_rate} is below 80% target"
    assert hit_3_rate == 1.0, f"Hit@3 rate {hit_3_rate} must be 100%"
    assert mrr >= 0.85, f"MRR {mrr} is below 0.85 target"


def test_protected_files_are_searchable_and_flagged(tmp_path: Path):
    """Verify that files inside protected projects appear in search with protected=True."""
    corpus = create_demo_corpus(tmp_path / "Corpus2")
    db_path = tmp_path / "eval2.db"
    repo = StorageRepository(db_path)

    repo.add_managed_root(corpus["projects"])
    prot_mgr = ProtectionManager(repo)
    prot_mgr.check_and_register_directory(corpus["next_demo"])

    scanner = FilesystemScanner(repo)
    scanner.scan_root(repo.list_managed_roots()[0])

    librarian = LibrarianAgent(repository=repo)
    all_files = repo.list_files(limit=100)
    for f in all_files:
        if librarian.extractor.can_extract(f.path):
            librarian.analyze_file(f.path)

    fts = FTSIndexManager(repo)
    engine = LocalEmbeddingEngine.get_instance()
    for f in all_files:
        u = repo.get_file_understanding(f.path)
        if u:
            fts.index_file(f.path, Path(f.path).name, u.title, u.summary, u.topics, u.entities, u.summary)
            rep = build_semantic_search_representation(u, Path(f.path).name, str(Path(f.path).parent))
            v = engine.embed_text(rep)
            repo.save_file_embedding(f.path, u.sha256_hash, engine.model_name, v, rep)

    retriever = HybridRetriever(
        repository=repo,
        embedding_engine=engine,
        fts_manager=fts,
        protection_manager=prot_mgr,
    )
    agent = SearchAgent(retriever=retriever)

    # Search for protected invoice asset inside Next.js public/
    results = agent.search("Next.js Storefront Invoice Asset")
    assert len(results) > 0

    protected_hit = None
    for r in results:
        if "next-demo" in r.file_path:
            protected_hit = r
            break

    assert protected_hit is not None
    assert protected_hit.protected is True
    assert protected_hit.project_type in ("nextjs", "node_next")
    assert any("protected" in reason.lower() for reason in protected_hit.match_reasons)

    repo.close()


def test_nonexistent_query_returns_no_results(tmp_path: Path):
    """Verify that searching for a non-existent file returns 0 results and avoids false positives."""
    corpus = create_demo_corpus(tmp_path / "CorpusEmpty")
    db_path = tmp_path / "empty_eval.db"
    repo = StorageRepository(db_path)

    # Add only downloads with standard baseline files (no hackathon file)
    root = repo.add_managed_root(corpus["downloads"])
    scanner = FilesystemScanner(repo)
    scanner.scan_root(root)

    fts = FTSIndexManager(repo)
    engine = LocalEmbeddingEngine.get_instance()
    all_files = repo.list_files(limit=100)
    for f in all_files:
        p = Path(f.path)
        fts.index_file(f.path, p.name, p.stem, f"Generic file: {p.name}", [], [], "")
        rep = f"File: {p.name}"
        v = engine.embed_text(rep)
        repo.save_file_embedding(f.path, f.sha256_hash or "h", engine.model_name, v, rep)

    retriever = HybridRetriever(repository=repo, embedding_engine=engine, fts_manager=fts)
    agent = SearchAgent(retriever=retriever)

    # Search for an agent hackathon PDF that does NOT exist in downloads
    results = agent.search("the PDF about the agent hackathon")
    # Must NOT falsely match baseline invoices or random files
    assert len(results) == 0, f"Expected 0 results for non-existent file, got {len(results)}"

    repo.close()


def test_poster_search_with_ocr_and_fyp_topic(tmp_path: Path):
    """Verify that visual poster and FYP queries rank the poster at #1."""
    corpus = create_demo_corpus(tmp_path / "CorpusPoster")
    db_path = tmp_path / "poster_eval.db"
    repo = StorageRepository(db_path)

    root = repo.add_managed_root(corpus["downloads"])
    scanner = FilesystemScanner(repo)
    scanner.scan_root(root)

    # Create a simulated FYP poster image
    poster_path = corpus["downloads"] / "fyp_capstone_poster.png"
    poster_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")

    u_poster = FileUnderstanding(
        file_path=str(poster_path),
        sha256_hash="poster_hash_123",
        document_type="poster",
        title="Autonomous Agent Systems Final Year Project Poster",
        summary="Final Year Project (FYP) poster describing architecture and neural evaluation for multi-agent systems.",
        topics=["FYP", "poster", "presentation", "project"],
        entities=["FYP"],
        confidence=0.92,
    )
    repo.save_file_understanding(u_poster)

    fts = FTSIndexManager(repo)
    engine = LocalEmbeddingEngine.get_instance()
    fts.index_file(str(poster_path), poster_path.name, u_poster.title, u_poster.summary, u_poster.topics, u_poster.entities, u_poster.summary)
    rep = build_semantic_search_representation(u_poster, poster_path.name, str(poster_path.parent))
    v = engine.embed_text(rep)
    repo.save_file_embedding(str(poster_path), u_poster.sha256_hash, engine.model_name, v, rep)

    retriever = HybridRetriever(repository=repo, embedding_engine=engine, fts_manager=fts)
    agent = SearchAgent(retriever=retriever)

    results = agent.search("the poster for my FYP")
    assert len(results) > 0
    top = results[0]
    assert top.filename == "fyp_capstone_poster.png"
    assert top.document_type == "poster"
    assert any("poster" in r.lower() or "fyp" in r.lower() for r in top.match_reasons)

    repo.close()
