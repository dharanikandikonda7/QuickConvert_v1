import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional

import pypdfium2 as pdfium
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from converters.base import BaseConverter, ConversionOptions, ConversionResult, ProgressCallback
from utils.path_helpers import sanitize_filename, get_unique_output_path


def read_text_with_encoding_fallback(source_path: Path) -> str:
    """
    Reads text file with strict encoding fallback:
    utf-8-sig -> utf-16 (if BOM) -> cp1252 -> latin-1.
    Normalizes only line endings (\r\n and \r -> \n).
    Never replaces characters with '?'.
    """
    raw = source_path.read_bytes()

    # UTF-16 with BOM
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        try:
            text = raw.decode("utf-16")
            return text.replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            pass

    # UTF-8 / UTF-8 with BOM
    try:
        text = raw.decode("utf-8-sig")
        return text.replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeDecodeError:
        pass

    # Windows-1252
    try:
        text = raw.decode("cp1252")
        return text.replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeDecodeError:
        pass

    # Latin-1 (decodes every byte 0x00-0xFF without error)
    text = raw.decode("latin-1")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def get_dejavu_font_path() -> Path:
    """Locates the bundled DejaVuSansMono.ttf font file."""
    base_dir = Path(__file__).resolve().parent.parent
    candidate = base_dir / "assets" / "fonts" / "DejaVuSansMono.ttf"
    if candidate.exists():
        return candidate
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        p = Path(sys._MEIPASS) / "assets" / "fonts" / "DejaVuSansMono.ttf"
        if p.exists():
            return p
    return candidate


def ensure_dejavu_font_registered() -> bool:
    """Registers the bundled DejaVuSansMono font with ReportLab if available."""
    if "DejaVuSansMono" in pdfmetrics.getRegisteredFontNames():
        return True
    font_path = get_dejavu_font_path()
    if font_path.exists():
        try:
            pdfmetrics.registerFont(TTFont("DejaVuSansMono", str(font_path)))
            return True
        except Exception:
            return False
    return False


def select_pdf_font_for_text(text: str) -> str:
    """
    Selects Courier if text is pure Latin-1; otherwise uses DejaVuSansMono
    for full Unicode monospace coverage.
    """
    try:
        text.encode("latin-1")
        return "Courier"
    except UnicodeEncodeError:
        if ensure_dejavu_font_registered():
            return "DejaVuSansMono"
        return "Courier"


class StrictHTMLToTextParser(HTMLParser):
    """
    Converts HTML markup to clean, unescaped plain text strictly following rules:
    - Removes <script>, <style>, <head>, and comments.
    - Block elements become newlines.
    - <li> becomes "- ".
    - <td> and <th> separated by tab.
    - Preserves <pre> whitespace exactly; elsewhere collapses whitespace like a browser.
    - Decodes entities. Never fetches external resources.
    """

    def __init__(self):
        super().__init__()
        self.output: List[str] = []
        self._skip_depth = 0
        self._in_pre = 0

    def handle_comment(self, data: str) -> None:
        pass

    def handle_starttag(self, tag: str, attrs) -> None:
        t = tag.lower()
        if t in ("script", "style", "head"):
            self._skip_depth += 1
        elif self._skip_depth > 0:
            return
        elif t == "pre":
            self._in_pre += 1
        elif t in (
            "p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr",
            "blockquote", "section", "article", "header", "footer",
        ):
            if self.output and not self.output[-1].endswith("\n"):
                self.output.append("\n")
        elif t == "br":
            self.output.append("\n")
        elif t == "li":
            if self.output and not self.output[-1].endswith("\n"):
                self.output.append("\n")
            self.output.append("- ")
        elif t in ("td", "th"):
            if self.output and not self.output[-1].endswith("\n") and not self.output[-1].endswith("\t"):
                self.output.append("\t")

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in ("script", "style", "head"):
            self._skip_depth = max(0, self._skip_depth - 1)
        elif self._skip_depth > 0:
            return
        elif t == "pre":
            self._in_pre = max(0, self._in_pre - 1)
        elif t in (
            "p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr",
            "blockquote", "section", "article", "header", "footer", "li",
        ):
            if self.output and not self.output[-1].endswith("\n"):
                self.output.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        if self._in_pre > 0:
            # Inside <pre>, HTMLParser automatically unescapes entities
            self.output.append(data)
        else:
            if not data.strip():
                return
            cleaned = re.sub(r"[ \t\r\n]+", " ", data)
            if cleaned:
                self.output.append(cleaned)

    def get_text(self) -> str:
        return "".join(self.output)


