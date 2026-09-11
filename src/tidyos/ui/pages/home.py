"""Home dashboard page for TidyOS."""

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
from tidyos.ui.components.metric_card import MetricCard
from tidyos.ui.components.badge import StatusBadge


class HomePage(QWidget):
    """Home dashboard screen establishing filesystem health, metrics, and recent activity."""

    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area for responsive dashboard
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(24)

        # Header greeting & status
        header_layout = QHBoxLayout()

        greeting_box = QVBoxLayout()
        greeting_box.setSpacing(4)

        title = QLabel("Good evening.")
        title.setObjectName("PageTitle")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {COLORS.text_primary};")
        greeting_box.addWidget(title)

        subtitle = QLabel("Your filesystem is under control.")
        subtitle.setStyleSheet(f"font-size: 14px; color: {COLORS.text_secondary};")
        greeting_box.addWidget(subtitle)

        header_layout.addLayout(greeting_box)
        header_layout.addStretch()

        # Watching badge
        watch_pill = StatusBadge("● Watching Active", variant="success")
        watch_pill.setFixedHeight(28)
        watch_pill.setStyleSheet(
            f"""
            background-color: {COLORS.success_bg};
            color: {COLORS.success};
            border: 1px solid {COLORS.success_border};
            border-radius: {RADII.full}px;
            padding: 4px 14px;
            font-size: 12px;
            font-weight: 600;
            """
        )
        header_layout.addWidget(watch_pill)
        layout.addLayout(header_layout)

        # Metric Cards Row
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(16)

        self.card_indexed = MetricCard("12,491", "Files indexed", "Across 3 approved roots")
        self.card_organized = MetricCard("128", "Organized", "Automatically or approved")
        self.card_protected = MetricCard("14", "Protected projects", "Codebases untouched")
        self.card_review = MetricCard("3", "Need review", "Awaiting confirmation")

        metrics_layout.addWidget(self.card_indexed)
        metrics_layout.addWidget(self.card_organized)
        metrics_layout.addWidget(self.card_protected)
        metrics_layout.addWidget(self.card_review)

        layout.addLayout(metrics_layout)

        # Protected Project Highlight Card (Demonstrates Safety Intelligence)
        protected_card = QFrame()
        protected_card.setObjectName("CardRaised")
        protected_card.setStyleSheet(
            f"""
            QFrame#CardRaised {{
                background-color: {COLORS.surface_raised};
                border: 1px solid {COLORS.protected_border};
                border-radius: {RADII.lg}px;
                padding: {SPACING.lg}px;
            }}
            """
        )
        p_layout = QVBoxLayout(protected_card)
        p_layout.setContentsMargins(18, 16, 18, 16)
        p_layout.setSpacing(8)

        p_header = QHBoxLayout()
        p_badge = StatusBadge("🛡️ Protected Project", variant="protected")
        p_header.addWidget(p_badge)

        p_repo_name = QLabel("mahad-ai-portfolio")
        p_repo_name.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {COLORS.text_primary};")
        p_header.addWidget(p_repo_name)

        p_type = QLabel("Next.js + Git repository")
        p_type.setStyleSheet(f"font-size: 12px; color: {COLORS.text_muted};")
        p_header.addWidget(p_type)

        p_header.addStretch()

        index_status = StatusBadge("Indexed for Search ✓", variant="neutral")
        p_header.addWidget(index_status)
        p_layout.addLayout(p_header)

        p_desc = QLabel(
            "TidyOS detected markers: package.json, next.config.ts, tsconfig.json, .git/. "
            "Internal project files are protected from automated moves and renames."
        )
        p_desc.setWordWrap(True)
        p_desc.setStyleSheet(f"font-size: 12px; color: {COLORS.text_secondary};")
        p_layout.addWidget(p_desc)

        layout.addWidget(protected_card)

        # Recent Activity Section
        section_header = QHBoxLayout()
        activity_title = QLabel("Recent Activity")
        activity_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {COLORS.text_primary};")
        section_header.addWidget(activity_title)
        section_header.addStretch()
        layout.addLayout(section_header)

        # Activity list container
        activity_card = QFrame()
        activity_card.setObjectName("Card")
        activity_card.setStyleSheet(
            f"""
            QFrame#Card {{
                background-color: {COLORS.surface};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.lg}px;
            }}
            """
        )
        act_layout = QVBoxLayout(activity_card)
        act_layout.setContentsMargins(16, 12, 16, 12)
        act_layout.setSpacing(12)

        # Activity item 1
        item1 = self._create_activity_row(
            icon="✓",
            filename="Vercel_Invoice_Sep_2026.pdf",
            path_change="Downloads → Finance / Software / Vercel",
            time_ago="Organized 2m ago",
            confidence="97% confidence",
        )
        act_layout.addLayout(item1)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet(f"border-top: 1px solid {COLORS.border_subtle};")
        act_layout.addWidget(sep1)

        # Activity item 2
        item2 = self._create_activity_row(
            icon="✓",
            filename="FastAPI_CORS_Error.png",
            path_change="Screenshots → Development / Errors",
            time_ago="Organized 14m ago",
            confidence="92% confidence",
        )
        act_layout.addLayout(item2)

        layout.addWidget(activity_card)
        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_activity_row(
        self, icon: str, filename: str, path_change: str, time_ago: str, confidence: str
    ) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"color: {COLORS.success}; font-weight: 700; font-size: 14px;")
        row.addWidget(icon_lbl)

        info_box = QVBoxLayout()
        info_box.setSpacing(2)

        file_lbl = QLabel(filename)
        file_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {COLORS.text_primary};")
        info_box.addWidget(file_lbl)

        path_lbl = QLabel(path_change)
        path_lbl.setStyleSheet(
            f"font-size: 11px; font-family: {TYPOGRAPHY.mono_family}; color: {COLORS.text_secondary};"
        )
        info_box.addWidget(path_lbl)
        row.addLayout(info_box, 1)

        meta_box = QVBoxLayout()
        meta_box.setSpacing(2)
        meta_box.setAlignment(Qt.AlignmentFlag.AlignRight)

        time_lbl = QLabel(time_ago)
        time_lbl.setStyleSheet(f"font-size: 11px; color: {COLORS.text_muted};")
        meta_box.addWidget(time_lbl)

        conf_lbl = QLabel(confidence)
        conf_lbl.setStyleSheet(f"font-size: 11px; color: {COLORS.text_secondary};")
        meta_box.addWidget(conf_lbl)
        row.addLayout(meta_box)

        why_btn = QPushButton("Why?")
        why_btn.setObjectName("BtnSubtle")
        why_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row.addWidget(why_btn)

        undo_btn = QPushButton("Undo")
        undo_btn.setObjectName("BtnSecondary")
        undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row.addWidget(undo_btn)

        return row
