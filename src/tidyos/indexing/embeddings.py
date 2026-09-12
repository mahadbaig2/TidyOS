"""Local embedding runtime using compact ONNX models with deterministic fallback."""

from __future__ import annotations

import hashlib
import logging
from typing import Any, List, Optional
import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSION = 384


def _fallback_hash_embedding(text: str, dim: int = EMBEDDING_DIMENSION) -> np.ndarray:
    """Deterministic, normalized pseudo-embedding fallback when ML model is unavailable."""
    vec = np.zeros(dim, dtype=np.float32)
    tokens = text.lower().split()
    if not tokens:
        vec[0] = 1.0
        return vec

    for token in tokens:
        # Hash each token into the dimension space
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h // dim) % 2 == 0 else -1.0
        vec[idx] += sign

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    else:
        vec[0] = 1.0
    return vec


class LocalEmbeddingEngine:
    """Singleton-style local embedding generator using FastEmbed (ONNX) with offline fallback."""

    _instance: Optional[LocalEmbeddingEngine] = None

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        self.model_name = model_name
        self.dimension = EMBEDDING_DIMENSION
        self._model = None
        self._init_failed = False

    @classmethod
    def get_instance(cls, model_name: str = DEFAULT_MODEL_NAME) -> LocalEmbeddingEngine:
        if cls._instance is None or cls._instance.model_name != model_name:
            cls._instance = cls(model_name=model_name)
        return cls._instance

    def _load_model(self):
        if self._model is not None or self._init_failed:
            return
        try:
            from fastembed import TextEmbedding
            logger.info("Loading FastEmbed local embedding model: %s", self.model_name)
            self._model = TextEmbedding(model_name=self.model_name)
        except Exception as e:
            logger.warning("Could not initialize FastEmbed model (%s); using deterministic fallback", e)
            self._init_failed = True

    def embed_text(self, text: str) -> np.ndarray:
        """Generate a normalized 384-dimensional embedding vector for a single string."""
        cleaned = (text or "").strip()
        if not cleaned:
            vec = np.zeros(self.dimension, dtype=np.float32)
            vec[0] = 1.0
            return vec

        self._load_model()
        if self._model is not None:
            try:
                embeddings = list(self._model.embed([cleaned]))
                vec = np.array(embeddings[0], dtype=np.float32)
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                return vec
            except Exception as e:
                logger.warning("Embedding generation error with model (%s); falling back", e)

        return _fallback_hash_embedding(cleaned, self.dimension)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Generate a normalized (N, 384) matrix for a batch of strings."""
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        cleaned_texts = [(t or "").strip() for t in texts]
        self._load_model()

        if self._model is not None:
            try:
                raw_list = list(self._model.embed(cleaned_texts))
                matrix = np.array(raw_list, dtype=np.float32)
                norms = np.linalg.norm(matrix, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                return matrix / norms
            except Exception as e:
                logger.warning("Batch embedding generation error (%s); falling back", e)

        # Fallback
        rows = [_fallback_hash_embedding(t, self.dimension) for t in cleaned_texts]
        return np.vstack(rows).astype(np.float32)


def build_semantic_search_representation(
    understanding: Any,
    filename: Optional[str] = None,
    path_context: Optional[str] = None,
) -> str:
    """Combine structured semantic fields into an optimal text representation for embedding."""
    fn = filename or getattr(understanding, "title", "File")
    title = getattr(understanding, "title", "")
    doc_type = getattr(understanding, "document_type", "document")
    summary = getattr(understanding, "summary", "")
    topics = getattr(understanding, "topics", [])
    entities = getattr(understanding, "entities", [])

    topics_str = ", ".join(topics) if isinstance(topics, list) else str(topics)
    entities_str = ", ".join(entities) if isinstance(entities, list) else str(entities)

    parts = [
        f"File: {fn}",
        f"Type: {doc_type}",
        f"Title: {title}",
    ]
    if path_context:
        parts.append(f"Folder: {path_context}")
    if topics_str:
        parts.append(f"Topics: {topics_str}")
    if entities_str:
        parts.append(f"Entities: {entities_str}")
    if summary:
        parts.append(f"Summary: {summary}")

    return "\n".join(parts)
