"""Hybrid file retrieval combining semantic vectors, FTS5 full-text, filename matching, and metadata."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from tidyos.indexing.embeddings import LocalEmbeddingEngine
from tidyos.indexing.fts import FTSIndexManager

logger = logging.getLogger(__name__)


@dataclass
class CandidateResult:
    """Consolidated search result candidate with granular scoring components and explanation."""

    file_path: str
    filename: str
    folder_path: str
    document_type: str
    title: str
    summary: str
    score: float
    semantic_score: float
    fts_score: float
    filename_score: float
    metadata_score: float
    recency_score: float
    modified_at: str
    protected: bool = False
    project_type: Optional[str] = None
    match_reasons: List[str] = field(default_factory=list)


def _compute_filename_relevance(query_tokens: List[str], filename: str, path_str: str) -> float:
    """Score filename and folder path relevance against query terms."""
    if not query_tokens:
        return 0.0

    lower_name = filename.lower()
    lower_path = path_str.lower()
    matches = 0
    exact_stem_matches = 0

    stem = Path(filename).stem.lower()

    for token in query_tokens:
        if len(token) < 2:
            continue
        if token in stem:
            matches += 1
            if token == stem:
                exact_stem_matches += 1
        elif token in lower_name:
            matches += 0.8
        elif token in lower_path:
            matches += 0.4

    if not matches:
        return 0.0

    score = min(1.0, (matches / len(query_tokens)) * (1.2 if exact_stem_matches else 1.0))
    return float(score)


def _compute_recency_score(modified_at_iso: Optional[str]) -> float:
    """Compute normalized recency score decaying over time."""
    if not modified_at_iso:
        return 0.1
    try:
        dt = datetime.fromisoformat(modified_at_iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_ago = max(0.0, (now - dt).total_seconds() / 86400.0)

        if days_ago <= 1.0:
            return 1.0
        elif days_ago <= 7.0:
            return 0.85
        elif days_ago <= 30.0:
            return 0.65
        elif days_ago <= 90.0:
            return 0.45
        else:
            return 0.20
    except Exception:
        return 0.20


RETRIEVAL_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "and", "or", "for", "of", "to",
    "in", "on", "at", "by", "with", "from", "about", "into", "through", "during",
    "before", "after", "above", "below", "up", "down", "out", "off", "over", "under",
    "then", "here", "there", "when", "where", "why", "how", "all", "any", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "can", "will", "just",
    "should", "now", "my", "your", "his", "her", "their", "our", "its", "me",
    "him", "them", "us", "find", "show", "search", "get", "where", "file", "files",
    "document", "documents", "that", "this"
}

FORMAT_TOKENS = {
    "pdf", "pdfs", "docx", "doc", "word", "png", "jpg", "jpeg", "webp", "gif", "txt", "md"
}


class HybridRetriever:
    """Hybrid retrieval engine combining dense vector search, FTS5, filename similarity, and metadata."""

    MIN_SCORE_THRESHOLD: float = 0.35

    def __init__(
        self,
        repository: Any,
        embedding_engine: Optional[LocalEmbeddingEngine] = None,
        fts_manager: Optional[FTSIndexManager] = None,
        protection_manager: Optional[Any] = None,
    ):
        self.repository = repository
        self.embedding_engine = embedding_engine or LocalEmbeddingEngine.get_instance()
        self.fts = fts_manager or FTSIndexManager(repository)
        self.protection_manager = protection_manager

    def retrieve(
        self,
        query: str,
        query_embedding: Optional[np.ndarray] = None,
        file_extensions: Optional[List[str]] = None,
        document_types: Optional[List[str]] = None,
        prefer_recent: bool = False,
        limit: int = 20,
    ) -> List[CandidateResult]:
        """Execute hybrid search and return ranked, explainable candidates."""
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return []

        # Extract tokens and filter out stopwords & format terms
        raw_tokens = [t.lower() for t in re.findall(r"\b\w+\b", cleaned_query) if len(t) > 1]
        content_tokens = [t for t in raw_tokens if t not in RETRIEVAL_STOPWORDS and t not in FORMAT_TOKENS]
        fts_search_query = " ".join(content_tokens) if content_tokens else " ".join([t for t in raw_tokens if t not in RETRIEVAL_STOPWORDS])
        topical_query = " ".join([t for t in re.findall(r"\b\w+\b", cleaned_query) if t.lower() not in RETRIEVAL_STOPWORDS and t.lower() not in FORMAT_TOKENS])

        # 1. Generate query embedding if not provided
        if query_embedding is None:
            q_emb = self.embedding_engine.embed_text(topical_query or cleaned_query)
        else:
            q_emb = query_embedding

        # 2. Dense Vector Retrieval
        emb_file_paths, emb_matrix = self.repository.list_all_embeddings(
            self.embedding_engine.model_name
        )
        semantic_scores: Dict[str, float] = {}
        if len(emb_file_paths) > 0 and emb_matrix.shape[0] > 0:
            # Cosine similarity for normalized vectors
            dot_products = emb_matrix @ q_emb
            for i, p in enumerate(emb_file_paths):
                # Clamp score to [0.0, 1.0]
                val = float(dot_products[i])
                semantic_scores[p] = max(0.0, min(1.0, val))

        # 3. SQLite FTS5 Full-Text Retrieval using content tokens (stops PDF/stopword false positives)
        fts_scores = self.fts.search(fts_search_query, limit=limit * 3) if fts_search_query else {}

        # 4. Pool candidate paths from semantic hits, FTS hits, and repository files
        candidate_paths: Set[str] = set(semantic_scores.keys()).union(fts_scores.keys())

        # Also pull files matching meaningful content tokens from repository
        all_files = self.repository.list_files(limit=200)
        file_lookup: Dict[str, Any] = {f.path: f for f in all_files}
        effective_tokens = content_tokens if content_tokens else raw_tokens
        for f in all_files:
            lower_name = f.filename.lower()
            if any(qt in lower_name for qt in effective_tokens):
                candidate_paths.add(f.path)

        # Filter out files that physically no longer exist
        valid_candidates: Set[str] = set()
        for cp in candidate_paths:
            if Path(cp).exists():
                valid_candidates.add(cp)

        if not valid_candidates:
            return []

        # 6. Fetch understandings and protection info for candidates
        results: List[CandidateResult] = []
        clean_extensions = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in (file_extensions or [])]
        clean_doc_types = [dt.lower() for dt in (document_types or [])]

        for p_str in valid_candidates:
            p = Path(p_str)
            filename = p.name
            folder_path = str(p.parent)
            ext = p.suffix.lower()

            # Retrieve semantic understanding if available
            understanding = self.repository.get_file_understanding(p_str)
            doc_type = understanding.document_type if understanding else "document"
            title = understanding.title if understanding else p.stem
            summary = understanding.summary if understanding else f"{doc_type.title()} file: {filename}"

            # File record for metadata
            f_record = file_lookup.get(p_str)
            mod_at = f_record.modified_at if f_record else None

            # Calculate individual signal scores
            sem_score = semantic_scores.get(p_str, 0.0)
            fts_score = fts_scores.get(p_str, 0.0)
            fn_score = _compute_filename_relevance(effective_tokens, filename, folder_path)
            rec_score = _compute_recency_score(mod_at)

            # Metadata matching score (extension / doc_type)
            meta_score = 0.0
            meta_reasons: List[str] = []
            has_ext_match = False
            has_type_match = False

            if clean_extensions:
                if ext in clean_extensions:
                    meta_score += 0.5
                    has_ext_match = True
                    meta_reasons.append(ext.upper().lstrip("."))
            else:
                meta_score += 0.25

            if clean_doc_types:
                if doc_type.lower() in clean_doc_types:
                    meta_score += 0.5
                    has_type_match = True
                    meta_reasons.append(doc_type.replace("_", " ").title())
            else:
                meta_score += 0.25

            # Evaluate protection status
            is_prot = False
            proj_type = None
            if self.protection_manager:
                try:
                    is_prot, prot_rec = self.protection_manager.is_protected(p_str)
                    if is_prot and prot_rec:
                        proj_type = prot_rec.project_type
                except Exception as e:
                    logger.debug("Failed checking protection for %s: %s", p_str, e)

            # Rank Fusion Formula
            # 45% semantic vector + 25% FTS5 + 15% filename + 10% metadata + 5% recency
            final_score = (
                0.45 * sem_score
                + 0.25 * fts_score
                + 0.15 * fn_score
                + 0.10 * meta_score
                + (0.05 * rec_score if prefer_recent else 0.02 * rec_score)
            )

            # Topical Grounding:
            # If the user queried specific content concepts (e.g. "agent hackathon", "poster FYP"),
            # a candidate must actually match the topic or have strong semantic similarity.
            # Unrelated files cannot piggyback on extension or generic vector proximity.
            has_topical_grounding = False
            if not content_tokens:
                has_topical_grounding = True
            else:
                searchable_haystack = (filename + " " + title + " " + summary).lower()
                token_matches = any(ct in searchable_haystack for ct in content_tokens)
                if token_matches or fts_score > 0.10 or sem_score >= 0.72:
                    has_topical_grounding = True

            if not has_topical_grounding:
                final_score *= 0.08  # Discount files with no topical relation

            # Hard filtering: if user specifically requested an extension (e.g. .pdf) or type (e.g. resume)
            # penalize candidates that do not match the explicit constraint
            if clean_extensions and not has_ext_match:
                final_score *= 0.15
            if clean_doc_types and not has_type_match:
                final_score *= 0.25

            # Formulate user-facing match reasons
            match_reasons: List[str] = []
            if sem_score > 0.65:
                match_reasons.append("Semantic match")
            if fts_score > 0.20:
                matching_terms = [ct for ct in content_tokens if ct in (title + " " + summary + " " + filename).lower()]
                if matching_terms:
                    match_reasons.append(f"Keyword: {', '.join(matching_terms[:2])}")
                else:
                    match_reasons.append("Text match")
            if fn_score > 0.50:
                match_reasons.append("Filename match")
            match_reasons.extend(meta_reasons)
            if prefer_recent and rec_score > 0.70:
                match_reasons.append("Recent")
            if is_prot:
                match_reasons.append("Protected project codebase")

            if not match_reasons:
                match_reasons.append("Relevant content")

            candidate = CandidateResult(
                file_path=p_str,
                filename=filename,
                folder_path=folder_path,
                document_type=doc_type,
                title=title,
                summary=summary,
                score=float(final_score),
                semantic_score=float(sem_score),
                fts_score=float(fts_score),
                filename_score=float(fn_score),
                metadata_score=float(meta_score),
                recency_score=float(rec_score),
                modified_at=mod_at or "",
                protected=is_prot,
                project_type=proj_type,
                match_reasons=match_reasons[:4],
            )
            results.append(candidate)

        # Filter out candidates below relevance threshold
        qualified = [c for c in results if c.score >= self.MIN_SCORE_THRESHOLD]
        qualified.sort(key=lambda c: c.score, reverse=True)
        return qualified[:limit]
