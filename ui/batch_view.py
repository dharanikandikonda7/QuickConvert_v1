import os
from pathlib import Path
from typing import List, Optional, Dict

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QScrollArea,
    QFrame,
    QFileDialog,
    QProgressBar,
    QMessageBox,
)

from converters.registry import registry
from converters.base import ConversionOptions, ConversionResult
from services.detector import FileDetector, FileInfo
from services.worker import ConversionWorker
from utils.path_helpers import format_file_size


class BatchFileItem(QFrame):
    """Row representing a single file in the batch conversion queue."""

    removed = Signal(Path)
    format_changed = Signal(Path, str)

    def __init__(self, file_path: Path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.file_info = FileDetector.detect(file_path)
        self.setObjectName("glassCard")
        self.setStyleSheet(
            "QFrame#glassCard { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; }"
        )
        self.setFixedHeight(54)

        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)

        # File Icon Badge
        fmt = self.file_info.detected_format.lower()
        icon_text = "📄"
        badge_color = "#3B82F6"
        if fmt == "pdf":
            icon_text = "📕"
            badge_color = "#EF4444"
        elif fmt in ("jpeg", "jpg", "png", "webp"):
            icon_text = "🖼️"
            badge_color = "#10B981"
        elif fmt == "docx":
            icon_text = "📘"
            badge_color = "#2563EB"
        elif fmt == "txt":
            icon_text = "📝"
            badge_color = "#6366F1"

        icon_lbl = QLabel(icon_text)
        icon_lbl.setStyleSheet("font-size: 18px;")
        layout.addWidget(icon_lbl)

        # Details
        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)
        name_lbl = QLabel(self.file_path.name)
        name_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #0F172A;")

        meta_str = f"{format_file_size(self.file_info.size_bytes)} • {fmt.upper()}"
        if self.file_info.page_count and self.file_info.page_count > 1:
            meta_str += f" • {self.file_info.page_count} pages"
        meta_lbl = QLabel(meta_str)
        meta_lbl.setStyleSheet("font-size: 11px; color: #64748B;")

        info_layout.addWidget(name_lbl)
        info_layout.addWidget(meta_lbl)
        layout.addLayout(info_layout, stretch=1)

        # Target Format Selector Dropdown
        self.combo = QComboBox()
        self.combo.setFixedWidth(110)
        self.combo.setStyleSheet(
            "QComboBox { background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; "
            "padding: 4px 10px; font-size: 12px; font-weight: 600; color: #1E293B; } "
            "QComboBox::drop-down { border: none; } "
            "QComboBox QAbstractItemView { background-color: #FFFFFF; border: 1px solid #E2E8F0; "
            "selection-background-color: #EDE9FE; selection-color: #6D28D9; }"
        )

        # Populate targets
        targets = registry.get_target_options_for_source(fmt)
        enabled_targets = [t for t in targets if t.is_enabled]
        for t in enabled_targets:
            self.combo.addItem(t.label, t.target_format)

        self.combo.currentIndexChanged.connect(self._on_combo_changed)
        layout.addWidget(self.combo)

        # Remove Button
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #94A3B8; font-weight: bold; border-radius: 12px; } "
            "QPushButton:hover { background-color: #FEE2E2; color: #EF4444; }"
        )
        remove_btn.clicked.connect(lambda: self.removed.emit(self.file_path))
        layout.addWidget(remove_btn)

    def _on_combo_changed(self):
        target_fmt = self.combo.currentData()
        self.format_changed.emit(self.file_path, target_fmt)

    @property
    def selected_target(self) -> Optional[str]:
        return self.combo.currentData()


