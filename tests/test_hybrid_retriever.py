"""Tests for HybridRetriever and multi-signal rank fusion."""

from pathlib import Path
import pytest
import numpy as np

from tidyos.storage.repository import StorageRepository
from tidyos.indexing.embeddings import LocalEmbeddingEngine, DEFAULT_MODEL_NAME
from tidyos.indexing.fts import FTSIndexManager
from tidyos.retrieval.hybrid import HybridRetriever
from tidyos.agents.librarian import FileUnderstanding


def test_hybrid_retrieval_ranking(tmp_path: Path):
    db_path = tmp_path / "hybrid.db"
    repo = StorageRepository(db_path)
    fts = FTSIndexManager(repo)
    engine = LocalEmbeddingEngine.get_instance()

    # Create dummy files on disk
    f1 = tmp_path / "invoice_vercel.pdf"
    f1.write_text("Vercel hosting invoice for September", encoding="utf-8")

    f2 = tmp_path / "screenshot_cors.png"
    f2.write_text("FastAPI CORS error screenshot", encoding="utf-8")

    f3 = tmp_path / "random_recipe.txt"
    f3.write_text("Tomato pasta cooking recipe", encoding="utf-8")

    # Save understandings
    u1 = FileUnderstanding(
        file_path=str(f1),
        sha256_hash="h1",
        document_type="invoice",
        title="Vercel Invoice September",
        summary="Monthly hosting bill from Vercel",
        topics=["finance", "vercel"],
        entities=["Vercel"],
        confidence=0.95,
    )
    u2 = FileUnderstanding(
        file_path=str(f2),
        sha256_hash="h2",
        document_type="screenshot",
        title="FastAPI CORS Error",
        summary="Browser console blocking request due to missing CORS origin",
        topics=["fastapi", "cors", "development"],
        entities=["FastAPI"],
        confidence=0.90,
    )
    u3 = FileUnderstanding(
        file_path=str(f3),
        sha256_hash="h3",
        document_type="notes",
        title="Pasta Recipe",
        summary="Dinner recipe for fresh tomato pasta",
        topics=["cooking"],
        confidence=0.80,
    )
    repo.save_file_understanding(u1)
    repo.save_file_understanding(u2)
    repo.save_file_understanding(u3)

    # Index into FTS
    fts.index_file(str(f1), f1.name, u1.title, u1.summary, u1.topics, u1.entities, "Vercel invoice text")
    fts.index_file(str(f2), f2.name, u2.title, u2.summary, u2.topics, u2.entities, "FastAPI CORS error text")
    fts.index_file(str(f3), f3.name, u3.title, u3.summary, u3.topics, u3.entities, "Pasta recipe text")

    # Generate and save real vector embeddings
    v1 = engine.embed_text(f"{u1.title} {u1.summary} {' '.join(u1.topics)}")
    v2 = engine.embed_text(f"{u2.title} {u2.summary} {' '.join(u2.topics)}")
    v3 = engine.embed_text(f"{u3.title} {u3.summary} {' '.join(u3.topics)}")
    repo.save_file_embedding(str(f1), "h1", DEFAULT_MODEL_NAME, v1, "u1")
    repo.save_file_embedding(str(f2), "h2", DEFAULT_MODEL_NAME, v2, "u2")
    repo.save_file_embedding(str(f3), "h3", DEFAULT_MODEL_NAME, v3, "u3")

    retriever = HybridRetriever(repository=repo, embedding_engine=engine, fts_manager=fts)

    # 1. Search for Vercel invoice
    results_inv = retriever.retrieve("Vercel invoice September")
    assert len(results_inv) > 0
    assert results_inv[0].file_path == str(f1)
    assert "invoice" in results_inv[0].document_type
    assert any("match" in r.lower() or "keyword" in r.lower() for r in results_inv[0].match_reasons)

    # 2. Search for FastAPI CORS error
    results_cors = retriever.retrieve("screenshot where FastAPI had the CORS error")
    assert len(results_cors) > 0
    assert results_cors[0].file_path == str(f2)
    assert results_cors[0].document_type == "screenshot"

    # 3. Test hard extension filtering
    results_pdf_only = retriever.retrieve("error or notes", file_extensions=[".png"])
    # The PNG should rank above text files
    assert results_pdf_only[0].file_path == str(f2)

    repo.close()
