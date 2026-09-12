"""Centralized QSS stylesheet generation for TidyOS dark theme."""

from __future__ import annotations
from tidyos.ui.theme.tokens import COLORS, SPACING, RADII, TYPOGRAPHY


def get_application_stylesheet() -> str:
    """Generate the complete application QSS stylesheet."""
    return f"""
    /* Global Window & Font Defaults */
    QMainWindow, QWidget {{
        background-color: {COLORS.app_bg};
        color: {COLORS.text_primary};
        font-family: {TYPOGRAPHY.font_family};
        font-size: {TYPOGRAPHY.size_body}px;
        selection-background-color: {COLORS.surface_active};
        selection-color: {COLORS.text_primary};
    }}

    /* Sidebar Container */
    QWidget#SidebarContainer {{
        background-color: {COLORS.sidebar_bg};
        border-right: 1px solid {COLORS.border_subtle};
    }}

    /* Main Content Area */
    QWidget#MainContentArea {{
        background-color: {COLORS.app_bg};
    }}

    /* Cards & Panels */
    QFrame.Card, QFrame#Card {{
        background-color: {COLORS.surface};
        border: 1px solid {COLORS.border};
        border-radius: {RADII.lg}px;
    }}

    QFrame.CardRaised, QFrame#CardRaised {{
        background-color: {COLORS.surface_raised};
        border: 1px solid {COLORS.border};
        border-radius: {RADII.lg}px;
    }}

    QFrame.HeroCard, QFrame#HeroCard {{
        background-color: {COLORS.surface_raised};
        border: 1px solid {COLORS.border};
        border-radius: {RADII.xl}px;
    }}

    /* Navigation Item Buttons */
    QPushButton.NavItem {{
        background-color: transparent;
        color: {COLORS.text_secondary};
        border: none;
        border-radius: {RADII.md}px;
        padding: 8px 12px;
        text-align: left;
        font-size: 13px;
        font-weight: 500;
    }}

    QPushButton.NavItem:hover {{
        background-color: {COLORS.surface_hover};
        color: {COLORS.text_primary};
    }}

    QPushButton.NavItem:checked, QPushButton.NavItem[active="true"] {{
        background-color: {COLORS.surface_raised};
        color: {COLORS.text_primary};
        font-weight: 600;
        border: 1px solid {COLORS.border_subtle};
    }}

    /* Action Buttons */
    QPushButton.BtnPrimary, QPushButton#BtnPrimary {{
        background-color: {COLORS.text_primary};
        color: {COLORS.app_bg};
        border: none;
        border-radius: {RADII.md}px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 13px;
    }}

    QPushButton.BtnPrimary:hover {{
        background-color: #E4E4E7;
    }}

    QPushButton.BtnPrimary:pressed {{
        background-color: #D4D4D8;
    }}

    QPushButton.BtnSecondary, QPushButton#BtnSecondary {{
        background-color: {COLORS.surface_raised};
        color: {COLORS.text_primary};
        border: 1px solid {COLORS.border};
        border-radius: {RADII.md}px;
        padding: 7px 14px;
        font-weight: 500;
        font-size: 13px;
    }}

    QPushButton.BtnSecondary:hover {{
        background-color: {COLORS.surface_hover};
        border-color: {COLORS.border_focus};
    }}

    QPushButton.BtnSubtle, QPushButton#BtnSubtle {{
        background-color: transparent;
        color: {COLORS.text_secondary};
        border: none;
        border-radius: {RADII.md}px;
        padding: 6px 12px;
        font-size: 12px;
    }}

    QPushButton.BtnSubtle:hover {{
        background-color: {COLORS.surface_hover};
        color: {COLORS.text_primary};
    }}

    /* Input & Search Bar */
    QLineEdit {{
        background-color: {COLORS.surface};
        color: {COLORS.text_primary};
        border: 1px solid {COLORS.border};
        border-radius: {RADII.lg}px;
        padding: 10px 14px;
        font-size: 14px;
    }}

    QLineEdit:focus {{
        border: 1px solid {COLORS.border_focus};
        background-color: {COLORS.surface_raised};
    }}

    QLineEdit#HeroSearchInput {{
        background-color: {COLORS.surface};
        color: {COLORS.text_primary};
        border: 1px solid {COLORS.border};
        border-radius: {RADII.xl}px;
        padding: 14px 20px;
        font-size: 16px;
    }}

    QLineEdit#HeroSearchInput:focus {{
        border: 1px solid {COLORS.accent_subtle};
        background-color: {COLORS.surface_raised};
    }}

    /* Scroll Area & Scrollbars */
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}

    QScrollBar:vertical {{
        border: none;
        background: transparent;
        width: 8px;
        margin: 0px;
    }}

    QScrollBar::handle:vertical {{
        background: {COLORS.surface_hover};
        min-height: 24px;
        border-radius: 4px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {COLORS.accent_subtle};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
        background: none;
    }}

    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}

    /* Typography Utilities */
    QLabel#PageTitle {{
        font-size: {TYPOGRAPHY.size_page_title}px;
        font-weight: 700;
        color: {COLORS.text_primary};
    }}

    QLabel#PageSubtitle {{
        font-size: {TYPOGRAPHY.size_body}px;
        color: {COLORS.text_secondary};
    }}

    QLabel#SectionTitle {{
        font-size: {TYPOGRAPHY.size_section_title}px;
        font-weight: 600;
        color: {COLORS.text_primary};
    }}

    QLabel#MutedText {{
        color: {COLORS.text_muted};
        font-size: {TYPOGRAPHY.size_caption}px;
    }}

    QLabel#MonoPath {{
        font-family: {TYPOGRAPHY.mono_family};
        font-size: {TYPOGRAPHY.size_mono}px;
        color: {COLORS.text_secondary};
    }}

    /* Badges */
    QLabel.Badge {{
        padding: 3px 8px;
        border-radius: {RADII.sm}px;
        font-size: 11px;
        font-weight: 600;
    }}

    QLabel.BadgeSuccess {{
        background-color: {COLORS.success_bg};
        color: {COLORS.success};
        border: 1px solid {COLORS.success_border};
    }}

    QLabel.BadgeProtected {{
        background-color: {COLORS.protected_bg};
        color: #A5B4FC;
        border: 1px solid {COLORS.protected_border};
    }}

    QLabel.BadgeWarning {{
        background-color: {COLORS.warning_bg};
        color: {COLORS.warning};
        border: 1px solid {COLORS.warning_border};
    }}

    /* Tooltips */
    QToolTip {{
        background-color: {COLORS.surface_raised};
        color: {COLORS.text_primary};
        border: 1px solid {COLORS.border};
        padding: 4px 8px;
        border-radius: {RADII.sm}px;
        font-size: 12px;
    }}

    /* ComboBox */
    QComboBox {{
        background-color: {COLORS.surface};
        color: {COLORS.text_primary};
        border: 1px solid {COLORS.border};
        border-radius: {RADII.md}px;
        padding: 6px 12px;
        font-size: 13px;
    }}

    QComboBox:focus {{
        border: 1px solid {COLORS.border_focus};
    }}

    QComboBox::drop-down {{
        border: none;
        padding-right: 8px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {COLORS.surface_raised};
        color: {COLORS.text_primary};
        selection-background-color: {COLORS.surface_active};
        selection-color: {COLORS.text_primary};
        border: 1px solid {COLORS.border};
        padding: 4px;
    }}
    """