class BatchConvertView(QWidget):
    """
    Batch conversion queue panel matching the dashboard view in the reference design.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.file_items: Dict[Path, BatchFileItem] = {}
        self.save_dir = Path.home() / "Documents"
        self._is_converting = False
        self._current_worker: Optional[ConversionWorker] = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # Top Drop Zone
        self.drop_frame = QFrame()
        self.drop_frame.setObjectName("dropZone")
        self.drop_frame.setCursor(Qt.PointingHandCursor)
        self.drop_frame.setFixedHeight(95)

        drop_layout = QVBoxLayout(self.drop_frame)
        drop_layout.setContentsMargins(12, 12, 12, 12)
        drop_layout.setAlignment(Qt.AlignCenter)
        drop_layout.setSpacing(4)

        drop_icon = QLabel("📁")
        drop_icon.setStyleSheet("font-size: 24px;")
        drop_layout.addWidget(drop_icon, alignment=Qt.AlignCenter)

        drop_title = QLabel("Drag & Drop Files Here or click to browse")
        drop_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #0F172A;")
        drop_layout.addWidget(drop_title, alignment=Qt.AlignCenter)

        drop_sub = QLabel("Supports PDF, Images (PNG, JPG, WebP), Word (DOCX), Text and more...")
        drop_sub.setStyleSheet("font-size: 11px; color: #64748B;")
        drop_layout.addWidget(drop_sub, alignment=Qt.AlignCenter)

        # Click drop zone to browse
        self.drop_frame.mousePressEvent = lambda e: self._on_browse_files()
        layout.addWidget(self.drop_frame)

        # Scroll Area for File Queue
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.queue_container = QWidget()
        self.queue_layout = QVBoxLayout(self.queue_container)
        self.queue_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_layout.setSpacing(8)
        self.queue_layout.addStretch()

        self.scroll.setWidget(self.queue_container)
        layout.addWidget(self.scroll, stretch=1)

        # Add More Files Button Row
        add_row = QHBoxLayout()
        self.add_btn = QPushButton("+ Add More Files")
        self.add_btn.setObjectName("secondaryBtn")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._on_browse_files)
        add_row.addWidget(self.add_btn)
        add_row.addStretch()
        layout.addLayout(add_row)

        # Bottom Bar: Save to & Convert All
        bottom_card = QFrame()
        bottom_card.setObjectName("glassCard")
        b_layout = QHBoxLayout(bottom_card)
        b_layout.setContentsMargins(16, 12, 16, 12)
        b_layout.setSpacing(14)

        dest_layout = QHBoxLayout()
        dest_layout.setSpacing(8)
        dest_lbl = QLabel("Save to:")
        dest_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569;")
        self.dest_path_lbl = QLabel(str(self.save_dir))
        self.dest_path_lbl.setStyleSheet(
            "background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; "
            "padding: 6px 12px; font-size: 12px; color: #0F172A;"
        )
        dest_btn = QPushButton("📁")
        dest_btn.setToolTip("Choose destination folder")
        dest_btn.setObjectName("secondaryBtn")
        dest_btn.clicked.connect(self._on_choose_save_dir)

        dest_layout.addWidget(dest_lbl)
        dest_layout.addWidget(self.dest_path_lbl, stretch=1)
        dest_layout.addWidget(dest_btn)
        b_layout.addLayout(dest_layout, stretch=1)

        self.convert_all_btn = QPushButton("Convert All")
        self.convert_all_btn.setObjectName("primaryBtn")
        self.convert_all_btn.setCursor(Qt.PointingHandCursor)
        self.convert_all_btn.clicked.connect(self._on_convert_all)
        b_layout.addWidget(self.convert_all_btn)

        layout.addWidget(bottom_card)

        # Progress bar
        self.prog_bar = QProgressBar()
        self.prog_bar.setVisible(False)
        layout.addWidget(self.prog_bar)

    def add_file(self, path: Path):
        resolved = path.resolve()
        if resolved in self.file_items:
            return

        item = BatchFileItem(resolved)
        item.removed.connect(self.remove_file)
        self.file_items[resolved] = item

        # Insert before stretch
        self.queue_layout.insertWidget(self.queue_layout.count() - 1, item)

    def remove_file(self, path: Path):
        resolved = path.resolve()
        if resolved in self.file_items:
            item = self.file_items.pop(resolved)
            self.queue_layout.removeWidget(item)
            item.deleteLater()

    def _on_browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files for Batch Conversion",
            "",
            "All Supported Files (*.pdf *.png *.jpg *.jpeg *.webp *.bmp *.tiff *.gif *.txt *.html *.docx);;All Files (*.*)",
        )
        for f in files:
            self.add_file(Path(f))

    def _on_choose_save_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Folder", str(self.save_dir))
        if folder:
            self.save_dir = Path(folder)
            self.dest_path_lbl.setText(str(self.save_dir))

    def _on_convert_all(self):
        if not self.file_items:
            QMessageBox.information(self, "No Files", "Please add files to convert.")
            return

        items = list(self.file_items.values())
        total = len(items)
        self.prog_bar.setVisible(True)
        self.prog_bar.setValue(0)
        self.convert_all_btn.setEnabled(False)

        success_count = 0
        error_messages = []

        for idx, item in enumerate(items):
            src_fmt = item.file_info.detected_format
            tgt_fmt = item.selected_target
            if not tgt_fmt:
                continue

            converter = registry.get_converter(src_fmt, tgt_fmt)
            if not converter:
                error_messages.append(f"{item.file_path.name}: No converter to {tgt_fmt}")
                continue

            opts = ConversionOptions(output_dir=self.save_dir)
            res = converter.convert(item.file_path, opts)
            if res.success:
                success_count += 1
            else:
                error_messages.append(f"{item.file_path.name}: {res.error_message}")

            self.prog_bar.setValue(int(((idx + 1) / total) * 100))

        self.convert_all_btn.setEnabled(True)
        self.prog_bar.setVisible(False)

        if error_messages:
            msg = f"Converted {success_count} of {total} files successfully.\n\nErrors:\n" + "\n".join(error_messages[:5])
            QMessageBox.warning(self, "Batch Conversion Complete with Errors", msg)
        else:
            QMessageBox.information(
                self,
                "Batch Conversion Completed!",
                f"Successfully converted all {total} files!\nSaved to: {self.save_dir}",
            )

    # Drag and Drop handlers
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("text/uri-list"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("text/uri-list"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        for u in urls:
            path_str = u.toLocalFile()
            if path_str:
                self.add_file(Path(path_str))
        event.acceptProposedAction()
