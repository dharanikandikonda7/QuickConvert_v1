import pytest
from pathlib import Path
from services.detector import FileDetector
from utils.sample_generator import generate_sample_files


@pytest.fixture(scope="session")
def sample_files(tmp_path_factory):
    dir_path = tmp_path_factory.mktemp("test_samples")
    return generate_sample_files(dir_path)


def test_detect_multipage_pdf(sample_files):
    info = FileDetector.detect(sample_files["pdf_multipage"])
    assert info.detected_format == "pdf"
    assert info.is_valid is True
    assert info.page_count == 2
    assert info.is_encrypted is False
    assert info.validation_error is None


def test_detect_encrypted_pdf(sample_files):
    info = FileDetector.detect(sample_files["pdf_encrypted"])
    assert info.detected_format == "pdf"
    assert info.is_encrypted is True
    assert info.is_valid is False
    assert "password-protected" in info.validation_error.lower()


def test_detect_empty_file(sample_files):
    info = FileDetector.detect(sample_files["empty"])
    assert info.detected_format == "empty"
    assert info.size_bytes == 0
    assert info.is_valid is False
    assert "0 bytes" in info.validation_error


def test_detect_corrupt_pdf(sample_files):
    info = FileDetector.detect(sample_files["corrupt_pdf"])
    assert info.detected_format == "pdf"
    assert info.is_valid is False
    assert "corrupt" in info.validation_error.lower() or "unreadable" in info.validation_error.lower()


def test_detect_misleading_extension(sample_files):
    # File is named .png but content is JPEG
    info = FileDetector.detect(sample_files["misleading_png"])
    assert info.detected_format == "jpeg"
    assert info.declared_extension == ".png"
    assert info.is_valid is True


def test_detect_png_with_transparency(sample_files):
    info = FileDetector.detect(sample_files["png"])
    assert info.detected_format == "png"
    assert info.is_valid is True
    assert info.has_transparency is True
    assert info.dimensions == (200, 200)


def test_detect_multipage_tiff(sample_files):
    info = FileDetector.detect(sample_files["tiff_multipage"])
    assert info.detected_format == "tiff"
    assert info.is_valid is True
    assert info.page_count == 2


def test_detect_animated_gif(sample_files):
    info = FileDetector.detect(sample_files["gif"])
    assert info.detected_format == "gif"
    assert info.is_valid is True
    assert info.page_count == 2


def test_detect_text(sample_files):
    info = FileDetector.detect(sample_files["txt"])
    assert info.detected_format == "txt"
    assert info.is_valid is True


def test_detect_html(sample_files):
    info = FileDetector.detect(sample_files["html"])
    assert info.detected_format == "html"
    assert info.is_valid is True
