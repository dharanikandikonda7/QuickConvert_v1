import pytest
from pathlib import Path
from PIL import Image
import pypdfium2 as pdfium

from converters.registry import registry
from converters.base import ConversionOptions
from utils.sample_generator import generate_sample_files


@pytest.fixture(scope="session")
def sample_files(tmp_path_factory):
    dir_path = tmp_path_factory.mktemp("test_samples")
    return generate_sample_files(dir_path)


@pytest.fixture
def output_dir(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    return out


# 1. PDF to PNG (every page separate image)
def test_pdf_to_png(sample_files, output_dir):
    converter = registry.get_converter("pdf", "png")
    assert converter is not None

    opts = ConversionOptions(output_dir=output_dir)
    res = converter.convert(sample_files["pdf_multipage"], opts)

    assert res.success is True
    assert len(res.output_files) == 2
    for out_path in res.output_files:
        assert out_path.exists()
        assert out_path.stat().st_size > 0
        with Image.open(out_path) as im:
            assert im.format == "PNG"


# 2. PDF to JPEG (every page separate image)
def test_pdf_to_jpeg(sample_files, output_dir):
    converter = registry.get_converter("pdf", "jpeg")
    assert converter is not None

    opts = ConversionOptions(output_dir=output_dir, jpeg_quality=85)
    res = converter.convert(sample_files["pdf_multipage"], opts)

    assert res.success is True
    assert len(res.output_files) == 2
    for out_path in res.output_files:
        assert out_path.exists()
        assert out_path.stat().st_size > 0
        with Image.open(out_path) as im:
            assert im.format == "JPEG"


# 3. PDF to TXT
def test_pdf_to_txt(sample_files, output_dir):
    converter = registry.get_converter("pdf", "txt")
    assert converter is not None

    opts = ConversionOptions(output_dir=output_dir)
    res = converter.convert(sample_files["pdf_multipage"], opts)

    assert res.success is True
    assert len(res.output_files) == 1
    txt_file = res.output_files[0]
    content = txt_file.read_text(encoding="utf-8")
    assert "Page 1" in content
    assert "Page 2" in content
    assert "QuickConvert Test Document" in content


# 4. TXT to PDF
def test_txt_to_pdf(sample_files, output_dir):
    converter = registry.get_converter("txt", "pdf")
    assert converter is not None

    opts = ConversionOptions(output_dir=output_dir)
    res = converter.convert(sample_files["txt"], opts)

    assert res.success is True
    assert len(res.output_files) == 1
    pdf_file = res.output_files[0]
    assert pdf_file.exists()
    assert pdf_file.stat().st_size > 0

    # Verify output is valid PDF
    doc = pdfium.PdfDocument(pdf_file)
    assert len(doc) >= 1
    doc.close()


# 5. PNG to JPEG
def test_png_to_jpeg(sample_files, output_dir):
    converter = registry.get_converter("png", "jpeg")
    opts = ConversionOptions(output_dir=output_dir)
    res = converter.convert(sample_files["png"], opts)

    assert res.success is True
    out_file = res.output_files[0]
    with Image.open(out_file) as im:
        assert im.format == "JPEG"
        assert im.mode == "RGB"


# 6. JPEG to PNG
def test_jpeg_to_png(sample_files, output_dir):
    converter = registry.get_converter("jpeg", "png")
    opts = ConversionOptions(output_dir=output_dir)
    res = converter.convert(sample_files["jpeg"], opts)

    assert res.success is True
    out_file = res.output_files[0]
    with Image.open(out_file) as im:
        assert im.format == "PNG"


# 7. PNG & JPEG to WebP
def test_png_and_jpeg_to_webp(sample_files, output_dir):
    converter_png = registry.get_converter("png", "webp")
    res1 = converter_png.convert(sample_files["png"], ConversionOptions(output_dir=output_dir))
    assert res1.success is True
    with Image.open(res1.output_files[0]) as im:
        assert im.format == "WEBP"

    converter_jpg = registry.get_converter("jpeg", "webp")
    res2 = converter_jpg.convert(sample_files["jpeg"], ConversionOptions(output_dir=output_dir))
    assert res2.success is True
    with Image.open(res2.output_files[0]) as im:
        assert im.format == "WEBP"


# 8. WebP to PNG and JPEG
def test_webp_to_png_and_jpeg(sample_files, output_dir):
    converter_png = registry.get_converter("webp", "png")
    res1 = converter_png.convert(sample_files["webp"], ConversionOptions(output_dir=output_dir))
    assert res1.success is True
    with Image.open(res1.output_files[0]) as im:
        assert im.format == "PNG"

    converter_jpg = registry.get_converter("webp", "jpeg")
    res2 = converter_jpg.convert(sample_files["webp"], ConversionOptions(output_dir=output_dir))
    assert res2.success is True
    with Image.open(res2.output_files[0]) as im:
        assert im.format == "JPEG"


# 9. BMP to PNG and JPEG
def test_bmp_to_png_and_jpeg(sample_files, output_dir):
    converter_png = registry.get_converter("bmp", "png")
    res1 = converter_png.convert(sample_files["bmp"], ConversionOptions(output_dir=output_dir))
    assert res1.success is True

    converter_jpg = registry.get_converter("bmp", "jpeg")
    res2 = converter_jpg.convert(sample_files["bmp"], ConversionOptions(output_dir=output_dir))
    assert res2.success is True


# 10. TIFF to PNG / JPEG (multipage TIFF)
def test_multipage_tiff_to_png(sample_files, output_dir):
    converter = registry.get_converter("tiff", "png")
    res = converter.convert(sample_files["tiff_multipage"], ConversionOptions(output_dir=output_dir))

    assert res.success is True
    assert len(res.output_files) == 2
    for out_path in res.output_files:
        assert out_path.exists()
        with Image.open(out_path) as im:
            assert im.format == "PNG"


# 11. GIF to PNG
def test_gif_to_png(sample_files, output_dir):
    converter = registry.get_converter("gif", "png")
    res = converter.convert(sample_files["gif"], ConversionOptions(output_dir=output_dir))

    assert res.success is True
    assert len(res.output_files) == 2  # animated GIF has 2 frames


# 12. Supported Image to PDF
def test_image_to_pdf(sample_files, output_dir):
    converter = registry.get_converter("png", "pdf")
    res = converter.convert(sample_files["png"], ConversionOptions(output_dir=output_dir))

    assert res.success is True
    out_pdf = res.output_files[0]
    assert out_pdf.exists()
    doc = pdfium.PdfDocument(out_pdf)
    assert len(doc) == 1
    doc.close()


# 13. TXT to HTML and HTML to TXT
def test_txt_to_html_and_back(sample_files, output_dir):
    converter_html = registry.get_converter("txt", "html")
    res_html = converter_html.convert(sample_files["txt"], ConversionOptions(output_dir=output_dir))
    assert res_html.success is True
    html_file = res_html.output_files[0]
    html_content = html_file.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html_content
    assert "QuickConvert" in html_content

    # Now convert HTML back to TXT
    converter_txt = registry.get_converter("html", "txt")
    res_txt = converter_txt.convert(sample_files["html"], ConversionOptions(output_dir=output_dir))
    assert res_txt.success is True
    txt_file = res_txt.output_files[0]
    txt_content = txt_file.read_text(encoding="utf-8")
    assert "Heading Level 1" in txt_content
    assert "First item" in txt_content


# 14. Overwrite Protection: Never overwrite existing file
def test_overwrite_protection(sample_files, output_dir):
    converter = registry.get_converter("png", "jpeg")
    opts = ConversionOptions(output_dir=output_dir, custom_output_name="test_doc")

    # Run 1
    res1 = converter.convert(sample_files["png"], opts)
    assert res1.success is True
    path1 = res1.output_files[0]
    assert path1.name == "test_doc.jpg"

    # Run 2 with same name - must not overwrite path1
    res2 = converter.convert(sample_files["png"], opts)
    assert res2.success is True
    path2 = res2.output_files[0]
    assert path2.name == "test_doc (1).jpg"
    assert path1.exists()
    assert path2.exists()
    assert path1 != path2


# 15. Encrypted PDF failure handling
def test_encrypted_pdf_failure(sample_files, output_dir):
    converter = registry.get_converter("pdf", "png")
    opts = ConversionOptions(output_dir=output_dir)
    res = converter.convert(sample_files["pdf_encrypted"], opts)

    assert res.success is False
    assert "password-protected" in res.error_message.lower()
    assert len(res.output_files) == 0


# 16. DOCX to TXT
def test_docx_to_txt(sample_files, output_dir):
    converter = registry.get_converter("docx", "txt")
    assert converter is not None
    res = converter.convert(sample_files["docx"], ConversionOptions(output_dir=output_dir))
    assert res.success is True
    out_file = res.output_files[0]
    content = out_file.read_text(encoding="utf-8")
    assert "QuickConvert Word Document" in content
    assert "Features Overview" in content


# 17. DOCX to PDF
def test_docx_to_pdf(sample_files, output_dir):
    converter = registry.get_converter("docx", "pdf")
    assert converter is not None
    res = converter.convert(sample_files["docx"], ConversionOptions(output_dir=output_dir))
    assert res.success is True
    out_file = res.output_files[0]
    assert out_file.exists()
    assert out_file.stat().st_size > 0


# 18. DOCX to HTML
def test_docx_to_html(sample_files, output_dir):
    converter = registry.get_converter("docx", "html")
    assert converter is not None
    res = converter.convert(sample_files["docx"], ConversionOptions(output_dir=output_dir))
    assert res.success is True
    content = res.output_files[0].read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "QuickConvert Word Document" in content


# 19. TXT to DOCX
def test_txt_to_docx(sample_files, output_dir):
    converter = registry.get_converter("txt", "docx")
    assert converter is not None
    res = converter.convert(sample_files["txt"], ConversionOptions(output_dir=output_dir))
    assert res.success is True
    out_file = res.output_files[0]
    assert out_file.suffix.lower() == ".docx"
    assert out_file.exists()
    assert out_file.stat().st_size > 0
