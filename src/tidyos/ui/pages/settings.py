"""Settings page for TidyOS configuration."""

from __future__ import annotations
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
)
from PySide6.QtCore import Qt
from tidyos.ui.theme.tokens import COLORS, RADII, SPACING, TYPOGRAPHY
from tidyos.ui.components.badge import StatusBadge


class SettingsPage(QWidget):
    """Settings page allowing configuration of managed roots, exclusions, and thresholds."""

    def __init__(self, parent=None):
        super().__init__(parent)

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

        # Section 1: Managed Roots
        s1_box = QVBoxLayout()
        s1_box.setSpacing(8)

        s1_header = QHBoxLayout()
        s1_title = QLabel("Approved Intake Folders")
        s1_title.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {COLORS.text_primary};")
        s1_header.addWidget(s1_title)
        s1_header.addStretch()

        add_btn = QPushButton("+ Add Folder")
        add_btn.setObjectName("BtnSecondary")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        s1_header.addWidget(add_btn)
        s1_box.addLayout(s1_header)

        roots_card = QFrame()
        roots_card.setObjectName("Card")
        roots_card.setStyleSheet(
            f"""
            QFrame#Card {{
                background-color: {COLORS.surface};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.lg}px;
                padding: {SPACING.md}px;
            }}
            """
        )
        r_layout = QVBoxLayout(roots_card)
        r_layout.setSpacing(8)

        folders = [
            ("C:\\Users\\User\\Downloads", "Auto Mode", "Active Watching"),
            ("C:\\Users\\User\\Desktop", "Auto Mode", "Active Watching"),
            ("C:\\Users\\User\\Documents", "Review Mode", "Index & Review Only"),
        ]

        for path, mode, status in folders:
            row = QHBoxLayout()
            row.setSpacing(12)

            p_lbl = QLabel(path)
            p_lbl.setStyleSheet(
                f"font-size: 12px; font-family: {TYPOGRAPHY.mono_family}; color: {COLORS.text_primary};"
            )
            row.addWidget(p_lbl, 1)

            mode_badge = StatusBadge(mode, variant="neutral")
            row.addWidget(mode_badge)

            stat_badge = StatusBadge(status, variant="success" if "Active" in status else "neutral")
            row.addWidget(stat_badge)

            remove_btn = QPushButton("Remove")
            remove_btn.setObjectName("BtnSubtle")
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            row.addWidget(remove_btn)

            r_layout.addLayout(row)

        s1_box.addWidget(roots_card)
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

        self.thresh_val = QLabel("85%")
        self.thresh_val.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {COLORS.text_primary};")
        thresh_row.addWidget(self.thresh_val)
        a_layout.addLayout(thresh_row)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(50, 99)
        slider.setValue(85)
        slider.valueChanged.connect(lambda val: self.thresh_val.setText(f"{val}%"))
        a_layout.addWidget(slider)

        chk_watch = QCheckBox("Enable filesystem watcher on approved intake folders")
        chk_watch.setChecked(True)
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
