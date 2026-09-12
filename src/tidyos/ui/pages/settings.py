"""Settings page for TidyOS configuration and managed roots."""

from __future__ import annotations

from typing import Optional, Callable
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QSlider,
    QScrollArea,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal

from tidyos.config import config
from tidyos.storage import StorageRepository, RootValidationError, ManagedRoot
from tidyos.ui.theme.tokens import COLORS, RADII, SPACING, TYPOGRAPHY
from tidyos.ui.components.badge import StatusBadge
from tidyos.logging_config import get_logger

logger = get_logger("ui.pages.settings")


class SettingsPage(QWidget):
    """Settings page allowing configuration of managed roots, exclusions, and thresholds."""

    scan_requested = Signal(object)  # Emits ManagedRoot or None (for all)
    roots_changed = Signal()  # Emitted when roots are added or removed

    def __init__(
        self,
        repository: Optional[StorageRepository] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.repository = repository or StorageRepository(config.database_path)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(24)

        # Header
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        title = QLabel("Settings")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {COLORS.text_primary};")
        header_box.addWidget(title)

        subtitle = QLabel("Manage approved filesystem intake roots, safety thresholds, and indexing scope.")
        subtitle.setStyleSheet(f"font-size: 13px; color: {COLORS.text_secondary};")
        header_box.addWidget(subtitle)
        layout.addLayout(header_box)

        # Scan status banner
        self.status_banner = QLabel("")
        self.status_banner.setStyleSheet(
            f"""
            QLabel {{
                background-color: {COLORS.surface_raised};
                color: {COLORS.text_primary};
                border: 1px solid {COLORS.border_subtle};
                border-radius: {RADII.md}px;
                padding: 8px 14px;
                font-size: 12px;
            }}
            """
        )
        self.status_banner.setVisible(False)
        layout.addWidget(self.status_banner)

        # Section 1: Managed Roots
        s1_box = QVBoxLayout()
        s1_box.setSpacing(10)

        s1_header = QHBoxLayout()
        s1_title = QLabel("Approved Intake Folders")
        s1_title.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {COLORS.text_primary};")
        s1_header.addWidget(s1_title)
        s1_header.addStretch()

        self.scan_all_btn = QPushButton("Scan All Folders")
        self.scan_all_btn.setObjectName("BtnPrimary")
        self.scan_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_all_btn.clicked.connect(self._on_scan_all)
        s1_header.addWidget(self.scan_all_btn)

        self.add_btn = QPushButton("+ Add Folder")
        self.add_btn.setObjectName("BtnSecondary")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._on_add_folder)
        s1_header.addWidget(self.add_btn)
        s1_box.addLayout(s1_header)

        self.roots_card = QFrame()
        self.roots_card.setObjectName("Card")
        self.roots_card.setStyleSheet(
            f"""
            QFrame#Card {{
                background-color: {COLORS.surface};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.lg}px;
                padding: {SPACING.md}px;
            }}
            """
        )
        self.roots_layout = QVBoxLayout(self.roots_card)
        self.roots_layout.setSpacing(10)
        s1_box.addWidget(self.roots_card)
        layout.addLayout(s1_box)

        # Section 2: Autonomous Organizer Thresholds
        s2_box = QVBoxLayout()
        s2_box.setSpacing(8)

        s2_title = QLabel("Autonomous Organizer")
        s2_title.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {COLORS.text_primary};")
        s2_box.addWidget(s2_title)

        auto_card = QFrame()
        auto_card.setObjectName("Card")
        auto_card.setStyleSheet(
            f"""
            QFrame#Card {{
                background-color: {COLORS.surface};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.lg}px;
                padding: {SPACING.lg}px;
            }}
            """
        )
        a_layout = QVBoxLayout(auto_card)
        a_layout.setSpacing(14)

        thresh_row = QHBoxLayout()
        thresh_lbl = QLabel("Minimum Confidence Threshold for Auto-Move")
        thresh_lbl.setStyleSheet(f"font-size: 13px; color: {COLORS.text_primary};")
        thresh_row.addWidget(thresh_lbl)
        thresh_row.addStretch()

        self.thresh_val = QLabel(f"{int(config.confidence_threshold * 100)}%")
        self.thresh_val.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {COLORS.text_primary};")
        thresh_row.addWidget(self.thresh_val)
        a_layout.addLayout(thresh_row)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(50, 99)
        slider.setValue(int(config.confidence_threshold * 100))
        slider.valueChanged.connect(lambda val: self.thresh_val.setText(f"{val}%"))
        a_layout.addWidget(slider)

        chk_watch = QCheckBox("Enable filesystem watcher on approved intake folders")
        chk_watch.setChecked(config.watcher_enabled)
        chk_watch.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 13px;")
        a_layout.addWidget(chk_watch)

        s2_box.addWidget(auto_card)
        layout.addLayout(s2_box)

        # Section 3: Semantic Search & Embedding Runtime
        s3_box = QVBoxLayout()
        s3_box.setSpacing(8)

        s3_title = QLabel("Search & Embedding Engine")
        s3_title.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {COLORS.text_primary};")
        s3_box.addWidget(s3_title)

        search_card = QFrame()
        search_card.setObjectName("Card")
        search_card.setStyleSheet(
            f"""
            QFrame#Card {{
                background-color: {COLORS.surface};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.lg}px;
                padding: {SPACING.lg}px;
            }}
            """
        )
        sc_layout = QVBoxLayout(search_card)
        sc_layout.setSpacing(10)

        runtime_row = QHBoxLayout()
        rt_lbl = QLabel("Embedding Runtime: ONNX Runtime (Local CPU / DirectML)")
        rt_lbl.setStyleSheet(f"font-size: 13px; color: {COLORS.text_primary};")
        runtime_row.addWidget(rt_lbl)
        runtime_row.addStretch()

        rt_badge = StatusBadge("Bundled & Offline", variant="success")
        runtime_row.addWidget(rt_badge)
        sc_layout.addLayout(runtime_row)

        ai_key_row = QHBoxLayout()
        ai_lbl = QLabel("OpenAI API Key (Optional for Multimodal Vision):")
        ai_lbl.setStyleSheet(f"font-size: 13px; color: {COLORS.text_secondary};")
        ai_key_row.addWidget(ai_lbl)

        key_input = QLineEdit()
        key_input.setEchoMode(QLineEdit.EchoMode.Password)
        key_input.setPlaceholderText("sk-...")
        if config.openai_api_key:
            key_input.setText(config.openai_api_key)
        ai_key_row.addWidget(key_input, 1)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("BtnSecondary")
        ai_key_row.addWidget(save_btn)
        sc_layout.addLayout(ai_key_row)

        s3_box.addWidget(search_card)
        layout.addLayout(s3_box)

        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Initial render of managed roots from database
        self.refresh_roots_list()

    def refresh_roots_list(self):
        """Render managed roots dynamically from SQLite."""
        # Clear existing rows in layout
        while self.roots_layout.count():
            item = self.roots_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                self._clear_layout(item.layout())

        roots = self.repository.list_managed_roots()

        if not roots:
            empty_lbl = QLabel(
                "No managed intake folders configured yet.\n"
                "Click '+ Add Folder' above to select a directory (e.g. Downloads, Documents, Projects)."
            )
            empty_lbl.setStyleSheet(
                f"font-size: 13px; color: {COLORS.text_muted}; padding: 16px 8px; line-height: 1.4;"
            )
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.roots_layout.addWidget(empty_lbl)
            return

        for root in roots:
            row_frame = QFrame()
            row_frame.setStyleSheet(
                f"""
                QFrame {{
                    background-color: {COLORS.surface_raised};
                    border: 1px solid {COLORS.border_subtle};
                    border-radius: {RADII.md}px;
                    padding: 6px 12px;
                }}
                """
            )
            row = QHBoxLayout(row_frame)
            row.setContentsMargins(10, 6, 10, 6)
            row.setSpacing(12)

            p_lbl = QLabel(root.path)
            p_lbl.setStyleSheet(
                f"font-size: 12px; font-family: {TYPOGRAPHY.mono_family}; color: {COLORS.text_primary};"
            )
            row.addWidget(p_lbl, 1)

            # Mode toggle button
            mode_btn = QPushButton(f"{root.mode} Mode")
            mode_btn.setToolTip("Click to toggle AUTO / REVIEW mode")
            mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            mode_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {COLORS.surface};
                    color: {COLORS.text_primary};
                    border: 1px solid {COLORS.border};
                    border-radius: {RADII.sm}px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    border-color: {COLORS.border_focus};
                }}
                """
            )
            mode_btn.clicked.connect(lambda _, r=root: self._toggle_mode(r))
            row.addWidget(mode_btn)

            # Status badge
            status_text = "Active" if root.enabled else "Paused"
            stat_badge = StatusBadge(status_text, variant="success" if root.enabled else "neutral")
            row.addWidget(stat_badge)

            # Scan individual root button
            scan_single_btn = QPushButton("Scan")
            scan_single_btn.setObjectName("BtnSecondary")
            scan_single_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            scan_single_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {COLORS.surface};
                    color: {COLORS.text_primary};
                    border: 1px solid {COLORS.border};
                    border-radius: {RADII.sm}px;
                    padding: 3px 12px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS.surface_hover};
                }}
                """
            )
            scan_single_btn.clicked.connect(lambda _, r=root: self._on_scan_single(r))
            row.addWidget(scan_single_btn)

            # Remove button
            remove_btn = QPushButton("Remove")
            remove_btn.setObjectName("BtnSubtle")
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS.danger};
                    border: none;
                    font-size: 11px;
                    padding: 3px 8px;
                }}
                QPushButton:hover {{
                    text-decoration: underline;
                }}
                """
            )
            remove_btn.clicked.connect(lambda _, r=root: self._on_remove_folder(r))
            row.addWidget(remove_btn)

            self.roots_layout.addWidget(row_frame)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _on_add_folder(self):
        """Open folder selection dialog and add managed root."""
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Approved Folder for TidyOS",
            str(Path.home()),
        )
        if not selected_dir:
            return

        try:
            self.repository.add_managed_root(selected_dir, mode="AUTO")
            logger.info(f"User added managed root: {selected_dir}")
            self.refresh_roots_list()
            self.roots_changed.emit()
            self.show_status_message(f"Added managed folder: {selected_dir}", duration_ms=4000)
        except RootValidationError as e:
            logger.warning(f"Failed to add managed root '{selected_dir}': {e}")
            QMessageBox.warning(self, "Invalid Folder", str(e))
        except Exception as e:
            logger.error(f"Unexpected error adding root '{selected_dir}': {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Could not add folder: {e}")

    def _on_remove_folder(self, root: ManagedRoot):
        """Confirm and remove managed root."""
        reply = QMessageBox.question(
            self,
            "Remove Managed Folder",
            f"Are you sure you want to stop managing this folder?\n\n{root.path}\n\n"
            "This will remove it from TidyOS indexing. No files on disk will be deleted or altered.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes and root.id is not None:
            self.repository.remove_managed_root(root.id)
            self.refresh_roots_list()
            self.roots_changed.emit()
            self.show_status_message(f"Removed folder: {root.path}", duration_ms=4000)

    def _toggle_mode(self, root: ManagedRoot):
        """Toggle mode between AUTO and REVIEW."""
        if root.id is None:
            return
        new_mode = "REVIEW" if root.mode == "AUTO" else "AUTO"
        self.repository.update_managed_root_mode(root.id, new_mode)
        self.refresh_roots_list()
        self.show_status_message(f"Updated {root.path} mode to {new_mode}", duration_ms=3000)

    def _on_scan_all(self):
        """Trigger scan of all enabled roots."""
        self.scan_requested.emit(None)

    def _on_scan_single(self, root: ManagedRoot):
        """Trigger scan of single root."""
        self.scan_requested.emit(root)

    def show_status_message(self, message: str, duration_ms: int = 5000):
        """Display an informational status banner."""
        self.status_banner.setText(message)
        self.status_banner.setVisible(True)
