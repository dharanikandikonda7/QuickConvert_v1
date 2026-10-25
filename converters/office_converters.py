"""
converters/office_converters.py

DOCX -> PDF using Microsoft Word through the `docx2pdf` library (best fidelity,
because Word itself lays out the page). LibreOffice is the fallback if Word is
not installed. There is NO text-extraction fallback: if neither renderer exists,
the conversion fails with a clear message.

NOTE: I could not see your base.py, so the class below uses a typical signature.
If your BaseConverter uses different method names/arguments, keep your existing
signatures and just paste the body of convert() into them.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .base import BaseConverter  # adjust if your base class lives elsewhere


# --------------------------------------------------------------------------
# Renderer detection
# --------------------------------------------------------------------------
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


def find_libreoffice() -> str | None:
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


# --------------------------------------------------------------------------
# Word (docx2pdf) path
# --------------------------------------------------------------------------
def _word_to_pdf(src: Path, dst: Path) -> None:
    """Convert via docx2pdf (drives real Microsoft Word through COM)."""
    # docx2pdf prints a tqdm progress bar; in a windowed PyInstaller app
    # sys.stdout/stderr are None and tqdm would crash. Give them a sink.
    devnull = None
    if sys.stdout is None or sys.stderr is None:
        devnull = open(os.devnull, "w")
        if sys.stdout is None:
            sys.stdout = devnull
        if sys.stderr is None:
            sys.stderr = devnull

    import pythoncom  # from pywin32
    pythoncom.CoInitialize()  # required: we run inside a QThread, not the main thread
    try:
        from docx2pdf import convert
        convert(str(src.resolve()), str(dst.resolve()))
    finally:
        pythoncom.CoUninitialize()


# --------------------------------------------------------------------------
# LibreOffice path (fallback)
# --------------------------------------------------------------------------
def _libreoffice_to_pdf(src: Path, dst: Path, timeout: int = 180) -> None:
    soffice = find_libreoffice()
    if not soffice:
        raise RuntimeError("LibreOffice not found.")
    with tempfile.TemporaryDirectory() as tmp:
        profile = Path(tmp) / "profile"
        outdir = Path(tmp) / "out"
        outdir.mkdir()
        cmd = [
            soffice,
            f"-env:UserInstallation={profile.resolve().as_uri()}",
            "--headless", "--norestore", "--nolockcheck",
            "--convert-to", "pdf",
            "--outdir", str(outdir),
            str(src.resolve()),
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


# --------------------------------------------------------------------------
# Output verification (never claim success on a bad file)
# --------------------------------------------------------------------------
def _verify_pdf(path: Path) -> int:
    """Return page count or raise."""
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


# --------------------------------------------------------------------------
# Converter
# --------------------------------------------------------------------------
class DocxToPdfConverter(BaseConverter):
    source_format = "docx"
    target_format = "pdf"

    @staticmethod
    def is_available() -> bool:
        return detect_msword() or find_libreoffice() is not None

    @staticmethod
    def unavailable_reason() -> str:
        return ("Requires Microsoft Word or LibreOffice to be installed "
                "(needed to keep fonts, colors and layout exactly).")

    def convert(self, src_path, out_path, progress_cb=None, cancel_check=None):
        src, dst = Path(src_path), Path(out_path)
        tmp_out = dst.with_suffix(".part.pdf")
        if progress_cb:
            progress_cb(5)

        errors = []
        done = False
        try:
            if detect_msword():
                try:
                    _word_to_pdf(src, tmp_out)
                    done = True
                except Exception as e:  # fall through to LibreOffice
                    errors.append(f"Word: {e}")
                    tmp_out.unlink(missing_ok=True)
            if not done and find_libreoffice():
                try:
                    _libreoffice_to_pdf(src, tmp_out)
                    done = True
                except Exception as e:
                    errors.append(f"LibreOffice: {e}")
                    tmp_out.unlink(missing_ok=True)
            if not done:
                detail = "; ".join(errors) or "no renderer installed"
                raise RuntimeError(
                    f"Could not convert with a layout-accurate renderer ({detail}).")

            if cancel_check and cancel_check():
                raise RuntimeError("Conversion was cancelled.")
            if progress_cb:
                progress_cb(90)

            pages = _verify_pdf(tmp_out)
            os.replace(tmp_out, dst)  # atomic; only a verified file becomes the output
            if progress_cb:
                progress_cb(100)
            return [dst]
        finally:
            tmp_out.unlink(missing_ok=True)  # never leave partial output behind


# --------------------------------------------------------------------------
# PDF -> DOCX (Microsoft Word opens the PDF and re-saves it as .docx)
# --------------------------------------------------------------------------
WD_FORMAT_XML_DOCUMENT = 16  # wdFormatXMLDocument (.docx)


def _pdf_to_docx_word(src: Path, dst: Path) -> None:
    """Let Word's own PDF Reflow engine convert PDF -> DOCX (Word 2013+)."""
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")  # private instance
        word.Visible = False
        word.DisplayAlerts = 0  # wdAlertsNone: no popups, e.g. the "PDF will be converted" prompt
        doc = word.Documents.Open(
            str(src.resolve()),
            ConfirmConversions=False,
            ReadOnly=True,
            AddToRecentFiles=False,
        )
        doc.SaveAs2(str(dst.resolve()), FileFormat=WD_FORMAT_XML_DOCUMENT)
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


def _verify_docx(path: Path, source_pdf: Path) -> None:
    """Output must open as a DOCX and must not be empty."""
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError("Conversion produced an empty file.")
    import docx  # python-docx
    try:
        d = docx.Document(str(path))
    except Exception as e:
        raise RuntimeError(f"Output is not a valid DOCX: {e}")
    has_text = any(p.text.strip() for p in d.paragraphs) or any(
        c.text.strip() for t in d.tables for r in t.rows for c in r.cells)
    has_images = len(d.inline_shapes) > 0
    if not (has_text or has_images):
        raise RuntimeError("Output DOCX is empty.")


class PdfToDocxConverter(BaseConverter):
    source_format = "pdf"
    target_format = "docx"
    # Shown in the success banner / fidelity report. PDF has no real paragraph
    # structure, so this can NEVER be a guaranteed exact copy.
    warning = ("PDF to Word is approximate: layout, columns and fonts may shift, "
               "and scanned (image-only) PDFs are not turned into editable text.")

    @staticmethod
    def is_available() -> bool:
        return detect_msword()

    @staticmethod
    def unavailable_reason() -> str:
        return "Requires Microsoft Word 2013 or newer to be installed."

    def convert(self, src_path, out_path, progress_cb=None, cancel_check=None):
        src, dst = Path(src_path), Path(out_path)
        tmp_out = dst.with_suffix(".part.docx")
        if progress_cb:
            progress_cb(5)
        try:
            if not detect_msword():
                raise RuntimeError(self.unavailable_reason())
            try:
                _pdf_to_docx_word(src, tmp_out)
            except Exception as e:
                raise RuntimeError(f"Word could not convert this PDF: {e}")

            if cancel_check and cancel_check():
                raise RuntimeError("Conversion was cancelled.")
            if progress_cb:
                progress_cb(90)

            _verify_docx(tmp_out, src)
            os.replace(tmp_out, dst)
            if progress_cb:
                progress_cb(100)
            return [dst]
        finally:
            tmp_out.unlink(missing_ok=True)
