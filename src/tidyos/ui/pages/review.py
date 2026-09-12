"""Review queue page for proposals requiring user confirmation."""

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
    QLineEdit,
)
from PySide6.QtCore import Qt, Signal

from tidyos.storage.models import ReviewQueueItem
from tidyos.storage.repository import StorageRepository
from tidyos.services.mutation_service import MutationService
from tidyos.agents.organizer import OrganizationProposal
from tidyos.ui.theme.tokens import COLORS, RADII, SPACING, TYPOGRAPHY
from tidyos.ui.components.badge import StatusBadge
from tidyos.logging_config import get_logger

logger = get_logger("ui.pages.review")


class ReviewProposalCard(QFrame):
    """Card for an organization proposal requiring user confirmation."""

    def __init__(
        self,
        item: ReviewQueueItem,
        on_approve: Callable[[ReviewQueueItem, str], None],
        on_reject: Callable[[ReviewQueueItem], None],
        parent=None,
    ):
        super().__init__(parent)
        self.item = item
        self.on_approve = on_approve
        self.on_reject = on_reject

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

        # Header: Type badge, filename, confidence badge
        ext = Path(item.suggested_filename).suffix.upper().lstrip(".") or "FILE"
        header = QHBoxLayout()
        header.addWidget(StatusBadge(ext, variant="neutral"))

        name_lbl = QLabel(item.current_filename or Path(item.source_path).name)
        name_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS.text_primary};")
        header.addWidget(name_lbl)

        header.addStretch()

        conf_pct = int(item.confidence * 100) if item.confidence <= 1.0 else int(item.confidence)
        conf_variant = "success" if conf_pct >= 85 else "warning"
        header.addWidget(StatusBadge(f"{conf_pct}% confidence", variant=conf_variant))
        layout.addLayout(header)

        # Before -> After path transformation box
        path_box = QFrame()
        path_box.setStyleSheet(
            f"""
            background-color: {COLORS.surface_raised};
            border: 1px solid {COLORS.border_subtle};
            border-radius: {RADII.md}px;
            padding: 10px 14px;
            """
        )
        p_layout = QVBoxLayout(path_box)
        p_layout.setContentsMargins(8, 6, 8, 6)
        p_layout.setSpacing(6)

        src_lbl = QLabel(f"Original:   {item.source_path}")
        src_lbl.setStyleSheet(
            f"font-size: 12px; font-family: {TYPOGRAPHY.mono_family}; color: {COLORS.text_muted};"
        )
        p_layout.addWidget(src_lbl)

        target_full = str(Path(item.suggested_destination) / item.suggested_filename)
        dst_lbl = QLabel(f"Proposed:   {target_full}")
        dst_lbl.setStyleSheet(
            f"font-size: 12px; font-family: {TYPOGRAPHY.mono_family}; color: {COLORS.text_primary}; font-weight: 600;"
        )
        p_layout.addWidget(dst_lbl)

        layout.addWidget(path_box)

        # Editable destination field
        edit_row = QHBoxLayout()
        edit_row.setSpacing(8)
        edit_lbl = QLabel("Move to:")
        edit_lbl.setStyleSheet(f"font-size: 12px; color: {COLORS.text_muted}; min-width: 56px;")
        edit_row.addWidget(edit_lbl)
        self.dest_edit = QLineEdit()
        self.dest_edit.setText(target_full)
        self.dest_edit.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {COLORS.surface_raised};
                color: {COLORS.text_primary};
                border: 1px solid {COLORS.border_subtle};
                border-radius: {RADII.sm}px;
                padding: 5px 10px;
                font-family: {TYPOGRAPHY.mono_family};
                font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {COLORS.border_focus}; }}
            """
        )
        edit_row.addWidget(self.dest_edit, 1)
        layout.addLayout(edit_row)

        # Rationale
        if item.reason:
            reason_lbl = QLabel(f'Rationale: "{item.reason}"')
            reason_lbl.setStyleSheet(f"font-size: 12px; color: {COLORS.text_secondary}; font-style: italic;")
            layout.addWidget(reason_lbl)

        # Action Buttons Row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        reject_btn = QPushButton("Reject")
        reject_btn.setObjectName("BtnSubtle")
        reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reject_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS.text_muted};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.md}px;
                padding: 6px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: {COLORS.danger};
                border-color: {COLORS.danger_border};
            }}
            """
        )
        reject_btn.clicked.connect(lambda: self.on_reject(self.item))
        btn_layout.addWidget(reject_btn)

        approve_btn = QPushButton("Approve Move")
        approve_btn.setObjectName("BtnPrimary")
        approve_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        approve_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLORS.text_primary};
                color: {COLORS.app_bg};
                border: none;
                border-radius: {RADII.md}px;
                padding: 7px 18px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #E4E4E7;
            }}
            """
        )
        approve_btn.clicked.connect(lambda: self.on_approve(self.item, self.dest_edit.text().strip()))
        btn_layout.addWidget(approve_btn)

        layout.addLayout(btn_layout)


class ReviewPage(QWidget):
    """Review screen holding proposals and low-confidence decisions awaiting human confirmation."""

    proposal_applied = Signal()

    def __init__(
        self,
        repository: Optional[StorageRepository] = None,
        mutation_service: Optional[MutationService] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.repository = repository
        self.mutation_service = mutation_service

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self.layout = QVBoxLayout(container)
        self.layout.setContentsMargins(36, 32, 36, 32)
        self.layout.setSpacing(20)

        # Header
        top_layout = QHBoxLayout()
        header_box = QVBoxLayout()
        header_box.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title = QLabel("Needs Your Attention")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {COLORS.text_primary};")
        title_row.addWidget(title)

        self.count_badge = StatusBadge("0 pending", variant="neutral")
        title_row.addWidget(self.count_badge)
        title_row.addStretch()
        header_box.addLayout(title_row)

        subtitle = QLabel(
            "TidyOS will fail closed and leave files untouched whenever confidence is below threshold or intent is ambiguous."
        )
        subtitle.setStyleSheet(f"font-size: 13px; color: {COLORS.text_secondary};")
        header_box.addWidget(subtitle)

        top_layout.addLayout(header_box)
        self.layout.addLayout(top_layout)

        # Items container layout
        self.cards_box = QVBoxLayout()
        self.cards_box.setSpacing(14)
        self.layout.addLayout(self.cards_box)

        self.layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Initial render
        self.refresh_queue()

    def refresh_queue(self):
        """Fetch and render pending review items from SQLite repository."""
        # Clear existing cards
        while self.cards_box.count():
            child = self.cards_box.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self.repository:
            return

        items = self.repository.list_review_items(status="PENDING")
        count = len(items)

        if count > 0:
            self.count_badge.setText(f"{count} pending")
            self.count_badge.set_variant("warning")
        else:
            self.count_badge.setText("0 pending")
            self.count_badge.set_variant("neutral")

        if not items:
            empty_card = QFrame()
            empty_card.setStyleSheet(
                f"""
                background-color: {COLORS.surface};
                border: 1px dashed {COLORS.border};
                border-radius: {RADII.lg}px;
                padding: 32px 16px;
                """
            )
            e_layout = QVBoxLayout(empty_card)
            e_lbl = QLabel("No items requiring review. TidyOS is organized and up to date.")
            e_lbl.setStyleSheet(f"font-size: 13px; color: {COLORS.text_muted};")
            e_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            e_layout.addWidget(e_lbl)
            self.cards_box.addWidget(empty_card)
            return

        for item in items:
            card = ReviewProposalCard(
                item=item,
                on_approve=self._on_approve_item,
                on_reject=self._on_reject_item,
            )
            self.cards_box.addWidget(card)

    def _on_approve_item(self, item: ReviewQueueItem, edited_dest: str = ""):
        """Execute approved proposal through central MutationService."""
        if not self.mutation_service:
            QMessageBox.warning(self, "Service Unavailable", "MutationService is not connected.")
            return

        # Honor the user's edited destination
        if edited_dest:
            dest_path = Path(edited_dest)
            proposed_filename = dest_path.name
            proposed_destination = str(dest_path.parent)
        else:
            proposed_filename = item.suggested_filename
            proposed_destination = item.suggested_destination

        proposal = OrganizationProposal(
            file_path=item.source_path,
            current_filename=item.current_filename or Path(item.source_path).name,
            proposed_filename=proposed_filename,
            proposed_destination=proposed_destination,
            reasoning=item.reason,
            confidence=item.confidence,
        )

        success, msg, action_id = self.mutation_service.apply_proposal(proposal, force_auto=True)
        if success:
            logger.info("User approved proposal for '%s' (action #%s)", item.source_path, action_id)
            if item.id and self.repository:
                self.repository.update_review_item_status(item.id, "APPLIED")
            self.refresh_queue()
            self.proposal_applied.emit()
        else:
            logger.warning("Failed to apply proposal for '%s': %s", item.source_path, msg)
            QMessageBox.critical(self, "Move Denied", f"Operation could not be completed:\n\n{msg}")

    def _on_reject_item(self, item: ReviewQueueItem):
        """Reject and dismiss a proposal."""
        if item.id and self.repository:
            self.repository.update_review_item_status(item.id, "REJECTED")
            logger.info("User rejected review item #%s (%s)", item.id, item.source_path)
            self.refresh_queue()
