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
    QComboBox,
)
from PySide6.QtCore import Qt, Signal, QObject, QRunnable, QThreadPool

from tidyos.config import config
from tidyos.storage import StorageRepository, RootValidationError, ManagedRoot
from tidyos.ui.theme.tokens import COLORS, RADII, SPACING, TYPOGRAPHY
from tidyos.ui.components.badge import StatusBadge
from tidyos.tools.openai_client import OpenAIClient, AIProviderConfig, get_active_ai_config
from tidyos.logging_config import get_logger

logger = get_logger("ui.pages.settings")

MODEL_PRESETS = {
    "openai": [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ],
    "openrouter": [
        "openai/gpt-4o-mini",
        "anthropic/claude-3.5-sonnet",
        "meta-llama/llama-3.3-70b-instruct",
        "google/gemini-2.0-flash-001",
        "deepseek/deepseek-chat",
    ],
}


class TestConnectionSignals(QObject):
    """Signals for background AI provider connection testing."""
    finished = Signal(bool, str)


class TestConnectionWorker(QRunnable):
    """Background worker verifying provider connectivity and model reachability."""

    def __init__(self, provider: str, api_key: str, model: str):
        super().__init__()
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.signals = TestConnectionSignals()
        self.setAutoDelete(True)

    def run(self):
        try:
            base_url = "https://openrouter.ai/api/v1" if self.provider == "openrouter" else None
            client = OpenAIClient(
                api_key=self.api_key,
                model=self.model,
                provider=self.provider,
                base_url=base_url,
            )
            success, msg = client.test_connection()
            self.signals.finished.emit(success, msg)
        except Exception as e:
            self.signals.finished.emit(False, f"Connection error: {str(e)[:40]}")


