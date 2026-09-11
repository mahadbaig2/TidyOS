"""Activity audit ledger and history page with Undo capabilities."""

from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QScrollArea,
)
from PySide6.QtCore import Qt
from tidyos.ui.theme.tokens import COLORS, RADII, SPACING, TYPOGRAPHY
from tidyos.ui.components.badge import StatusBadge


class ActivityEntryCard(QFrame):
    """Chronological activity ledger entry with explanation and Undo action."""

    def __init__(
        self,
        time_str: str,
        action_type: str,
        badge_variant: str,
        target_name: str,
        path_change: str,
        confidence: str | None,
        rationale: str,
        can_undo: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setStyleSheet(
            f"""
            QFrame#Card {{
                background-color: {COLORS.surface};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.lg}px;
                padding: {SPACING.lg}px;
            }}
            QFrame#Card:hover {{
                border-color: {COLORS.border_focus};
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        # Header: Timestamp + Action Badge + Target + Undo
        header = QHBoxLayout()
        header.setSpacing(10)

        time_lbl = QLabel(time_str)
        time_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {COLORS.text_muted};")
        header.addWidget(time_lbl)

        badge = StatusBadge(action_type, variant=badge_variant)
        header.addWidget(badge)

        name_lbl = QLabel(target_name)
        name_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS.text_primary};")
        header.addWidget(name_lbl)

        header.addStretch()

        if confidence:
            conf_lbl = QLabel(confidence)
            conf_lbl.setStyleSheet(f"font-size: 12px; color: {COLORS.text_secondary};")
            header.addWidget(conf_lbl)

        if can_undo:
            undo_btn = QPushButton("Undo")
            undo_btn.setObjectName("BtnSecondary")
            undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            header.addWidget(undo_btn)

        layout.addLayout(header)

        # Path info
        if path_change:
            path_lbl = QLabel(path_change)
            path_lbl.setStyleSheet(
                f"font-size: 12px; font-family: {TYPOGRAPHY.mono_family}; color: {COLORS.text_secondary};"
            )
            layout.addWidget(path_lbl)

        # Rationale
        why_box = QHBoxLayout()
        why_box.setSpacing(6)
        why_tag = QLabel("Why?")
        why_tag.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {COLORS.text_muted};")
        why_box.addWidget(why_tag)

        why_text = QLabel(f'"{rationale}"')
        why_text.setStyleSheet(f"font-size: 12px; color: {COLORS.text_secondary};")
        why_box.addWidget(why_text, 1)

        layout.addLayout(why_box)


class ActivityPage(QWidget):
    """Activity ledger screen providing transparency and reversible action history."""

    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(20)

        # Header
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        title = QLabel("Activity Ledger")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {COLORS.text_primary};")
        header_box.addWidget(title)

        subtitle = QLabel("Full audit trail of all file discoveries, agent proposals, moves, and protected boundaries.")
        subtitle.setStyleSheet(f"font-size: 13px; color: {COLORS.text_secondary};")
        header_box.addWidget(subtitle)
        layout.addLayout(header_box)

        # Date Section: Today
        day_lbl = QLabel("Today")
        day_lbl.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {COLORS.text_primary}; margin-top: 10px;")
        layout.addWidget(day_lbl)

        # Entry 1: Organized Vercel Invoice
        e1 = ActivityEntryCard(
            time_str="18:42",
            action_type="✓ Organized",
            badge_variant="success",
            target_name="document(17).pdf",
            path_change="Downloads/document(17).pdf → Finance/Software/Vercel/Vercel_Invoice_Sep_2026.pdf",
            confidence="97% confidence",
            rationale="This document is a September 2026 Vercel invoice. Similar software billing records are located in Finance/Software/Vercel.",
            can_undo=True,
        )
        layout.addWidget(e1)

        # Entry 2: Protected Next.js Project
        e2 = ActivityEntryCard(
            time_str="18:31",
            action_type="🛡️ Protected",
            badge_variant="protected",
            target_name="mahad-ai-portfolio",
            path_change="Detected package.json, next.config.ts, .git/ — protected root and all child files",
            confidence=None,
            rationale="Project root contains Next.js and Git markers. Structural files must not be reorganized.",
            can_undo=False,
        )
        layout.addWidget(e2)

        # Entry 3: Organized FastAPI screenshot
        e3 = ActivityEntryCard(
            time_str="18:14",
            action_type="✓ Organized",
            badge_variant="success",
            target_name="Screenshot_20260911_192234.png",
            path_change="Screenshots/Screenshot_...png → Development/Errors/FastAPI_CORS_Error.png",
            confidence="92% confidence",
            rationale="Screenshot contains Python FastAPI CORSMiddleware exception in VS Code terminal.",
            can_undo=True,
        )
        layout.addWidget(e3)

        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)
