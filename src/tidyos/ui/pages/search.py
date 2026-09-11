"""Search page for TidyOS featuring the hero semantic search experience."""

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
from tidyos.ui.components.search_bar import HeroSearchBar
from tidyos.ui.components.badge import StatusBadge


class SearchResultCard(QFrame):
    """Detailed search result card displaying relevance, summary, and actions."""

    def __init__(
        self,
        file_type: str,
        filename: str,
        folder_path: str,
        match_score: str,
        summary: str,
        matched_terms: str,
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
                background-color: {COLORS.surface_raised};
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        # Header: File type badge + Filename + Match %
        top_layout = QHBoxLayout()
        type_badge = StatusBadge(file_type, variant="neutral")
        top_layout.addWidget(type_badge)

        name_lbl = QLabel(filename)
        name_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS.text_primary};")
        top_layout.addWidget(name_lbl)

        top_layout.addStretch()

        score_badge = StatusBadge(match_score, variant="success")
        top_layout.addWidget(score_badge)
        layout.addLayout(top_layout)

        # Folder path
        path_lbl = QLabel(f"📂 {folder_path}")
        path_lbl.setStyleSheet(
            f"font-size: 12px; font-family: {TYPOGRAPHY.mono_family}; color: {COLORS.text_secondary};"
        )
        layout.addWidget(path_lbl)

        # Snippet / summary
        summary_lbl = QLabel(summary)
        summary_lbl.setWordWrap(True)
        summary_lbl.setStyleSheet(f"font-size: 13px; color: {COLORS.text_primary};")
        layout.addWidget(summary_lbl)

        # Footer: match explanation + action buttons
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 4, 0, 0)

        match_lbl = QLabel(f"Matched: {matched_terms}")
        match_lbl.setStyleSheet(f"font-size: 11px; color: {COLORS.text_muted};")
        footer_layout.addWidget(match_lbl)

        footer_layout.addStretch()

        open_btn = QPushButton("Open")
        open_btn.setObjectName("BtnPrimary")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        footer_layout.addWidget(open_btn)

        show_btn = QPushButton("Show in Folder")
        show_btn.setObjectName("BtnSecondary")
        show_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        footer_layout.addWidget(show_btn)

        layout.addLayout(footer_layout)


class SearchPage(QWidget):
    """Hero search screen allowing natural language semantic file retrieval."""

    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(24)

        # Hero header
        hero_header = QVBoxLayout()
        hero_header.setSpacing(6)

        title = QLabel("Find anything.")
        title.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {COLORS.text_primary};")
        hero_header.addWidget(title)

        subtitle = QLabel("Search by what you remember: meaning, content, context, or visual description.")
        subtitle.setStyleSheet(f"font-size: 14px; color: {COLORS.text_secondary};")
        hero_header.addWidget(subtitle)

        layout.addLayout(hero_header)

        # Dominant Hero Search Bar
        self.search_bar = HeroSearchBar(
            placeholder='Try: "the PDF about the agent hackathon I downloaded yesterday"...'
        )
        self.search_bar.search_submitted.connect(self._on_search)
        layout.addWidget(self.search_bar)

        # Prompt suggestions
        suggest_box = QHBoxLayout()
        suggest_box.setSpacing(8)

        try_lbl = QLabel("Try:")
        try_lbl.setStyleSheet(f"font-size: 12px; color: {COLORS.text_muted};")
        suggest_box.addWidget(try_lbl)

        suggestions = [
            "the PDF about the agent hackathon",
            "my latest AI resume",
            "the screenshot with the FastAPI error",
            "Vercel invoice from last month",
        ]

        for s in suggestions:
            btn = QPushButton(f'"{s}"')
            btn.setObjectName("BtnSubtle")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {COLORS.surface_raised};
                    color: {COLORS.text_secondary};
                    border: 1px solid {COLORS.border};
                    border-radius: {RADII.md}px;
                    padding: 4px 10px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    color: {COLORS.text_primary};
                    border-color: {COLORS.border_focus};
                }}
                """
            )
            btn.clicked.connect(lambda checked=False, query=s: self._fill_and_search(query))
            suggest_box.addWidget(btn)

        suggest_box.addStretch()
        layout.addLayout(suggest_box)

        # Results header
        results_header = QHBoxLayout()
        self.results_title = QLabel("Example Results (Indexed Local Files)")
        self.results_title.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {COLORS.text_primary};")
        results_header.addWidget(self.results_title)
        results_header.addStretch()
        layout.addLayout(results_header)

        # Results Cards
        result1 = SearchResultCard(
            file_type="PDF",
            filename="AI_Tinkerers_Agents_Everywhere_Handbook.pdf",
            folder_path="Projects / Hackathons / AI Tinkerers",
            match_score="94% match",
            summary="Autonomous agent hackathon handbook covering rules, judging criteria, local agent requirements, and timeline.",
            matched_terms="agent hackathon · PDF · downloaded yesterday",
        )
        layout.addWidget(result1)

        result2 = SearchResultCard(
            file_type="PNG",
            filename="FastAPI_CORS_Error.png",
            folder_path="Development / Errors / Backend",
            match_score="91% match",
            summary="Screenshot of VS Code editor displaying FastAPI CORSMiddleware configuration error with origin wildcard.",
            matched_terms="FastAPI · CORS error · screenshot · VS Code",
        )
        layout.addWidget(result2)

        result3 = SearchResultCard(
            file_type="PDF",
            filename="Vercel_Invoice_Sep_2026.pdf",
            folder_path="Finance / Software / Vercel",
            match_score="89% match",
            summary="Monthly subscription invoice for Vercel Pro hosting plan covering September 2026 usage.",
            matched_terms="Vercel · invoice · subscription · last month",
        )
        layout.addWidget(result3)

        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _fill_and_search(self, query: str):
        self.search_bar.set_text(query)
        self._on_search(query)

    def _on_search(self, query: str):
        self.results_title.setText(f'Results for "{query}"')
