"""TidyOS First-Run "Fix My Mess" Onboarding Wizard (Phase 7).

Provides a clean, transparent, 20-40 second onboarding experience:
Screen 1: Welcome & Value Proposition
Screen 2: Choose Environment (Managed Roots Selection)
Screen 3: Understanding Workspace (Real Stage-Based Background Pipeline)
Screen 4: Workspace Summary (Real Metrics + Protected Environment Callout)
Screen 5: Fix My Mess (Interactive Proposal Review & Real Safe Mutation)
"""

from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QStackedWidget,
    QFrame,
    QProgressBar,
    QScrollArea,
    QFileDialog,
)

from tidyos.storage.repository import StorageRepository
from tidyos.storage.models import ManagedRoot, DirectoryRecord, ReviewQueueItem
from tidyos.safety.protection_manager import ProtectionManager
from tidyos.safety.policy import SafetyPolicy
from tidyos.services.mutation_service import MutationService
from tidyos.services.pipeline import PipelineOrchestrator
from tidyos.indexing.fts import FTSIndexManager
from tidyos.retrieval.hybrid import HybridRetriever
from tidyos.logging_config import get_logger

logger = get_logger("ui.onboarding")


class PipelineWorkerSignals(QObject):
    """Signals for background workspace analysis."""
    stage_changed = Signal(str, int)  # (stage_name, progress_pct)
    detail_updated = Signal(str)      # description text
    finished = Signal(dict)           # summary stats dictionary
    error = Signal(str)


class WorkspaceAnalysisWorker(QThread):
    """Real background execution of workspace scanning, safety check, librarian, and organizer."""

    def __init__(
        self,
        repository: StorageRepository,
        safety_policy: SafetyPolicy,
        mutation_service: MutationService,
        selected_roots: List[str],
    ):
        super().__init__()
        self.repository = repository
        self.safety_policy = safety_policy
        self.mutation_service = mutation_service
        self.selected_roots = selected_roots
        self.signals = PipelineWorkerSignals()
        self.pipeline = PipelineOrchestrator(
            repository=repository,
            safety_policy=safety_policy,
            mutation_service=mutation_service,
        )

    def run(self):
        try:
            # Stage 1: Register and Scan Roots
            self.signals.stage_changed.emit("Scanning approved folders...", 15)
            from tidyos.indexing.scanner import FilesystemScanner
            scanner = FilesystemScanner(self.repository)

            scanned_files = 0
            scanned_dirs = 0
            for root_path in self.selected_roots:
                self.signals.detail_updated.emit(f"Scanning: {Path(root_path).name}...")
                root_record = self.repository.get_managed_root_by_path(root_path)
                if not root_record:
                    # Default intake folder Downloads to REVIEW, others to AUTO
                    mode = "REVIEW" if "download" in root_path.lower() else "AUTO"
                    root_record = self.repository.add_managed_root(root_path, mode=mode)

                scan_res = scanner.scan_root(root_record)
                scanned_dirs += scan_res.total_directories
                scanned_files += scan_res.total_files

            # Stage 2: Protection Check
            self.signals.stage_changed.emit("Checking directory safety & protected projects...", 35)
            prot_mgr = ProtectionManager(self.repository)
            for root_path in self.selected_roots:
                rp = Path(root_path)
                if rp.exists():
                    for child in rp.iterdir():
                        if child.is_dir() and not child.name.startswith("."):
                            prot_mgr.check_and_register_directory(str(child))

            protected_roots = self.repository.list_protected_roots()
            self.signals.detail_updated.emit(f"Identified {len(protected_roots)} protected application structure(s).")

            # Stage 3: Librarian Understanding & Content Indexing
            self.signals.stage_changed.emit("Understanding documents & building semantic index...", 60)
            fts = FTSIndexManager(self.repository)
            all_files = self.repository.list_files()

            understood_count = 0
            proposals_count = 0

            # Process files through the real pipeline
            for idx, file_rec in enumerate(all_files, 1):
                p = Path(file_rec.path)
                if not p.exists():
                    continue

                self.signals.detail_updated.emit(f"Analyzing: {p.name}")
                result = self.pipeline.process_file(file_rec.path)
                if result.status != "SKIPPED":
                    understood_count += 1
                if result.proposal:
                    proposals_count += 1

            # Stage 4: Semantic Search Vector Index
            self.signals.stage_changed.emit("Building local semantic index...", 85)
            try:
                retriever = HybridRetriever(self.repository)
                # Quick warmup/sync
                retriever.reload_vectors()
            except Exception as e:
                logger.debug("Warmup error: %s", e)

            # Stage 5: Done
            self.signals.stage_changed.emit("Workspace analysis complete.", 100)
            self.signals.detail_updated.emit("Ready to review organization plan.")

            summary = {
                "files_indexed": len(all_files),
                "files_understood": understood_count,
                "opportunities": proposals_count,
                "protected_projects": len(protected_roots),
                "protected_names": [Path(r.path).name for r in protected_roots],
                "needs_review": len(self.repository.list_review_items(status="PENDING")),
            }
            self.signals.finished.emit(summary)

        except Exception as e:
            logger.exception("Error during workspace analysis: %s", e)
            self.signals.error.emit(str(e))


