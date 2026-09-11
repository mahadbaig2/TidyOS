"""Sidebar navigation component for TidyOS UI."""

from __future__ import annotations
from typing import Callable
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QButtonGroup,
    QSpacerItem,
    QSizePolicy,
    QFrame,
)
from PySide6.QtCore import Qt, Signal
from tidyos.ui.theme.tokens import COLORS, RADII, SPACING


class NavButton(QPushButton):
    """Custom sidebar navigation button with icon and active state."""

    def __init__(self, icon_str: str, text: str, page_id: str, parent=None):
        super().__init__(f"{icon_str}   {text}", parent)
        self.page_id = page_id
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(38)
        self._update_style(False)

    def set_active(self, active: bool):
        self.setChecked(active)
        self._update_style(active)

    def _update_style(self, active: bool):
        if active:
            self.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {COLORS.surface_raised};
                    color: {COLORS.text_primary};
                    border: 1px solid {COLORS.border_subtle};
                    border-radius: {RADII.md}px;
                    padding-left: 14px;
                    text-align: left;
                    font-size: 13px;
                    font-weight: 600;
                }}
                """
            )
        else:
            self.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS.text_secondary};
                    border: none;
                    border-radius: {RADII.md}px;
                    padding-left: 14px;
                    text-align: left;
                    font-size: 13px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {COLORS.surface_hover};
                    color: {COLORS.text_primary};
                }}
                """
            )


class Sidebar(QWidget):
    """Sidebar widget with brand header, primary navigation, settings, and watch status."""

    page_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarContainer")
        self.setFixedWidth(210)
        self.setStyleSheet(
            f"""
            QWidget#SidebarContainer {{
                background-color: {COLORS.sidebar_bg};
                border-right: 1px solid {COLORS.border_subtle};
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(6)

        # Brand header
        brand_layout = QHBoxLayout()
        brand_layout.setSpacing(8)

        brand_logo = QLabel("📁")
        brand_logo.setStyleSheet("font-size: 18px; background: transparent;")
        brand_layout.addWidget(brand_logo)

        brand_title = QLabel("TidyOS")
        brand_title.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {COLORS.text_primary}; background: transparent;"
        )
        brand_layout.addWidget(brand_title)

        version_badge = QLabel("v0.1.0")
        version_badge.setStyleSheet(
            f"""
            background-color: {COLORS.surface_raised};
            color: {COLORS.text_muted};
            border-radius: {RADII.sm}px;
            padding: 1px 5px;
            font-size: 10px;
            """
        )
        brand_layout.addWidget(version_badge)
        brand_layout.addStretch()

        layout.addLayout(brand_layout)
        layout.addSpacing(18)

        # Navigation Button Group
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        self.buttons: dict[str, NavButton] = {}

        nav_items = [
            ("🏠", "Home", "home"),
            ("🔍", "Search", "search"),
            ("🗂️", "Organize", "organize"),
            ("📋", "Review", "review"),
            ("⏱️", "Activity", "activity"),
        ]

        for icon, label, page_id in nav_items:
            btn = NavButton(icon, label, page_id)
            btn.clicked.connect(lambda checked=False, pid=page_id: self._on_nav_clicked(pid))
            self.button_group.addButton(btn)
            self.buttons[page_id] = btn
            layout.addWidget(btn)

        # Vertical Spacer pushing Settings to bottom
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"border: none; border-top: 1px solid {COLORS.border_subtle}; margin: 8px 0;")
        layout.addWidget(divider)

        # Settings Nav Button
        settings_btn = NavButton("⚙️", "Settings", "settings")
        settings_btn.clicked.connect(lambda checked=False: self._on_nav_clicked("settings"))
        self.button_group.addButton(settings_btn)
        self.buttons["settings"] = settings_btn
        layout.addWidget(settings_btn)

        layout.addSpacing(10)

        # Watch Status Card
        status_frame = QFrame()
        status_frame.setStyleSheet(
            f"""
            background-color: {COLORS.surface};
            border: 1px solid {COLORS.border_subtle};
            border-radius: {RADII.md}px;
            padding: 8px 10px;
            """
        )
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(8, 6, 8, 6)
        status_layout.setSpacing(2)

        status_header = QHBoxLayout()
        status_header.setSpacing(6)

        dot_label = QLabel("●")
        dot_label.setStyleSheet(f"color: {COLORS.success}; font-size: 10px; background: transparent;")
        status_header.addWidget(dot_label)

        status_text = QLabel("Watching")
        status_text.setStyleSheet(
            f"color: {COLORS.text_primary}; font-size: 12px; font-weight: 600; background: transparent;"
        )
        status_header.addWidget(status_text)
        status_header.addStretch()

        status_layout.addLayout(status_header)

        subtext = QLabel("Downloads & Desktop")
        subtext.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 10px; background: transparent;")
        status_layout.addWidget(subtext)

        layout.addWidget(status_frame)

        # Select 'home' by default
        self.set_active_page("home")

    def _on_nav_clicked(self, page_id: str):
        for pid, btn in self.buttons.items():
            btn._update_style(pid == page_id)
        self.page_changed.emit(page_id)

    def set_active_page(self, page_id: str):
        if page_id in self.buttons:
            self.buttons[page_id].setChecked(True)
            for pid, btn in self.buttons.items():
                btn._update_style(pid == page_id)
