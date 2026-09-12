"""Tests for SearchAgent and natural language query interpretation."""

from pathlib import Path
import pytest

from tidyos.agents.search_agent import (
    SearchAgent,
    SearchResult,
    StructuredQuery,
    parse_query_heuristics,
)
from tidyos.storage.repository import StorageRepository
from tidyos.retrieval.hybrid import HybridRetriever
from tidyos.indexing.embeddings import LocalEmbeddingEngine
from tidyos.indexing.fts import FTSIndexManager


def test_parse_query_heuristics_pdf_hackathon():
    q = "Find the PDF about the agent hackathon I'm attending today."
    res = parse_query_heuristics(q)

    assert ".pdf" in res.file_extensions
    assert res.prefer_recent is True
    assert "agent hackathon" in res.semantic_query.lower()


def test_parse_query_heuristics_screenshot_cors():
    q = "Find the screenshot where FastAPI had the CORS error"
    res = parse_query_heuristics(q)

    assert "screenshot" in res.document_types
    assert ".png" in res.file_extensions or ".jpg" in res.file_extensions
    assert "FastAPI" in res.entities
    assert "cors" in res.keywords or "cors" in res.semantic_query.lower()


def test_parse_query_heuristics_resume():
    q = "Find my latest AI Product Engineering resume"
    res = parse_query_heuristics(q)

    assert "resume" in res.document_types
    assert res.prefer_recent is True
    assert "ai" in res.semantic_query.lower() or "resume" in res.semantic_query.lower()


def test_search_agent_execution(tmp_path: Path):
    db_path = tmp_path / "search_agent.db"
    repo = StorageRepository(db_path)
    fts = FTSIndexManager(repo)
    engine = LocalEmbeddingEngine.get_instance()
    retriever = HybridRetriever(repository=repo, embedding_engine=engine, fts_manager=fts)
    agent = SearchAgent(retriever=retriever)

    # Empty database search should return empty list gracefully without error
    results = agent.search("Find the PDF about hackathons")
    assert isinstance(results, list)
    assert len(results) == 0

    repo.close()
