"""Design tokens for TidyOS PySide6 UI.

Defines the centralized color palette, typography hierarchy, spacing scale,
and border radii based on DESIGN.md.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ColorTokens:
    # Base Canvas
    app_bg: str = "#0B0C0E"
    sidebar_bg: str = "#101114"
    surface: str = "#15171B"
    surface_raised: str = "#1B1E23"
    surface_card: str = "#16181D"
    surface_hover: str = "#1E222A"
    surface_active: str = "#242932"

    # Borders
    border: str = "#272A31"
    border_subtle: str = "#1C1F25"
    border_focus: str = "#4B5563"

    # Typography / Foregrounds
    text_primary: str = "#F4F4F5"
    text_secondary: str = "#A1A1AA"
    text_muted: str = "#71717A"
    text_disabled: str = "#52525B"

    # Semantic Status Colors (Restrained)
    success: str = "#22C55E"
    success_bg: str = "#0F291E"
    success_border: str = "#166534"

    warning: str = "#F59E0B"
    warning_bg: str = "#2A200B"
    warning_border: str = "#854D0E"

    danger: str = "#EF4444"
    danger_bg: str = "#2D1214"
    danger_border: str = "#991B1B"

    protected: str = "#6366F1"
    protected_bg: str = "#151833"
    protected_border: str = "#3730A3"

    # Accent
    accent: str = "#F4F4F5"
    accent_subtle: str = "#3F3F46"


@dataclass(frozen=True)
class SpacingTokens:
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24
    xxl: int = 32
    xxxl: int = 48


@dataclass(frozen=True)
class RadiusTokens:
    sm: int = 4
    md: int = 6
    lg: int = 8
    xl: int = 12
    full: int = 9999


@dataclass(frozen=True)
class TypographyTokens:
    font_family: str = "Segoe UI, -apple-system, Inter, BlinkMacSystemFont, sans-serif"
    mono_family: str = "Cascadia Code, Consolas, Monaco, Courier New, monospace"

    size_display: int = 28
    size_page_title: int = 22
    size_section_title: int = 16
    size_body: int = 13
    size_caption: int = 11
    size_mono: int = 12


COLORS = ColorTokens()
SPACING = SpacingTokens()
RADII = RadiusTokens()
TYPOGRAPHY = TypographyTokens()
