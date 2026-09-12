"""LangGraph workflow for orchestrating natural language search and rank fusion."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END

from tidyos.agents.search_agent import SearchAgent, SearchResult, StructuredQuery
from tidyos.retrieval.hybrid import CandidateResult

logger = logging.getLogger(__name__)


class SearchGraphState(TypedDict, total=False):
    """Shared state dictionary passed across LangGraph search nodes."""

    query: str
    limit: int
    structured_query: Dict[str, Any]
    candidates: List[Dict[str, Any]]
    results: List[Dict[str, Any]]
    total_found: int


def create_search_graph(search_agent: SearchAgent):
    """Construct and compile LangGraph state graph for intelligent file search."""
    builder = StateGraph(SearchGraphState)

    # 1. Interpret Node: Natural language parsing into structured constraints
    def interpret_node(state: SearchGraphState) -> Dict[str, Any]:
        raw_query = state.get("query", "")
        structured: StructuredQuery = search_agent.interpret_query(raw_query)
        return {
            "structured_query": structured.model_dump(),
        }

    # 2. Retrieve Node: Multi-signal candidate retrieval (Vectors, FTS5, Filenames)
    def retrieve_node(state: SearchGraphState) -> Dict[str, Any]:
        sq_dict = state.get("structured_query", {})
        limit = state.get("limit", 15)

        candidates: List[CandidateResult] = search_agent.retriever.retrieve(
            query=sq_dict.get("semantic_query", state.get("query", "")),
            file_extensions=sq_dict.get("file_extensions"),
            document_types=sq_dict.get("document_types"),
            prefer_recent=sq_dict.get("prefer_recent", False),
            limit=limit,
        )

        candidates_data = [
            {
                "file_path": c.file_path,
                "filename": c.filename,
                "folder_path": c.folder_path,
                "document_type": c.document_type,
                "title": c.title,
                "summary": c.summary,
                "score": c.score,
                "semantic_score": c.semantic_score,
                "fts_score": c.fts_score,
                "filename_score": c.filename_score,
                "metadata_score": c.metadata_score,
                "recency_score": c.recency_score,
                "modified_at": c.modified_at,
                "protected": c.protected,
                "project_type": c.project_type,
                "match_reasons": list(c.match_reasons),
            }
            for c in candidates
        ]

        return {"candidates": candidates_data}

    # 3. Rank Fusion & Explanation Node
    def rank_and_explain_node(state: SearchGraphState) -> Dict[str, Any]:
        candidates = state.get("candidates", [])
        sq_dict = state.get("structured_query", {})
        req_exts = sq_dict.get("file_extensions", [])

        # Format final search results with human-readable explanations
        formatted_results: List[Dict[str, Any]] = []
        for c in candidates:
            reasons = list(c.get("match_reasons", []))
            if req_exts and any(e in c["file_path"].lower() for e in req_exts):
                ext_name = c["file_path"].split(".")[-1].upper()
                if ext_name and ext_name not in reasons:
                    reasons.insert(0, ext_name)

            c_copy = dict(c)
            c_copy["match_reasons"] = reasons[:4]
            formatted_results.append(c_copy)

        return {
            "results": formatted_results,
            "total_found": len(formatted_results),
        }

    # Connect nodes in sequence
    builder.add_node("interpret", interpret_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("rank_and_explain", rank_and_explain_node)

    builder.add_edge(START, "interpret")
    builder.add_edge("interpret", "retrieve")
    builder.add_edge("retrieve", "rank_and_explain")
    builder.add_edge("rank_and_explain", END)

    compiled_graph = builder.compile()
    logger.info("Compiled LangGraph Search workflow.")
    return compiled_graph
