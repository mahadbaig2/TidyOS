"""UI integration tests for SearchPage and SearchResultCard."""

from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from tidyos.storage.repository import StorageRepository
from tidyos.indexing.embeddings import LocalEmbeddingEngine, DEFAULT_MODEL_NAME
from tidyos.indexing.fts import FTSIndexManager
from tidyos.agents.librarian import FileUnderstanding
from tidyos.ui.pages.search import SearchPage, SearchResultCard


def test_search_page_ui_execution(qapp, tmp_path: Path):
    db_path = tmp_path / "ui_search.db"
    repo = StorageRepository(db_path)
    fts = FTSIndexManager(repo)
    engine = LocalEmbeddingEngine.get_instance()

    # Create dummy file and index it
    file1 = tmp_path / "document_17.pdf"
    file1.write_text("Hackathon guide for AI Tinkerers", encoding="utf-8")

    u1 = FileUnderstanding(
        file_path=str(file1),
        sha256_hash="h17",
        document_type="document",
        title="Agents Everywhere Handbook",
        summary="Event handbook covering the AI agent hackathon rules and build session",
        topics=["hackathon", "agents", "ai"],
        entities=["AI Tinkerers"],
        confidence=0.95,
    )
    repo.save_file_understanding(u1)
    fts.index_file(str(file1), file1.name, u1.title, u1.summary, u1.topics, u1.entities, "Hackathon handbook text")
    v = engine.embed_text(f"{u1.title} {u1.summary}")
    repo.save_file_embedding(str(file1), "h17", DEFAULT_MODEL_NAME, v, "rep17")

    # Instantiate SearchPage
    page = SearchPage(repository=repo)

    # Perform search
    page._fill_and_search("Find the PDF about the agent hackathon")

    # Verify results container has result card
    assert page.results_layout.count() >= 1
    card = page.results_layout.itemAt(0).widget()
    assert isinstance(card, SearchResultCard)
    assert card.file_path == str(file1)

    repo.close()