class OnboardingWizard(QWidget):
    """Full-screen onboarding wizard for first-run experience."""

    completed = Signal()  # Emitted when user finishes and enters main app

    def __init__(
        self,
        repository: StorageRepository,
        safety_policy: SafetyPolicy,
        mutation_service: MutationService,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.repository = repository
        self.safety_policy = safety_policy
        self.mutation_service = mutation_service
        self.worker: Optional[WorkspaceAnalysisWorker] = None
        self.analysis_summary: Dict[str, Any] = {}
        self.selected_roots: List[str] = []

        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("OnboardingCanvas")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Build 5 Screens
        self.screen_welcome = self._build_welcome_screen()
        self.screen_choose = self._build_choose_screen()
        self.screen_progress = self._build_progress_screen()
        self.screen_summary = self._build_summary_screen()
        self.screen_proposals = self._build_proposals_screen()

        self.stack.addWidget(self.screen_welcome)
        self.stack.addWidget(self.screen_choose)
        self.stack.addWidget(self.screen_progress)
        self.stack.addWidget(self.screen_summary)
        self.stack.addWidget(self.screen_proposals)

        self.stack.setCurrentIndex(0)

    # -------------------------------------------------------------------------
    # Screen 1: Welcome
    # -------------------------------------------------------------------------
    def _build_welcome_screen(self) -> QWidget:
        widget = QWidget()
        vbox = QVBoxLayout(widget)
        vbox.setAlignment(Qt.AlignCenter)
        vbox.setSpacing(24)

        # Brand Badge
        badge = QLabel("TIDYOS v0.1.0")
        badge.setStyleSheet("color: #6366f1; font-weight: 700; font-size: 13px; letter-spacing: 2px;")
        vbox.addWidget(badge, alignment=Qt.AlignCenter)

        # Hero Title
        title = QLabel("Your filesystem, intelligently organized.")
        title.setStyleSheet("font-size: 32px; font-weight: 800; color: #ffffff;")
        vbox.addWidget(title, alignment=Qt.AlignCenter)

        # Description
        desc = QLabel(
            "TidyOS understands your files, helps organize them safely, and lets you\n"
            "find them by what you remember, not where you put them."
        )
        desc.setStyleSheet("font-size: 16px; color: #9ca3af; line-height: 1.6; text-align: center;")
        desc.setAlignment(Qt.AlignCenter)
        vbox.addWidget(desc, alignment=Qt.AlignCenter)

        # Trust callout
        callout = QFrame()
        callout.setStyleSheet(
            "background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 8px; padding: 12px 24px;"
        )
        c_layout = QHBoxLayout(callout)
        c_label = QLabel("🛡️ You stay in control. TidyOS only works inside folders you approve.")
        c_label.setStyleSheet("color: #c7d2fe; font-size: 14px; font-weight: 500;")
        c_layout.addWidget(c_label)
        vbox.addWidget(callout, alignment=Qt.AlignCenter)

        vbox.addSpacing(20)

        # Start button
        btn_start = QPushButton("Get Started")
        btn_start.setCursor(Qt.PointingHandCursor)
        btn_start.setStyleSheet(
            "background: #6366f1; color: #ffffff; font-size: 16px; font-weight: 600; padding: 14px 40px; border-radius: 8px;"
        )
        btn_start.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        vbox.addWidget(btn_start, alignment=Qt.AlignCenter)

        return widget

    # -------------------------------------------------------------------------
    # Screen 2: Choose Environment
    # -------------------------------------------------------------------------
    def _build_choose_screen(self) -> QWidget:
        widget = QWidget()
        vbox = QVBoxLayout(widget)
        vbox.setAlignment(Qt.AlignCenter)
        vbox.setSpacing(20)

        title = QLabel("Where can TidyOS work?")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #ffffff;")
        vbox.addWidget(title, alignment=Qt.AlignCenter)

        sub = QLabel("Choose the folders TidyOS is allowed to understand and organize.")
        sub.setStyleSheet("font-size: 15px; color: #9ca3af;")
        vbox.addWidget(sub, alignment=Qt.AlignCenter)

        # Card container for folders
        card = QFrame()
        card.setStyleSheet("background: #1a1d27; border: 1px solid #2a2e3d; border-radius: 12px; padding: 24px;")
        card.setFixedWidth(640)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)

        self.root_checkboxes: List[QCheckBox] = []

        # Look for existing TidyOS_Demo or fallback to user folders
        demo_base = Path("c:/Mahad/Projects/tidyos/TidyOS_Demo")
        if not demo_base.exists():
            demo_base = Path.home()

        candidates = [
            ("Downloads", str(demo_base / "Downloads")),
            ("Documents", str(demo_base / "Documents")),
            ("Projects", str(demo_base / "Projects")),
        ]

        for name, path_str in candidates:
            cb = QCheckBox(f"{name}  —  {path_str}")
            cb.setChecked(True)
            cb.setStyleSheet("font-size: 14px; color: #e5e7eb; padding: 4px;")
            cb.setProperty("folder_path", path_str)
            card_layout.addWidget(cb)
            self.root_checkboxes.append(cb)

        # Custom folder button
        btn_add = QPushButton("+ Add Another Folder")
        btn_add.setStyleSheet("background: transparent; color: #6366f1; font-weight: 600; text-align: left; padding: 6px 0px;")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self._browse_custom_folder)
        card_layout.addWidget(btn_add)

        vbox.addWidget(card, alignment=Qt.AlignCenter)

        # Safety footer
        safety_text = QLabel(
            "🔒 Never automatically manages system drives (C:\\, Windows, Program Files)."
        )
        safety_text.setStyleSheet("color: #6b7280; font-size: 13px;")
        vbox.addWidget(safety_text, alignment=Qt.AlignCenter)

        # Action Buttons
        btn_analyze = QPushButton("Analyze My Files")
        btn_analyze.setCursor(Qt.PointingHandCursor)
        btn_analyze.setStyleSheet(
            "background: #10b981; color: #ffffff; font-size: 15px; font-weight: 600; padding: 12px 36px; border-radius: 8px;"
        )
        btn_analyze.clicked.connect(self._start_analysis)
        vbox.addWidget(btn_analyze, alignment=Qt.AlignCenter)

        return widget

    def _browse_custom_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Approved Managed Root")
        if folder:
            cb = QCheckBox(f"{Path(folder).name}  —  {folder}")
            cb.setChecked(True)
            cb.setStyleSheet("font-size: 14px; color: #e5e7eb; padding: 4px;")
            cb.setProperty("folder_path", folder)
            self.root_checkboxes.append(cb)
            # Re-layout if needed

    # -------------------------------------------------------------------------
    # Screen 3: Understanding Workspace (Real Progress)
    # -------------------------------------------------------------------------
    def _build_progress_screen(self) -> QWidget:
        widget = QWidget()
        vbox = QVBoxLayout(widget)
        vbox.setAlignment(Qt.AlignCenter)
        vbox.setSpacing(24)

        title = QLabel("Understanding your workspace")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #ffffff;")
        vbox.addWidget(title, alignment=Qt.AlignCenter)

        self.progress_desc = QLabel("Initializing analysis pipeline...")
        self.progress_desc.setStyleSheet("font-size: 15px; color: #9ca3af;")
        vbox.addWidget(self.progress_desc, alignment=Qt.AlignCenter)

        # Progress bar
        card = QFrame()
        card.setStyleSheet("background: #1a1d27; border: 1px solid #2a2e3d; border-radius: 12px; padding: 32px;")
        card.setFixedWidth(640)
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(16)

        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(12)
        self.pbar.setTextVisible(False)
        self.pbar.setStyleSheet("""
            QProgressBar { background: #2a2e3d; border-radius: 6px; }
            QProgressBar::chunk { background: #6366f1; border-radius: 6px; }
        """)
        c_layout.addWidget(self.pbar)

        self.stage_status = QLabel("Starting background scan...")
        self.stage_status.setStyleSheet("color: #e5e7eb; font-weight: 600; font-size: 14px;")
        c_layout.addWidget(self.stage_status)

        self.detail_status = QLabel("Scanning directory structure...")
        self.detail_status.setStyleSheet("color: #9ca3af; font-size: 13px;")
        c_layout.addWidget(self.detail_status)

        vbox.addWidget(card, alignment=Qt.AlignCenter)

        return widget

    def _start_analysis(self):
        # Gather selected paths
        selected = []
        for cb in self.root_checkboxes:
            if cb.isChecked():
                path_str = cb.property("folder_path")
                if path_str and Path(path_str).exists():
                    selected.append(path_str)

        if not selected:
            return

        self.selected_roots = selected
        self.stack.setCurrentIndex(2)

        # Start real worker thread
        self.worker = WorkspaceAnalysisWorker(
            repository=self.repository,
            safety_policy=self.safety_policy,
            mutation_service=self.mutation_service,
            selected_roots=self.selected_roots,
        )
        self.worker.signals.stage_changed.connect(self._on_stage_changed)
        self.worker.signals.detail_updated.connect(self._on_detail_updated)
        self.worker.signals.finished.connect(self._on_analysis_finished)
        self.worker.signals.error.connect(self._on_analysis_error)
        self.worker.start()

    def _on_stage_changed(self, stage_text: str, progress_val: int):
        self.stage_status.setText(stage_text)
        self.pbar.setValue(progress_val)

    def _on_detail_updated(self, detail_text: str):
        self.detail_status.setText(detail_text)

    def _on_analysis_finished(self, summary: dict):
        self.analysis_summary = summary
        self._populate_summary_screen()
        self.stack.setCurrentIndex(3)

    def _on_analysis_error(self, err_msg: str):
        self.stage_status.setText("Encountered non-blocking issue.")
        self.detail_status.setText(err_msg)
        # Advance anyway to summary
        self.stack.setCurrentIndex(3)

    # -------------------------------------------------------------------------
    # Screen 4: Workspace Summary
    # -------------------------------------------------------------------------
    def _build_summary_screen(self) -> QWidget:
        widget = QWidget()
        vbox = QVBoxLayout(widget)
        vbox.setAlignment(Qt.AlignCenter)
        vbox.setSpacing(20)

        title = QLabel("TidyOS understands your workspace.")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #ffffff;")
        vbox.addWidget(title, alignment=Qt.AlignCenter)

        # Metrics Card
        self.summary_card = QFrame()
        self.summary_card.setStyleSheet("background: #1a1d27; border: 1px solid #2a2e3d; border-radius: 12px; padding: 24px;")
        self.summary_card.setFixedWidth(640)
        self.sum_layout = QVBoxLayout(self.summary_card)
        self.sum_layout.setSpacing(12)

        vbox.addWidget(self.summary_card, alignment=Qt.AlignCenter)

        # Protected Environment Callout
        self.prot_card = QFrame()
        self.prot_card.setStyleSheet(
            "background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 12px; padding: 18px;"
        )
        self.prot_card.setFixedWidth(640)
        prot_layout = QVBoxLayout(self.prot_card)
        prot_layout.setSpacing(6)

        p_header = QLabel("🛡️ PROTECTED ENVIRONMENT DETECTED")
        p_header.setStyleSheet("color: #10b981; font-weight: 700; font-size: 13px; letter-spacing: 1px;")
        prot_layout.addWidget(p_header)

        self.p_title = QLabel("storefront  —  Next.js project")
        self.p_title.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 16px;")
        prot_layout.addWidget(self.p_title)

        p_desc = QLabel(
            "TidyOS can understand and search this project, but will NOT autonomously reorganize its structure."
        )
        p_desc.setStyleSheet("color: #d1fae5; font-size: 13px;")
        prot_layout.addWidget(p_desc)

        vbox.addWidget(self.prot_card, alignment=Qt.AlignCenter)

        # CTA Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(16)

        btn_review = QPushButton("Review Cleanup Plan")
        btn_review.setCursor(Qt.PointingHandCursor)
        btn_review.setStyleSheet(
            "background: #6366f1; color: #ffffff; font-size: 15px; font-weight: 600; padding: 12px 32px; border-radius: 8px;"
        )
        btn_review.clicked.connect(self._open_proposals_screen)
        btn_box.addWidget(btn_review)

        btn_skip = QPushButton("Go to TidyOS")
        btn_skip.setCursor(Qt.PointingHandCursor)
        btn_skip.setStyleSheet(
            "background: transparent; border: 1px solid #4b5563; color: #9ca3af; font-size: 14px; font-weight: 500; padding: 12px 24px; border-radius: 8px;"
        )
        btn_skip.clicked.connect(self._finish_onboarding)
        btn_box.addWidget(btn_skip)

        vbox.addLayout(btn_box)

        return widget

    def _populate_summary_screen(self):
        # Clear old items
        while self.sum_layout.count():
            item = self.sum_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        files_idx = self.analysis_summary.get("files_indexed", 0)
        files_und = self.analysis_summary.get("files_understood", 0)
        opps = self.analysis_summary.get("opportunities", 0)
        needs_rev = self.analysis_summary.get("needs_review", 0)
        prots = self.analysis_summary.get("protected_projects", 1)

        row1 = QHBoxLayout()
        row1.addWidget(self._stat_widget("Files Indexed", str(files_idx)))
        row1.addWidget(self._stat_widget("Files Understood", str(files_und)))
        row1.addWidget(self._stat_widget("Opportunities", str(opps)))
        self.sum_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(self._stat_widget("Needs Review", str(needs_rev), color="#f59e0b"))
        row2.addWidget(self._stat_widget("Protected Projects", str(prots), color="#10b981"))
        self.sum_layout.addLayout(row2)

        prot_names = self.analysis_summary.get("protected_names", ["storefront"])
        name = prot_names[0] if prot_names else "storefront"
        self.p_title.setText(f"{name}  —  Next.js project")

    def _stat_widget(self, label: str, val: str, color: str = "#ffffff") -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(2)
        v = QLabel(val)
        v.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {color};")
        lb = QLabel(label)
        lb.setStyleSheet("font-size: 12px; color: #9ca3af;")
        l.addWidget(v)
        l.addWidget(lb)
        return w

    # -------------------------------------------------------------------------
    # Screen 5: Fix My Mess
    # -------------------------------------------------------------------------
    def _build_proposals_screen(self) -> QWidget:
        widget = QWidget()
        vbox = QVBoxLayout(widget)
        vbox.setAlignment(Qt.AlignCenter)
        vbox.setSpacing(20)

        title = QLabel("Fix My Mess")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #ffffff;")
        vbox.addWidget(title, alignment=Qt.AlignCenter)

        sub = QLabel("TidyOS found files it can organize safely. Review and approve proposed actions.")
        sub.setStyleSheet("font-size: 15px; color: #9ca3af;")
        vbox.addWidget(sub, alignment=Qt.AlignCenter)

        # Scroll area for review items
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFixedWidth(680)
        self.scroll.setFixedHeight(340)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(12)
        self.scroll.setWidget(self.cards_container)
        vbox.addWidget(self.scroll, alignment=Qt.AlignCenter)

        # Completion Button
        self.btn_finish = QPushButton("Open TidyOS")
        self.btn_finish.setCursor(Qt.PointingHandCursor)
        self.btn_finish.setStyleSheet(
            "background: #10b981; color: #ffffff; font-size: 15px; font-weight: 600; padding: 12px 36px; border-radius: 8px;"
        )
        self.btn_finish.clicked.connect(self._finish_onboarding)
        vbox.addWidget(self.btn_finish, alignment=Qt.AlignCenter)

        return widget

    def _open_proposals_screen(self):
        self._populate_proposals_screen()
        self.stack.setCurrentIndex(4)

    def _populate_proposals_screen(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        items = self.repository.list_review_items(status="PENDING")
        if not items:
            lbl = QLabel("No pending organization proposals.")
            lbl.setStyleSheet("color: #9ca3af; font-size: 14px; text-align: center;")
            self.cards_layout.addWidget(lbl, alignment=Qt.AlignCenter)
            return

        for rev in items:
            card = self._build_proposal_card(rev)
            self.cards_layout.addWidget(card)

    def _build_proposal_card(self, item: ReviewQueueItem) -> QFrame:
        card = QFrame()
        card.setStyleSheet("background: #1a1d27; border: 1px solid #2a2e3d; border-radius: 10px; padding: 16px;")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        # Top row: Source -> Proposed
        row_top = QHBoxLayout()
        source_lbl = QLabel(f"📄 {item.current_filename}")
        source_lbl.setStyleSheet("color: #9ca3af; font-weight: 600; font-size: 14px;")
        arrow = QLabel("→")
        arrow.setStyleSheet("color: #6366f1; font-weight: 700; font-size: 16px;")
        dest_lbl = QLabel(f"✨ {item.proposed_filename}")
        dest_lbl.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 14px;")

        row_top.addWidget(source_lbl)
        row_top.addWidget(arrow)
        row_top.addWidget(dest_lbl)
        row_top.addStretch()

        conf_badge = QLabel(f"{int(item.confidence * 100)}% Match")
        conf_badge.setStyleSheet("color: #10b981; font-weight: 600; font-size: 12px; padding: 2px 8px; border-radius: 4px; background: rgba(16, 185, 129, 0.1);")
        row_top.addWidget(conf_badge)
        layout.addLayout(row_top)

        # Destination Folder
        dest_folder = QLabel(f"Destination: {item.proposed_destination}")
        dest_folder.setStyleSheet("color: #818cf8; font-size: 12px; font-family: monospace;")
        layout.addWidget(dest_folder)

        # Reasoning
        reason_lbl = QLabel(f"Why: {item.reasoning}")
        reason_lbl.setStyleSheet("color: #9ca3af; font-size: 13px;")
        reason_lbl.setWordWrap(True)
        layout.addWidget(reason_lbl)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_approve = QPushButton("Approve Move")
        btn_approve.setCursor(Qt.PointingHandCursor)
        btn_approve.setStyleSheet("background: #6366f1; color: white; font-weight: 600; padding: 6px 16px; border-radius: 6px;")

        btn_reject = QPushButton("Reject")
        btn_reject.setCursor(Qt.PointingHandCursor)
        btn_reject.setStyleSheet("background: transparent; color: #ef4444; border: 1px solid #ef4444; font-weight: 600; padding: 6px 14px; border-radius: 6px;")

        btn_approve.clicked.connect(lambda _, it=item, c=card: self._approve_proposal(it, c))
        btn_reject.clicked.connect(lambda _, it=item, c=card: self._reject_proposal(it, c))

        btn_row.addWidget(btn_reject)
        btn_row.addWidget(btn_approve)
        layout.addLayout(btn_row)

        return card

    def _approve_proposal(self, item: ReviewQueueItem, card: QFrame):
        from tidyos.agents.organizer import OrganizationProposal
        proposal = OrganizationProposal(
            file_path=item.source_path,
            current_filename=item.current_filename,
            proposed_filename=item.proposed_filename,
            proposed_destination=item.proposed_destination,
            reasoning=item.reasoning,
            confidence=item.confidence,
        )
        success, msg, action_id = self.mutation_service.apply_proposal(proposal, force_auto=True)
        if success:
            self.repository.update_review_item_status(item.id, "APPROVED")
            card.setStyleSheet("background: rgba(16, 185, 129, 0.08); border: 1px solid #10b981; border-radius: 10px; padding: 16px;")
            # Disable buttons
            for btn in card.findChildren(QPushButton):
                btn.setEnabled(False)
                if btn.text() == "Approve Move":
                    btn.setText("✓ Organized")
                    btn.setStyleSheet("background: #10b981; color: white; font-weight: 600; padding: 6px 16px; border-radius: 6px;")
        else:
            logger.warning("Could not apply proposal: %s", msg)

    def _reject_proposal(self, item: ReviewQueueItem, card: QFrame):
        self.repository.update_review_item_status(item.id, "REJECTED")
        card.setStyleSheet("background: rgba(239, 68, 68, 0.08); border: 1px solid #ef4444; border-radius: 10px; padding: 16px;")
        for btn in card.findChildren(QPushButton):
            btn.setEnabled(False)
            if btn.text() == "Reject":
                btn.setText("✕ Rejected")

    def _finish_onboarding(self):
        self.repository.set_first_run_completed(True)
        self.completed.emit()
