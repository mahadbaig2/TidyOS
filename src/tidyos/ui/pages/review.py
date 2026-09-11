"""Review queue page for ambiguous actions requiring user confirmation."""

from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QComboBox,
    QScrollArea,
)
from PySide6.QtCore import Qt
from tidyos.ui.theme.tokens import COLORS, RADII, SPACING, TYPOGRAPHY
from tidyos.ui.components.badge import StatusBadge


class ReviewItemCard(QFrame):
    """Card for an uncertain file decision allowing destination selection or dismissal."""

    def __init__(
        self,
        file_type: str,
        filename: str,
        current_path: str,
        guess_category: str,
        confidence: str,
        candidate_destinations: list[str],
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
        layout.setSpacing(12)

        # Header
        top_layout = QHBoxLayout()
        type_badge = StatusBadge(file_type, variant="neutral")
        top_layout.addWidget(type_badge)

        name_lbl = QLabel(filename)
        name_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS.text_primary};")
        top_layout.addWidget(name_lbl)

        top_layout.addStretch()

        conf_badge = StatusBadge(confidence, variant="warning")
        top_layout.addWidget(conf_badge)
        layout.addLayout(top_layout)

        # Current location
        path_lbl = QLabel(f"Current location: {current_path}")
        path_lbl.setStyleSheet(
            f"font-size: 12px; font-family: {TYPOGRAPHY.mono_family}; color: {COLORS.text_muted};"
        )
        layout.addWidget(path_lbl)

        # AI interpretation
        intent_lbl = QLabel(f"TidyOS inference: {guess_category}")
        intent_lbl.setStyleSheet(f"font-size: 13px; color: {COLORS.text_secondary};")
        layout.addWidget(intent_lbl)

        # Destination selector
        dest_layout = QHBoxLayout()
        dest_lbl = QLabel("Suggested destination:")
        dest_lbl.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {COLORS.text_secondary};")
        dest_layout.addWidget(dest_lbl)

        combo = QComboBox()
        combo.addItems(candidate_destinations)
        combo.setStyleSheet(
            f"""
            QComboBox {{
                background-color: {COLORS.surface_raised};
                color: {COLORS.text_primary};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.md}px;
                padding: 6px 12px;
                min-width: 240px;
                font-size: 12px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS.surface_raised};
                color: {COLORS.text_primary};
                selection-background-color: {COLORS.surface_active};
                border: 1px solid {COLORS.border};
            }}
            """
        )
        dest_layout.addWidget(combo)
        dest_layout.addStretch()
        layout.addLayout(dest_layout)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        approve_btn = QPushButton("Approve Move")
        approve_btn.setObjectName("BtnPrimary")
        approve_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_layout.addWidget(approve_btn)

        leave_btn = QPushButton("Leave Where It Is")
        leave_btn.setObjectName("BtnSecondary")
        leave_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_layout.addWidget(leave_btn)

        layout.addLayout(btn_layout)


class ReviewPage(QWidget):
    """Review screen holding uncertain items and low-confidence decisions."""

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
        top_layout = QHBoxLayout()

        header_box = QVBoxLayout()
        header_box.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title = QLabel("Needs Your Attention")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {COLORS.text_primary};")
        title_row.addWidget(title)

        count_badge = StatusBadge("3 pending", variant="warning")
        title_row.addWidget(count_badge)
        title_row.addStretch()

        header_box.addLayout(title_row)

        subtitle = QLabel(
            "TidyOS will fail closed and leave files untouched whenever confidence is below threshold or intent is ambiguous."
        )
        subtitle.setStyleSheet(f"font-size: 13px; color: {COLORS.text_secondary};")
        header_box.addWidget(subtitle)

        top_layout.addLayout(header_box)
        layout.addLayout(top_layout)

        # Review Cards
        r1 = ReviewItemCard(
            file_type="PDF",
            filename="report-final.pdf",
            current_path="Downloads / report-final.pdf",
            guess_category="Research document on Agentic Frameworks (confidence 72%)",
            confidence="72% confidence",
            candidate_destinations=[
                "Research / AI / LangGraph_Frameworks",
                "Documents / Work / Reports",
                "Downloads (Keep in place)",
            ],
        )
        layout.addWidget(r1)

        r2 = ReviewItemCard(
            file_type="JPG",
            filename="IMG_8829.jpg",
            current_path="Pictures / Camera / IMG_8829.jpg",
            guess_category="Possible hardware expense receipt or hardware setup photo (confidence 68%)",
            confidence="68% confidence",
            candidate_destinations=[
                "Finance / Expenses / Hardware",
                "Pictures / Hardware / Lab",
                "Pictures / Camera (Keep in place)",
            ],
        )
        layout.addWidget(r2)

        r3 = ReviewItemCard(
            file_type="DOCX",
            filename="Contract_Draft_v1.docx",
            current_path="Downloads / Contract_Draft_v1.docx",
            guess_category="Legal agreement draft or consulting proposal (confidence 74%)",
            confidence="74% confidence",
            candidate_destinations=[
                "Legal / Contracts / Consulting",
                "Work / Projects / Client_Work",
                "Downloads (Keep in place)",
            ],
        )
        layout.addWidget(r3)

        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)