class SettingsPage(QWidget):
    """Settings page allowing configuration of managed roots, exclusions, thresholds, and AI provider."""

    scan_requested = Signal(object)  # Emits ManagedRoot or None (for all)
    roots_changed = Signal()  # Emitted when roots are added or removed
    reset_demo_requested = Signal()  # Emitted when user wants to reset onboarding tour

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

        # Section 3: AI Intelligence & Provider Configuration
        s3_box = QVBoxLayout()
        s3_box.setSpacing(10)

        s3_title = QLabel("AI Provider & Intelligence Engine")
        s3_title.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {COLORS.text_primary};")
        s3_box.addWidget(s3_title)

        ai_card = QFrame()
        ai_card.setObjectName("Card")
        ai_card.setStyleSheet(
            f"""
            QFrame#Card {{
                background-color: {COLORS.surface};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.lg}px;
                padding: {SPACING.lg}px;
            }}
            """
        )
        ai_layout = QVBoxLayout(ai_card)
        ai_layout.setSpacing(14)

        # Local Runtime Status
        runtime_row = QHBoxLayout()
        rt_lbl = QLabel("Local Embedding Runtime: ONNX DirectML / CPU")
        rt_lbl.setStyleSheet(f"font-size: 13px; color: {COLORS.text_secondary};")
        runtime_row.addWidget(rt_lbl)
        runtime_row.addStretch()

        rt_badge = StatusBadge("Bundled & Offline", variant="success")
        runtime_row.addWidget(rt_badge)
        ai_layout.addLayout(runtime_row)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"background-color: {COLORS.border_subtle}; max-height: 1px;")
        ai_layout.addWidget(divider)

        # 1. AI Provider Selector
        prov_row = QHBoxLayout()
        prov_lbl = QLabel("AI Provider:")
        prov_lbl.setStyleSheet(f"font-size: 13px; font-weight: 500; color: {COLORS.text_primary};")
        prov_lbl.setFixedWidth(120)
        prov_row.addWidget(prov_lbl)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["OpenAI", "OpenRouter"])
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        prov_row.addWidget(self.provider_combo, 1)
        ai_layout.addLayout(prov_row)

        # 2. API Key
        key_row = QHBoxLayout()
        key_lbl = QLabel("API Key:")
        key_lbl.setStyleSheet(f"font-size: 13px; font-weight: 500; color: {COLORS.text_primary};")
        key_lbl.setFixedWidth(120)
        key_row.addWidget(key_lbl)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Enter API Key (sk-... or sk-or-v1-...)")
        key_row.addWidget(self.api_key_input, 1)
        ai_layout.addLayout(key_row)

        # 3. Model
        model_row = QHBoxLayout()
        model_lbl = QLabel("Model:")
        model_lbl.setStyleSheet(f"font-size: 13px; font-weight: 500; color: {COLORS.text_primary};")
        model_lbl.setFixedWidth(120)
        model_row.addWidget(model_lbl)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        model_row.addWidget(self.model_combo, 1)
        ai_layout.addLayout(model_row)

        # 4. Action Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.save_ai_btn = QPushButton("Save Settings")
        self.save_ai_btn.setObjectName("BtnPrimary")
        self.save_ai_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_ai_btn.clicked.connect(self._on_save_ai_settings)
        btn_row.addWidget(self.save_ai_btn)

        self.test_conn_btn = QPushButton("Test Connection")
        self.test_conn_btn.setObjectName("BtnSecondary")
        self.test_conn_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_conn_btn.clicked.connect(self._on_test_connection)
        btn_row.addWidget(self.test_conn_btn)

        self.test_status_lbl = QLabel("")
        self.test_status_lbl.setStyleSheet(f"font-size: 13px; font-weight: 500;")
        btn_row.addWidget(self.test_status_lbl, 1)

        ai_layout.addLayout(btn_row)

        s3_box.addWidget(ai_card)
        layout.addLayout(s3_box)

        # Section 4: Demo & Onboarding Controls
        s4_box = QVBoxLayout()
        s4_box.setSpacing(8)

        s4_title = QLabel("Demo & Onboarding")
        s4_title.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {COLORS.text_primary};")
        s4_box.addWidget(s4_title)

        demo_card = QFrame()
        demo_card.setObjectName("Card")
        demo_card.setStyleSheet(
            f"""
            QFrame#Card {{
                background-color: {COLORS.surface};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.lg}px;
                padding: {SPACING.md}px;
            }}
            """
        )
        d_layout = QHBoxLayout(demo_card)
        d_desc = QLabel("Reset the onboarding tour and re-run the workspace introduction flow.")
        d_desc.setStyleSheet(f"font-size: 13px; color: {COLORS.text_secondary};")
        d_layout.addWidget(d_desc, 1)

        self.reset_tour_btn = QPushButton("Reset Onboarding Tour")
        self.reset_tour_btn.setObjectName("BtnSecondary")
        self.reset_tour_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_tour_btn.clicked.connect(self.reset_demo_requested.emit)
        d_layout.addWidget(self.reset_tour_btn)

        s4_box.addWidget(demo_card)
        layout.addLayout(s4_box)

        # Load active provider configuration into UI
        initial_cfg = get_active_ai_config(self.repository)
        if initial_cfg.provider.lower() == "openrouter":
            self.provider_combo.setCurrentIndex(1)
        else:
            self.provider_combo.setCurrentIndex(0)
        self._load_provider_settings(initial_cfg.provider.lower())

        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Initial render of managed roots from database
        self.refresh_roots_list()

    def _on_provider_changed(self, index: int):
        """Handle user changing the AI Provider dropdown."""
        provider = "openrouter" if index == 1 else "openai"
        self._load_provider_settings(provider)

    def _load_provider_settings(self, provider: str):
        """Populate API key and model fields for selected provider from preferences/env."""
        # 1. API key
        key = self.repository.get_preference(f"{provider}_api_key")
        if key is None:
            key = config.openrouter_api_key if provider == "openrouter" else config.openai_api_key
        self.api_key_input.setText(key or "")

        # 2. Model
        saved_model = self.repository.get_preference(f"{provider}_model")
        if not saved_model:
            saved_model = config.openrouter_model if provider == "openrouter" else config.openai_model
        if not saved_model:
            saved_model = "openai/gpt-4o-mini" if provider == "openrouter" else "gpt-4o-mini"

        self.model_combo.clear()
        presets = MODEL_PRESETS.get(provider, [])
        for m in presets:
            self.model_combo.addItem(m)
        if saved_model not in presets:
            self.model_combo.insertItem(0, saved_model)
        self.model_combo.setCurrentText(saved_model)

        # 3. Reset test status
        self.test_status_lbl.setText("")

    def _on_save_ai_settings(self):
        """Persist user-configured provider, API key, and model to SQLite preferences."""
        provider = "openrouter" if self.provider_combo.currentIndex() == 1 else "openai"
        api_key = self.api_key_input.text().strip()
        model = self.model_combo.currentText().strip()

        self.repository.set_preference("ai_provider", provider)
        self.repository.set_preference(f"{provider}_api_key", api_key)
        self.repository.set_preference(f"{provider}_model", model)

        # Update in-memory configuration
        config.ai_provider = provider
        if provider == "openrouter":
            config.openrouter_api_key = api_key
            config.openrouter_model = model
        else:
            config.openai_api_key = api_key
            config.openai_model = model

        logger.info("Saved AI Provider configuration: provider=%s, model=%s", provider, model)
        self.show_status_message(f"AI settings saved for {self.provider_combo.currentText()}.", duration_ms=4000)

    def _on_test_connection(self):
        """Execute non-blocking provider connectivity and model availability check."""
        provider = "openrouter" if self.provider_combo.currentIndex() == 1 else "openai"
        api_key = self.api_key_input.text().strip()
        model = self.model_combo.currentText().strip()

        if not api_key:
            self.test_status_lbl.setStyleSheet(f"color: {COLORS.danger}; font-size: 13px; font-weight: 600;")
            self.test_status_lbl.setText("Please enter an API key")
            return

        self.test_conn_btn.setEnabled(False)
        self.test_conn_btn.setText("Testing...")
        self.test_status_lbl.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 13px;")
        self.test_status_lbl.setText("Contacting provider...")

        worker = TestConnectionWorker(provider, api_key, model)
        worker.signals.finished.connect(self._on_test_connection_finished)
        QThreadPool.globalInstance().start(worker)

    def _on_test_connection_finished(self, success: bool, message: str):
        """Handle result from background connection test."""
        self.test_conn_btn.setEnabled(True)
        self.test_conn_btn.setText("Test Connection")
        if success:
            self.test_status_lbl.setStyleSheet(f"color: {COLORS.success}; font-size: 13px; font-weight: 600;")
            self.test_status_lbl.setText(f"✔ {message}")
        else:
            self.test_status_lbl.setStyleSheet(f"color: {COLORS.danger}; font-size: 13px; font-weight: 600;")
            self.test_status_lbl.setText(f"✖ {message}")

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
