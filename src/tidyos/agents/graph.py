"""LangGraph safety workflow orchestrating Guardian agent and deterministic routing."""

from __future__ import annotations

from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END

from tidyos.agents.state import TidyOSState
from tidyos.agents.guardian import GuardianAgent
from tidyos.logging_config import get_logger

logger = get_logger("agents.graph")


def create_safety_graph(guardian_agent: GuardianAgent):
    """Construct and compile LangGraph workflow for Phase 2 safety verification."""

    builder = StateGraph(TidyOSState)

    # 1. Guardian Node
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

    # 2. Safety Branch Nodes
    def protected_node(state: TidyOSState) -> Dict[str, Any]:
        logger.info(f"LangGraph safety routing -> PROTECTED (Stop Mutation): {state.get('file_path')}")
        return {
            "status": "PROTECTED_MUTATION_STOPPED",
            "requires_review": False,
        }

    def review_node(state: TidyOSState) -> Dict[str, Any]:
        logger.info(f"LangGraph safety routing -> REVIEW: {state.get('file_path')}")
        return {
            "status": "NEEDS_USER_REVIEW",
            "requires_review": True,
        }

    def safe_node(state: TidyOSState) -> Dict[str, Any]:
        logger.info(f"LangGraph safety routing -> SAFE: {state.get('file_path')}")
        return {
            "status": "SAFE_FOR_SEMANTIC_PROCESSING",
            "requires_review": False,
        }

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
    logger.info("Compiled LangGraph safety workflow.")
    return compiled_graph
