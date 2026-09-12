"""Organize page for TidyOS — Scan → Summary+Actions → Done."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QScrollArea,
    QProgressBar,
    QLineEdit,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QThreadPool, QRunnable, QObject

from tidyos.storage.repository import StorageRepository
from tidyos.storage.models import ReviewQueueItem
from tidyos.services.mutation_service import MutationService
from tidyos.services.pipeline import PipelineOrchestrator, PipelineResult
from tidyos.agents.organizer import OrganizationProposal
from tidyos.ui.theme.tokens import COLORS, RADII, SPACING, TYPOGRAPHY
from tidyos.ui.components.badge import StatusBadge
from tidyos.logging_config import get_logger

logger = get_logger("ui.pages.organize")


# ---------------------------------------------------------------------------
# Background scan + propose worker
# ---------------------------------------------------------------------------

class ScanProposalSignals(QObject):
    started = Signal(int)                    # total_files
    progress = Signal(int, int, str)         # current, total, filename
    completed = Signal(list, int, float)     # proposals[], total_scanned, duration_s
    error = Signal(str)


class ScanProposalWorker(QRunnable):
    """Scans all managed files and collects proposals WITHOUT executing moves."""

    def __init__(self, pipeline: PipelineOrchestrator, repository: StorageRepository):
        super().__init__()
        self.pipeline = pipeline
        self.repository = repository
        self.signals = ScanProposalSignals()
        self.setAutoDelete(True)

    def run(self):
        start = time.time()
        try:
            files = [f for f in self.repository.list_files(limit=500) if f.is_present]
            total = len(files)
            self.signals.started.emit(total)
            proposals: List[OrganizationProposal] = []
            for idx, file_rec in enumerate(files, 1):
                self.signals.progress.emit(idx, total, Path(file_rec.path).name)
                try:
                    result: PipelineResult = self.pipeline.process_file(file_rec.path, auto_mode=False)
                    # Collect proposals for SAFE files that need moving
                    if result.proposal and result.proposal.organization_needed and not result.is_protected:
                        proposals.append(result.proposal)
                except Exception as e:
                    logger.warning("Error scanning '%s': %s", file_rec.path, e)
            self.signals.completed.emit(proposals, total, time.time() - start)
        except Exception as e:
            logger.error("Fatal scan error: %s", e, exc_info=True)
            self.signals.error.emit(str(e))


class OrganizeAllSignals(QObject):
    progress = Signal(int, int, str)           # current, total, filename
    completed = Signal(int, int, float)        # organized, total, duration_s


class OrganizeAllWorker(QRunnable):
    """Executes all proposals immediately (auto_mode=True)."""

    def __init__(self, proposals: List[OrganizationProposal], pipeline: PipelineOrchestrator):
        super().__init__()
        self.proposals = proposals
        self.pipeline = pipeline
        self.signals = OrganizeAllSignals()
        self.setAutoDelete(True)

    def run(self):
        start = time.time()
        organized = 0
        total = len(self.proposals)
        for idx, proposal in enumerate(self.proposals, 1):
            self.signals.progress.emit(idx, total, proposal.current_filename)
            try:
                result = self.pipeline.process_file(proposal.file_path, auto_mode=True)
                if result.status == "AUTO_ORGANIZED":
                    organized += 1
            except Exception as e:
                logger.warning("Failed to organize '%s': %s", proposal.file_path, e)
        self.signals.completed.emit(organized, total, time.time() - start)


# ---------------------------------------------------------------------------
# Editable proposal row for Review mode
# ---------------------------------------------------------------------------

class ProposalReviewRow(QFrame):
    """A single editable proposal row shown in Review Files mode."""

    def __init__(self, proposal: OrganizationProposal, parent=None):
        super().__init__(parent)
        self.proposal = proposal
        self._approved = True  # default: included in apply

        self.setObjectName("ProposalRow")
        self.setStyleSheet(f"""
            QFrame#ProposalRow {{
                background-color: {COLORS.surface};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.md}px;
            }}
            QFrame#ProposalRow:hover {{
                border-color: {COLORS.border_focus};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Top row: checkbox-like toggle + filename + confidence
        top = QHBoxLayout()

        self.toggle_btn = QPushButton("✓")
        self.toggle_btn.setFixedSize(28, 28)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.success};
                color: white;
                border: none;
                border-radius: 14px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {COLORS.success_border}; }}
        """)
        self.toggle_btn.clicked.connect(self._toggle)
        top.addWidget(self.toggle_btn)

        ext = Path(proposal.proposed_filename).suffix.upper().lstrip(".") or "FILE"
        top.addWidget(StatusBadge(ext, variant="neutral"))

        src_lbl = QLabel(proposal.current_filename)
        src_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {COLORS.text_primary};")
        top.addWidget(src_lbl, 1)

        conf_pct = int(proposal.confidence * 100)
        top.addWidget(StatusBadge(
            f"{conf_pct}%",
            variant="success" if conf_pct >= 70 else "warning"
        ))
        layout.addLayout(top)

        # Destination edit row
        dest_row = QHBoxLayout()
        dest_row.setSpacing(8)

        src_icon = QLabel("→")
        src_icon.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 14px; font-weight: 700;")
        dest_row.addWidget(src_icon)

        self.dest_edit = QLineEdit()
        self.dest_edit.setText(str(Path(proposal.proposed_destination) / proposal.proposed_filename))
        self.dest_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS.surface_raised};
                color: {COLORS.text_primary};
                border: 1px solid {COLORS.border_subtle};
                border-radius: {RADII.sm}px;
                padding: 5px 10px;
                font-family: {TYPOGRAPHY.mono_family};
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS.border_focus};
            }}
        """)
        dest_row.addWidget(self.dest_edit, 1)
        layout.addLayout(dest_row)

    def _toggle(self):
        self._approved = not self._approved
        if self._approved:
            self.toggle_btn.setText("✓")
            self.toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.success};
                    color: white; border: none; border-radius: 14px;
                    font-weight: 700; font-size: 13px;
                }}
            """)
            self.setStyleSheet(f"""
                QFrame#ProposalRow {{
                    background-color: {COLORS.surface};
                    border: 1px solid {COLORS.border};
                    border-radius: {RADII.md}px;
                }}
            """)
        else:
            self.toggle_btn.setText("✗")
            self.toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.surface_raised};
                    color: {COLORS.text_muted}; border: 1px solid {COLORS.border};
                    border-radius: 14px; font-weight: 700; font-size: 13px;
                }}
            """)
            self.setStyleSheet(f"""
                QFrame#ProposalRow {{
                    background-color: {COLORS.surface_raised};
                    border: 1px solid {COLORS.border_subtle};
                    border-radius: {RADII.md}px;
                    opacity: 0.6;
                }}
            """)

    def get_edited_proposal(self) -> Optional[OrganizationProposal]:
        """Return a (possibly destination-edited) proposal if approved."""
        if not self._approved:
            return None
        dest_text = self.dest_edit.text().strip()
        dest_path = Path(dest_text)
        return OrganizationProposal(
            file_path=self.proposal.file_path,
            current_filename=self.proposal.current_filename,
            proposed_filename=dest_path.name,
            proposed_destination=str(dest_path.parent),
            reasoning=self.proposal.reasoning,
            confidence=self.proposal.confidence,
        )


