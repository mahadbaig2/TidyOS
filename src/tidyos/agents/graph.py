"""LangGraph safety workflow orchestrating Guardian agent, Librarian agent, and deterministic routing."""

from __future__ import annotations

from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END

from tidyos.agents.state import TidyOSState
from tidyos.agents.guardian import GuardianAgent
from tidyos.agents.librarian import LibrarianAgent, FileUnderstanding
from tidyos.logging_config import get_logger

logger = get_logger("agents.graph")


def create_safety_graph(
    guardian_agent: GuardianAgent,
    librarian_agent: Optional[LibrarianAgent] = None,
):
    """Construct and compile LangGraph workflow for safety verification and semantic indexing."""

    builder = StateGraph(TidyOSState)

    # 1. Guardian Node (Deterministic safety policy evaluation)
    def guardian_node(state: TidyOSState) -> Dict[str, Any]:
        file_path = state.get("file_path", "")
        dest_path = state.get("suggested_destination")
        confidence = state.get("confidence", 1.0)

        decision, explanation = guardian_agent.inspect(
            file_path=file_path,
            destination_path=dest_path,
            confidence=confidence,
        )

        return {
            "protected": explanation.is_protected,
            "project_type": explanation.project_type,
            "protection_reason": explanation.explanation,
            "policy_status": decision.status.value,
            "policy_reason_code": decision.reason_code.value,
            "policy_explanation": decision.explanation,
            "guardian_explanation": explanation.explanation,
            "suggested_routing": explanation.suggested_routing,
        }

    # Helper for running Librarian analysis
    def _run_librarian(state: TidyOSState) -> Dict[str, Any]:
        if not librarian_agent:
            return {}
        file_path = state.get("file_path", "")
        parent_dir = state.get("parent_directory", "")
        try:
            u: FileUnderstanding = librarian_agent.analyze_file(file_path, path_context=parent_dir)
            return {
                "document_type": u.document_type,
                "title": u.title,
                "summary": u.summary,
                "entities": u.entities,
                "topics": u.topics,
                "suggested_folder": u.suggested_folder,
                "analysis_source": u.analysis_source,
                "extracted_chars": u.extracted_chars,
                "is_truncated": u.is_truncated,
                "confidence": u.confidence,
            }
        except Exception as e:
            logger.warning("Librarian analysis failed for %s: %s", file_path, e)
            return {"errors": [f"Librarian error: {e}"]}

    # 2. Safety Branch Nodes
    def protected_node(state: TidyOSState) -> Dict[str, Any]:
        logger.info(f"LangGraph safety routing -> PROTECTED (Stop Mutation): {state.get('file_path')}")
        result: Dict[str, Any] = {
            "status": "PROTECTED_SEMANTICALLY_INDEXED" if librarian_agent else "PROTECTED_MUTATION_STOPPED",
            "requires_review": False,
        }
        if librarian_agent:
            result.update(_run_librarian(state))
        return result

    def review_node(state: TidyOSState) -> Dict[str, Any]:
        logger.info(f"LangGraph safety routing -> REVIEW: {state.get('file_path')}")
        result: Dict[str, Any] = {
            "status": "REVIEW_SEMANTICALLY_INDEXED" if librarian_agent else "NEEDS_USER_REVIEW",
            "requires_review": True,
        }
        if librarian_agent:
            result.update(_run_librarian(state))
        return result

    def safe_node(state: TidyOSState) -> Dict[str, Any]:
        logger.info(f"LangGraph safety routing -> SAFE: {state.get('file_path')}")
        result: Dict[str, Any] = {
            "status": "SAFE_FOR_ORGANIZATION" if librarian_agent else "SAFE_FOR_SEMANTIC_PROCESSING",
            "requires_review": False,
        }
        if librarian_agent:
            result.update(_run_librarian(state))
        return result

    # 3. Conditional Router
    def route_safety(state: TidyOSState) -> str:
        status = state.get("policy_status", "DENY")
        if status == "DENY":
            return "protected"
        elif status == "REVIEW":
            return "review"
        else:
            return "safe"

    # Add nodes to graph
    builder.add_node("guardian", guardian_node)
    builder.add_node("protected_branch", protected_node)
    builder.add_node("review_branch", review_node)
    builder.add_node("safe_branch", safe_node)

    # Add edges
    builder.add_edge(START, "guardian")
    builder.add_conditional_edges(
        "guardian",
        route_safety,
        {
            "protected": "protected_branch",
            "review": "review_branch",
            "safe": "safe_branch",
        },
    )

    builder.add_edge("protected_branch", END)
    builder.add_edge("review_branch", END)
    builder.add_edge("safe_branch", END)

    compiled_graph = builder.compile()
    logger.info("Compiled LangGraph workflow.")
    return compiled_graph
