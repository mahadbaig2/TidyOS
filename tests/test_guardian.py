"""Unit tests for Guardian Agent contextual interpretation and safety enforcement."""

import pytest
from pathlib import Path

from tidyos.storage import StorageRepository
from tidyos.safety import (
    SafetyPolicy,
    ProtectionManager,
    PolicyStatus,
)
from tidyos.agents import (
    GuardianAgent,
    GuardianExplanation,
)
from tidyos.testing.demo_corpus import create_demo_corpus


def test_guardian_contextual_explanations(tmp_path: Path):
    """Test Guardian contextual explanations for runtime assets, routes, and user documents."""
    corpus = create_demo_corpus(tmp_path / "DemoEnvironment")
    db_path = tmp_path / "test.db"
    repo = StorageRepository(db_path)

    repo.add_managed_root(corpus["downloads"])
    repo.add_managed_root(corpus["projects"])
    repo.add_managed_root(corpus["documents"])

    prot_mgr = ProtectionManager(repo)
    prot_mgr.check_and_register_directory(corpus["next_demo"])
    prot_mgr.check_and_register_directory(corpus["python_demo"])

    policy = SafetyPolicy(protection_manager=prot_mgr)
    guardian = GuardianAgent(safety_policy=policy, protection_manager=prot_mgr)

    # 1. Next.js public asset
    next_asset = corpus["next_demo"] / "public" / "invoice.pdf"
    decision1, exp1 = guardian.inspect(str(next_asset))
    assert decision1.status == PolicyStatus.DENY
    assert exp1.is_protected is True
    assert exp1.project_type == "nextjs"
    assert exp1.context_role == "Runtime Public Asset"
    assert "public/ assets" in exp1.explanation
    assert exp1.suggested_routing == "STOP_PROTECTED"

    # 2. Next.js package.json / internal
    next_pkg = corpus["next_demo"] / "package.json"
    decision2, exp2 = guardian.inspect(str(next_pkg))
    assert decision2.status == PolicyStatus.DENY
    assert exp2.is_protected is True
    assert exp2.suggested_routing == "STOP_PROTECTED"

    # 3. Python codebase file
    py_file = corpus["python_demo"] / "main.py"
    decision3, exp3 = guardian.inspect(str(py_file))
    assert decision3.status == PolicyStatus.DENY
    assert exp3.is_protected is True
    assert exp3.project_type == "python"
    assert "Python project" in exp3.explanation
    assert exp3.suggested_routing == "STOP_PROTECTED"

    # 4. Ordinary file in Downloads
    dl_file = corpus["downloads"] / "invoice.pdf"
    decision4, exp4 = guardian.inspect(str(dl_file))
    assert decision4.status == PolicyStatus.ALLOW
    assert exp4.is_protected is False
    assert exp4.context_role == "Eligible User Document"
    assert exp4.suggested_routing == "ELIGIBLE"


def test_guardian_cannot_override_policy_deny(tmp_path: Path):
    """INVARIANT 1: An agent/LLM cannot override a deterministic DENY."""
    corpus = create_demo_corpus(tmp_path / "DemoEnvironment")
    db_path = tmp_path / "test.db"
    repo = StorageRepository(db_path)

    repo.add_managed_root(corpus["projects"])
    prot_mgr = ProtectionManager(repo)
    prot_mgr.check_and_register_directory(corpus["next_demo"])

    policy = SafetyPolicy(protection_manager=prot_mgr)
    guardian = GuardianAgent(safety_policy=policy, protection_manager=prot_mgr)

    # Attempt to move protected file
    next_asset = corpus["next_demo"] / "public" / "invoice.pdf"
    decision, exp = guardian.inspect(
        str(next_asset),
        destination_path=str(corpus["projects"] / "invoice.pdf"),
    )

    # Policy MUST be authoritative DENY
    assert decision.status == PolicyStatus.DENY
    assert exp.suggested_routing == "STOP_PROTECTED"
