from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
)

from services.detector import FileInfo
from utils.path_helpers import format_file_size
from ui.glass_styles import PALETTE, FORMAT_ACCENT_COLORS


class FileCard(QFrame):
    """
    Drop-zone and selected file info card.
    Supports file dragging directly from Windows Explorer.
    """

    file_dropped = Signal(Path)
    file_cleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glassCard")
        self.setAcceptDrops(True)
        self.setMinimumHeight(84)

        self.current_file_info: Optional[FileInfo] = None
        self._init_ui()

    def _init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(16, 12, 16, 12)
        self.main_layout.setSpacing(14)

        # File Icon / Badge
        self.icon_label = QLabel("📂")
        self.icon_label.setStyleSheet("font-size: 26px; padding-right: 4px;")
        self.main_layout.addWidget(self.icon_label)

        # File Details Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        self.title_label = QLabel("Drag & drop any file here")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #0F172A;")
        text_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("Supports PDF, PNG, JPG, WebP, BMP, TIFF, GIF, TXT, HTML")
        self.subtitle_label.setStyleSheet("font-size: 12px; color: #64748B;")
        text_layout.addWidget(self.subtitle_label)

        self.main_layout.addLayout(text_layout, stretch=1)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.browse_btn = QPushButton("Browse Files")
        self.browse_btn.setObjectName("secondaryBtn")
        self.browse_btn.setCursor(Qt.PointingHandCursor)
        self.browse_btn.clicked.connect(self._on_browse_clicked)
        btn_layout.addWidget(self.browse_btn)

        self.clear_btn = QPushButton("✕")
        self.clear_btn.setObjectName("iconBtn")
        self.clear_btn.setToolTip("Clear selected file")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setVisible(False)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        btn_layout.addWidget(self.clear_btn)

        self.main_layout.addLayout(btn_layout)

    def set_file(self, info: Optional[FileInfo]):
        self.current_file_info = info
        if not info:
            self.icon_label.setText("📂")
            self.title_label.setText("Drag & drop any file here")
            self.title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #0F172A;")
            self.subtitle_label.setText("Supports PDF, PNG, JPG, WebP, BMP, TIFF, GIF, TXT, HTML")
            self.subtitle_label.setStyleSheet("font-size: 12px; color: #64748B;")
            self.clear_btn.setVisible(False)
            self.browse_btn.setText("Browse Files")
            return

        self.clear_btn.setVisible(True)
        self.browse_btn.setText("Change File")

        if not info.is_valid:
            self.icon_label.setText("⚠️")
            self.title_label.setText(info.path.name)
            self.title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #DC2626;")
            self.subtitle_label.setText(info.validation_error or "File is unsupported or corrupt")
            self.subtitle_label.setStyleSheet("font-size: 12px; color: #DC2626;")
            return

        fmt = info.detected_format.upper()
        self.icon_label.setText("📄")
        self.title_label.setText(info.path.name)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #0F172A;")

        details = f"{fmt} • {format_file_size(info.size_bytes)}"
        if info.page_count and info.page_count > 1:
            details += f" • {info.page_count} pages"
        if info.has_transparency:
            details += " • Transparent"
        self.subtitle_label.setText(details)
        self.subtitle_label.setStyleSheet("font-size: 12px; color: #64748B;")

    def _on_browse_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Convert",
            "",
            "All Supported Files (*.pdf *.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif *.gif *.txt *.html *.docx *.md);;Word Documents (*.docx);;PDF Documents (*.pdf);;Images (*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.gif);;Text Documents (*.txt *.html *.md);;All Files (*.*)",
        )
        if file_path:
            self.file_dropped.emit(Path(file_path))

    def _on_clear_clicked(self):
        self.set_file(None)
        self.file_cleared.emit()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("text/uri-list"):
            event.acceptProposedAction()
            self.setStyleSheet(
                "QFrame#glassCard { background-color: #EDE9FE; border: 2px dashed #8B5CF6; border-radius: 16px; }"
            )
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("text/uri-list"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
        event.accept()

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        urls = event.mimeData().urls()
        if urls:
            path_str = urls[0].toLocalFile()
            if path_str:
                self.file_dropped.emit(Path(path_str))
        event.acceptProposedAction()
