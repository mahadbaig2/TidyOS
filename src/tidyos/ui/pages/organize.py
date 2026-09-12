"""Organize cleanup plan page for TidyOS."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Callable
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QScrollArea,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QThreadPool

from tidyos.storage.models import ReviewQueueItem
from tidyos.storage.repository import StorageRepository
from tidyos.services.mutation_service import MutationService
from tidyos.workers.organizer_worker import OrganizerWorker
from tidyos.ui.theme.tokens import COLORS, RADII, SPACING, TYPOGRAPHY
from tidyos.ui.components.badge import StatusBadge
from tidyos.logging_config import get_logger

logger = get_logger("ui.pages.organize")


class OrganizePage(QWidget):
    """Organize screen displaying cleanup plans, organization status, and batch triggers."""

    navigate_requested = Signal(str)  # Emits target page id (e.g. "review")

    def __init__(
        self,
        repository: Optional[StorageRepository] = None,
        mutation_service: Optional[MutationService] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.repository = repository
        self.mutation_service = mutation_service
        self.active_worker: Optional[OrganizerWorker] = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self.layout = QVBoxLayout(container)
        self.layout.setContentsMargins(36, 32, 36, 32)
        self.layout.setSpacing(20)

        # Page Header
        top_bar = QHBoxLayout()
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        title = QLabel("Organize")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {COLORS.text_primary};")
        header_box.addWidget(title)

        self.subtitle = QLabel("Autonomous organization plans adhering to existing folder structures and safety policies.")
        self.subtitle.setStyleSheet(f"font-size: 13px; color: {COLORS.text_secondary};")
        header_box.addWidget(self.subtitle)
        top_bar.addLayout(header_box)

        top_bar.addStretch()

        self.scan_btn = QPushButton("Scan & Propose Organization")
        self.scan_btn.setObjectName("BtnPrimary")
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.setStyleSheet(
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
        self.scan_btn.clicked.connect(self._on_scan_clicked)
        top_bar.addWidget(self.scan_btn)

        self.layout.addLayout(top_bar)

        # Status banner
        self.status_banner = QLabel("")
        self.status_banner.setStyleSheet(
            f"""
            background-color: {COLORS.surface_raised};
            color: {COLORS.text_primary};
            border: 1px solid {COLORS.border_subtle};
            border-radius: {RADII.md}px;
            padding: 8px 14px;
            font-size: 12px;
            """
        )
        self.status_banner.setVisible(False)
        self.layout.addWidget(self.status_banner)

        # Overview Stats Card
        self.stats_card = QFrame()
        self.stats_card.setObjectName("Card")
        self.stats_card.setStyleSheet(
            f"""
            QFrame#Card {{
                background-color: {COLORS.surface};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.lg}px;
                padding: {SPACING.lg}px;
            }}
            """
        )
        s_layout = QHBoxLayout(self.stats_card)
        s_layout.setSpacing(24)

        self.stat_files = QLabel("0 Indexed Files")
        self.stat_files.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS.text_primary};")
        s_layout.addWidget(self.stat_files)

        self.stat_protected = QLabel("0 Protected Projects")
        self.stat_protected.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS.protected};")
        s_layout.addWidget(self.stat_protected)

        self.stat_pending = QLabel("0 Pending Review")
        self.stat_pending.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS.warning};")
        s_layout.addWidget(self.stat_pending)

        s_layout.addStretch()

        review_nav_btn = QPushButton("Open Review Queue →")
        review_nav_btn.setObjectName("BtnSecondary")
        review_nav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        review_nav_btn.clicked.connect(lambda: self.navigate_requested.emit("review"))
        s_layout.addWidget(review_nav_btn)

        self.layout.addWidget(self.stats_card)

        # Section Header
        sec_lbl = QLabel("Active Proposals Awaiting Approval")
        sec_lbl.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {COLORS.text_primary}; margin-top: 10px;")
        self.layout.addWidget(sec_lbl)

        # Proposals List Container
        self.proposals_box = QVBoxLayout()
        self.proposals_box.setSpacing(12)
        self.layout.addLayout(self.proposals_box)

        self.layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Initial render
        self.refresh_page()

    def refresh_page(self):
        """Update statistics and active proposals."""
        if not self.repository:
            return

        # 1. Update stats
        try:
            stats = self.repository.get_statistics()
            self.stat_files.setText(f"{stats.get('total_files', 0)} Indexed Files")
            self.stat_protected.setText(f"{stats.get('total_protected', 0)} Protected Projects")
        except Exception:
            pass

        pending_items = self.repository.list_review_items(status="PENDING")
        self.stat_pending.setText(f"{len(pending_items)} Pending Review")
        self.subtitle.setText(
            f"TidyOS has {len(pending_items)} proposals ready for approval in your approved intake folders."
        )

        # 2. Render proposal cards
        while self.proposals_box.count():
            child = self.proposals_box.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not pending_items:
            empty_card = QFrame()
            empty_card.setStyleSheet(
                f"""
                background-color: {COLORS.surface};
                border: 1px dashed {COLORS.border};
                border-radius: {RADII.lg}px;
                padding: 24px 16px;
                """
            )
            e_layout = QVBoxLayout(empty_card)
            e_lbl = QLabel("No pending proposals. Click 'Scan & Propose Organization' or drop files into watched folders.")
            e_lbl.setStyleSheet(f"font-size: 13px; color: {COLORS.text_muted};")
            e_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            e_layout.addWidget(e_lbl)
            self.proposals_box.addWidget(empty_card)
            return

        for item in pending_items[:10]:  # Show top 10
            card = QFrame()
            card.setStyleSheet(
                f"""
                QFrame {{
                    background-color: {COLORS.surface};
                    border: 1px solid {COLORS.border};
                    border-radius: {RADII.lg}px;
                    padding: {SPACING.md}px;
                }}
                """
            )
            c_layout = QVBoxLayout(card)
            c_layout.setSpacing(8)

            row = QHBoxLayout()
            ext = Path(item.suggested_filename).suffix.upper().lstrip(".") or "FILE"
            row.addWidget(StatusBadge(ext, variant="neutral"))

            title_lbl = QLabel(f"{item.current_filename} → {item.suggested_filename}")
            title_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {COLORS.text_primary};")
            row.addWidget(title_lbl, 1)

            conf_pct = int(item.confidence * 100) if item.confidence <= 1.0 else int(item.confidence)
            row.addWidget(StatusBadge(f"{conf_pct}%", variant="success" if conf_pct >= 85 else "warning"))
            c_layout.addLayout(row)

            dest_lbl = QLabel(f"Destination: {item.suggested_destination}")
            dest_lbl.setStyleSheet(f"font-size: 12px; font-family: {TYPOGRAPHY.mono_family}; color: {COLORS.text_secondary};")
            c_layout.addWidget(dest_lbl)

            if item.reason:
                r_lbl = QLabel(f'Rationale: "{item.reason}"')
                r_lbl.setStyleSheet(f"font-size: 11px; color: {COLORS.text_muted}; font-style: italic;")
                c_layout.addWidget(r_lbl)

            self.proposals_box.addWidget(card)

    def _on_scan_clicked(self):
        """Trigger background organization scan."""
        if not self.repository:
            return

        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning & Evaluating...")
        self.status_banner.setText("Evaluating files against semantic understanding and existing folder structures...")
        self.status_banner.setVisible(True)

        worker = OrganizerWorker(repository=self.repository)
        worker.signals.completed.connect(self._on_scan_completed)
        self.active_worker = worker
        QThreadPool.globalInstance().start(worker)

    def _on_scan_completed(self, queued_or_applied: int, total: int, duration_s: float):
        """Handle organization scan completion."""
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan & Propose Organization")
        self.status_banner.setText(f"✔ Completed evaluation of {total} files in {duration_s:.1f}s. {queued_or_applied} new proposals generated.")
        self.refresh_page()
