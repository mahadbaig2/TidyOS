"""Tests for LangGraph Search orchestration workflow."""

from pathlib import Path
import pytest

from tidyos.storage.repository import StorageRepository
from tidyos.indexing.embeddings import LocalEmbeddingEngine, DEFAULT_MODEL_NAME
from tidyos.indexing.fts import FTSIndexManager
from tidyos.retrieval.hybrid import HybridRetriever
from tidyos.agents.search_agent import SearchAgent
from tidyos.agents.search_graph import create_search_graph
from tidyos.agents.librarian import FileUnderstanding


def test_search_graph_orchestration(tmp_path: Path):
    db_path = tmp_path / "search_graph.db"
    repo = StorageRepository(db_path)
    fts = FTSIndexManager(repo)
    engine = LocalEmbeddingEngine.get_instance()
    retriever = HybridRetriever(repository=repo, embedding_engine=engine, fts_manager=fts)
    agent = SearchAgent(retriever=retriever)

    # Setup demo candidate file
    doc_file = tmp_path / "handbook.pdf"
    doc_file.write_text("Hackathon details and instructions", encoding="utf-8")

    u = FileUnderstanding(
        file_path=str(doc_file),
        sha256_hash="h123",
        document_type="document",
        title="Agent Hackathon Handbook",
        summary="Complete rules and guide for AI hackathon attendees",
        topics=["hackathon", "agents", "ai"],
        entities=["AI Tinkerers"],
        confidence=0.92,
    )
    repo.save_file_understanding(u)
    fts.index_file(str(doc_file), doc_file.name, u.title, u.summary, u.topics, u.entities, "Hackathon text")
    v = engine.embed_text(f"{u.title} {u.summary}")
    repo.save_file_embedding(str(doc_file), "h123", DEFAULT_MODEL_NAME, v, "handbook rep")

    # Compile graph
    graph = create_search_graph(agent)

    # Invoke search workflow
    output = graph.invoke({
        "query": "Find the PDF about the agent hackathon",
        "limit": 5,
    })

    assert "structured_query" in output
    assert output["structured_query"]["prefer_recent"] is False
    assert ".pdf" in output["structured_query"]["file_extensions"]

    assert "results" in output
    assert len(output["results"]) > 0
    top_result = output["results"][0]
    assert top_result["file_path"] == str(doc_file)
    assert top_result["title"] == "Agent Hackathon Handbook"
    assert len(top_result["match_reasons"]) > 0

    repo.close()
