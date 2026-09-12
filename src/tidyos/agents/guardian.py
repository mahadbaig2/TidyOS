"""Guardian Agent for contextual interpretation of filesystem boundaries.

PROBABILISTIC INTELLIGENCE. DETERMINISTIC AUTHORITY.
The Guardian interprets context and generates human-readable explanations.
It does NOT own authority to override SafetyPolicy or turn DENY into ALLOW.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from tidyos.config import config
from tidyos.safety import SafetyPolicy, FileOperation, PolicyDecision, PolicyStatus
from tidyos.safety.protection_manager import ProtectionManager
from tidyos.logging_config import get_logger

logger = get_logger("agents.guardian")


class GuardianExplanation(BaseModel):
    """Structured output contract from Guardian Agent."""
    path: str
    is_protected: bool
    project_type: Optional[str] = None
    context_role: Optional[str] = None
    explanation: str
    suggested_routing: str  # "STOP_PROTECTED" | "REVIEW" | "ELIGIBLE"


class GuardianAgent:
    """Guardian Agent responsible for contextual safety understanding.

    Inspects directory markers, project boundaries, and file context.
    Provides human-understandable explanations while respecting deterministic policy.
    """

    def __init__(
        self,
        safety_policy: SafetyPolicy,
        protection_manager: ProtectionManager,
    ):
        self.policy = safety_policy
        self.protection = protection_manager

    def inspect(
        self,
        file_path: str,
        destination_path: Optional[str] = None,
        confidence: float = 1.0,
    ) -> Tuple[PolicyDecision, GuardianExplanation]:
        """Inspect a file path and evaluate both deterministic policy and Guardian context."""
        op = FileOperation(
            operation_type="MOVE",
            source_path=file_path,
            destination_path=destination_path,
            confidence=confidence,
        )

        # 1. Deterministic authority check
        decision = self.policy.validate(op)

        # 2. Contextual understanding
        explanation = self._generate_contextual_explanation(file_path, decision)

        # Invariant check: Guardian cannot suggest ELIGIBLE if policy DENIED
        if decision.status == PolicyStatus.DENY and explanation.suggested_routing == "ELIGIBLE":
            logger.error("Guardian attempted to override DENY with ELIGIBLE! Correcting to STOP_PROTECTED.")
            explanation.suggested_routing = "STOP_PROTECTED"

        return decision, explanation

    def _generate_contextual_explanation(
        self,
        file_path: str,
        decision: PolicyDecision,
    ) -> GuardianExplanation:
        """Generate human-oriented contextual explanation with 100% offline fallback."""
        path_obj = Path(file_path)
        path_lower = file_path.lower().replace("\\", "/")

        is_prot, prot_record = self.protection.is_protected(file_path)
        proj_type = prot_record.project_type if prot_record else None

        # Next.js Specific Contexts
        if is_prot and proj_type == "nextjs":
            if "/public/" in path_lower or path_lower.endswith("/public"):
                return GuardianExplanation(
                    path=file_path,
                    is_protected=True,
                    project_type="nextjs",
                    context_role="Runtime Public Asset",
                    explanation=(
                        f"'{path_obj.name}' is located inside the public/ assets folder of a Next.js application. "
                        "Even if it looks like an ordinary document or image, moving it would break runtime references."
                    ),
                    suggested_routing="STOP_PROTECTED",
                )
            if "/app/" in path_lower or "/pages/" in path_lower or "/components/" in path_lower:
                return GuardianExplanation(
                    path=file_path,
                    is_protected=True,
                    project_type="nextjs",
                    context_role="Application Source Code",
                    explanation=(
                        f"'{path_obj.name}' is part of a Next.js route or component structure. "
                        "Internal project structure is required by the framework and protected from automated changes."
                    ),
                    suggested_routing="STOP_PROTECTED",
                )
            return GuardianExplanation(
                path=file_path,
                is_protected=True,
                project_type="nextjs",
                context_role="Project Internal File",
                explanation=f"'{path_obj.name}' is inside a Next.js project boundary ({prot_record.path}). Untouched.",
                suggested_routing="STOP_PROTECTED",
            )

        # Python Specific Contexts
        if is_prot and proj_type == "python":
            return GuardianExplanation(
                path=file_path,
                is_protected=True,
                project_type="python",
                context_role="Python Codebase Environment",
                explanation=f"'{path_obj.name}' is within a Python project structure ({prot_record.path}). Protected.",
                suggested_routing="STOP_PROTECTED",
            )

        # Generic Git Contexts
        if is_prot and proj_type == "generic_git":
            return GuardianExplanation(
                path=file_path,
                is_protected=True,
                project_type="generic_git",
                context_role="Git Repository Member",
                explanation=f"'{path_obj.name}' is tracked within a Git repository ({prot_record.path}). Protected.",
                suggested_routing="STOP_PROTECTED",
            )

        # Policy Denied for out of scope / system paths
        if decision.status == PolicyStatus.DENY:
            return GuardianExplanation(
                path=file_path,
                is_protected=is_prot,
                project_type=proj_type,
                context_role="Denied File",
                explanation=f"Operation denied by safety policy: {decision.explanation}",
                suggested_routing="STOP_PROTECTED",
            )

        # Policy Requires Review
        if decision.status == PolicyStatus.REVIEW:
            return GuardianExplanation(
                path=file_path,
                is_protected=False,
                project_type=None,
                context_role="Uncertain Context",
                explanation=f"Requires user confirmation: {decision.explanation}",
                suggested_routing="REVIEW",
            )

        # Safe ordinary file
        return GuardianExplanation(
            path=file_path,
            is_protected=False,
            project_type=None,
            context_role="Eligible User Document",
            explanation=f"'{path_obj.name}' is an ordinary user file in an approved intake folder and eligible for organization.",
            suggested_routing="ELIGIBLE",
        )
