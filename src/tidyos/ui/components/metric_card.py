"""Metric card component for TidyOS dashboard."""

from __future__ import annotations
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from tidyos.ui.theme.tokens import COLORS, RADII, SPACING


class MetricCard(QFrame):
    """Clean metric card widget for summary counts."""

    def __init__(
        self,
        value: str,
        label: str,
        hint: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
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
                background-color: {COLORS.surface_raised};
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(4)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            f"font-size: 26px; font-weight: 700; color: {COLORS.text_primary};"
        )
        layout.addWidget(self.value_label)

        self.title_label = QLabel(label)
        self.title_label.setStyleSheet(
            f"font-size: 13px; font-weight: 500; color: {COLORS.text_secondary};"
        )
        layout.addWidget(self.title_label)

        if hint:
            self.hint_label = QLabel(hint)
            self.hint_label.setStyleSheet(
                f"font-size: 11px; color: {COLORS.text_muted};"
            )
            layout.addWidget(self.hint_label)

    def set_value(self, value: str):
        self.value_label.setText(value)
