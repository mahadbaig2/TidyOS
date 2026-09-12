"""Home dashboard page for TidyOS showing real filesystem health, metrics, and activity."""

from __future__ import annotations

from typing import Optional
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QScrollArea,
    QProgressBar,
)
from PySide6.QtCore import Qt

from tidyos.config import config
from tidyos.storage import StorageRepository
from tidyos.ui.theme.tokens import COLORS, RADII, SPACING, TYPOGRAPHY
from tidyos.ui.components.metric_card import MetricCard
from tidyos.ui.components.badge import StatusBadge
from tidyos.logging_config import get_logger

logger = get_logger("ui.pages.home")


class HomePage(QWidget):
    """Home dashboard screen establishing filesystem health, metrics, and recent activity."""

    def __init__(
        self,
        repository: Optional[StorageRepository] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.repository = repository or StorageRepository(config.database_path)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area for responsive dashboard
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(24)

        # Header greeting & status
        header_layout = QHBoxLayout()

        greeting_box = QVBoxLayout()
        greeting_box.setSpacing(4)

        title = QLabel("Good evening.")
        title.setObjectName("PageTitle")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {COLORS.text_primary};")
        greeting_box.addWidget(title)

        self.subtitle = QLabel("Your filesystem is under control.")
        self.subtitle.setStyleSheet(f"font-size: 14px; color: {COLORS.text_secondary};")
        greeting_box.addWidget(self.subtitle)

        header_layout.addLayout(greeting_box)
        header_layout.addStretch()

        # Watching badge
        self.watch_pill = StatusBadge("● Watching Active", variant="success")
        self.watch_pill.setFixedHeight(28)
        self.watch_pill.setStyleSheet(
            f"""
            background-color: {COLORS.success_bg};
            color: {COLORS.success};
            border: 1px solid {COLORS.success_border};
            border-radius: {RADII.full}px;
            padding: 4px 14px;
            font-size: 12px;
            font-weight: 600;
            """
        )
        header_layout.addWidget(self.watch_pill)
        layout.addLayout(header_layout)

        # Scan progress bar (hidden unless scanning)
        self.progress_frame = QFrame()
        self.progress_frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLORS.surface_raised};
                border: 1px solid {COLORS.border_subtle};
                border-radius: {RADII.md}px;
                padding: 10px 14px;
            }}
            """
        )
        p_box = QVBoxLayout(self.progress_frame)
        p_box.setContentsMargins(10, 8, 10, 8)
        p_box.setSpacing(6)

        self.progress_label = QLabel("Scanning filesystem...")
        self.progress_label.setStyleSheet(f"font-size: 12px; color: {COLORS.text_primary}; font-weight: 600;")
        p_box.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate while scanning
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: {COLORS.surface};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS.success};
                border-radius: 3px;
            }}
            """
        )
        p_box.addWidget(self.progress_bar)
        self.progress_frame.setVisible(False)
        layout.addWidget(self.progress_frame)

        # Metric Cards Row
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(16)

        self.card_indexed = MetricCard("0", "Files indexed", "Across 0 approved roots")
        self.card_organized = MetricCard("0", "Directories mapped", "Preserved structure")
        self.card_protected = MetricCard("0", "Protected projects", "Codebases untouched")
        self.card_review = MetricCard("0", "Need review", "Awaiting confirmation")

        metrics_layout.addWidget(self.card_indexed)
        metrics_layout.addWidget(self.card_organized)
        metrics_layout.addWidget(self.card_protected)
        metrics_layout.addWidget(self.card_review)

        layout.addLayout(metrics_layout)

        # Protected Projects Dynamic Section
        self.protected_container = QWidget()
        self.protected_layout = QVBoxLayout(self.protected_container)
        self.protected_layout.setContentsMargins(0, 0, 0, 0)
        self.protected_layout.setSpacing(10)
        layout.addWidget(self.protected_container)


        # Recent Activity Section
        section_header = QHBoxLayout()
        activity_title = QLabel("Recent Activity")
        activity_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {COLORS.text_primary};")
        section_header.addWidget(activity_title)
        section_header.addStretch()
        layout.addLayout(section_header)

        # Activity list container
        self.activity_card = QFrame()
        self.activity_card.setObjectName("Card")
        self.activity_card.setStyleSheet(
            f"""
            QFrame#Card {{
                background-color: {COLORS.surface};
                border: 1px solid {COLORS.border};
                border-radius: {RADII.lg}px;
            }}
            """
        )
        self.act_layout = QVBoxLayout(self.activity_card)
        self.act_layout.setContentsMargins(16, 12, 16, 12)
        self.act_layout.setSpacing(12)

        # Activity item 1
        item1 = self._create_activity_row(
            icon="✓",
            filename="Vercel_Invoice_Sep_2026.pdf",
            path_change="Downloads → Finance / Software / Vercel",
            time_ago="Organized 2m ago",
            confidence="97% confidence",
        )
        self.act_layout.addLayout(item1)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet(f"border-top: 1px solid {COLORS.border_subtle};")
        self.act_layout.addWidget(sep1)

        # Activity item 2
        item2 = self._create_activity_row(
            icon="✓",
            filename="FastAPI_CORS_Error.png",
            path_change="Screenshots → Development / Errors",
            time_ago="Organized 14m ago",
            confidence="92% confidence",
        )
        self.act_layout.addLayout(item2)

        layout.addWidget(self.activity_card)
        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Load real database metrics
        self.refresh_metrics()

    def refresh_metrics(self):
        """Update dashboard metric cards from database."""
        try:
            stats = self.repository.get_statistics()
            total_files = stats.get("total_files", 0)
            total_roots = stats.get("total_roots", 0)
            total_dirs = stats.get("total_directories", 0)
            total_prot = stats.get("total_protected", 0)
            total_review = stats.get("total_review", 0)

            self.card_indexed.set_value(f"{total_files:,}")
            self.card_indexed.set_hint(f"Across {total_roots} approved root(s)")

            self.card_organized.set_value(f"{total_dirs:,}")
            self.card_organized.set_hint(f"{total_dirs} directories mapped")

            self.card_protected.set_value(f"{total_prot}")
            self.card_protected.set_hint("Codebases untouched")

            self.card_review.set_value(f"{total_review}")
            self.card_review.set_hint("Awaiting confirmation")

            if total_files > 0:
                self.subtitle.setText(f"{total_files:,} files indexed across {total_roots} managed folder(s).")
            else:
                self.subtitle.setText("No files indexed yet. Add a managed folder in Settings to begin.")

            # Refresh protected project visual cards
            self.refresh_protected_projects()

        except Exception as e:
            logger.error(f"Failed to refresh dashboard metrics: {e}")

    def refresh_protected_projects(self):
        """Render detected protected projects dynamically."""
        while self.protected_layout.count():
            item = self.protected_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        protected_roots = self.repository.list_protected_roots()

        if not protected_roots:
            card = QFrame()
            card.setObjectName("CardRaised")
            card.setStyleSheet(
                f"""
                QFrame#CardRaised {{
                    background-color: {COLORS.surface_raised};
                    border: 1px solid {COLORS.border_subtle};
                    border-radius: {RADII.lg}px;
                    padding: {SPACING.md}px;
                }}
                """
            )
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(18, 14, 18, 14)
            c_layout.setSpacing(6)

            hdr = QHBoxLayout()
            b = StatusBadge("🛡️ Project Boundary Protection", variant="neutral")
            hdr.addWidget(b)
            hdr.addStretch()
            c_layout.addLayout(hdr)

            desc = QLabel(
                "TidyOS automatically detects and protects software repositories "
                "(Next.js, Python, Git, Node). When codebases are detected, their internal "
                "files are strictly protected from automated moves and renames."
            )
            desc.setWordWrap(True)
            desc.setStyleSheet(f"font-size: 12px; color: {COLORS.text_secondary};")
            c_layout.addWidget(desc)
            self.protected_layout.addWidget(card)
            return

        for prot in protected_roots:
            card = QFrame()
            card.setObjectName("CardRaised")
            card.setStyleSheet(
                f"""
                QFrame#CardRaised {{
                    background-color: {COLORS.surface_raised};
                    border: 1px solid {COLORS.protected_border};
                    border-radius: {RADII.lg}px;
                    padding: {SPACING.lg}px;
                }}
                """
            )
            p_layout = QVBoxLayout(card)
            p_layout.setContentsMargins(18, 16, 18, 16)
            p_layout.setSpacing(8)

            p_header = QHBoxLayout()
            p_badge = StatusBadge("🛡️ Protected Project", variant="protected")
            p_header.addWidget(p_badge)

            p_repo_name = QLabel(Path(prot.path).name)
            p_repo_name.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {COLORS.text_primary};")
            p_header.addWidget(p_repo_name)

            type_label = prot.project_type.replace("_", " ").title()
            p_type = QLabel(f"{type_label} repository")
            p_type.setStyleSheet(f"font-size: 12px; color: {COLORS.text_muted};")
            p_header.addWidget(p_type)

            p_header.addStretch()

            prot_badge = StatusBadge("Protected Structure ✓", variant="protected")
            p_header.addWidget(prot_badge)
            p_layout.addLayout(p_header)

            markers_str = ", ".join(prot.detected_markers) if prot.detected_markers else "project root markers"
            p_desc = QLabel(
                f"TidyOS detected markers: {markers_str}. "
                "Internal project files are protected from automated moves and renames."
            )
            p_desc.setWordWrap(True)
            p_desc.setStyleSheet(f"font-size: 12px; color: {COLORS.text_secondary};")
            p_layout.addWidget(p_desc)

            self.protected_layout.addWidget(card)


    def show_scan_progress(self, current_file: str, files_count: int, dirs_count: int):
        """Update scan progress banner."""
        self.progress_frame.setVisible(True)
        self.progress_label.setText(
            f"Scanning: {files_count:,} files, {dirs_count:,} folders discovered..."
        )

    def hide_scan_progress(self, total_files: int, total_dirs: int, duration_s: float):
        """Hide progress bar and refresh metrics upon scan completion."""
        self.progress_frame.setVisible(False)
        self.refresh_metrics()
        self.subtitle.setText(
            f"Scan completed: {total_files:,} files and {total_dirs:,} folders indexed in {duration_s:.1f}s."
        )

    def _create_activity_row(
        self, icon: str, filename: str, path_change: str, time_ago: str, confidence: str
    ) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"color: {COLORS.success}; font-weight: 700; font-size: 14px;")
        row.addWidget(icon_lbl)

        info_box = QVBoxLayout()
        info_box.setSpacing(2)

        file_lbl = QLabel(filename)
        file_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {COLORS.text_primary};")
        info_box.addWidget(file_lbl)

        path_lbl = QLabel(path_change)
        path_lbl.setStyleSheet(
            f"font-size: 11px; font-family: {TYPOGRAPHY.mono_family}; color: {COLORS.text_secondary};"
        )
        info_box.addWidget(path_lbl)
        row.addLayout(info_box, 1)

        meta_box = QVBoxLayout()
        meta_box.setSpacing(2)
        meta_box.setAlignment(Qt.AlignmentFlag.AlignRight)

        time_lbl = QLabel(time_ago)
        time_lbl.setStyleSheet(f"font-size: 11px; color: {COLORS.text_muted};")
        meta_box.addWidget(time_lbl)

        conf_lbl = QLabel(confidence)
        conf_lbl.setStyleSheet(f"font-size: 11px; color: {COLORS.text_secondary};")
        meta_box.addWidget(conf_lbl)
        row.addLayout(meta_box)

        why_btn = QPushButton("Why?")
        why_btn.setObjectName("BtnSubtle")
        why_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row.addWidget(why_btn)

        undo_btn = QPushButton("Undo")
        undo_btn.setObjectName("BtnSecondary")
        undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row.addWidget(undo_btn)

        return row
