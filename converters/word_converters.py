"""
converters/word_converters.py

DOCX -> PDF and PDF -> DOCX using the REAL Microsoft Word engine, so the output
keeps fonts, sizes, colors, shaded headings, bullets, tables and hyperlinks.

- DOCX -> PDF: Word first, LibreOffice second. NO text-extraction fallback ever.
  If neither is installed the conversion fails with a clear message.
- PDF -> DOCX: Word only (approximate by nature - a warning is always attached).

Why not call docx2pdf directly? It uses the shared Word instance and calls
Quit() at the end, which can close a Word window you already have open, and it
prints a progress bar that crashes windowed PyInstaller apps. This file drives
the SAME Word engine through COM (pywin32) in a private, hidden Word instance.

Matches converters/base.py: convert(source_path, options, progress_cb) -> ConversionResult
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from .base import (
    BaseConverter,
    ConversionOptions,
    ConversionResult,
    ProgressCallback,
)

WD_FORMAT_PDF = 17            # wdFormatPDF
WD_FORMAT_XML_DOCUMENT = 16   # wdFormatXMLDocument (.docx)


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------
def detect_msword() -> bool:
    """True if Microsoft Word is installed (COM class registered)."""
    if os.name != "nt":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"):
            return True
    except OSError:
        return False


def find_libreoffice() -> Optional[str]:
    """Path to soffice.exe, or None."""
    found = shutil.which("soffice") or shutil.which("soffice.exe")
    if found:
        return found
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if base:
            p = Path(base) / "LibreOffice" / "program" / "soffice.exe"
            if p.exists():
                return str(p)
    return None


# ---------------------------------------------------------------------------
# Small helpers (self-contained so this file has no hidden dependencies)
# ---------------------------------------------------------------------------
_BAD_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe_stem(name: str) -> str:
    name = _BAD_CHARS.sub("_", name).strip().strip(".")
    return name or "output"


def _unique_path(directory: Path, stem: str, ext: str) -> Path:
    """file.pdf, then 'file (1).pdf', 'file (2).pdf' ... never overwrites."""
    candidate = directory / f"{stem}{ext}"
    n = 1
    while candidate.exists():
        candidate = directory / f"{stem} ({n}){ext}"
        n += 1
    return candidate


def _plan_output(source: Path, options: ConversionOptions, ext: str) -> Path:
    out_dir = Path(options.output_dir) if options.output_dir else source.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = options.custom_output_name or f"{source.stem}_Converted"
    return _unique_path(out_dir, _safe_stem(stem), ext)


def _report(cb: Optional[ProgressCallback], pct: int, msg: str) -> None:
    # The worker's callback raises InterruptedError when the user cancels.
    if cb:
        cb(pct, msg)


# ---------------------------------------------------------------------------
# Word COM engines
# ---------------------------------------------------------------------------
def _word_save_as(src: Path, dst: Path, file_format: int) -> None:
    """Open src in a private hidden Word instance and save as dst."""
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()  # needed: we run inside a QThread
    word = None
    doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")  # private instance
        word.Visible = False
        word.DisplayAlerts = 0  # no popups
        doc = word.Documents.Open(
            str(src),
            ConfirmConversions=False,
            ReadOnly=True,
            AddToRecentFiles=False,
        )
        doc.SaveAs2(str(dst), FileFormat=file_format)
    finally:
        try:
            if doc is not None:
                doc.Close(False)
        except Exception:
            pass
        try:
            if word is not None:
                word.Quit(False)
        except Exception:
            pass
        pythoncom.CoUninitialize()


def _libreoffice_to_pdf(src: Path, dst: Path, workdir: Path, timeout: int = 180) -> None:
    soffice = find_libreoffice()
    if not soffice:
        raise RuntimeError("LibreOffice not found.")
    profile = workdir / "lo_profile"
    outdir = workdir / "lo_out"
    outdir.mkdir(exist_ok=True)
    cmd = [
        soffice,
        f"-env:UserInstallation={profile.resolve().as_uri()}",
        "--headless", "--norestore", "--nolockcheck",
        "--convert-to", "pdf",
        "--outdir", str(outdir),
        str(src),
    ]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.run(cmd, check=True, capture_output=True,
                       timeout=timeout, creationflags=flags)
    except subprocess.TimeoutExpired:
        raise RuntimeError("LibreOffice timed out.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"LibreOffice failed: {e.stderr.decode(errors='ignore')[:200]}")
    produced = outdir / (src.stem + ".pdf")
    if not produced.exists():
        raise RuntimeError("LibreOffice produced no output.")
    shutil.move(str(produced), str(dst))


# ---------------------------------------------------------------------------
# Output verification (never claim success on a bad file)
# ---------------------------------------------------------------------------
def _verify_pdf(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError("Conversion produced an empty file.")
    with open(path, "rb") as f:
        if not f.read(5).startswith(b"%PDF"):
            raise RuntimeError("Output is not a valid PDF.")
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(str(path))
    try:
        pages = len(pdf)
    finally:
        pdf.close()
    if pages < 1:
        raise RuntimeError("Output PDF has no pages.")
    return pages


def _verify_docx(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError("Conversion produced an empty file.")
    import docx  # python-docx
    try:
        d = docx.Document(str(path))
    except Exception as e:
        raise RuntimeError(f"Output is not a valid DOCX: {e}")
    has_text = any(p.text.strip() for p in d.paragraphs) or any(
        c.text.strip() for t in d.tables for r in t.rows for c in r.cells)
    if not (has_text or len(d.inline_shapes) > 0):
        raise RuntimeError("Output DOCX is empty.")


# ---------------------------------------------------------------------------
# Converters
# ---------------------------------------------------------------------------
class DocxToPdfConverter(BaseConverter):
    source_format = "docx"
    target_format = "pdf"
    display_name = "PDF"
    output_extension = "pdf"
    is_multipage_capable = False

    def convert(
        self,
        source_path: Path,
        options: ConversionOptions,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        source = Path(source_path)
        work = Path(tempfile.mkdtemp(prefix="qc_docx2pdf_"))
        final_out: Optional[Path] = None
        try:
            _report(progress_cb, 8, "Checking document...")
            with open(source, "rb") as f:
                if f.read(4) != b"PK\x03\x04":
                    return ConversionResult(
                        False, source,
                        error_message="Not a valid DOCX (it may be password-protected or corrupt).")

            has_word = detect_msword()
            has_lo = find_libreoffice() is not None
            if not (has_word or has_lo):
                return ConversionResult(
                    False, source,
                    error_message=("Cannot convert: Microsoft Word or LibreOffice is required "
                                   "to keep fonts, colors and layout exactly."))

            # Work on a copy: source stays untouched and Word makes no lock file next to it.
            tmp_in = work / "input.docx"
            shutil.copy2(source, tmp_in)
            tmp_out = work / "output.pdf"

            engine = None
            errors = []
            _report(progress_cb, 20, "Rendering with Microsoft Word..." if has_word
                    else "Rendering with LibreOffice...")
            if has_word:
                try:
                    _word_save_as(tmp_in, tmp_out, WD_FORMAT_PDF)
                    engine = "Microsoft Word"
                except Exception as e:
                    errors.append(f"Word: {e}")
                    tmp_out.unlink(missing_ok=True)
            if engine is None and has_lo:
                _report(progress_cb, 40, "Rendering with LibreOffice...")
                try:
                    _libreoffice_to_pdf(tmp_in, tmp_out, work)
                    engine = "LibreOffice"
                except Exception as e:
                    errors.append(f"LibreOffice: {e}")
                    tmp_out.unlink(missing_ok=True)
            if engine is None:
                return ConversionResult(
                    False, source,
                    error_message="Conversion failed (" + "; ".join(errors) + ").")

            _report(progress_cb, 85, "Verifying output...")
            pages = _verify_pdf(tmp_out)

            final_out = _plan_output(source, options, ".pdf")
            shutil.move(str(tmp_out), str(final_out))
            _report(progress_cb, 100, "Done")
            return ConversionResult(
                True, source, [final_out],
                details=f"Converted with {engine} ({pages} page{'s' if pages != 1 else ''}).")
        except InterruptedError:
            if final_out is not None:
                final_out.unlink(missing_ok=True)
            raise  # worker reports "cancelled"
        except Exception as e:
            if final_out is not None:
                final_out.unlink(missing_ok=True)
            return ConversionResult(False, source, error_message=f"Conversion failed: {e}")
        finally:
            shutil.rmtree(work, ignore_errors=True)


class PdfToDocxConverter(BaseConverter):
    source_format = "pdf"
    target_format = "docx"
    display_name = "DOCX"
    output_extension = "docx"
    is_multipage_capable = False

    WARNING = ("PDF to Word is approximate: layout, columns and fonts may shift, "
               "and scanned (image-only) PDFs are not turned into editable text.")

    def convert(
        self,
        source_path: Path,
        options: ConversionOptions,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        source = Path(source_path)
        work = Path(tempfile.mkdtemp(prefix="qc_pdf2docx_"))
        final_out: Optional[Path] = None
        try:
            if not detect_msword():
                return ConversionResult(
                    False, source,
                    error_message="PDF to Word requires Microsoft Word 2013 or newer.")

            _report(progress_cb, 10, "Opening PDF in Microsoft Word...")
            tmp_in = work / "input.pdf"
            shutil.copy2(source, tmp_in)
            tmp_out = work / "output.docx"

            _report(progress_cb, 25, "Converting with Microsoft Word...")
            try:
                _word_save_as(tmp_in, tmp_out, WD_FORMAT_XML_DOCUMENT)
            except Exception as e:
                return ConversionResult(False, source,
                                        error_message=f"Word could not convert this PDF: {e}")

            _report(progress_cb, 85, "Verifying output...")
            _verify_docx(tmp_out)

            final_out = _plan_output(source, options, ".docx")
            shutil.move(str(tmp_out), str(final_out))
            _report(progress_cb, 100, "Done")
            return ConversionResult(True, source, [final_out],
                                    details="Converted with Microsoft Word. " + self.WARNING)
        except InterruptedError:
            if final_out is not None:
                final_out.unlink(missing_ok=True)
            raise
        except Exception as e:
            if final_out is not None:
                final_out.unlink(missing_ok=True)
            return ConversionResult(False, source, error_message=f"Conversion failed: {e}")
        finally:
            shutil.rmtree(work, ignore_errors=True)