# ---------------------------------------------------------------------------
# Main OrganizePage
# ---------------------------------------------------------------------------

class OrganizePage(QWidget):
    """
    3-state organize flow:
      STATE_READY    → [Scan] button
      STATE_SCANNED  → Summary + [Organize All] / [Review Files]
      STATE_DONE     → Completion summary
    """

    navigate_requested = Signal(str)

    STATE_READY = "ready"
    STATE_SCANNING = "scanning"
    STATE_SCANNED = "scanned"
    STATE_RUNNING = "running"
    STATE_DONE = "done"

    def __init__(
        self,
        repository: Optional[StorageRepository] = None,
        mutation_service: Optional[MutationService] = None,
        pipeline: Optional[PipelineOrchestrator] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.repository = repository
        self.mutation_service = mutation_service
        self.pipeline = pipeline or (
            PipelineOrchestrator(repository=repository) if repository else None
        )
        self._proposals: List[OrganizationProposal] = []
        self._review_rows: List[ProposalReviewRow] = []
        self._state = self.STATE_READY

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(40, 36, 40, 36)
        self._layout.setSpacing(24)

        self._build_header()
        self._build_ready_state()
        self._build_scanning_state()
        self._build_scanned_state()
        self._build_running_state()
        self._build_done_state()

        self._layout.addStretch()
        scroll.setWidget(self._container)
        main_layout.addWidget(scroll)

        self._show_state(self.STATE_READY)

    # ------------------------------------------------------------------
    # UI construction helpers
    # ------------------------------------------------------------------

    def _build_header(self):
        hdr = QVBoxLayout()
        hdr.setSpacing(4)

        title = QLabel("Organize")
        title.setStyleSheet(f"font-size: 26px; font-weight: 700; color: {COLORS.text_primary};")
        hdr.addWidget(title)

        self._subtitle = QLabel("Scan your approved folders and let TidyOS sort everything into place.")
        self._subtitle.setStyleSheet(f"font-size: 14px; color: {COLORS.text_secondary};")
        hdr.addWidget(self._subtitle)

        self._layout.addLayout(hdr)

    def _build_ready_state(self):
        """State 0: big Scan button."""
        self._ready_frame = QFrame()
        self._ready_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.surface};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.xl}px;
            }}
        """)
        rl = QVBoxLayout(self._ready_frame)
        rl.setContentsMargins(48, 56, 48, 56)
        rl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.setSpacing(16)

        icon_lbl = QLabel("🗂")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 48px;")
        rl.addWidget(icon_lbl)

        tip = QLabel("TidyOS will scan your approved folders, understand each file,\nand show you exactly where everything should go.")
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip.setWordWrap(True)
        tip.setStyleSheet(f"font-size: 14px; color: {COLORS.text_secondary};")
        rl.addWidget(tip)

        self._scan_btn = QPushButton("  Scan my files  ")
        self._scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._scan_btn.setFixedHeight(48)
        self._scan_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.text_primary};
                color: {COLORS.app_bg};
                border: none;
                border-radius: {RADII.md}px;
                font-size: 15px;
                font-weight: 700;
                padding: 0 32px;
            }}
            QPushButton:hover {{ background-color: #E4E4E7; }}
        """)
        self._scan_btn.clicked.connect(self._start_scan)

        btn_wrapper = QHBoxLayout()
        btn_wrapper.addStretch()
        btn_wrapper.addWidget(self._scan_btn)
        btn_wrapper.addStretch()
        rl.addLayout(btn_wrapper)

        self._layout.addWidget(self._ready_frame)

    def _build_scanning_state(self):
        """State 1: scanning progress."""
        self._scanning_frame = QFrame()
        self._scanning_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.surface};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.lg}px;
            }}
        """)
        sl = QVBoxLayout(self._scanning_frame)
        sl.setContentsMargins(32, 28, 32, 28)
        sl.setSpacing(12)

        self._scan_progress_label = QLabel("Scanning files...")
        self._scan_progress_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS.text_primary};")
        sl.addWidget(self._scan_progress_label)

        self._scan_progress_bar = QProgressBar()
        self._scan_progress_bar.setFixedHeight(8)
        self._scan_progress_bar.setTextVisible(False)
        self._scan_progress_bar.setRange(0, 0)
        self._scan_progress_bar.setStyleSheet(f"""
            QProgressBar {{ background-color: {COLORS.surface_raised}; border: none; border-radius: 4px; }}
            QProgressBar::chunk {{ background-color: {COLORS.success}; border-radius: 4px; }}
        """)
        sl.addWidget(self._scan_progress_bar)

        self._scan_file_label = QLabel("")
        self._scan_file_label.setStyleSheet(f"font-size: 11px; color: {COLORS.text_muted}; font-family: {TYPOGRAPHY.mono_family};")
        sl.addWidget(self._scan_file_label)

        self._layout.addWidget(self._scanning_frame)

    def _build_scanned_state(self):
        """State 2: scan summary + action buttons + optional review table."""
        self._scanned_frame = QWidget()
        sf_layout = QVBoxLayout(self._scanned_frame)
        sf_layout.setContentsMargins(0, 0, 0, 0)
        sf_layout.setSpacing(20)

        # Summary card
        self._summary_card = QFrame()
        self._summary_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.surface};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.lg}px;
            }}
        """)
        sc_layout = QVBoxLayout(self._summary_card)
        sc_layout.setContentsMargins(28, 22, 28, 22)
        sc_layout.setSpacing(14)

        self._summary_title = QLabel("Scan complete")
        self._summary_title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {COLORS.text_primary};")
        sc_layout.addWidget(self._summary_title)

        self._summary_stats = QHBoxLayout()
        self._summary_stats.setSpacing(32)
        self._stat_total = self._make_stat("0", "files scanned")
        self._stat_to_move = self._make_stat("0", "to organize")
        self._stat_protected = self._make_stat("0", "protected (untouched)")
        for w in [self._stat_total, self._stat_to_move, self._stat_protected]:
            self._summary_stats.addLayout(w)
        self._summary_stats.addStretch()
        sc_layout.addLayout(self._summary_stats)

        sf_layout.addWidget(self._summary_card)

        # Action buttons row
        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        self._organize_all_btn = QPushButton("⚡  Organize All")
        self._organize_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._organize_all_btn.setFixedHeight(44)
        self._organize_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.text_primary};
                color: {COLORS.app_bg};
                border: none;
                border-radius: {RADII.md}px;
                font-size: 14px;
                font-weight: 700;
                padding: 0 28px;
            }}
            QPushButton:hover {{ background-color: #E4E4E7; }}
            QPushButton:disabled {{ background-color: {COLORS.border}; color: {COLORS.text_muted}; }}
        """)
        self._organize_all_btn.clicked.connect(self._start_organize_all)
        action_row.addWidget(self._organize_all_btn)

        self._review_btn = QPushButton("Review Files")
        self._review_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._review_btn.setFixedHeight(44)
        self._review_btn.setCheckable(True)
        self._review_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS.text_primary};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.md}px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 24px;
            }}
            QPushButton:hover {{ border-color: {COLORS.border_focus}; }}
            QPushButton:checked {{
                background-color: {COLORS.surface_raised};
                border-color: {COLORS.border_focus};
            }}
        """)
        self._review_btn.clicked.connect(self._toggle_review_panel)
        action_row.addWidget(self._review_btn)

        action_row.addStretch()

        self._rescan_btn = QPushButton("↺  Rescan")
        self._rescan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._rescan_btn.setFixedHeight(36)
        self._rescan_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS.text_muted};
                border: 1px solid {COLORS.border_subtle};
                border-radius: {RADII.md}px;
                font-size: 12px;
                padding: 0 14px;
            }}
            QPushButton:hover {{ color: {COLORS.text_primary}; border-color: {COLORS.border}; }}
        """)
        self._rescan_btn.clicked.connect(self._start_scan)
        action_row.addWidget(self._rescan_btn)

        sf_layout.addLayout(action_row)

        # Review panel (collapsed by default)
        self._review_panel = QWidget()
        self._review_panel.setVisible(False)
        rp_layout = QVBoxLayout(self._review_panel)
        rp_layout.setContentsMargins(0, 0, 0, 0)
        rp_layout.setSpacing(12)

        review_hdr = QHBoxLayout()
        review_hdr_lbl = QLabel("Proposed Moves — edit any destination before applying")
        review_hdr_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS.text_primary};")
        review_hdr.addWidget(review_hdr_lbl)
        review_hdr.addStretch()

        self._apply_selected_btn = QPushButton("Apply Selected")
        self._apply_selected_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_selected_btn.setFixedHeight(36)
        self._apply_selected_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.success};
                color: white;
                border: none;
                border-radius: {RADII.md}px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 18px;
            }}
            QPushButton:hover {{ background-color: {COLORS.success_border}; }}
        """)
        self._apply_selected_btn.clicked.connect(self._apply_selected)
        review_hdr.addWidget(self._apply_selected_btn)
        rp_layout.addLayout(review_hdr)

        # Rows container
        self._review_rows_container = QVBoxLayout()
        self._review_rows_container.setSpacing(8)
        rp_layout.addLayout(self._review_rows_container)

        sf_layout.addWidget(self._review_panel)
        self._layout.addWidget(self._scanned_frame)

    def _build_running_state(self):
        """State 3: running organize-all progress."""
        self._running_frame = QFrame()
        self._running_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.surface};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.lg}px;
            }}
        """)
        rl = QVBoxLayout(self._running_frame)
        rl.setContentsMargins(32, 28, 32, 28)
        rl.setSpacing(12)

        self._run_label = QLabel("Organizing files...")
        self._run_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS.text_primary};")
        rl.addWidget(self._run_label)

        self._run_bar = QProgressBar()
        self._run_bar.setFixedHeight(8)
        self._run_bar.setTextVisible(False)
        self._run_bar.setRange(0, 100)
        self._run_bar.setStyleSheet(f"""
            QProgressBar {{ background-color: {COLORS.surface_raised}; border: none; border-radius: 4px; }}
            QProgressBar::chunk {{ background-color: {COLORS.success}; border-radius: 4px; }}
        """)
        rl.addWidget(self._run_bar)

        self._run_file_label = QLabel("")
        self._run_file_label.setStyleSheet(f"font-size: 11px; color: {COLORS.text_muted}; font-family: {TYPOGRAPHY.mono_family};")
        rl.addWidget(self._run_file_label)

        self._layout.addWidget(self._running_frame)

    def _build_done_state(self):
        """State 4: done confirmation."""
        self._done_frame = QFrame()
        self._done_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.surface};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.xl}px;
            }}
        """)
        dl = QVBoxLayout(self._done_frame)
        dl.setContentsMargins(48, 48, 48, 48)
        dl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dl.setSpacing(16)

        done_icon = QLabel("✅")
        done_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        done_icon.setStyleSheet("font-size: 52px;")
        dl.addWidget(done_icon)

        self._done_title = QLabel("All done!")
        self._done_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._done_title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {COLORS.text_primary};")
        dl.addWidget(self._done_title)

        self._done_subtitle = QLabel("")
        self._done_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._done_subtitle.setWordWrap(True)
        self._done_subtitle.setStyleSheet(f"font-size: 14px; color: {COLORS.text_secondary};")
        dl.addWidget(self._done_subtitle)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        search_btn = QPushButton("Search my files →")
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setFixedHeight(42)
        search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.text_primary};
                color: {COLORS.app_bg};
                border: none;
                border-radius: {RADII.md}px;
                font-size: 14px;
                font-weight: 700;
                padding: 0 24px;
            }}
            QPushButton:hover {{ background-color: #E4E4E7; }}
        """)
        search_btn.clicked.connect(lambda: self.navigate_requested.emit("search"))
        btn_row.addWidget(search_btn)

        again_btn = QPushButton("Scan again")
        again_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        again_btn.setFixedHeight(42)
        again_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS.text_muted};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.md}px;
                font-size: 13px;
                padding: 0 18px;
            }}
            QPushButton:hover {{ color: {COLORS.text_primary}; }}
        """)
        again_btn.clicked.connect(self._start_scan)
        btn_row.addWidget(again_btn)

        btn_row.addStretch()
        dl.addLayout(btn_row)

        self._layout.addWidget(self._done_frame)

    def _make_stat(self, value: str, label: str) -> QVBoxLayout:
        l = QVBoxLayout()
        l.setSpacing(2)
        v = QLabel(value)
        v.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {COLORS.text_primary};")
        l.addWidget(v)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 12px; color: {COLORS.text_muted};")
        l.addWidget(lbl)
        # stash refs so we can update them
        l._value_lbl = v
        l._label_lbl = lbl
        return l

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _show_state(self, state: str):
        self._state = state
        self._ready_frame.setVisible(state == self.STATE_READY)
        self._scanning_frame.setVisible(state == self.STATE_SCANNING)
        self._scanned_frame.setVisible(state in (self.STATE_SCANNED,))
        self._running_frame.setVisible(state == self.STATE_RUNNING)
        self._done_frame.setVisible(state == self.STATE_DONE)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _start_scan(self):
        if not self.pipeline:
            return
        self._review_btn.setChecked(False)
        self._review_panel.setVisible(False)
        self._show_state(self.STATE_SCANNING)
        self._scan_progress_bar.setRange(0, 0)
        self._scan_progress_label.setText("Scanning files…")
        self._scan_file_label.setText("")

        worker = ScanProposalWorker(pipeline=self.pipeline, repository=self.repository)
        worker.signals.started.connect(self._on_scan_started)
        worker.signals.progress.connect(self._on_scan_progress)
        worker.signals.completed.connect(self._on_scan_completed)
        worker.signals.error.connect(lambda e: self._show_state(self.STATE_READY))
        QThreadPool.globalInstance().start(worker)

    def _on_scan_started(self, total: int):
        self._scan_progress_bar.setRange(0, max(total, 1))

    def _on_scan_progress(self, current: int, total: int, filename: str):
        self._scan_progress_label.setText(f"Scanning… {current}/{total} files")
        self._scan_file_label.setText(filename)
        self._scan_progress_bar.setValue(current)

    def _on_scan_completed(self, proposals: list, total_scanned: int, duration_s: float):
        self._proposals = proposals
        n = len(proposals)
        protected = (total_scanned - n) if total_scanned > n else 0

        # Update summary stat labels
        self._stat_total._value_lbl.setText(str(total_scanned))
        self._stat_to_move._value_lbl.setText(str(n))
        self._stat_protected._value_lbl.setText(str(protected))

        self._summary_title.setText(f"Scan complete — {total_scanned} files in {duration_s:.1f}s")

        if n == 0:
            self._organize_all_btn.setEnabled(False)
            self._review_btn.setEnabled(False)
            self._subtitle.setText("Everything is already organised. Your folders are clean!")
        else:
            self._organize_all_btn.setEnabled(True)
            self._review_btn.setEnabled(True)
            self._subtitle.setText(f"{n} file(s) can be organised automatically.")

        self._show_state(self.STATE_SCANNED)
        self._build_review_rows()

    def _toggle_review_panel(self):
        visible = self._review_btn.isChecked()
        self._review_panel.setVisible(visible)

    def _build_review_rows(self):
        """Populate the review rows from current proposals."""
        while self._review_rows_container.count():
            child = self._review_rows_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._review_rows = []

        for proposal in self._proposals:
            row = ProposalReviewRow(proposal)
            self._review_rows.append(row)
            self._review_rows_container.addWidget(row)

        if not self._proposals:
            empty = QLabel("No files to organise — everything is already in the right place.")
            empty.setStyleSheet(f"font-size: 13px; color: {COLORS.text_muted}; padding: 16px 0;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._review_rows_container.addWidget(empty)

    def _start_organize_all(self):
        if not self._proposals or not self.pipeline:
            return
        self._show_state(self.STATE_RUNNING)
        self._run_bar.setRange(0, len(self._proposals))
        self._run_bar.setValue(0)
        self._run_label.setText(f"Organizing {len(self._proposals)} files…")

        worker = OrganizeAllWorker(proposals=self._proposals, pipeline=self.pipeline)
        worker.signals.progress.connect(self._on_organize_progress)
        worker.signals.completed.connect(self._on_organize_completed)
        QThreadPool.globalInstance().start(worker)

    def _on_organize_progress(self, current: int, total: int, filename: str):
        self._run_label.setText(f"Organizing… {current}/{total}")
        self._run_file_label.setText(filename)
        self._run_bar.setValue(current)

    def _on_organize_completed(self, organized: int, total: int, duration_s: float):
        self._done_title.setText("All done!")
        self._done_subtitle.setText(
            f"Moved {organized} of {total} files in {duration_s:.1f}s.\n"
            f"Protected projects were left untouched."
        )
        self._show_state(self.STATE_DONE)

    def _apply_selected(self):
        """Apply the approved (possibly edited) proposals from the review panel."""
        if not self.pipeline:
            return

        approved = [row.get_edited_proposal() for row in self._review_rows]
        approved = [p for p in approved if p is not None]

        if not approved:
            return

        self._show_state(self.STATE_RUNNING)
        self._run_bar.setRange(0, len(approved))
        self._run_bar.setValue(0)
        self._run_label.setText(f"Applying {len(approved)} selected moves…")

        worker = OrganizeAllWorker(proposals=approved, pipeline=self.pipeline)
        worker.signals.progress.connect(self._on_organize_progress)
        worker.signals.completed.connect(self._on_organize_completed)
        QThreadPool.globalInstance().start(worker)

    def refresh_page(self):
        """Called by cross-page signals — reset to ready if currently done."""
        if self._state == self.STATE_DONE:
            self._show_state(self.STATE_READY)
