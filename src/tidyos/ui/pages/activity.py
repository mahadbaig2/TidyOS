"""Activity audit ledger and history page with real Undo capabilities."""

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
from PySide6.QtCore import Qt, Signal

from tidyos.storage.models import ActionRecord
from tidyos.storage.repository import StorageRepository
from tidyos.services.mutation_service import MutationService
from tidyos.ui.theme.tokens import COLORS, RADII, SPACING, TYPOGRAPHY
from tidyos.ui.components.badge import StatusBadge
from tidyos.logging_config import get_logger

logger = get_logger("ui.pages.activity")


class ActivityEntryCard(QFrame):
    """Chronological activity ledger entry with explanation and Undo action."""

    def __init__(
        self,
        action: ActionRecord,
        on_undo: Optional[Callable[[ActionRecord], None]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.action = action
        self.on_undo = on_undo

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

        # Header: Time + Action Badge + Filename + Status + Undo Button
        header = QHBoxLayout()
        header.setSpacing(10)

        # Parse timestamp
        time_str = action.executed_at or action.created_at
        if "T" in time_str:
            time_part = time_str.split("T")[1][:5]
        else:
            time_part = time_str[:16]

        time_lbl = QLabel(time_part)
        time_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {COLORS.text_muted};")
        header.addWidget(time_lbl)

        # Badge variant based on status
        if action.status == "APPLIED":
            variant = "success"
            badge_text = f"✓ {action.action_type}"
        elif action.status == "UNDONE":
            variant = "neutral"
            badge_text = "↩ Undone"
        else:
            variant = "warning"
            badge_text = action.status

        badge = StatusBadge(badge_text, variant=variant)
        header.addWidget(badge)

        target_name = Path(action.dest_path).name
        name_lbl = QLabel(target_name)
        name_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS.text_primary};")
        header.addWidget(name_lbl)

        header.addStretch()

        if action.confidence is not None:
            conf_pct = int(action.confidence * 100) if action.confidence <= 1.0 else int(action.confidence)
            conf_lbl = QLabel(f"{conf_pct}% confidence")
            conf_lbl.setStyleSheet(f"font-size: 12px; color: {COLORS.text_secondary};")
            header.addWidget(conf_lbl)

        # Undo Button (enabled only for APPLIED actions)
        if action.status == "APPLIED" and self.on_undo:
            self.undo_btn = QPushButton("Undo")
            self.undo_btn.setObjectName("BtnSecondary")
            self.undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.undo_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {COLORS.surface_raised};
                    color: {COLORS.text_primary};
                    border: 1px solid {COLORS.border};
                    border-radius: {RADII.md}px;
                    padding: 4px 14px;
                    font-size: 12px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    border-color: {COLORS.border_focus};
                    background-color: {COLORS.surface_active};
                }}
                """
            )
            self.undo_btn.clicked.connect(lambda: self.on_undo(self.action))
            header.addWidget(self.undo_btn)

        layout.addLayout(header)

        # Path change details
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
        p_layout.setContentsMargins(6, 4, 6, 4)
        p_layout.setSpacing(4)

        src_lbl = QLabel(f"From:  {action.source_path}")
        src_lbl.setStyleSheet(
            f"font-size: 12px; font-family: {TYPOGRAPHY.mono_family}; color: {COLORS.text_muted};"
        )
        p_layout.addWidget(src_lbl)

        dst_lbl = QLabel(f"To:    {action.dest_path}")
        dst_lbl.setStyleSheet(
            f"font-size: 12px; font-family: {TYPOGRAPHY.mono_family}; color: {COLORS.text_primary}; font-weight: 600;"
        )
        p_layout.addWidget(dst_lbl)

        layout.addWidget(path_box)

        # Rationale
        if action.agent_rationale:
            why_box = QHBoxLayout()
            why_box.setSpacing(6)
            why_tag = QLabel("Why?")
            why_tag.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {COLORS.text_muted};")
            why_box.addWidget(why_tag)

            why_text = QLabel(f'"{action.agent_rationale}"')
            why_text.setStyleSheet(f"font-size: 12px; color: {COLORS.text_secondary}; font-style: italic;")
            why_box.addWidget(why_text, 1)
            layout.addLayout(why_box)


class ActivityPage(QWidget):
    """Activity ledger screen providing transparency and reversible action history."""

    action_undone = Signal()

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
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        title = QLabel("Activity Ledger")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {COLORS.text_primary};")
        header_box.addWidget(title)

        subtitle = QLabel("Full audit trail of all file movements, renames, and reversible actions.")
        subtitle.setStyleSheet(f"font-size: 13px; color: {COLORS.text_secondary};")
        header_box.addWidget(subtitle)
        self.layout.addLayout(header_box)

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

        # Entries container
        self.entries_box = QVBoxLayout()
        self.entries_box.setSpacing(12)
        self.layout.addLayout(self.entries_box)

        self.layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Initial render
        self.refresh_ledger()

    def refresh_ledger(self):
        """Fetch and display real actions from SQLite repository."""
        while self.entries_box.count():
            child = self.entries_box.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self.repository:
            return

        actions = self.repository.list_actions(limit=50)

        if not actions:
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
            e_lbl = QLabel("No filesystem actions recorded yet.")
            e_lbl.setStyleSheet(f"font-size: 13px; color: {COLORS.text_muted};")
            e_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            e_layout.addWidget(e_lbl)
            self.entries_box.addWidget(empty_card)
            return

        for action in actions:
            card = ActivityEntryCard(
                action=action,
                on_undo=self._on_undo_action,
            )
            self.entries_box.addWidget(card)

    def _on_undo_action(self, action: ActionRecord):
        """Handle user clicking Undo on an action card."""
        if not self.mutation_service or not action.id:
            QMessageBox.warning(self, "Unavailable", "MutationService is not connected.")
            return

        success, msg = self.mutation_service.undo_action(action.id)
        if success:
            logger.info("Successfully executed Undo for action #%s", action.id)
            self.status_banner.setText(f"✔ {msg}")
            self.status_banner.setStyleSheet(
                f"background-color: {COLORS.surface_raised}; color: {COLORS.success}; border: 1px solid {COLORS.success_border}; border-radius: {RADII.md}px; padding: 8px 14px; font-size: 12px; font-weight: 600;"
            )
            self.status_banner.setVisible(True)
            self.refresh_ledger()
            self.action_undone.emit()
        else:
            logger.warning("Failed to undo action #%s: %s", action.id, msg)
            QMessageBox.critical(self, "Undo Failed", f"Could not undo action:\n\n{msg}")
