"""Tests for local embedding engine and vector persistence."""

from pathlib import Path
import numpy as np
import pytest

from tidyos.indexing.embeddings import (
    DEFAULT_MODEL_NAME,
    EMBEDDING_DIMENSION,
    LocalEmbeddingEngine,
    build_semantic_search_representation,
    _fallback_hash_embedding,
)
from tidyos.storage.repository import StorageRepository
from tidyos.agents.librarian import FileUnderstanding


def test_embedding_generation_and_normalization():
    engine = LocalEmbeddingEngine.get_instance()
    text = "Autonomous agent hackathon handbook"
    vec = engine.embed_text(text)

    assert isinstance(vec, np.ndarray)
    assert vec.shape == (EMBEDDING_DIMENSION,)
    assert vec.dtype == np.float32
    # Verify L2 unit normalization
    norm = float(np.linalg.norm(vec))
    assert norm == pytest.approx(1.0, rel=1e-3)


def test_batch_embedding_generation():
    engine = LocalEmbeddingEngine.get_instance()
    texts = [
        "Vercel Pro Plan invoice for September 2026",
        "FastAPI CORS Error in local backend development",
        "AI Product Engineer resume Mirza Mahad Baig",
    ]
    matrix = engine.embed_batch(texts)

    assert isinstance(matrix, np.ndarray)
    assert matrix.shape == (3, EMBEDDING_DIMENSION)
    # Each row must be normalized
    for i in range(3):
        norm = float(np.linalg.norm(matrix[i]))
        assert norm == pytest.approx(1.0, rel=1e-3)


def test_fallback_hash_embedding():
    text1 = "FastAPI CORS Error"
    text2 = "FastAPI CORS Error"
    text3 = "Unrelated cooking recipe"

    vec1 = _fallback_hash_embedding(text1)
    vec2 = _fallback_hash_embedding(text2)
    vec3 = _fallback_hash_embedding(text3)

    assert vec1.shape == (EMBEDDING_DIMENSION,)
    assert np.allclose(vec1, vec2)
    assert not np.allclose(vec1, vec3)


def test_build_semantic_search_representation():
    understanding = FileUnderstanding(
        file_path="/downloads/invoice.pdf",
        sha256_hash="abc123hash",
        document_type="invoice",
        title="Vercel Invoice Sep 2026",
        summary="Hosting invoice for September 2026",
        entities=["Vercel", "Acme"],
        topics=["finance", "hosting"],
        confidence=0.95,
    )
    rep = build_semantic_search_representation(
        understanding=understanding,
        filename="invoice.pdf",
        path_context="Downloads/Invoices",
    )

    assert "File: invoice.pdf" in rep
    assert "Type: invoice" in rep
    assert "Title: Vercel Invoice Sep 2026" in rep
    assert "Topics: finance, hosting" in rep
    assert "Entities: Vercel, Acme" in rep
    assert "Folder: Downloads/Invoices" in rep


def test_vector_persistence_and_matrix_loading(tmp_path: Path):
    db_path = tmp_path / "vectors.db"
    repo = StorageRepository(db_path)

    v1 = np.ones(EMBEDDING_DIMENSION, dtype=np.float32)
    v1 = v1 / np.linalg.norm(v1)

    v2 = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    v2[1] = 1.0

    repo.save_file_embedding(
        file_path="doc1.pdf",
        sha256_hash="hash1",
        embedding_model=DEFAULT_MODEL_NAME,
        vector=v1,
        semantic_representation="Doc 1 representation",
    )
    repo.save_file_embedding(
        file_path="doc2.png",
        sha256_hash="hash2",
        embedding_model=DEFAULT_MODEL_NAME,
        vector=v2,
        semantic_representation="Doc 2 representation",
    )

    # Test single vector retrieval
    loaded_v1 = repo.get_file_embedding("doc1.pdf", "hash1", DEFAULT_MODEL_NAME)
    assert loaded_v1 is not None
    assert np.allclose(loaded_v1, v1)

    # Test batch matrix retrieval for dot product scoring
    file_paths, matrix = repo.list_all_embeddings(DEFAULT_MODEL_NAME)
    assert len(file_paths) == 2
    assert matrix.shape == (2, EMBEDDING_DIMENSION)

    # Test cosine similarity / dot product scoring against query
    query_vec = v1
    scores = matrix @ query_vec
    assert float(scores[0]) == pytest.approx(1.0, rel=1e-3)
    assert float(scores[1]) < 0.2

    repo.close()
