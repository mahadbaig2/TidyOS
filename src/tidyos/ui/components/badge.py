"""Status badge component for TidyOS UI."""

from __future__ import annotations
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from tidyos.ui.theme.tokens import COLORS, RADII


class StatusBadge(QLabel):
    """Calm status pill badge widget."""

    VARIANT_STYLES = {
        "success": (COLORS.success_bg, COLORS.success, COLORS.success_border),
        "protected": (COLORS.protected_bg, "#A5B4FC", COLORS.protected_border),
        "warning": (COLORS.warning_bg, COLORS.warning, COLORS.warning_border),
        "danger": (COLORS.danger_bg, COLORS.danger, COLORS.danger_border),
        "neutral": (COLORS.surface_raised, COLORS.text_secondary, COLORS.border),
    }

    def __init__(self, text: str, variant: str = "neutral", parent=None):
        super().__init__(text, parent)
        self.variant = variant
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(22)
        self._apply_style()

    def set_variant(self, variant: str):
        self.variant = variant
        self._apply_style()

    def _apply_style(self):
        bg, fg, border = self.VARIANT_STYLES.get(
            self.variant, self.VARIANT_STYLES["neutral"]
        )
        self.setStyleSheet(
            f"""
            background-color: {bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: {RADII.sm}px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: 600;
            """
        )
