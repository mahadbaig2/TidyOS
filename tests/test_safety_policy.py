"""Unit tests verifying central deterministic SafetyPolicy and safety invariants."""

import pytest
from pathlib import Path

from tidyos.storage import StorageRepository
from tidyos.safety import (
    SafetyPolicy,
    ProtectionManager,
    FileOperation,
    PolicyStatus,
    ReasonCode,
)
from tidyos.testing.demo_corpus import create_demo_corpus


def test_safety_invariants_and_environment_contrast(tmp_path: Path):
    """Test all central safety invariants, especially contrasting Downloads vs Next.js project."""
    corpus = create_demo_corpus(tmp_path / "DemoEnvironment")
    db_path = tmp_path / "test.db"
    repo = StorageRepository(db_path)

    # User explicitly manages Downloads and Projects
    root_dl = repo.add_managed_root(corpus["downloads"])
    root_proj = repo.add_managed_root(corpus["projects"])

    prot_mgr = ProtectionManager(repo)
    # Register the Next.js project
    prot_mgr.check_and_register_directory(corpus["next_demo"])

    policy = SafetyPolicy(
        protection_manager=prot_mgr,
        confidence_threshold=0.85,
    )

    # -------------------------------------------------------------------------
    # INVARIANT 6: The environment changes the agent's decision.
    # Downloads/invoice.pdf vs Projects/next-demo/public/invoice.pdf
    # -------------------------------------------------------------------------

    # 1. Downloads/invoice.pdf -> SAFE, should be ALLOWED to move to Documents
    safe_op = FileOperation(
        operation_type="MOVE",
        source_path=str(corpus["downloads"] / "invoice.pdf"),
        destination_path=str(corpus["documents"] / "Finance" / "invoice.pdf"),
        confidence=0.95,
        reason="Invoice belongs in Finance",
    )
    # Documents isn't managed yet; let's add Documents to managed roots to allow destination
    repo.add_managed_root(corpus["documents"])

    decision_safe = policy.validate(safe_op)
    assert decision_safe.status == PolicyStatus.ALLOW
    assert decision_safe.reason_code == ReasonCode.VALID_SAFE_OPERATION

    # 2. Projects/next-demo/public/invoice.pdf -> PROTECTED Next.js runtime asset
    # Even though file contents and filename are IDENTICAL to Downloads/invoice.pdf,
    # moving it must be strictly DENIED!
    protected_op = FileOperation(
        operation_type="MOVE",
        source_path=str(corpus["next_demo"] / "public" / "invoice.pdf"),
        destination_path=str(corpus["documents"] / "Finance" / "invoice.pdf"),
        confidence=0.99,  # High confidence agent
        reason="Agent thinks this is an invoice",
    )
    decision_prot = policy.validate(protected_op)
    assert decision_prot.status == PolicyStatus.DENY
    assert decision_prot.reason_code == ReasonCode.SOURCE_PROTECTED
    assert "protected nextjs project" in decision_prot.explanation.lower()

    # -------------------------------------------------------------------------
    # INVARIANT 2: Descendants of a protected root cannot be mutated
    # -------------------------------------------------------------------------
    page_op = FileOperation(
        operation_type="RENAME",
        source_path=str(corpus["next_demo"] / "package.json"),
        destination_path=str(corpus["next_demo"] / "package-renamed.json"),
    )
    assert policy.validate(page_op).status == PolicyStatus.DENY
    assert policy.validate(page_op).reason_code == ReasonCode.SOURCE_PROTECTED

    # Destination inside protected root is also DENIED
    dest_in_proj_op = FileOperation(
        operation_type="MOVE",
        source_path=str(corpus["downloads"] / "random_notes.txt"),
        destination_path=str(corpus["next_demo"] / "notes.txt"),
    )
    decision_dest_prot = policy.validate(dest_in_proj_op)
    assert decision_dest_prot.status == PolicyStatus.DENY
    assert decision_dest_prot.reason_code == ReasonCode.DESTINATION_PROTECTED

    # -------------------------------------------------------------------------
    # INVARIANT 3: Paths outside authorized managed scope are DENIED
    # -------------------------------------------------------------------------
    outside_dir = tmp_path / "UnmanagedExternal"
    outside_dir.mkdir()
    outside_file = outside_dir / "secret.pdf"
    outside_file.write_text("secret", encoding="utf-8")

    out_scope_op = FileOperation(
        operation_type="MOVE",
        source_path=str(outside_file),
        destination_path=str(corpus["downloads"] / "secret.pdf"),
    )
    decision_out = policy.validate(out_scope_op)
    assert decision_out.status == PolicyStatus.DENY
    assert decision_out.reason_code == ReasonCode.OUT_OF_SCOPE_SOURCE

    # Destination escaping managed scope is also DENIED
    escape_dest_op = FileOperation(
        operation_type="MOVE",
        source_path=str(corpus["downloads"] / "random_notes.txt"),
        destination_path=str(outside_dir / "random_notes.txt"),
    )
    decision_escape = policy.validate(escape_dest_op)
    assert decision_escape.status == PolicyStatus.DENY
    assert decision_escape.reason_code == ReasonCode.OUT_OF_SCOPE_DESTINATION

    # -------------------------------------------------------------------------
    # INVARIANT 5: Permanent deletion is strictly DENIED
    # -------------------------------------------------------------------------
    delete_op = FileOperation(
        operation_type="DELETE",
        source_path=str(corpus["downloads"] / "random_notes.txt"),
    )
    decision_del = policy.validate(delete_op)
    assert decision_del.status == PolicyStatus.DENY
    assert decision_del.reason_code == ReasonCode.DELETION_DENIED

    # -------------------------------------------------------------------------
    # Overwrite prevention: Cannot overwrite existing destination
    # -------------------------------------------------------------------------
    existing_dest_op = FileOperation(
        operation_type="MOVE",
        source_path=str(corpus["downloads"] / "random_notes.txt"),
        destination_path=str(corpus["downloads"] / "Screenshot_2026.png"),  # Already exists!
    )
    decision_ovw = policy.validate(existing_dest_op)
    assert decision_ovw.status == PolicyStatus.DENY
    assert decision_ovw.reason_code == ReasonCode.OVERWRITE_DENIED

    # -------------------------------------------------------------------------
    # INVARIANT 4: Low confidence or uncertain routes to REVIEW
    # -------------------------------------------------------------------------
    low_conf_op = FileOperation(
        operation_type="MOVE",
        source_path=str(corpus["downloads"] / "random_notes.txt"),
        destination_path=str(corpus["documents"] / "Work" / "notes.txt"),
        confidence=0.60,  # Below threshold (0.85)
    )
    decision_low = policy.validate(low_conf_op)
    assert decision_low.status == PolicyStatus.REVIEW
    assert decision_low.reason_code == ReasonCode.LOW_CONFIDENCE