class TxtToPdfConverter(BaseConverter):
    """
    Converts plain text to PDF with strict formatting rules:
    - A4 (595x842 pt), 54 pt margins.
    - Courier 10 pt (or bundled DejaVuSansMono for non-Latin-1), line height 1.2x (12 pt leading).
    - Text color pure black (0, 0, 0) on white. NEVER shrinks font.
    - Preserves line breaks, blank lines, leading spaces; tab = 4 spaces.
    - Long lines wrapped using font metrics and flow onto extra pages.
    """

    def __init__(self):
        self.source_format = "txt"
        self.target_format = "pdf"
        self.output_extension = "pdf"
        self.display_name = "PDF Document"
        self.is_multipage_capable = True

    def convert(
        self,
        source_path: Path,
        options: ConversionOptions,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        if progress_cb:
            progress_cb(10, "Reading text file with encoding detection...")

        target_dir = options.output_dir or source_path.parent
        raw_name = options.custom_output_name or f"{source_path.stem}_Converted"
        base_name = sanitize_filename(raw_name)
        out_path = get_unique_output_path(target_dir, base_name, self.output_extension)

        try:
            content = read_text_with_encoding_fallback(source_path)

            if progress_cb:
                progress_cb(25, "Analyzing text and selecting font...")

            font_name = select_pdf_font_for_text(content)

            # Geometry specifications
            page_w, page_h = 595.0, 842.0  # A4
            margin = 54.0
            usable_w = page_w - margin * 2.0  # 487 pt
            line_height = 12.0  # 1.2x of 10 pt
            font_size = 10.0

            # Wrap lines using font metrics, preserving leading spaces and tabs
            raw_lines = content.split("\n")
            wrapped_lines: List[str] = []

            for raw_line in raw_lines:
                line = raw_line.replace("\t", "    ")
                if not line:
                    wrapped_lines.append("")
                    continue

                if pdfmetrics.stringWidth(line, font_name, font_size) <= usable_w:
                    wrapped_lines.append(line)
                else:
                    # Wrap long line greedily using exact character widths
                    current = ""
                    for char in line:
                        candidate = current + char
                        if pdfmetrics.stringWidth(candidate, font_name, font_size) <= usable_w:
                            current = candidate
                        else:
                            if current:
                                wrapped_lines.append(current)
                            current = char
                    if current:
                        wrapped_lines.append(current)

            if progress_cb:
                progress_cb(50, "Rendering PDF pages...")

            pdf_canvas = canvas.Canvas(str(out_path), pagesize=(page_w, page_h))
            y_start = page_h - margin - font_size
            y = y_start
            pdf_canvas.setFont(font_name, font_size)
            pdf_canvas.setFillColorRGB(0.0, 0.0, 0.0)

            total_lines = len(wrapped_lines)
            for idx, line in enumerate(wrapped_lines):
                if idx % 100 == 0 and progress_cb:
                    pct = 50 + int((idx / max(1, total_lines)) * 40)
                    progress_cb(pct, f"Writing line {idx + 1} of {total_lines}...")

                if y - line_height < margin:
                    pdf_canvas.showPage()
                    y = y_start
                    pdf_canvas.setFont(font_name, font_size)
                    pdf_canvas.setFillColorRGB(0.0, 0.0, 0.0)

                if line:
                    pdf_canvas.drawString(margin, y, line)
                y -= line_height

            pdf_canvas.showPage()
            pdf_canvas.save()

            # Verification: reopen and verify valid PDF
            if not out_path.exists() or out_path.stat().st_size == 0:
                raise RuntimeError("PDF generation produced an empty file.")

            with pdfium.PdfDocument(out_path) as verify_doc:
                if len(verify_doc) == 0:
                    raise RuntimeError("Verification failed: generated PDF has 0 pages.")

            if progress_cb:
                progress_cb(100, "PDF created successfully.")

            return ConversionResult(
                success=True,
                source_file=source_path,
                output_files=[out_path],
                details="Converted text to multi-page PDF document.",
            )

        except Exception as e:
            if out_path.exists():
                try:
                    out_path.unlink()
                except OSError:
                    pass
            return ConversionResult(
                success=False,
                source_file=source_path,
                output_files=[],
                error_message=f"Text to PDF conversion failed: {str(e)}",
            )


class TxtToHtmlConverter(BaseConverter):
    """Converts plain text to strict, minimal HTML5 with fixed CSS and escaping."""

    def __init__(self):
        self.source_format = "txt"
        self.target_format = "html"
        self.output_extension = "html"
        self.display_name = "HTML Document"

    def convert(
        self,
        source_path: Path,
        options: ConversionOptions,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        if progress_cb:
            progress_cb(20, "Reading text file with encoding detection...")

        target_dir = options.output_dir or source_path.parent
        raw_name = options.custom_output_name or f"{source_path.stem}_Converted"
        base_name = sanitize_filename(raw_name)
        out_path = get_unique_output_path(target_dir, base_name, self.output_extension)

        try:
            content = read_text_with_encoding_fallback(source_path)

            if progress_cb:
                progress_cb(50, "Generating HTML template...")

            title = html.escape(source_path.stem)
            escaped_body = html.escape(content)

            # Strict minimal HTML5 with specified fixed CSS
            html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        pre {{
            font-family: Consolas, "Courier New", monospace;
            font-size: 14px;
            color: #000;
            background: #fff;
            white-space: pre-wrap;
            margin: 1em;
        }}
    </style>
</head>
<body>
    <pre>{escaped_body}</pre>
</body>
</html>
"""
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html_document)

            if not out_path.exists() or out_path.stat().st_size == 0:
                raise RuntimeError("HTML output verification failed.")

            if progress_cb:
                progress_cb(100, "HTML created successfully.")

            return ConversionResult(
                success=True,
                source_file=source_path,
                output_files=[out_path],
                details="Converted text to styled HTML document.",
            )

        except Exception as e:
            if out_path.exists():
                try:
                    out_path.unlink()
                except OSError:
                    pass
            return ConversionResult(
                success=False,
                source_file=source_path,
                output_files=[],
                error_message=f"Text to HTML conversion failed: {str(e)}",
            )


class HtmlToTxtConverter(BaseConverter):
    """Converts HTML markup to clean, unescaped plain text strictly preserving structure."""

    def __init__(self):
        self.source_format = "html"
        self.target_format = "txt"
        self.output_extension = "txt"
        self.display_name = "Text Document (TXT)"

    def convert(
        self,
        source_path: Path,
        options: ConversionOptions,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        if progress_cb:
            progress_cb(20, "Reading HTML document...")

        target_dir = options.output_dir or source_path.parent
        raw_name = options.custom_output_name or f"{source_path.stem}_Converted"
        base_name = sanitize_filename(raw_name)
        out_path = get_unique_output_path(target_dir, base_name, self.output_extension)

        try:
            raw_html = read_text_with_encoding_fallback(source_path)

            if progress_cb:
                progress_cb(60, "Parsing HTML tags and unescaping entities...")

            parser = StrictHTMLToTextParser()
            parser.feed(raw_html)
            text_result = parser.get_text()

            with open(out_path, "w", encoding="utf-8-sig") as f:
                f.write(text_result)

            if not out_path.exists() or out_path.stat().st_size == 0 and len(text_result.strip()) > 0:
                raise RuntimeError("TXT output verification failed.")

            if progress_cb:
                progress_cb(100, "TXT created successfully.")

            return ConversionResult(
                success=True,
                source_file=source_path,
                output_files=[out_path],
                details="Extracted clean plain text from HTML.",
            )

        except Exception as e:
            if out_path.exists():
                try:
                    out_path.unlink()
                except OSError:
                    pass
            return ConversionResult(
                success=False,
                source_file=source_path,
                output_files=[],
                error_message=f"HTML to text conversion failed: {str(e)}",
            )
