"""Hero search bar component for TidyOS Search experience."""

from __future__ import annotations
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QLabel
from PySide6.QtCore import Qt, Signal
from tidyos.ui.theme.tokens import COLORS, RADII, SPACING


class HeroSearchBar(QFrame):
    """Prominent search bar widget with shortcut badge and instant query signals."""

    search_submitted = Signal(str)
    text_changed = Signal(str)

    def __init__(self, placeholder: str = "Find anything by meaning or content...", parent=None):
        super().__init__(parent)
        self.setObjectName("HeroCard")
        self.setStyleSheet(
            f"""
            QFrame#HeroCard {{
                background-color: {COLORS.surface};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.xl}px;
                padding: 4px 8px;
            }}
            QFrame#HeroCard:focus-within {{
                border-color: {COLORS.border_focus};
                background-color: {COLORS.surface_raised};
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(SPACING.md)

        # Search icon glyph
        self.icon_label = QLabel("🔍")
        self.icon_label.setStyleSheet(
            f"font-size: 16px; color: {COLORS.text_muted}; background: transparent;"
        )
        layout.addWidget(self.icon_label)

        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(placeholder)
        self.input_field.setStyleSheet(
            f"""
            QLineEdit {{
                background: transparent;
                border: none;
                color: {COLORS.text_primary};
                font-size: 15px;
                padding: 6px 0;
            }}
            QLineEdit:focus {{
                border: none;
                background: transparent;
            }}
            """
        )
        self.input_field.textChanged.connect(self.text_changed.emit)
        self.input_field.returnPressed.connect(self._on_return_pressed)
        layout.addWidget(self.input_field, 1)

        # Shortcut badge
        self.shortcut_label = QLabel("Ctrl+K")
        self.shortcut_label.setStyleSheet(
            f"""
            background-color: {COLORS.surface_raised};
            color: {COLORS.text_muted};
            border: 1px solid {COLORS.border};
            border-radius: {RADII.sm}px;
            padding: 3px 6px;
            font-size: 11px;
            font-weight: 600;
            """
        )
        layout.addWidget(self.shortcut_label)

    def _on_return_pressed(self):
        query = self.input_field.text().strip()
        if query:
            self.search_submitted.emit(query)

    def text(self) -> str:
        return self.input_field.text()

    def set_text(self, text: str):
        self.input_field.setText(text)

    def set_focus(self):
        self.input_field.setFocus()
