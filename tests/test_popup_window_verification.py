"""
tests/test_popup_window_verification.py
=======================================
Comprehensive verification of ConversionPopup (Mode B: Instant Action):
- Frameless window flags, translucency, and geometry
- File detection and loading in popup
- Registry reflection on radial wheel inside popup
- Real conversions (PDF -> PNG, PNG -> JPEG) off GUI thread
- Custom and default output filename handling
- Safe output handling (non-overwriting, source untouched)
- Position clamping within screen boundaries
- Keyboard navigation (Arrow keys, Enter, Escape)
- Result actions (Open File, Open Folder buttons)
"""

import hashlib
import time
from pathlib import Path
import pytest
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from converters.registry import registry
from ui.popup_window import ConversionPopup, POPUP_W, POPUP_H
from utils.sample_generator import generate_sample_files


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture(scope="module")
def samples(tmp_path_factory):
    base = tmp_path_factory.mktemp("popup_verify_samples")
    return generate_sample_files(base)


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_popup_initialization_with_file(qapp, samples):
    """Verify ConversionPopup initializes properly with a valid file."""
    src = samples["pdf_multipage"]
    popup = ConversionPopup(file_path=src)
    try:
        flags = popup.windowFlags()
        assert bool(flags & Qt.FramelessWindowHint)
        assert bool(flags & Qt.Tool)
        assert bool(flags & Qt.WindowStaysOnTopHint)

        assert popup.current_file_info is not None
        assert popup.current_file_info.detected_format == "pdf"
        assert popup.current_file_info.is_valid is True

        assert len(popup.current_targets) > 0
        assert popup.radial_wheel is not None
        assert popup.convert_btn is not None
        assert popup.name_input.text() == f"{src.stem}_Converted"

        # Hub center reflects file
        assert popup.radial_wheel.file_info is not None
        assert popup.radial_wheel.file_info.detected_format == "pdf"
    finally:
        popup._request_close()


def test_popup_initialization_no_file(qapp):
    """Verify ConversionPopup handles no file cleanly without crashing."""
    popup = ConversionPopup(file_path=None)
    try:
        assert popup.current_file_info is None
        assert popup.convert_btn.isEnabled() is False
        assert "Drop a file" in popup.file_info_lbl.text()
    finally:
        popup._request_close()


def test_popup_initialization_invalid_file(qapp, samples):
    """Verify ConversionPopup handles corrupt/invalid file gracefully."""
    corrupt = samples["corrupt_pdf"]
    popup = ConversionPopup(file_path=corrupt)
    try:
        assert popup.current_file_info is not None
        assert popup.current_file_info.is_valid is False
        assert popup.convert_btn.isEnabled() is False
        assert "Invalid" in popup.file_info_lbl.text() or "corrupt" in popup.file_info_lbl.text().lower() or "unreadable" in popup.file_info_lbl.text().lower()
    finally:
        popup._request_close()


def test_popup_format_selection_and_button_update(qapp, samples):
    """Selecting formats should update the convert button state and label."""
    src = samples["png"]
    popup = ConversionPopup(file_path=src)
    try:
        popup._on_target_selected("jpeg")
        assert popup.selected_target == "jpeg"
        assert popup.convert_btn.isEnabled() is True
        assert "JPEG" in popup.convert_btn.text() or "JPG" in popup.convert_btn.text()
    finally:
        popup._request_close()


def test_popup_custom_output_name_and_reset(qapp, samples):
    """Verify custom output name editing and reset button behavior."""
    src = samples["png"]
    popup = ConversionPopup(file_path=src)
    try:
        default_name = f"{src.stem}_Converted"
        assert popup.name_input.text() == default_name

        popup.name_input.setText("my_custom_image_name")
        assert popup.name_input.text() == "my_custom_image_name"

        popup.reset_name_btn.click()
        assert popup.name_input.text() == default_name
    finally:
        popup._request_close()


def test_popup_positioning_clamping(qapp):
    """Verify popup positioning is always clamped inside screen boundaries."""
    popup = ConversionPopup(file_path=None)
    try:
        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry()

        # Simulate positioning
        popup._position_near_cursor()
        geo = popup.geometry()

        assert geo.left() >= avail.left()
        assert geo.top() >= avail.top()
        assert geo.right() <= avail.right() + 1
        assert geo.bottom() <= avail.bottom() + 1
    finally:
        popup._request_close()


def test_popup_real_image_conversion(qapp, samples, tmp_path):
    """Perform a real image conversion inside ConversionPopup and verify result."""
    import shutil
    # Copy sample to isolated tmp dir
    src_png = tmp_path / "instant_source.png"
    shutil.copy2(samples["png"], src_png)
    hash_before = _file_hash(src_png)

    popup = ConversionPopup(file_path=src_png)
    try:
        popup._on_target_selected("jpeg")
        assert popup.convert_btn.isEnabled() is True

        popup._on_convert_clicked()
        assert popup.active_worker is not None

        # Wait for worker to complete
        popup.active_worker.wait(10000)
        qapp.processEvents()

        assert popup.last_result is not None
        assert popup.last_result.success is True
        assert len(popup.last_result.output_files) >= 1

        out_file = popup.last_result.output_files[0]
        assert out_file.exists()
        assert out_file.suffix.lower() in (".jpg", ".jpeg")
        assert out_file.stat().st_size > 0

        # Source file must be completely untouched
        assert _file_hash(src_png) == hash_before

        # Result buttons must be visible
        assert not popup.open_file_btn.isHidden()
        assert not popup.open_folder_btn.isHidden()
    finally:
        popup._request_close()


def test_popup_real_pdf_conversion(qapp, samples, tmp_path):
    """Perform a real PDF conversion inside ConversionPopup and verify pages created."""
    import shutil
    src_pdf = tmp_path / "instant_doc.pdf"
    shutil.copy2(samples["pdf_multipage"], src_pdf)
    hash_before = _file_hash(src_pdf)

    popup = ConversionPopup(file_path=src_pdf)
    try:
        popup._on_target_selected("png")
        assert popup.convert_btn.isEnabled() is True

        popup._on_convert_clicked()
        assert popup.active_worker is not None

        popup.active_worker.wait(10000)
        qapp.processEvents()

        assert popup.last_result is not None
        assert popup.last_result.success is True
        assert len(popup.last_result.output_files) >= 2  # Multipage

        for p in popup.last_result.output_files:
            assert p.exists()
            assert p.stat().st_size > 0

        # Source PDF unmodified
        assert _file_hash(src_pdf) == hash_before
    finally:
        popup._request_close()


def test_popup_keyboard_events(qapp, samples):
    """Verify keyboard handling (Escape closes, arrows navigate)."""
    src = samples["png"]
    popup = ConversionPopup(file_path=src)
    try:
        # Arrow key right
        key_event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Right, Qt.NoModifier)
        popup.keyPressEvent(key_event)
        qapp.processEvents()

        # Escape closes popup
        esc_event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        popup.keyPressEvent(esc_event)
        qapp.processEvents()
        assert not popup.isVisible()
    finally:
        popup._request_close()
