"""Organize cleanup plan page for TidyOS."""

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


class ProposalCard(QFrame):
    """File organization proposal card with before/after paths, confidence and actions."""

    def __init__(
        self,
        file_type: str,
        original_name: str,
        source_path: str,
        dest_path: str,
        reason: str,
        confidence: str,
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
        layout.setSpacing(10)

        # Header: File type, original name, confidence badge
        header = QHBoxLayout()
        type_badge = StatusBadge(file_type, variant="neutral")
        header.addWidget(type_badge)

        name_lbl = QLabel(original_name)
        name_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS.text_primary};")
        header.addWidget(name_lbl)

        header.addStretch()

        conf_badge = StatusBadge(confidence, variant="success")
        header.addWidget(conf_badge)
        layout.addLayout(header)

        # Path Transformation Frame (Before -> After)
        path_box = QFrame()
        path_box.setStyleSheet(
            f"""
            background-color: {COLORS.surface_raised};
            border: 1px solid {COLORS.border_subtle};
            border-radius: {RADII.md}px;
            padding: 8px 12px;
            """
        )
        p_layout = QVBoxLayout(path_box)
        p_layout.setContentsMargins(10, 8, 10, 8)
        p_layout.setSpacing(4)

        src_lbl = QLabel(f"From:  {source_path}")
        src_lbl.setStyleSheet(
            f"font-size: 12px; font-family: {TYPOGRAPHY.mono_family}; color: {COLORS.text_muted};"
        )
        p_layout.addWidget(src_lbl)

        arrow_lbl = QLabel("  ↓")
        arrow_lbl.setStyleSheet(f"font-size: 12px; color: {COLORS.text_secondary}; font-weight: 700;")
        p_layout.addWidget(arrow_lbl)

        dst_lbl = QLabel(f"To:    {dest_path}")
        dst_lbl.setStyleSheet(
            f"font-size: 12px; font-family: {TYPOGRAPHY.mono_family}; color: {COLORS.text_primary}; font-weight: 600;"
        )
        p_layout.addWidget(dst_lbl)

        layout.addWidget(path_box)

        # Reason rationale
        reason_lbl = QLabel(f'Rationale: "{reason}"')
        reason_lbl.setStyleSheet(f"font-size: 12px; color: {COLORS.text_secondary}; font-style: italic;")
        layout.addWidget(reason_lbl)

        # Actions
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()

        approve_btn = QPushButton("Approve")
        approve_btn.setObjectName("BtnPrimary")
        approve_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        actions_layout.addWidget(approve_btn)

        change_btn = QPushButton("Change")
        change_btn.setObjectName("BtnSecondary")
        change_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        actions_layout.addWidget(change_btn)

        reject_btn = QPushButton("Reject")
        reject_btn.setObjectName("BtnSubtle")
        reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        actions_layout.addWidget(reject_btn)

        layout.addLayout(actions_layout)


class OrganizePage(QWidget):
    """Organize screen displaying first-run cleanup plans and batch review."""

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

        # Page Header
        top_bar = QHBoxLayout()

        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        title = QLabel("Organize")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {COLORS.text_primary};")
        header_box.addWidget(title)

        subtitle = QLabel("TidyOS analyzed 1,284 files: 211 ready for safe organization, 14 protected projects, 16 need review.")
        subtitle.setStyleSheet(f"font-size: 13px; color: {COLORS.text_secondary};")
        header_box.addWidget(subtitle)
        top_bar.addLayout(header_box)

        top_bar.addStretch()

        bulk_btn = QPushButton("Approve 38 Safe Changes")
        bulk_btn.setObjectName("BtnPrimary")
        bulk_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        bulk_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLORS.text_primary};
                color: {COLORS.app_bg};
                border-radius: {RADII.md}px;
                padding: 10px 18px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #E4E4E7;
            }}
            """
        )
        top_bar.addWidget(bulk_btn)

        layout.addLayout(top_bar)

        # Filter buttons row
        filters_row = QHBoxLayout()
        filters_row.setSpacing(8)

        filters = [
            ("All (241)", True),
            ("Ready to Organize (211)", False),
            ("Protected Projects (14)", False),
            ("Needs Review (16)", False),
        ]

        for label, is_active in filters:
            f_btn = QPushButton(label)
            if is_active:
                f_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {COLORS.surface_raised};
                        color: {COLORS.text_primary};
                        border: 1px solid {COLORS.border_subtle};
                        border-radius: {RADII.md}px;
                        padding: 6px 14px;
                        font-weight: 600;
                        font-size: 12px;
                    }}
                    """
                )
            else:
                f_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {COLORS.text_secondary};
                        border: 1px solid {COLORS.border};
                        border-radius: {RADII.md}px;
                        padding: 6px 14px;
                        font-weight: 500;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS.surface_hover};
                        color: {COLORS.text_primary};
                    }}
                    """
                )
            filters_row.addWidget(f_btn)

        filters_row.addStretch()
        layout.addLayout(filters_row)

        # Proposal Cards
        p1 = ProposalCard(
            file_type="PDF",
            original_name="document(17).pdf",
            source_path="Downloads / document(17).pdf",
            dest_path="Finance / Software / Vercel / Vercel_Invoice_Sep_2026.pdf",
            reason="Librarian identified this as a September 2026 Vercel hosting invoice; matched to Finance/Software.",
            confidence="97% confidence",
        )
        layout.addWidget(p1)

        p2 = ProposalCard(
            file_type="PDF",
            original_name="resume_final_v3.pdf",
            source_path="Downloads / resume_final_v3.pdf",
            dest_path="Career / Resumes / Resume_2026_Senior_AI_Engineer.pdf",
            reason="Document contains updated AI engineer resume and experience sections; routed to Career/Resumes.",
            confidence="95% confidence",
        )
        layout.addWidget(p2)

        p3 = ProposalCard(
            file_type="PNG",
            original_name="Screenshot_20260911_192234.png",
            source_path="Pictures / Screenshots / Screenshot_20260911_192234.png",
            dest_path="Development / Errors / FastAPI_CORS_Error.png",
            reason="Visual inspection identified FastAPI CORS traceback on Python 3.12; routed to Development/Errors.",
            confidence="92% confidence",
        )
        layout.addWidget(p3)

        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)
