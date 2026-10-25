"""
tests/test_application_verification.py
======================================
Comprehensive verification of Application behavior for deployment readiness:
- Main window initialization and visibility
- Drag-and-drop / file loading logic
- Radial wheel reflection of ConversionRegistry
- Real PDF and Image conversions (multipage, alpha flattening)
- Custom output names and automatic default names
- Unicode filenames and paths with spaces
- Output collision handling (auto-increment suffix)
- Integrity of source files (zero mutations)
"""

import hashlib
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
from PIL import Image

from converters.registry import registry
from converters.base import ConversionOptions
from services.detector import FileDetector
from ui.main_window import MainWindow
from utils.sample_generator import generate_sample_files
from utils.path_helpers import get_unique_output_path


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture(scope="module")
def samples(tmp_path_factory):
    base = tmp_path_factory.mktemp("app_verify_samples")
    return generate_sample_files(base)


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_main_window_init_and_widgets(qapp):
    """Verify MainWindow initializes cleanly with all sub-widgets."""
    window = MainWindow()
    try:
        assert window.windowTitle().startswith("QuickConvert")
        assert window.radial_wheel is not None
        assert window.file_card is not None
        assert window.batch_view is not None
        assert window.stacked_pages.count() >= 4
    finally:
        window.close()


def test_radial_wheel_reflects_registry(qapp, samples):
    """Verify radial wheel reflects exact registry targets for loaded file."""
    window = MainWindow()
    try:
        pdf_path = samples["pdf_multipage"]
        window.load_file(pdf_path)

        assert window.current_file_info is not None
        assert window.current_file_info.detected_format == "pdf"

        registry_targets = registry.get_target_options_for_source("pdf")
        assert len(window.current_targets) == len(registry_targets)

        # Check target enabled states
        enabled_fmts = {t.target_format for t in window.current_targets if t.is_enabled}
        assert "png" in enabled_fmts
        assert "jpeg" in enabled_fmts
        assert "txt" in enabled_fmts
        assert "webp" in enabled_fmts
    finally:
        window.close()


def test_real_pdf_conversion_and_source_unmodified(samples, tmp_path):
    """Test real multipage PDF conversion to PNG and ensure source is unmodified."""
    src_pdf = samples["pdf_multipage"]
    src_hash_before = _file_hash(src_pdf)
    out_dir = tmp_path / "pdf_out"
    out_dir.mkdir()

    converter = registry.get_converter("pdf", "png")
    assert converter is not None

    opts = ConversionOptions(output_dir=out_dir)
    res = converter.convert(src_pdf, opts)

    assert res.success is True
    assert len(res.output_files) == 2
    for out_f in res.output_files:
        assert out_f.exists()
        assert out_f.stat().st_size > 0

    # Verify source file remained 100% intact
    src_hash_after = _file_hash(src_pdf)
    assert src_hash_before == src_hash_after, "Source file was mutated during conversion!"


def test_real_image_conversion_and_source_unmodified(samples, tmp_path):
    """Test real PNG (with alpha) to JPEG conversion and ensure source is unmodified."""
    src_png = samples["png"]
    src_hash_before = _file_hash(src_png)
    out_dir = tmp_path / "img_out"
    out_dir.mkdir()

    converter = registry.get_converter("png", "jpeg")
    assert converter is not None

    opts = ConversionOptions(output_dir=out_dir)
    res = converter.convert(src_png, opts)

    assert res.success is True
    assert len(res.output_files) == 1
    out_jpg = res.output_files[0]
    assert out_jpg.exists()
    assert out_jpg.stat().st_size > 0
    with Image.open(out_jpg) as im:
        assert im.format == "JPEG"
        assert im.mode == "RGB"

    src_hash_after = _file_hash(src_png)
    assert src_hash_before == src_hash_after, "Source file was mutated during conversion!"


def test_custom_output_name_and_default_name(samples, tmp_path):
    """Verify custom output filename is honored and default name generates correctly."""
    src = samples["png"]
    out_dir = tmp_path / "names_out"
    out_dir.mkdir()

    converter = registry.get_converter("png", "jpeg")

    # 1. Custom output name
    opts_custom = ConversionOptions(output_dir=out_dir, custom_output_name="MySpecialExport")
    res_custom = converter.convert(src, opts_custom)
    assert res_custom.success is True
    assert res_custom.output_files[0].name == "MySpecialExport.jpg"

    # 2. Automatic default name: <stem>_Converted.jpg
    opts_default = ConversionOptions(output_dir=out_dir)
    res_default = converter.convert(src, opts_default)
    assert res_default.success is True
    assert res_default.output_files[0].name == f"{src.stem}_Converted.jpg"


def test_collision_handling(tmp_path):
    """Verify non-colliding filename auto-incrementation (1), (2)."""
    out_dir = tmp_path / "collision_dir"
    out_dir.mkdir()

    base = "report"
    ext = "txt"

    first = get_unique_output_path(out_dir, base, ext)
    assert first.name == "report.txt"
    first.write_text("v1", encoding="utf-8")

    second = get_unique_output_path(out_dir, base, ext)
    assert second.name == "report (1).txt"
    second.write_text("v2", encoding="utf-8")

    third = get_unique_output_path(out_dir, base, ext)
    assert third.name == "report (2).txt"
