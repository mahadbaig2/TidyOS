"""Natural Language Search Agent and Query Interpretation Engine."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from tidyos.retrieval.hybrid import CandidateResult, HybridRetriever
from tidyos.tools.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class StructuredQuery(BaseModel):
    """Structured constraints and intent extracted from a natural language query."""

    raw_query: str
    semantic_query: str
    keywords: List[str] = Field(default_factory=list)
    file_extensions: List[str] = Field(default_factory=list)
    document_types: List[str] = Field(default_factory=list)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    prefer_recent: bool = False
    entities: List[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    """Clean, explainable search result ready for UI display."""

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
    modified_at: str = ""
    protected: bool = False
    project_type: Optional[str] = None
    match_reasons: List[str] = Field(default_factory=list)


def parse_query_heuristics(raw_query: str) -> StructuredQuery:
    """Fast, deterministic local rule-based query parser (100% offline)."""
    text = (raw_query or "").strip()
    lower = text.lower()

    file_extensions: List[str] = []
    document_types: List[str] = []
    prefer_recent = False
    entities: List[str] = []

    # 1. Detect file formats & visual document types
    if re.search(r"\bpdf\b|\bpdfs\b", lower):
        file_extensions.append(".pdf")
    if re.search(r"\bdocx?\b|\bword\b", lower):
        file_extensions.append(".docx")
    if re.search(r"\bposters?\b|\bbanners?\b|\bflyers?\b|\binfographics?\b|\bpresentations?\b", lower):
        document_types.extend(["poster", "diagram", "photo"])
        file_extensions.extend([".png", ".jpg", ".jpeg", ".webp", ".pdf"])
    elif re.search(r"\bscreenshot\b|\bscreenshots\b", lower):
        document_types.append("screenshot")
        file_extensions.extend([".png", ".jpg", ".jpeg"])
    elif re.search(r"\bimages?\b|\bphotos?\b|\bpng\b|\bjpg\b|\bjpeg\b", lower):
        file_extensions.extend([".png", ".jpg", ".jpeg"])

    # 2. Detect document types & academic project markers
    if re.search(r"\binvoices?\b|\bbills?\b|\breceipts?\b", lower):
        document_types.append("invoice")
    if re.search(r"\bresumes?\b|\bcvs?\b", lower):
        document_types.append("resume")
    if re.search(r"\bnotes?\b", lower) and "screenshot" not in document_types:
        document_types.append("notes")
    if re.search(r"\bfyp\b|\bfinal year project\b|\bcapstone\b|\bthesis\b", lower):
        if "FYP" not in entities:
            entities.append("FYP")

    # 3. Detect recency preferences
    if re.search(r"\blatest\b|\brecent\b|\btoday\b|\byesterday\b|\bthis month\b|\bthis week\b", lower):
        prefer_recent = True

    # 4. Detect known entities / brands
    for brand in ["Vercel", "FastAPI", "Next.js", "Python", "LangGraph", "Acme", "AWS"]:
        if re.search(rf"\b{re.escape(brand.lower())}\b", lower):
            entities.append(brand)

    # 5. Extract core semantic query by stripping conversational filler prefixes
    filler_patterns = [
        r"^find\s+(the\s+|my\s+|a\s+|some\s+)?",
        r"^search\s+(for\s+)?",
        r"^show\s+(me\s+)?",
        r"^where\s+is\s+(the\s+|my\s+)?",
        r"^get\s+(the\s+|my\s+)?",
    ]
    cleaned = text
    for pat in filler_patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

    # Stopwords set to prevent keyword and FTS pollution
    query_stopwords = {
        "find", "show", "search", "get", "where", "file", "files", "the", "about",
        "with", "that", "this", "from", "for", "and", "or", "in", "on", "at", "by",
        "to", "of", "my", "your", "his", "her", "their", "our", "its", "me", "a", "an",
        "is", "are", "was", "were", "it", "into", "during", "before", "after", "document"
    }

    # Extract clean topical keywords
    words = [
        w for w in re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", cleaned)
        if w.lower() not in query_stopwords
    ]

    return StructuredQuery(
        raw_query=text,
        semantic_query=cleaned.strip() or text,
        keywords=words,
        file_extensions=list(set(file_extensions)),
        document_types=list(set(document_types)),
        prefer_recent=prefer_recent,
        entities=entities,
    )


class SearchAgent:
    """Intelligent Search Agent managing natural-language interpretation and hybrid retrieval.

    SAFETY INVARIANT:
    Zero mutation authority. Search is strictly read-only; never touches,
    moves, renames, or deletes files on the filesystem.
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        openai_client: Optional[OpenAIClient] = None,
    ):
        self.retriever = retriever
        self.openai_client = openai_client or OpenAIClient()

    def interpret_query(self, raw_query: str) -> StructuredQuery:
        """Interpret natural-language user query into structured retrieval constraints."""
        # Always run deterministic parser first for speed and offline stability
        heuristic_query = parse_query_heuristics(raw_query)

        # If OpenAI is unavailable or prompt is very simple, return heuristic result directly
        if not self.openai_client.is_available() or len(raw_query.split()) < 3:
            return heuristic_query

        # Richer query interpretation with OpenAI if available
        try:
            prompt = (
                f"Analyze this file search query: '{raw_query}'\n"
                f"Extract structured search parameters in JSON format with keys:\n"
                f"- 'semantic_query': string (concise semantic meaning without conversational filler)\n"
                f"- 'keywords': list of strings\n"
                f"- 'file_extensions': list of strings (e.g. ['.pdf'] or empty)\n"
                f"- 'document_types': list of strings (e.g. ['invoice', 'resume', 'screenshot'] or empty)\n"
                f"- 'prefer_recent': boolean\n"
                f"- 'entities': list of strings (names, products, technologies)\n"
            )
            assert self.openai_client._client is not None
            resp = self.openai_client._client.chat.completions.create(
                model=self.openai_client.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are the TidyOS Search Intent Agent. Output only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=250,
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            return StructuredQuery(
                raw_query=raw_query,
                semantic_query=data.get("semantic_query") or heuristic_query.semantic_query,
                keywords=data.get("keywords") or heuristic_query.keywords,
                file_extensions=data.get("file_extensions") or heuristic_query.file_extensions,
                document_types=data.get("document_types") or heuristic_query.document_types,
                prefer_recent=bool(data.get("prefer_recent", heuristic_query.prefer_recent)),
                entities=data.get("entities") or heuristic_query.entities,
            )
        except Exception as e:
            logger.debug("OpenAI query interpretation failed (%s); using heuristic query", e)
            return heuristic_query

    def search(self, query: str, limit: int = 15) -> List[SearchResult]:
        """Execute intelligent natural-language file retrieval."""
        structured = self.interpret_query(query)

        candidates: List[CandidateResult] = self.retriever.retrieve(
            query=structured.semantic_query,
            file_extensions=structured.file_extensions,
            document_types=structured.document_types,
            prefer_recent=structured.prefer_recent,
            limit=limit,
        )

        results: List[SearchResult] = []
        for c in candidates:
            # Build clean user-facing match reasons
            reasons = list(c.match_reasons)
            if structured.file_extensions and any(e in c.file_path.lower() for e in structured.file_extensions):
                ext_name = Path(c.file_path).suffix.upper().lstrip(".")
                if ext_name and ext_name not in reasons:
                    reasons.insert(0, ext_name)

            results.append(
                SearchResult(
                    file_path=c.file_path,
                    filename=c.filename,
                    folder_path=c.folder_path,
                    document_type=c.document_type,
                    title=c.title,
                    summary=c.summary,
                    score=c.score,
                    semantic_score=c.semantic_score,
                    fts_score=c.fts_score,
                    filename_score=c.filename_score,
                    metadata_score=c.metadata_score,
                    recency_score=c.recency_score,
                    modified_at=c.modified_at,
                    protected=c.protected,
                    project_type=c.project_type,
                    match_reasons=reasons[:4],
                )
            )

        return results
