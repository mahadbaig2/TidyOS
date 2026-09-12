"""Tests for SQLite FTS5 full-text indexing and retrieval."""

from pathlib import Path
import pytest

from tidyos.storage.repository import StorageRepository
from tidyos.indexing.fts import FTSIndexManager, sanitize_fts_query


def test_sanitize_fts_query():
    assert sanitize_fts_query("") == ""
    assert sanitize_fts_query("   ") == ""
    assert sanitize_fts_query('FastAPI "CORS" error!') == '"FastAPI"* OR "CORS"* OR "error"*'
    assert sanitize_fts_query("AND OR NOT") == ""
    assert sanitize_fts_query("invoice AND finance") == '"invoice"* OR "finance"*'


def test_fts_indexing_and_search(tmp_path: Path):
    db_path = tmp_path / "fts_test.db"
    repo = StorageRepository(db_path)
    fts = FTSIndexManager(repo)

    # 1. Index test files
    fts.index_file(
        file_path="C:/Downloads/invoice.pdf",
        filename="invoice.pdf",
        title="Vercel Pro Invoice",
        summary="Hosting invoice for September 2026",
        topics=["finance", "vercel", "hosting"],
        entities=["Vercel"],
        extracted_text="Total amount due $20.00 for project deployment.",
    )
    fts.index_file(
        file_path="C:/Screenshots/error.png",
        filename="error.png",
        title="FastAPI CORS Error",
        summary="Browser console displaying CORS wildcard blockage",
        topics=["fastapi", "cors", "backend"],
        entities=["FastAPI"],
        extracted_text="Access-Control-Allow-Origin blocked by client.",
    )
    fts.index_file(
        file_path="C:/Documents/notes.md",
        filename="notes.md",
        title="Agent Hackathon Handbook",
        summary="Rules and judging criteria for AI Hackathon",
        topics=["hackathon", "agents", "ai"],
        entities=["AI Tinkerers"],
        extracted_text="Submissions must include local retrieval engine.",
    )

    # 2. Search for exact technical acronym "CORS"
    res_cors = fts.search("CORS")
    assert "C:/Screenshots/error.png" in res_cors
    assert "C:/Downloads/invoice.pdf" not in res_cors

    # 3. Search for "hackathon"
    res_hack = fts.search("hackathon")
    assert "C:/Documents/notes.md" in res_hack
    assert "C:/Screenshots/error.png" not in res_hack

    # 4. Search for "Vercel invoice"
    res_inv = fts.search("Vercel invoice")
    assert "C:/Downloads/invoice.pdf" in res_inv

    # 5. Remove file and verify search excludes it
    fts.remove_file("C:/Screenshots/error.png")
    res_after = fts.search("CORS")
    assert "C:/Screenshots/error.png" not in res_after

    repo.close()
