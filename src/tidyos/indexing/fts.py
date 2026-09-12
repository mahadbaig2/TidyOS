"""SQLite FTS5 full-text indexing and retrieval manager."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def sanitize_fts_query(raw_query: str) -> str:
    """Sanitize user search query into safe, effective FTS5 match expression."""
    if not raw_query:
        return ""

    # Replace non-alphanumeric characters (except underscores and spaces) with spaces
    cleaned = re.sub(r"[^a-zA-Z0-9_\s]", " ", raw_query)
    # Extract alpha-numeric tokens
    tokens = [t.strip() for t in cleaned.split() if t.strip()]

    # Ignore isolated standard boolean keywords that might confuse FTS5
    safe_tokens = [t for t in tokens if t.upper() not in {"AND", "OR", "NOT", "NEAR"}]
    if not safe_tokens:
        return ""

    # Form prefix-match query with OR disjunction for broad candidate discovery
    # e.g. "fastapi cors" -> "fastapi* OR cors*"
    return " OR ".join(f'"{t}"*' for t in safe_tokens)


class FTSIndexManager:
    """Manages SQLite FTS5 table indexing and keyword/phrase retrieval."""

    def __init__(self, repository: Any):
        self.repository = repository

    def index_file(
        self,
        file_path: str,
        filename: str,
        title: str = "",
        summary: str = "",
        topics: Optional[List[str]] = None,
        entities: Optional[List[str]] = None,
        extracted_text: str = "",
    ) -> None:
        """Upsert a file's searchable text into the FTS5 index."""
        conn = self.repository.get_connection()
        topics_str = " ".join(topics or [])
        entities_str = " ".join(entities or [])
        path_str = str(file_path)

        with conn:
            cur = conn.cursor()
            # Delete existing entry if present
            cur.execute("DELETE FROM files_fts WHERE file_path = ?", (path_str,))
            cur.execute(
                """
                INSERT INTO files_fts (
                    file_path, filename, title, summary, topics, entities, extracted_text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    path_str,
                    filename,
                    title,
                    summary,
                    topics_str,
                    entities_str,
                    extracted_text[:10000],  # Bounded extracted text
                ),
            )

    def remove_file(self, file_path: str) -> None:
        """Remove a file from the FTS5 index."""
        conn = self.repository.get_connection()
        with conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM files_fts WHERE file_path = ?", (str(file_path),))

    def search(self, query: str, limit: int = 50) -> Dict[str, float]:
        """Perform full-text search and return {file_path: normalized_score (0.0 - 1.0)}."""
        match_expr = sanitize_fts_query(query)
        if not match_expr:
            return {}

        conn = self.repository.get_connection()
        cur = conn.cursor()

        try:
            # SQLite bm25() returns negative values (e.g. -5.2 is better than -1.1)
            cur.execute(
                """
                SELECT file_path, bm25(files_fts) as rank
                FROM files_fts
                WHERE files_fts MATCH ?
                ORDER BY rank ASC
                LIMIT ?
                """,
                (match_expr, limit),
            )
            rows = cur.fetchall()
            if not rows:
                return {}

            scores: Dict[str, float] = {}
            # Transform bm25 score to [0.0, 1.0] scale
            # Smaller (more negative) rank indicates higher relevance
            best_rank = abs(float(rows[0]["rank"])) if rows else 1.0
            for r in rows:
                raw_rank = float(r["rank"])
                # Normalized score: 1.0 for top hit, gracefully decaying
                score = max(0.1, min(1.0, 1.0 / (1.0 + max(0.0, (raw_rank + best_rank) * 0.2))))
                scores[r["file_path"]] = float(score)

            return scores
        except Exception as e:
            logger.warning("FTS search query failed for expression '%s': %s", match_expr, e)
            return {}
