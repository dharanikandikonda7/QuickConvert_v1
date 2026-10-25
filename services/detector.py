#detector.py 
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FileInfo:
    path: Path
    detected_format: str        # e.g. "pdf", "png", "jpeg", "webp", "bmp", "tiff", "gif", "txt", "html", "unknown"
    declared_extension: str     # e.g. ".png"
    size_bytes: int
    is_valid: bool
    is_encrypted: bool = False
    validation_error: Optional[str] = None
    mime_type: str = "application/octet-stream"
    page_count: Optional[int] = None
    dimensions: Optional[tuple[int, int]] = None
    has_transparency: bool = False


class FileDetector:
    """
    Robust file type detector that inspects content magic bytes and structure
    rather than blindly trusting file extensions.
    """

    MAGIC_SIGNATURES = {
        b"%PDF-": "pdf",
        b"\x89PNG\r\n\x1a\n": "png",
        b"\xff\xd8\xff": "jpeg",
        b"GIF87a": "gif",
        b"GIF89a": "gif",
        b"BM": "bmp",
        b"II*\x00": "tiff",
        b"MM\x00*": "tiff",
    }

    MIME_TYPES = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
        "gif": "image/gif",
        "txt": "text/plain",
        "html": "text/html",
        "unknown": "application/octet-stream",
    }

    @classmethod
    def detect(cls, file_path: Path | str) -> FileInfo:
        path = Path(file_path).resolve()

        if not path.exists():
            return FileInfo(
                path=path,
                detected_format="unknown",
                declared_extension=path.suffix.lower(),
                size_bytes=0,
                is_valid=False,
                validation_error=f"File not found: {path.name}",
            )

        if not path.is_file():
            return FileInfo(
                path=path,
                detected_format="unknown",
                declared_extension=path.suffix.lower(),
                size_bytes=0,
                is_valid=False,
                validation_error=f"Path is not a regular file: {path.name}",
            )

        try:
            size = path.stat().st_size
        except OSError as e:
            return FileInfo(
                path=path,
                detected_format="unknown",
                declared_extension=path.suffix.lower(),
                size_bytes=0,
                is_valid=False,
                validation_error=f"Cannot read file metadata: {e}",
            )

        if size == 0:
            return FileInfo(
                path=path,
                detected_format="empty",
                declared_extension=path.suffix.lower(),
                size_bytes=0,
                is_valid=False,
                validation_error="File is 0 bytes (empty file).",
            )

        # Read leading bytes for magic byte matching
        header_sample = b""
        try:
            with open(path, "rb") as f:
                header_sample = f.read(min(size, 4096))
        except Exception as e:
            return FileInfo(
                path=path,
                detected_format="unknown",
                declared_extension=path.suffix.lower(),
                size_bytes=size,
                is_valid=False,
                validation_error=f"Cannot open file for reading: {e}",
            )

        detected_fmt = cls._detect_raw_format(header_sample)

        # Check zip_or_docx
        if detected_fmt == "zip_or_docx":
            import zipfile
            try:
                with zipfile.ZipFile(path, "r") as zf:
                    names = zf.namelist()
                    if "word/document.xml" in names:
                        detected_fmt = "docx"
                    elif "xl/workbook.xml" in names:
                        detected_fmt = "xlsx"
                    elif "ppt/presentation.xml" in names:
                        detected_fmt = "pptx"
                    else:
                        detected_fmt = "unknown"
            except Exception:
                detected_fmt = "unknown"

        # If still unknown, check text / html
        if detected_fmt == "unknown":
            detected_fmt = cls._detect_text_format(header_sample)

        # Fallback to extension check if magic bytes didn't identify it
        ext_clean = path.suffix.lower().lstrip(".")
        if ext_clean in ("jpg", "jpeg") and detected_fmt == "unknown":
            detected_fmt = "jpeg"
        elif ext_clean in ("txt", "md", "csv", "log") and detected_fmt == "unknown":
            detected_fmt = "txt"
        elif ext_clean == "docx" and detected_fmt == "unknown":
            detected_fmt = "docx"

        info = FileInfo(
            path=path,
            detected_format=detected_fmt,
            declared_extension=path.suffix.lower(),
            size_bytes=size,
            is_valid=True,
            mime_type=cls.MIME_TYPES.get(detected_fmt, "application/octet-stream"),
        )

        # Deep validation based on detected format
        cls._validate_and_enrich(info)
        return info

    @classmethod
    def _detect_raw_format(cls, header: bytes) -> str:
        # Check standard prefix signatures
        for sig, fmt in cls.MAGIC_SIGNATURES.items():
            if header.startswith(sig):
                return fmt

        # PDF sometimes has leading whitespace or comments before %PDF-
        if b"%PDF-" in header[:1024]:
            return "pdf"

        # WebP signature: "RIFF" .... "WEBP"
        if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            return "webp"

        # DOCX / ZIP package signature
        if header.startswith(b"PK\x03\x04"):
            return "zip_or_docx"

        return "unknown"

    @classmethod
    def _detect_text_format(cls, sample: bytes) -> str:
        # Binary null byte detection
        if b"\x00" in sample:
            return "unknown"

        # Try utf-8 decode
        try:
            text = sample.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = sample.decode("latin-1")
            except Exception:
                return "unknown"

        clean_text = text.strip().lower()
        if clean_text.startswith("<!doctype html") or "<html" in clean_text[:500]:
            return "html"

        return "txt"

    @classmethod
    def _validate_and_enrich(cls, info: FileInfo) -> None:
        """Runs format-specific integrity checks."""
        fmt = info.detected_format

        if fmt == "pdf":
            cls._validate_pdf(info)
        elif fmt in ("png", "jpeg", "webp", "bmp", "tiff", "gif"):
            cls._validate_image(info)
        elif fmt in ("txt", "html"):
            cls._validate_text(info)

    @classmethod
    def _validate_pdf(cls, info: FileInfo) -> None:
        try:
            import pypdfium2 as pdfium
            try:
                doc = pdfium.PdfDocument(info.path)
            except Exception as e:
                err_str = str(e).lower()
                if "password" in err_str or "encrypted" in err_str:
                    info.is_encrypted = True
                    info.is_valid = False
                    info.validation_error = "PDF is password-protected or encrypted."
                    return
                raise

            info.page_count = len(doc)
            if info.page_count == 0:
                info.is_valid = False
                info.validation_error = "PDF document contains 0 pages."
            else:
                p0 = doc[0]
                w, h = p0.get_size()
                info.dimensions = (int(w), int(h))
            doc.close()
        except ImportError:
            pass
        except Exception as e:
            info.is_valid = False
            info.validation_error = f"Corrupt or unreadable PDF: {str(e)}"

    @classmethod
    def _validate_image(cls, info: FileInfo) -> None:
        try:
            from PIL import Image, ImageSequence
            with Image.open(info.path) as img:
                img.verify()
                info.dimensions = img.size
                
                # Check for transparency
                info.has_transparency = img.mode in ("RGBA", "LA") or (
                    img.mode == "P" and "transparency" in img.info
                )
                
            # Check frame count if multipage format
            if info.detected_format in ("tiff", "gif"):
                with Image.open(info.path) as img:
                    frames = 0
                    for _ in ImageSequence.Iterator(img):
                        frames += 1
                    info.page_count = frames
        except ImportError:
            pass
        except Exception as e:
            info.is_valid = False
            info.validation_error = f"Corrupt or invalid image: {str(e)}"

    @classmethod
    def _validate_text(cls, info: FileInfo) -> None:
        try:
            with open(info.path, "rb") as f:
                raw = f.read(min(info.size_bytes, 1024 * 1024))
            try:
                raw.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    raw.decode("latin-1")
                except Exception as e:
                    info.is_valid = False
                    info.validation_error = f"Unable to decode text: {e}"
        except Exception as e:
            info.is_valid = False
            info.validation_error = f"Cannot read text file: {e}"
