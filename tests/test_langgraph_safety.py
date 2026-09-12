"""Unit tests for LangGraph safety state graph and conditional routing."""

import pytest
from pathlib import Path

from tidyos.storage import StorageRepository
from tidyos.safety import SafetyPolicy, ProtectionManager
from tidyos.agents import GuardianAgent, create_safety_graph, TidyOSState
from tidyos.testing.demo_corpus import create_demo_corpus


def test_langgraph_conditional_safety_routing(tmp_path: Path):
    """Test real LangGraph conditional edges routing to PROTECTED, REVIEW, and SAFE branches."""
    corpus = create_demo_corpus(tmp_path / "DemoEnvironment")
    db_path = tmp_path / "test.db"
    repo = StorageRepository(db_path)

    repo.add_managed_root(corpus["downloads"])
    repo.add_managed_root(corpus["projects"])
    repo.add_managed_root(corpus["documents"])

    prot_mgr = ProtectionManager(repo)
    prot_mgr.check_and_register_directory(corpus["next_demo"])

    policy = SafetyPolicy(protection_manager=prot_mgr, confidence_threshold=0.85)
    guardian = GuardianAgent(safety_policy=policy, protection_manager=prot_mgr)
    graph = create_safety_graph(guardian)

    # 1. Protected file input -> Should conditionally route to protected_branch
    prot_state_in: TidyOSState = {
        "file_path": str(corpus["next_demo"] / "public" / "invoice.pdf"),
        "confidence": 1.0,
    }
    result_prot = graph.invoke(prot_state_in)
    assert result_prot["status"] == "PROTECTED_MUTATION_STOPPED"
    assert result_prot["policy_status"] == "DENY"
    assert result_prot["protected"] is True
    assert result_prot["project_type"] == "nextjs"

    # 2. Low confidence file input -> Should conditionally route to review_branch
    review_state_in: TidyOSState = {
        "file_path": str(corpus["downloads"] / "invoice.pdf"),
        "suggested_destination": str(corpus["documents"] / "Finance" / "invoice.pdf"),
        "confidence": 0.50,  # Below threshold
    }
    result_review = graph.invoke(review_state_in)
    assert result_review["status"] == "NEEDS_USER_REVIEW"
    assert result_review["policy_status"] == "REVIEW"
    assert result_review["requires_review"] is True

    # 3. High confidence safe file input -> Should conditionally route to safe_branch
    safe_state_in: TidyOSState = {
        "file_path": str(corpus["downloads"] / "invoice.pdf"),
        "suggested_destination": str(corpus["documents"] / "Finance" / "invoice.pdf"),
        "confidence": 0.95,
    }
    result_safe = graph.invoke(safe_state_in)
    assert result_safe["status"] == "SAFE_FOR_SEMANTIC_PROCESSING"
    assert result_safe["policy_status"] == "ALLOW"
    assert result_safe["requires_review"] is False
