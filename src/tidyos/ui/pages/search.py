"""Search page for TidyOS featuring the hero semantic search experience."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from tidyos.agents.search_agent import SearchAgent, SearchResult
from tidyos.config import config
from tidyos.indexing.embeddings import LocalEmbeddingEngine
from tidyos.indexing.fts import FTSIndexManager
from tidyos.logging_config import get_logger
from tidyos.retrieval.hybrid import HybridRetriever
from tidyos.safety.protection_manager import ProtectionManager
from tidyos.storage import StorageRepository
from tidyos.ui.components.badge import StatusBadge
from tidyos.ui.components.search_bar import HeroSearchBar
from tidyos.ui.theme.tokens import COLORS, RADII, SPACING, TYPOGRAPHY

logger = get_logger("ui.pages.search")


class SearchResultCard(QFrame):
    """Detailed search result card displaying relevance, summary, and actions."""

    def __init__(
        self,
        file_path: str,
        file_type: str,
        filename: str,
        folder_path: str,
        match_score: str,
        summary: str,
        matched_terms: str,
        protected: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.file_path = file_path
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

        # Header: File type badge + Filename + (Protected badge) + Match %
        top_layout = QHBoxLayout()
        type_badge = StatusBadge(file_type, variant="neutral")
        top_layout.addWidget(type_badge)

        name_lbl = QLabel(filename)
        name_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS.text_primary};")
        top_layout.addWidget(name_lbl)

        if protected:
            prot_badge = StatusBadge("🛡️ Protected project", variant="protected")
            top_layout.addWidget(prot_badge)

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
        open_btn.clicked.connect(self._open_file)
        footer_layout.addWidget(open_btn)

        show_btn = QPushButton("Show in Folder")
        show_btn.setObjectName("BtnSecondary")
        show_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        show_btn.clicked.connect(self._show_in_folder)
        footer_layout.addWidget(show_btn)

        layout.addLayout(footer_layout)

    def _open_file(self):
        """Open the target file in its Windows default application."""
        try:
            if Path(self.file_path).exists():
                os.startfile(self.file_path)
            else:
                logger.warning("File no longer exists: %s", self.file_path)
        except Exception as e:
            logger.error("Failed to open file %s: %s", self.file_path, e)

    def _show_in_folder(self):
        """Reveal file in Windows Explorer with selection."""
        try:
            p = str(Path(self.file_path).resolve())
            if Path(p).exists():
                subprocess.Popen(["explorer.exe", f"/select,{p}"])
            else:
                logger.warning("File no longer exists: %s", self.file_path)
        except Exception as e:
            logger.error("Failed to reveal file in folder %s: %s", self.file_path, e)


class SearchPage(QWidget):
    """Hero search screen allowing natural language semantic file retrieval."""

    def __init__(
        self,
        repository: Optional[StorageRepository] = None,
        search_agent: Optional[SearchAgent] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.repository = repository or StorageRepository(config.database_path)

        # Initialize search agent and retriever dependencies
        if search_agent:
            self.search_agent = search_agent
        else:
            engine = LocalEmbeddingEngine.get_instance()
            fts = FTSIndexManager(self.repository)
            prot_mgr = ProtectionManager(self.repository)
            retriever = HybridRetriever(
                repository=self.repository,
                embedding_engine=engine,
                fts_manager=fts,
                protection_manager=prot_mgr,
            )
            self.search_agent = SearchAgent(retriever=retriever)

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
        self.results_title = QLabel("Indexed Files & Semantic Results")
        self.results_title.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {COLORS.text_primary};")
        results_header.addWidget(self.results_title)
        results_header.addStretch()
        layout.addLayout(results_header)

        # Dynamic Results Cards Container
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(14)
        layout.addWidget(self.results_container)

        # Initial default demonstration results
        self._load_initial_results()

        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _load_initial_results(self):
        """Populate initial results from database or examples."""
        understandings = self.repository.list_file_understandings(limit=4)
        if understandings:
            for u in understandings:
                p = Path(u.file_path)
                conf_pct = int(u.confidence * 100)
                card = SearchResultCard(
                    file_path=u.file_path,
                    file_type=p.suffix.upper().lstrip(".") or "FILE",
                    filename=p.name,
                    folder_path=str(p.parent),
                    match_score=f"{conf_pct}% match",
                    summary=u.summary,
                    matched_terms=f"Indexed · {u.document_type.title()} · {u.analysis_source}",
                )
                self.results_layout.addWidget(card)
        else:
            result1 = SearchResultCard(
                file_path="",
                file_type="PDF",
                filename="AI_Tinkerers_Agents_Everywhere_Handbook.pdf",
                folder_path="Projects / Hackathons / AI Tinkerers",
                match_score="94% match",
                summary="Autonomous agent hackathon handbook covering rules, judging criteria, local agent requirements, and timeline.",
                matched_terms="agent hackathon · PDF · downloaded yesterday",
            )
            self.results_layout.addWidget(result1)

    def _fill_and_search(self, query: str):
        self.search_bar.set_text(query)
        self._on_search(query)

    def _on_search(self, query: str):
        """Handle search execution and render live results."""
        clean_q = (query or "").strip()
        if not clean_q:
            return

        self.results_title.setText(f'Searching for "{clean_q}"...')

        # Clear existing cards
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        try:
            results: List[SearchResult] = self.search_agent.search(clean_q, limit=15)

            if not results:
                empty_card = QFrame()
                empty_card.setObjectName("Card")
                empty_card.setStyleSheet(
                    f"""
                    QFrame#Card {{
                        background-color: {COLORS.surface};
                        border: 1px dashed {COLORS.border};
                        border-radius: {RADII.lg}px;
                        padding: {SPACING.xl * 2}px;
                    }}
                    """
                )
                e_layout = QVBoxLayout(empty_card)
                e_layout.setSpacing(12)
                e_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

                e_icon = QLabel("🔍")
                e_icon.setStyleSheet("font-size: 36px;")
                e_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
                e_layout.addWidget(e_icon)

                e_title = QLabel("No matching files found")
                e_title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {COLORS.text_primary};")
                e_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
                e_layout.addWidget(e_title)

                e_desc = QLabel(
                    f'We searched your indexed files for "<b>{clean_q}</b>", but couldn\'t find any files matching your description.<br>'
                    f'This file may not exist on your computer, or it may be located in a folder that hasn\'t been added to TidyOS yet.'
                )
                e_desc.setTextFormat(Qt.TextFormat.RichText)
                e_desc.setStyleSheet(f"font-size: 13px; color: {COLORS.text_secondary}; line-height: 1.5;")
                e_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
                e_layout.addWidget(e_desc)

                tips_box = QFrame()
                tips_box.setStyleSheet(f"background-color: {COLORS.surface_raised}; border: 1px solid {COLORS.border}; border-radius: {RADII.md}px; padding: 12px 16px; margin-top: 10px;")
                tb_layout = QVBoxLayout(tips_box)
                tb_layout.setSpacing(6)

                tip_hdr = QLabel("💡 Suggestions:")
                tip_hdr.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {COLORS.text_primary};")
                tb_layout.addWidget(tip_hdr)

                tip1 = QLabel("• Check <b>Settings</b> to ensure the folder containing your file is added and scanned.")
                tip1.setStyleSheet(f"font-size: 12px; color: {COLORS.text_muted};")
                tb_layout.addWidget(tip1)

                tip2 = QLabel("• Try searching with broader keywords or removing specific file extensions.")
                tip2.setStyleSheet(f"font-size: 12px; color: {COLORS.text_muted};")
                tb_layout.addWidget(tip2)

                e_layout.addWidget(tips_box)

                self.results_layout.addWidget(empty_card)
                self.results_title.setText(f'0 matching files for "{clean_q}"')
                return

            self.results_title.setText(f'Found {len(results)} matching file(s) for "{clean_q}"')

            for r in results:
                p = Path(r.file_path)
                score_pct = int(min(1.0, max(0.1, r.score)) * 100)
                reasons_str = " · ".join(r.match_reasons) if r.match_reasons else "Relevance match"

                card = SearchResultCard(
                    file_path=r.file_path,
                    file_type=p.suffix.upper().lstrip(".") or r.document_type.upper(),
                    filename=r.filename,
                    folder_path=r.folder_path,
                    match_score=f"{score_pct}% match",
                    summary=r.summary,
                    matched_terms=reasons_str,
                    protected=r.protected,
                )
                self.results_layout.addWidget(card)

        except Exception as e:
            logger.error("Error running search query '%s': %s", clean_q, e, exc_info=True)
            self.results_title.setText(f'Error executing search for "{clean_q}"')
