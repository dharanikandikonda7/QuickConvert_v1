"""
converters/office_converters.py

DOCX -> TXT and DOCX -> HTML (python-docx, no Word needed).

DOCX -> PDF and PDF -> DOCX now live in word_converters.py (real Microsoft Word
engine). They are re-exported here so older imports keep working.
"""
from __future__ import annotations

import html
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from .base import (
    BaseConverter,
    ConversionOptions,
    ConversionResult,
    ProgressCallback,
)
from .word_converters import (  # noqa: F401  (re-exports)
    DocxToPdfConverter,
    PdfToDocxConverter,
    _plan_output,
    _report,
    detect_msword,
    find_libreoffice,
)


def _load_docx(path: Path):
    import docx
    try:
        return docx.Document(str(path))
    except Exception as e:
        raise RuntimeError(f"Corrupt or unreadable DOCX: {e}")


def _iter_blocks(document):
    """Yield paragraphs and tables in real document order."""
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    for child in document.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            yield Paragraph(child, document)
        elif tag == "tbl":
            yield Table(child, document)


# ---------------------------------------------------------------------------
# DOCX -> TXT
# ---------------------------------------------------------------------------
class DocxToTextConverter(BaseConverter):
    source_format = "docx"
    target_format = "txt"
    display_name = "TXT"
    output_extension = "txt"
    is_multipage_capable = False

    def convert(
        self,
        source_path: Path,
        options: ConversionOptions,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        source = Path(source_path)
        final_out: Optional[Path] = None
        try:
            _report(progress_cb, 10, "Reading document...")
            document = _load_docx(source)
            lines = []
            for block in _iter_blocks(document):
                if hasattr(block, "rows"):  # table: one row per line, cells tab-separated
                    for row in block.rows:
                        lines.append("\t".join(c.text.replace("\n", " ") for c in row.cells))
                else:
                    lines.append(block.text)
            text = "\n".join(lines)
            if not text.strip():
                return ConversionResult(False, source, error_message="Document contains no text.")

            _report(progress_cb, 70, "Writing text file...")
            final_out = _plan_output(source, options, ".txt")
            final_out.write_text(text, encoding="utf-8-sig", newline="\n")
            if final_out.stat().st_size == 0:
                raise RuntimeError("Conversion produced an empty file.")
            _report(progress_cb, 100, "Done")
            return ConversionResult(True, source, [final_out],
                                    details="Plain text only - formatting is not kept.")
        except InterruptedError:
            if final_out is not None:
                final_out.unlink(missing_ok=True)
            raise
        except Exception as e:
            if final_out is not None:
                final_out.unlink(missing_ok=True)
            return ConversionResult(False, source, error_message=f"Conversion failed: {e}")


# ---------------------------------------------------------------------------
# DOCX -> HTML
# ---------------------------------------------------------------------------
def _run_html(run) -> str:
    text = html.escape(run.text)
    if not text:
        return ""
    text = text.replace("\t", "&emsp;")
    styles = []
    try:
        if run.font.color is not None and run.font.color.rgb is not None:
            styles.append(f"color:#{run.font.color.rgb}")
        if run.font.size is not None:
            styles.append(f"font-size:{run.font.size.pt}pt")
        if run.font.name:
            styles.append(f"font-family:'{run.font.name}'")
    except Exception:
        pass
    if styles:
        text = f'<span style="{";".join(styles)}">{text}</span>'
    if run.bold:
        text = f"<b>{text}</b>"
    if run.italic:
        text = f"<i>{text}</i>"
    if run.underline:
        text = f"<u>{text}</u>"
    return text


def _paragraph_inner(paragraph) -> str:
    parts = []
    inner = getattr(paragraph, "iter_inner_content", None)
    items = inner() if inner else paragraph.runs
    for item in items:
        if hasattr(item, "url"):  # hyperlink
            label = "".join(_run_html(r) for r in item.runs) or html.escape(item.text)
            url = html.escape(item.url or "", quote=True)
            parts.append(f'<a href="{url}">{label}</a>' if url else label)
        else:
            parts.append(_run_html(item))
    return "".join(parts)


class DocxToHtmlConverter(BaseConverter):
    source_format = "docx"
    target_format = "html"
    display_name = "HTML"
    output_extension = "html"
    is_multipage_capable = False

    def convert(
        self,
        source_path: Path,
        options: ConversionOptions,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        source = Path(source_path)
        final_out: Optional[Path] = None
        try:
            _report(progress_cb, 10, "Reading document...")
            document = _load_docx(source)
            body = []
            in_list = False
            for block in _iter_blocks(document):
                if hasattr(block, "rows"):
                    if in_list:
                        body.append("</ul>")
                        in_list = False
                    body.append('<table border="1" cellspacing="0" cellpadding="4">')
                    for row in block.rows:
                        cells = "".join(
                            f"<td>{html.escape(c.text).replace(chr(10), '<br>')}</td>"
                            for c in row.cells)
                        body.append(f"<tr>{cells}</tr>")
                    body.append("</table>")
                    continue
                style = (block.style.name if block.style is not None else "") or ""
                inner = _paragraph_inner(block)
                if style.lower().startswith("list"):
                    if not in_list:
                        body.append("<ul>")
                        in_list = True
                    body.append(f"<li>{inner}</li>")
                    continue
                if in_list:
                    body.append("</ul>")
                    in_list = False
                if style.lower().startswith("heading") and inner.strip():
                    level = "".join(ch for ch in style if ch.isdigit()) or "1"
                    level = min(max(int(level), 1), 6)
                    body.append(f"<h{level}>{inner}</h{level}>")
                elif style.lower() == "title" and inner.strip():
                    body.append(f"<h1>{inner}</h1>")
                else:
                    body.append(f"<p>{inner}</p>" if inner.strip() else "<p>&nbsp;</p>")
            if in_list:
                body.append("</ul>")

            _report(progress_cb, 70, "Writing HTML file...")
            title = html.escape(source.stem)
            page = (
                "<!DOCTYPE html>\n<html>\n<head>\n<meta charset=\"utf-8\">\n"
                f"<title>{title}</title>\n"
                "<style>body{font-family:'Times New Roman',serif;font-size:12pt;"
                "color:#000;background:#fff;max-width:800px;margin:2em auto;}"
                "p{margin:0.4em 0;}</style>\n</head>\n<body>\n"
                + "\n".join(body) + "\n</body>\n</html>\n")
            final_out = _plan_output(source, options, ".html")
            final_out.write_text(page, encoding="utf-8", newline="\n")
            if final_out.stat().st_size == 0:
                raise RuntimeError("Conversion produced an empty file.")
            _report(progress_cb, 100, "Done")
            return ConversionResult(
                True, source, [final_out],
                details="Basic HTML: text styling, lists, tables and links are kept; "
                        "page layout and images are not.")
        except InterruptedError:
            if final_out is not None:
                final_out.unlink(missing_ok=True)
            raise
        except Exception as e:
            if final_out is not None:
                final_out.unlink(missing_ok=True)
            return ConversionResult(False, source, error_message=f"Conversion failed: {e}")
