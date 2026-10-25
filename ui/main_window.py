import os
import subprocess
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import (
    QDesktopServices,
    QIcon,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QLinearGradient,
    QColor,
)
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QFrame,
    QFileDialog,
    QMessageBox,
    QStackedWidget,
    QSlider,
)

from converters.registry import registry, TargetOption
from converters.base import ConversionOptions, ConversionResult
from services.detector import FileDetector, FileInfo
from services.worker import ConversionWorker
from ui.radial_wheel import RadialWheel
from ui.file_card import FileCard
from ui.batch_view import BatchConvertView
from ui.glass_styles import MAIN_STYLESHEET, PALETTE, FORMAT_NODE_THEMES


class MainWindow(QMainWindow):
    """
    Main application window for QuickConvert matching the official design specification.
    Includes:
    - Radial Wheel Conversion view (with live glowing nodes, progress card, and success card)
    - Batch Conversion queue dashboard
    - Settings & About panels
    - Top header and feature badges
    - Full window drag-and-drop
    """

    def __init__(self, initial_files: Optional[List[str]] = None):
        super().__init__()
        self.setWindowTitle("QuickConvert — Fast Offline File Converter")
        self.resize(1020, 780)
        self.setMinimumSize(860, 680)
        self.setStyleSheet(MAIN_STYLESHEET)
        self.setAcceptDrops(True)

        self.current_file_info: Optional[FileInfo] = None
        self.current_targets: List[TargetOption] = []
        self.selected_target: Optional[str] = "png"
        self.custom_output_dir: Optional[Path] = None
        self.active_worker: Optional[ConversionWorker] = None
        self.last_result: Optional[ConversionResult] = None

        # Settings
        self.setting_jpeg_quality = 90
        self.setting_dpi = 150

        self._init_ui()

        # Load initial file if passed from command line or Windows Explorer context menu
        if initial_files:
            valid_paths = [Path(p) for p in initial_files if Path(p).exists()]
            if valid_paths:
                if len(valid_paths) == 1:
                    self.load_file(valid_paths[0])
                else:
                    self._switch_nav(1)  # Switch to Batch Convert
                    for p in valid_paths:
                        self.batch_view.add_file(p)

    def _init_ui(self):
        root_widget = QWidget()
        self.setCentralWidget(root_widget)

        root_layout = QVBoxLayout(root_widget)
        root_layout.setContentsMargins(24, 18, 24, 18)
        root_layout.setSpacing(14)

        # 1. Top Header Bar
        root_layout.addLayout(self._create_header())

        # 2. Main Content Stage: Sidebar + Stacked Content Area
        stage_layout = QHBoxLayout()
        stage_layout.setSpacing(16)

        # Left Navigation Sidebar
        stage_layout.addWidget(self._create_sidebar(), stretch=0)

        # Right Stacked Pages
        self.stacked_pages = QStackedWidget()
        self.stacked_pages.addWidget(self._create_radial_home_page())   # Page 0: Home / Wheel
        self.batch_view = BatchConvertView()
        self.stacked_pages.addWidget(self.batch_view)                  # Page 1: Batch Convert
        self.stacked_pages.addWidget(self._create_settings_page())     # Page 2: Settings
        self.stacked_pages.addWidget(self._create_about_page())        # Page 3: About
        stage_layout.addWidget(self.stacked_pages, stretch=1)

        root_layout.addLayout(stage_layout, stretch=1)

        # 3. Bottom Feature Badges Bar
        root_layout.addLayout(self._create_bottom_badges())

        # Populate initial targets
        self._refresh_targets()

    def _create_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(14)

        # Logo and Tagline
        logo_layout = QVBoxLayout()
        logo_layout.setSpacing(2)

        title_lbl = QLabel("QuickConvert")
        title_lbl.setStyleSheet(
            "font-size: 26px; font-weight: 800; color: #4338CA; letter-spacing: -0.6px;"
        )
        tagline_lbl = QLabel("Right Click  →  Choose  →  Convert  →  Done")
        tagline_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B;")
        logo_layout.addWidget(title_lbl)
        logo_layout.addWidget(tagline_lbl)
        header.addLayout(logo_layout)

        # Promotional Pill
        promo_pill = QLabel("›  A faster, smarter, and more beautiful way to convert files on Windows.")
        promo_pill.setStyleSheet(
            "background-color: #EDE9FE; color: #5B21B6; font-size: 11px; font-weight: 600; "
            "padding: 6px 14px; border-radius: 14px; border: 1px solid #DDD6FE;"
        )
        header.addWidget(promo_pill)
        header.addStretch(1)

        # Feature Badges
        f1 = QLabel("⚡ One Click")
        f1.setObjectName("featurePill")
        f2 = QLabel("🎯 Interactive Wheel")
        f2.setObjectName("featurePill")
        f3 = QLabel("🔒 Offline & Secure")
        f3.setObjectName("featurePill")
        f4 = QLabel("✨ Beautiful UI")
        f4.setObjectName("featurePill")

        header.addWidget(f1)
        header.addWidget(f2)
        header.addWidget(f3)
        header.addWidget(f4)
        return header

    def _create_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebarFrame")
        sidebar.setFixedWidth(160)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(4, 8, 8, 8)
        layout.setSpacing(6)

        self.nav_home = QPushButton("🏠  Home")
        self.nav_home.setObjectName("navBtn")
        self.nav_home.setProperty("active", "true")
        self.nav_home.setCursor(Qt.PointingHandCursor)
        self.nav_home.clicked.connect(lambda: self._switch_nav(0))

        self.nav_batch = QPushButton("📑  Batch Convert")
        self.nav_batch.setObjectName("navBtn")
        self.nav_batch.setProperty("active", "false")
        self.nav_batch.setCursor(Qt.PointingHandCursor)
        self.nav_batch.clicked.connect(lambda: self._switch_nav(1))

        self.nav_settings = QPushButton("⚙️  Settings")
        self.nav_settings.setObjectName("navBtn")
        self.nav_settings.setProperty("active", "false")
        self.nav_settings.setCursor(Qt.PointingHandCursor)
        self.nav_settings.clicked.connect(lambda: self._switch_nav(2))

        self.nav_about = QPushButton("ℹ️  About")
        self.nav_about.setObjectName("navBtn")
        self.nav_about.setProperty("active", "false")
        self.nav_about.setCursor(Qt.PointingHandCursor)
        self.nav_about.clicked.connect(lambda: self._switch_nav(3))

        layout.addWidget(self.nav_home)
        layout.addWidget(self.nav_batch)
        layout.addWidget(self.nav_settings)
        layout.addWidget(self.nav_about)
        layout.addStretch(1)

        return sidebar

    def _switch_nav(self, page_index: int):
        self.stacked_pages.setCurrentIndex(page_index)
        buttons = [self.nav_home, self.nav_batch, self.nav_settings, self.nav_about]
        for i, btn in enumerate(buttons):
            btn.setProperty("active", "true" if i == page_index else "false")
            btn.setStyle(btn.style())  # Force QSS refresh

    def _create_radial_home_page(self) -> QWidget:
        """Page 0: Radial Conversion Wheel and Selected File View."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Top File Drop Card
        self.file_card = FileCard()
        self.file_card.file_dropped.connect(self.load_file)
        self.file_card.file_cleared.connect(self._on_file_cleared)
        layout.addWidget(self.file_card)

        # Middle Section: Wheel Frame + In-place Conversion Progress Frame
        middle_row = QHBoxLayout()
        middle_row.setSpacing(14)

        # 1. Radial Format Wheel Card (Step 2)
        wheel_card = QFrame()
        wheel_card.setObjectName("glassCard")
        w_layout = QVBoxLayout(wheel_card)
        w_layout.setContentsMargins(8, 8, 8, 8)
        w_layout.setAlignment(Qt.AlignCenter)

        self.radial_wheel = RadialWheel()
        self.radial_wheel.target_selected.connect(self._on_target_selected)
        w_layout.addWidget(self.radial_wheel)
        middle_row.addWidget(wheel_card, stretch=3)

        # 2. Conversion Progress & Result Card (Step 3 & Step 4)
        self.status_card = QFrame()
        self.status_card.setObjectName("glassCard")
        self.status_card.setMinimumWidth(260)
        s_layout = QVBoxLayout(self.status_card)
        s_layout.setContentsMargins(20, 20, 20, 20)
        s_layout.setSpacing(16)
        s_layout.setAlignment(Qt.AlignCenter)

        # Stage A: File Preview and Ready to Convert
        self.preview_badge = QLabel("📄")
        self.preview_badge.setStyleSheet("font-size: 38px;")
        self.preview_title = QLabel("Select File & Format")
        self.preview_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #0F172A;")
        self.preview_meta = QLabel("Supported formats will glow on the wheel")
        self.preview_meta.setStyleSheet("font-size: 12px; color: #64748B;")

        s_layout.addWidget(self.preview_badge, alignment=Qt.AlignCenter)
        s_layout.addWidget(self.preview_title, alignment=Qt.AlignCenter)
        s_layout.addWidget(self.preview_meta, alignment=Qt.AlignCenter)

        # Arrow down
        self.arrow_lbl = QLabel("↓")
        self.arrow_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #8B5CF6;")
        s_layout.addWidget(self.arrow_lbl, alignment=Qt.AlignCenter)

        # Converting / Progress Section
        self.step_target_lbl = QLabel("Target: PNG")
        self.step_target_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #0F172A;")
        s_layout.addWidget(self.step_target_lbl, alignment=Qt.AlignCenter)

        self.prog_detail_lbl = QLabel("Ready to convert")
        self.prog_detail_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
        s_layout.addWidget(self.prog_detail_lbl, alignment=Qt.AlignCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        s_layout.addWidget(self.progress_bar)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondaryBtn")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        s_layout.addWidget(self.cancel_btn, alignment=Qt.AlignCenter)

        # Success Action Buttons (Step 4)
        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.setObjectName("primaryBtn")
        self.open_folder_btn.setCursor(Qt.PointingHandCursor)
        self.open_folder_btn.setVisible(False)
        self.open_folder_btn.clicked.connect(self._on_open_folder_clicked)
        s_layout.addWidget(self.open_folder_btn, alignment=Qt.AlignCenter)

        self.open_file_btn = QPushButton("Open File")
        self.open_file_btn.setObjectName("secondaryBtn")
        self.open_file_btn.setVisible(False)
        self.open_file_btn.clicked.connect(self._on_open_file_clicked)
        s_layout.addWidget(self.open_file_btn, alignment=Qt.AlignCenter)

        middle_row.addWidget(self.status_card, stretch=2)
        layout.addLayout(middle_row, stretch=1)

        # Bottom Configuration & Convert Action Bar
        bottom_bar = QFrame()
        bottom_bar.setObjectName("glassCard")
        b_layout = QHBoxLayout(bottom_bar)
        b_layout.setContentsMargins(16, 10, 16, 10)
        b_layout.setSpacing(12)

        name_lbl = QLabel("Output name:")
        name_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569;")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Auto-generated (e.g. filename_Converted)")
        self.reset_name_btn = QPushButton("Reset")
        self.reset_name_btn.setObjectName("secondaryBtn")
        self.reset_name_btn.clicked.connect(self._on_reset_name_clicked)

        b_layout.addWidget(name_lbl)
        b_layout.addWidget(self.name_input, stretch=1)
        b_layout.addWidget(self.reset_name_btn)

        # Primary Convert Button
        self.convert_btn = QPushButton("Convert to PNG")
        self.convert_btn.setObjectName("primaryBtn")
        self.convert_btn.setCursor(Qt.PointingHandCursor)
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self._on_convert_clicked)
        b_layout.addWidget(self.convert_btn)

        layout.addWidget(bottom_bar)
        return page

    def _create_settings_page(self) -> QWidget:
        """Page 2: Conversion options and preferences."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("glassCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(24, 20, 24, 20)
        c_layout.setSpacing(16)

        title = QLabel("Conversion Settings")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A;")
        c_layout.addWidget(title)

        # JPEG Quality
        lbl_q = QLabel("JPEG / WebP Export Quality (Default: 90%):")
        lbl_q.setStyleSheet("font-size: 13px; font-weight: 600;")
        c_layout.addWidget(lbl_q)
        self.slider_quality = QSlider(Qt.Horizontal)
        self.slider_quality.setRange(50, 100)
        self.slider_quality.setValue(90)
        c_layout.addWidget(self.slider_quality)

        # PDF DPI
        lbl_dpi = QLabel("PDF Page Rendering Resolution (Default: 150 DPI):")
        lbl_dpi.setStyleSheet("font-size: 13px; font-weight: 600;")
        c_layout.addWidget(lbl_dpi)
        self.slider_dpi = QSlider(Qt.Horizontal)
        self.slider_dpi.setRange(72, 300)
        self.slider_dpi.setValue(150)
        c_layout.addWidget(self.slider_dpi)

        # Context menu setup button
        c_layout.addSpacing(10)
        ctx_btn = QPushButton("Re-register Windows Explorer Context Menu")
        ctx_btn.setObjectName("secondaryBtn")
        ctx_btn.clicked.connect(self._run_context_menu_script)
        c_layout.addWidget(ctx_btn)

        c_layout.addStretch(1)
        layout.addWidget(card)
        return page

    def _create_about_page(self) -> QWidget:
        """Page 3: About and offline security info."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)

        card = QFrame()
        card.setObjectName("glassCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(28, 24, 28, 24)
        c_layout.setSpacing(12)

        t = QLabel("About QuickConvert")
        t.setStyleSheet("font-size: 20px; font-weight: 700; color: #4338CA;")
        c_layout.addWidget(t)

        sub = QLabel("Modern Windows 11 Document & Image Converter")
        sub.setStyleSheet("font-size: 13px; color: #64748B;")
        c_layout.addWidget(sub)

        desc = QLabel(
            "QuickConvert runs 100% locally on your computer with zero telemetry and zero cloud uploads.\n\n"
            "• Engine: Python 3.11, PySide6 (Qt6), pypdfium2, Pillow, ReportLab, python-docx\n"
            "• Explorer Integration: Per-user HKCU right-click context menu\n"
            "• Safety: Strict overwrite protection, honest progress, and fail-safe file cleanup."
        )
        desc.setStyleSheet("font-size: 12px; line-height: 1.6; color: #334155;")
        desc.setWordWrap(True)
        c_layout.addWidget(desc)

        c_layout.addStretch(1)
        layout.addWidget(card)
        return page

    def _create_bottom_badges(self) -> QHBoxLayout:
        b_layout = QHBoxLayout()
        b_layout.setSpacing(14)

        b1 = QLabel("💻 Works on all Windows laptops (Windows 11 and later)")
        b1.setObjectName("featurePill")
        b2 = QLabel("🔒 100% Offline (Your files stay on your device)")
        b2.setObjectName("featurePill")
        b3 = QLabel("⚡ Fast & Lightweight (Built for everyday use)")
        b3.setObjectName("featurePill")

        b_layout.addWidget(b1)
        b_layout.addWidget(b2)
        b_layout.addWidget(b3)
        b_layout.addStretch(1)
        return b_layout

    def load_file(self, file_path: Path):
        info = FileDetector.detect(file_path)
        self.current_file_info = info
        self.file_card.set_file(info)

        if not info.is_valid:
            self._refresh_targets()
            self.convert_btn.setEnabled(False)
            self.convert_btn.setText("Cannot convert invalid file")
            self.preview_badge.setText("⚠️")
            self.preview_title.setText("Invalid File")
            self.preview_meta.setText(info.validation_error or "Corrupt file")
            return

        self.preview_badge.setText("📄")
        self.preview_title.setText(info.path.name)
        meta = f"{info.detected_format.upper()} • {info.size_bytes // 1024} KB"
        if info.page_count and info.page_count > 1:
            meta += f" • {info.page_count} pages"
        self.preview_meta.setText(meta)

        self.name_input.setText(f"{info.path.stem}_Converted")
        self._refresh_targets()
        self._update_convert_button()

    def _refresh_targets(self):
        source_fmt = self.current_file_info.detected_format if (self.current_file_info and self.current_file_info.is_valid) else None
        self.current_targets = registry.get_target_options_for_source(source_fmt)
        self.radial_wheel.set_file_info(self.current_file_info, self.current_targets)

    def _on_target_selected(self, target_fmt: str):
        self.selected_target = target_fmt
        self.step_target_lbl.setText(f"Target: {target_fmt.upper()}")
        self._update_convert_button()

    def _update_convert_button(self):
        if not self.current_file_info or not self.current_file_info.is_valid:
            self.convert_btn.setEnabled(False)
            self.convert_btn.setText("Select a file first")
            return

        if not self.selected_target:
            self.convert_btn.setEnabled(False)
            self.convert_btn.setText("Select an output format")
            return

        target_opt = next((t for t in self.current_targets if t.target_format == self.selected_target), None)
        if target_opt and target_opt.is_enabled:
            self.convert_btn.setEnabled(True)
            self.convert_btn.setText(f"Convert to {target_opt.label} ({target_opt.output_extension.upper()})")
        else:
            self.convert_btn.setEnabled(False)
            self.convert_btn.setText("Unsupported Format")

    def _on_file_cleared(self):
        self.current_file_info = None
        self.selected_target = "png"
        self.name_input.clear()
        self.preview_badge.setText("📄")
        self.preview_title.setText("Select File & Format")
        self.preview_meta.setText("Supported formats will glow on the wheel")
        self.step_target_lbl.setText("Target: PNG")
        self.prog_detail_lbl.setText("Ready to convert")
        self.open_folder_btn.setVisible(False)
        self.open_file_btn.setVisible(False)
        self._refresh_targets()
        self._update_convert_button()

    def _on_reset_name_clicked(self):
        if self.current_file_info and self.current_file_info.is_valid:
            self.name_input.setText(f"{self.current_file_info.path.stem}_Converted")

    def _on_convert_clicked(self):
        if not self.current_file_info or not self.selected_target:
            return

        converter = registry.get_converter(
            self.current_file_info.detected_format, self.selected_target
        )
        if not converter:
            QMessageBox.warning(
                self,
                "Unsupported",
                f"No converter found for {self.current_file_info.detected_format} to {self.selected_target}.",
            )
            return

        options = ConversionOptions(
            custom_output_name=self.name_input.text().strip() or None,
            output_dir=self.custom_output_dir or self.current_file_info.path.parent,
            jpeg_quality=self.slider_quality.value(),
            dpi=self.slider_dpi.value(),
        )

        # UI state during conversion (Step 3)
        self.convert_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.cancel_btn.setVisible(True)
        self.open_folder_btn.setVisible(False)
        self.open_file_btn.setVisible(False)
        self.prog_detail_lbl.setText("Starting conversion...")

        self.active_worker = ConversionWorker(
            converter, self.current_file_info.path, options, self
        )
        self.active_worker.progress_changed.connect(self._on_worker_progress)
        self.active_worker.finished.connect(self._on_worker_finished)
        self.active_worker.start()

    def _on_worker_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.prog_detail_lbl.setText(f"{msg} ({pct}%)")

    def _on_cancel_clicked(self):
        if self.active_worker and self.active_worker.isRunning():
            self.prog_detail_lbl.setText("Cancelling...")
            self.active_worker.cancel()

    def _on_worker_finished(self, result: ConversionResult):
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)
        self._update_convert_button()
        self.last_result = result

        if result.success:
            count = len(result.output_files)
            plural = "s" if count > 1 else ""
            self.preview_badge.setText("✅")
            self.preview_title.setText("Conversion Completed!")
            self.preview_meta.setText(f"{count} file{plural} saved in original folder")
            self.prog_detail_lbl.setText("All pages processed successfully.")
            self.open_folder_btn.setVisible(True)
            self.open_file_btn.setVisible(True)
        else:
            self.preview_badge.setText("❌")
            self.preview_title.setText("Conversion Failed")
            err = result.error_message or "Unknown error."
            self.preview_meta.setText(err[:60])
            self.prog_detail_lbl.setText(err)
            self.open_folder_btn.setVisible(False)
            self.open_file_btn.setVisible(False)

    def _on_open_file_clicked(self):
        if self.last_result and self.last_result.primary_output and self.last_result.primary_output.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_result.primary_output)))

    def _on_open_folder_clicked(self):
        if self.last_result and self.last_result.primary_output and self.last_result.primary_output.exists():
            folder = str(self.last_result.primary_output.parent)
            file_path = str(self.last_result.primary_output)
            subprocess.run(["explorer", "/select,", file_path], check=False)

    def _run_context_menu_script(self):
        script = Path(__file__).parent.parent / "install_context_menu.ps1"
        if script.exists():
            subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)], check=False)
            QMessageBox.information(self, "Context Menu", "Windows Explorer context menu registered successfully!")

    # Window-wide Drag and Drop handlers
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
        if urls:
            paths = [Path(u.toLocalFile()) for u in urls if u.toLocalFile()]
            if len(paths) == 1:
                self._switch_nav(0)
                self.load_file(paths[0])
            elif len(paths) > 1:
                self._switch_nav(1)  # Batch mode
                for p in paths:
                    self.batch_view.add_file(p)
            event.acceptProposedAction()
            return
        event.ignore()
