"""
ui/popup_window.py — Compact Radial Conversion Popup for Windows File Explorer Integration.

Launched by main.py when --popup or --quick-action flag is passed (from context menu).
Shows a frameless, glassmorphic popup near the cursor with the radial wheel.
Does NOT open the full application window.
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QEvent, QObject, QRectF, QPoint
from PySide6.QtGui import (
    QColor, QCursor, QIcon, QKeyEvent, QPainter,
    QPainterPath, QLinearGradient, QBrush, QPen, QDesktopServices,
)
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QProgressBar, QPushButton, QSizePolicy, QVBoxLayout, QWidget, QMessageBox,
)
from PySide6.QtCore import QUrl

from converters.base import ConversionOptions, ConversionResult
from converters.registry import registry, TargetOption
from services.detector import FileDetector, FileInfo
from services.worker import ConversionWorker
from ui.glass_styles import FORMAT_ACCENT_COLORS, MAIN_STYLESHEET
from ui.radial_wheel import RadialWheel


POPUP_W = 500
POPUP_H = 640
CORNER_RADIUS = 22


class _ClickOutsideFilter(QObject):
    """Application-level event filter: closes popup on click outside its bounds."""

    def __init__(self, popup: "ConversionPopup"):
        super().__init__(popup)
        self._popup = popup

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.MouseButtonPress:
            # If click is outside the popup geometry, close it (unless converting)
            global_pos = QCursor.pos()
            popup_rect = self._popup.geometry()
            if not popup_rect.contains(global_pos):
                self._popup._request_close()
        return False  # Never consume the event


class ConversionPopup(QWidget):
    """
    Frameless, compact radial conversion popup.
    Appears near the cursor; the user picks a format and converts.
    """

    def __init__(self, file_path: Optional[Path] = None, parent=None):
        super().__init__(parent)

        # ── Window flags for frameless, always-on-top, non-taskbar popup ──
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setFixedSize(POPUP_W, POPUP_H)
        self.setStyleSheet(MAIN_STYLESHEET)

        # State
        self.current_file_info: Optional[FileInfo] = None
        self.current_targets: List[TargetOption] = []
        self.selected_target: Optional[str] = None
        self.active_worker: Optional[ConversionWorker] = None
        self.last_result: Optional[ConversionResult] = None
        self._is_converting = False

        # Build UI
        self._build_ui()

        # Install click-outside filter
        self._outside_filter = _ClickOutsideFilter(self)
        QApplication.instance().installEventFilter(self._outside_filter)

        # Load file if given
        if file_path:
            self.load_file(file_path)

        # Position near cursor
        self._position_near_cursor()

    # ── Positioning ──────────────────────────────────────────────────────────

    def _position_near_cursor(self):
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos) or QApplication.primaryScreen()
        avail = screen.availableGeometry()

        # Default: show popup slightly right and below cursor
        x = cursor_pos.x() - POPUP_W // 4
        y = cursor_pos.y() - 30

        # Clamp to screen bounds safely across multiple monitors and DPI scales
        max_x = avail.left() + max(0, avail.width() - POPUP_W)
        max_y = avail.top() + max(0, avail.height() - POPUP_H)
        x = max(avail.left(), min(x, max_x))
        y = max(avail.top(), min(y, max_y))

        self.move(x, y)

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # Outer layout with padding for the drop shadow / border space
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(0)

        # Inner content card (will be drawn as rounded rect in paintEvent)
        self.card = QWidget()
        self.card.setObjectName("popupCard")
        self.card.setStyleSheet("""
            QWidget#popupCard {
                background: transparent;
            }
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 14, 16, 16)
        card_layout.setSpacing(8)

        # ── Header Row ────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        self.app_icon_lbl = QLabel("⚡")
        self.app_icon_lbl.setStyleSheet("font-size: 16px;")
        header_row.addWidget(self.app_icon_lbl)

        self.app_title_lbl = QLabel("QuickConvert")
        self.app_title_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #4338CA;"
        )
        header_row.addWidget(self.app_title_lbl)

        header_row.addStretch(1)

        # Privacy badge
        privacy_lbl = QLabel("🔒 Offline")
        privacy_lbl.setStyleSheet(
            "background: #EDE9FE; color: #5B21B6; font-size: 10px; "
            "font-weight: 600; padding: 3px 8px; border-radius: 10px; "
            "border: 1px solid #DDD6FE;"
        )
        header_row.addWidget(privacy_lbl)

        # Close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; font-size: 14px; "
            "color: #94A3B8; border-radius: 14px; }"
            "QPushButton:hover { background: #FEE2E2; color: #EF4444; }"
        )
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self._request_close)
        header_row.addWidget(self.close_btn)

        card_layout.addLayout(header_row)

        # ── File Info Row ─────────────────────────────────────────────────────
        self.file_info_lbl = QLabel("Drop a file or launch from Explorer")
        self.file_info_lbl.setStyleSheet(
            "font-size: 11px; color: #64748B; padding: 2px 0;"
        )
        self.file_info_lbl.setWordWrap(True)
        card_layout.addWidget(self.file_info_lbl)

        # ── Divider ───────────────────────────────────────────────────────────
        card_layout.addWidget(self._make_divider())

        # ── Radial Wheel ──────────────────────────────────────────────────────
        self.radial_wheel = RadialWheel()
        self.radial_wheel.setFixedSize(420, 360)
        self.radial_wheel.target_selected.connect(self._on_target_selected)
        self.radial_wheel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        wheel_row = QHBoxLayout()
        wheel_row.setAlignment(Qt.AlignCenter)
        wheel_row.addWidget(self.radial_wheel)
        card_layout.addLayout(wheel_row)

        # ── Divider ───────────────────────────────────────────────────────────
        card_layout.addWidget(self._make_divider())

        # ── Output Name Row ───────────────────────────────────────────────────
        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        name_lbl = QLabel("Output name:")
        name_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #475569;")
        name_lbl.setFixedWidth(82)
        name_row.addWidget(name_lbl)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Auto-generated...")
        self.name_input.setStyleSheet(
            "QLineEdit { font-size: 12px; padding: 6px 10px; border-radius: 8px; }"
        )
        name_row.addWidget(self.name_input, stretch=1)

        self.reset_name_btn = QPushButton("Reset")
        self.reset_name_btn.setObjectName("secondaryBtn")
        self.reset_name_btn.setFixedWidth(52)
        self.reset_name_btn.clicked.connect(self._on_reset_name)
        name_row.addWidget(self.reset_name_btn)

        card_layout.addLayout(name_row)

        # ── Convert Button ────────────────────────────────────────────────────
        self.convert_btn = QPushButton("Select a format to convert")
        self.convert_btn.setObjectName("primaryBtn")
        self.convert_btn.setEnabled(False)
        self.convert_btn.setCursor(Qt.PointingHandCursor)
        self.convert_btn.setStyleSheet(
            "QPushButton#primaryBtn { font-size: 13px; padding: 10px 20px; border-radius: 12px; }"
        )
        self.convert_btn.clicked.connect(self._on_convert_clicked)
        card_layout.addWidget(self.convert_btn)

        # ── Progress Section (hidden initially) ───────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(8)
        card_layout.addWidget(self.progress_bar)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
        self.status_lbl.setVisible(False)
        self.status_lbl.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.status_lbl)

        # ── Result Row (hidden initially) ─────────────────────────────────────
        result_row = QHBoxLayout()
        result_row.setSpacing(8)
        result_row.setAlignment(Qt.AlignCenter)

        self.result_lbl = QLabel("")
        self.result_lbl.setStyleSheet("font-size: 11px; font-weight: 600;")
        self.result_lbl.setVisible(False)
        result_row.addWidget(self.result_lbl)

        self.open_file_btn = QPushButton("Open File")
        self.open_file_btn.setObjectName("secondaryBtn")
        self.open_file_btn.setVisible(False)
        self.open_file_btn.setCursor(Qt.PointingHandCursor)
        self.open_file_btn.clicked.connect(self._on_open_file)
        result_row.addWidget(self.open_file_btn)

        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.setObjectName("secondaryBtn")
        self.open_folder_btn.setVisible(False)
        self.open_folder_btn.setCursor(Qt.PointingHandCursor)
        self.open_folder_btn.clicked.connect(self._on_open_folder)
        result_row.addWidget(self.open_folder_btn)

        card_layout.addLayout(result_row)

        outer.addWidget(self.card)
        self._refresh_targets()

    def _make_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("border: none; border-top: 1px solid rgba(226,232,240,0.8); margin: 2px 0;")
        line.setFixedHeight(1)
        return line

    # ── Custom Paint (glassmorphic rounded card with shadow) ──────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Drop shadow effect (drawn slightly offset below)
        shadow_rect = QRectF(self.rect()).adjusted(6, 8, -6, -8)
        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(shadow_rect, CORNER_RADIUS + 2, CORNER_RADIUS + 2)
        for i in range(8, 0, -1):
            expanded = shadow_rect.adjusted(-i, -i, i, i)
            p2 = QPainterPath()
            p2.addRoundedRect(expanded, CORNER_RADIUS + 3, CORNER_RADIUS + 3)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, max(0, 4 - i // 2)))
            painter.drawPath(p2)

        # Main card background
        card_rect = QRectF(self.rect()).adjusted(10, 10, -10, -10)
        card_path = QPainterPath()
        card_path.addRoundedRect(card_rect, CORNER_RADIUS, CORNER_RADIUS)

        # Glassmorphic gradient fill — translucent, not opaque white
        grad = QLinearGradient(card_rect.topLeft(), card_rect.bottomRight())
        grad.setColorAt(0.0, QColor(255, 255, 255, 210))
        grad.setColorAt(0.5, QColor(245, 248, 255, 200))
        grad.setColorAt(1.0, QColor(238, 242, 255, 195))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawPath(card_path)

        # Subtle border
        painter.setPen(QPen(QColor(226, 232, 240, 200), 1.2))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(card_path)

        # Top edge accent (thin gradient line)
        accent_rect = QRectF(card_rect.left() + CORNER_RADIUS, card_rect.top(),
                             card_rect.width() - 2 * CORNER_RADIUS, 3)
        accent_grad = QLinearGradient(accent_rect.left(), 0, accent_rect.right(), 0)
        accent_grad.setColorAt(0.0, QColor(0x06, 0xB6, 0xD4, 180))
        accent_grad.setColorAt(0.5, QColor(0x3B, 0x82, 0xF6, 200))
        accent_grad.setColorAt(1.0, QColor(0x8B, 0x5C, 0xF6, 180))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(accent_grad))
        painter.drawRoundedRect(accent_rect, 2, 2)

        painter.end()

    # ── File Loading ──────────────────────────────────────────────────────────

    def load_file(self, file_path: Path):
        info = FileDetector.detect(file_path)
        self.current_file_info = info

        if not info.is_valid:
            self.file_info_lbl.setText(
                f"⚠️  {file_path.name}  —  {info.validation_error or 'Invalid file'}"
            )
            self.file_info_lbl.setStyleSheet("font-size: 11px; color: #EF4444;")
            self.name_input.clear()
            self._refresh_targets()
            self._update_convert_button()
            return

        # Format info row
        fmt = info.detected_format.upper()
        size_str = self._fmt_size(info.size_bytes)
        extra = ""
        if info.page_count and info.page_count > 1:
            extra = f"  •  {info.page_count} pages"
        elif info.dimensions:
            w, h = info.dimensions
            extra = f"  •  {w}×{h}px"
        self.file_info_lbl.setText(f"📄  {file_path.name}  •  {fmt}  •  {size_str}{extra}")
        self.file_info_lbl.setStyleSheet("font-size: 11px; color: #475569;")

        self.name_input.setText(f"{file_path.stem}_Converted")
        self._refresh_targets()
        self._update_convert_button()

    def _fmt_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        if size_bytes < 1024 * 1024:
            return f"{size_bytes // 1024} KB"
        return f"{size_bytes / (1024*1024):.1f} MB"

    # ── Targets / Wheel ───────────────────────────────────────────────────────

    def _refresh_targets(self):
        src_fmt = (
            self.current_file_info.detected_format
            if self.current_file_info and self.current_file_info.is_valid
            else None
        )
        self.current_targets = registry.get_target_options_for_source(src_fmt)
        self.radial_wheel.set_file_info(self.current_file_info, self.current_targets)

    def _on_target_selected(self, fmt: str):
        self.selected_target = fmt
        self._update_convert_button()

    def _update_convert_button(self):
        if not self.current_file_info or not self.current_file_info.is_valid:
            self.convert_btn.setEnabled(False)
            self.convert_btn.setText("No valid file loaded")
            return
        if not self.selected_target:
            self.convert_btn.setEnabled(False)
            self.convert_btn.setText("Select a format to convert")
            return

        opt = next(
            (t for t in self.current_targets if t.target_format == self.selected_target), None
        )
        if opt and opt.is_enabled:
            self.convert_btn.setEnabled(True)
            self.convert_btn.setText(
                f"Convert to {opt.label} ({opt.output_extension.upper()})"
            )
        else:
            self.convert_btn.setEnabled(False)
            self.convert_btn.setText("Unsupported conversion")

    # ── Conversion ────────────────────────────────────────────────────────────

    def _on_convert_clicked(self):
        if not self.current_file_info or not self.selected_target:
            return

        converter = registry.get_converter(
            self.current_file_info.detected_format, self.selected_target
        )
        if not converter:
            QMessageBox.warning(self, "Error", "No converter available.")
            return

        options = ConversionOptions(
            custom_output_name=self.name_input.text().strip() or None,
            output_dir=self.current_file_info.path.parent,
        )

        # UI → converting state
        self._is_converting = True
        self.convert_btn.setEnabled(False)
        self.convert_btn.setText("Converting...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_lbl.setVisible(True)
        self.status_lbl.setText("Starting conversion...")
        self.result_lbl.setVisible(False)
        self.open_file_btn.setVisible(False)
        self.open_folder_btn.setVisible(False)

        self.active_worker = ConversionWorker(
            converter, self.current_file_info.path, options, self
        )
        self.active_worker.progress_changed.connect(self._on_progress)
        self.active_worker.finished.connect(self._on_finished)
        self.active_worker.start()

    def _on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.status_lbl.setText(f"{msg} ({pct}%)")

    def _on_finished(self, result: ConversionResult):
        self._is_converting = False
        self.last_result = result
        self.progress_bar.setVisible(False)

        if result.success:
            count = len(result.output_files)
            self.status_lbl.setText(f"✅  {count} file(s) saved successfully!")
            self.status_lbl.setStyleSheet("font-size: 11px; color: #059669; font-weight: 600;")
            self.result_lbl.setVisible(False)
            self.open_file_btn.setVisible(True)
            self.open_folder_btn.setVisible(True)
        else:
            err = result.error_message or "Unknown error."
            self.status_lbl.setText(f"❌  {err[:80]}")
            self.status_lbl.setStyleSheet("font-size: 11px; color: #DC2626; font-weight: 600;")

        self._update_convert_button()

    # ── Output Name ───────────────────────────────────────────────────────────

    def _on_reset_name(self):
        if self.current_file_info and self.current_file_info.is_valid:
            self.name_input.setText(f"{self.current_file_info.path.stem}_Converted")
        else:
            self.name_input.clear()

    # ── Open Result ───────────────────────────────────────────────────────────

    def _on_open_file(self):
        if self.last_result and self.last_result.output_files:
            p = self.last_result.output_files[0]
            if p.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))

    def _on_open_folder(self):
        if self.last_result and self.last_result.output_files:
            p = self.last_result.output_files[0]
            if p.exists():
                subprocess.run(["explorer", "/select,", str(p)], check=False)

    # ── Close Handling ────────────────────────────────────────────────────────

    def _request_close(self):
        """Close popup, safely handling an in-progress conversion."""
        if self._is_converting and self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()
            self.active_worker.wait(3000)
        self.close()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self._request_close()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.convert_btn.isEnabled() and not self._is_converting:
                self._on_convert_clicked()
        elif event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            self.radial_wheel.keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        # Remove event filter before closing to avoid dangling reference
        app = QApplication.instance()
        if app and self._outside_filter:
            app.removeEventFilter(self._outside_filter)
        super().closeEvent(event)
