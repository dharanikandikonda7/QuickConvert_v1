"""
converters/registry.py

Single place that decides which conversions exist and whether they are enabled.
PRD rule: NEVER enable a conversion that has no working implementation.

Public API used by the app (do not rename):
    registry                                  shared instance
    ConversionRegistry                        the class
    TargetOption                              one wheel node (dataclass)
    registry.get_converter(src, tgt)          converter instance or None
    registry.get_target_options_for_source(f) list[TargetOption] (f may be None)
    registry._converters                      dict[(src, tgt)] -> converter instance
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from converters.base import BaseConverter
from converters.image_converters import GenericImageConverter
from converters.office_converters import DocxToHtmlConverter, DocxToTextConverter
from converters.pdf_converters import PdfToImageConverter, PdfToTextConverter
from converters.text_converters import (
    HtmlToTxtConverter,
    TxtToHtmlConverter,
    TxtToPdfConverter,
)
from converters.word_converters import (
    DocxToPdfConverter,
    PdfToDocxConverter,
    detect_msword,
    find_libreoffice,
)

# (format key, label shown on the wheel / button, file extension without dot)
TARGET_CATALOG: List[Tuple[str, str, str]] = [
    ("png", "PNG", "png"),
    ("jpeg", "JPG", "jpg"),
    ("webp", "WebP", "webp"),
    ("pdf", "PDF", "pdf"),
    ("txt", "TXT", "txt"),
    ("html", "HTML", "html"),
    ("bmp", "BMP", "bmp"),
    ("tiff", "TIFF", "tiff"),
    ("gif", "GIF", "gif"),
    ("docx", "Word", "docx"),
    ("xlsx", "Excel", "xlsx"),
]
_CATALOG_BY_KEY = {k: (label, ext) for k, label, ext in TARGET_CATALOG}

IMAGE_FORMATS = ["png", "jpeg", "webp", "bmp", "tiff", "gif"]

_ALIASES = {"jpg": "jpeg", "tif": "tiff", "htm": "html"}

NO_MSWORD = "Requires Microsoft Word 2013 or newer to be installed."
NO_OFFICE = ("Requires Microsoft Word or LibreOffice to be installed "
             "(needed to keep fonts, colors and layout exactly).")
NO_FILE = "No valid file loaded. Select a file first."


def normalize_format(fmt: Optional[str]) -> str:
    fmt = (fmt or "").strip().lower().lstrip(".")
    return _ALIASES.get(fmt, fmt)


@dataclass
class TargetOption:
    """One node on the radial wheel."""
    target_format: str
    label: str
    output_extension: str
    is_enabled: bool = False
    disabled_reason: str = ""
    lossy_note: Optional[str] = None
    display_name: str = ""

    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.label


def _lossy_note(src: str, tgt: str) -> Optional[str]:
    if (src, tgt) == ("pdf", "docx"):
        return ("Approximate: layout, columns and fonts may shift, and scanned PDFs "
                "are not turned into editable text.")
    if (src, tgt) == ("pdf", "txt"):
        return "Plain text only - formatting is not kept."
    if (src, tgt) in (("docx", "txt"),):
        return "Plain text only - formatting is not kept."
    if (src, tgt) == ("docx", "html"):
        return "Basic HTML: page layout and images are not kept."
    if tgt == "gif" and src != "gif":
        return "GIF is limited to 256 colors."
    if tgt in ("jpeg", "webp") and src in ("png", "bmp", "tiff", "gif", "pdf"):
        return "Lossy format: tiny quality differences are possible."
    return None


class ConversionRegistry:
    def __init__(self):
        # Detect renderers ONCE (the UI asks for targets on every refresh)
        self._has_msword = detect_msword()
        self._has_libreoffice = find_libreoffice() is not None
        self._converters: Dict[Tuple[str, str], BaseConverter] = {}
        self._build()

    # ---- renderer availability -----------------------------------------
    @property
    def has_msword(self) -> bool:
        return self._has_msword

    @property
    def has_libreoffice(self) -> bool:
        return self._has_libreoffice

    @property
    def has_office_renderer(self) -> bool:
        return self._has_msword or self._has_libreoffice

    # ---- registration --------------------------------------------------
    def _register(self, converter: BaseConverter) -> None:
        key = (normalize_format(converter.source_format),
               normalize_format(converter.target_format))
        self._converters[key] = converter

    def _build(self) -> None:
        # image <-> image and image -> PDF
        for src in IMAGE_FORMATS:
            for tgt in IMAGE_FORMATS + ["pdf"]:
                if src != tgt:
                    label, ext = _CATALOG_BY_KEY[tgt]
                    self._register(GenericImageConverter(src, tgt, ext, label))

        # PDF -> images / text / Word
        for tgt in ("png", "jpeg", "webp"):
            label, ext = _CATALOG_BY_KEY[tgt]
            self._register(PdfToImageConverter(tgt, ext, label))
        self._register(PdfToTextConverter())
        self._register(PdfToDocxConverter())

        # text / html
        self._register(TxtToPdfConverter())
        self._register(TxtToHtmlConverter())
        self._register(HtmlToTxtConverter())

        # Word documents
        self._register(DocxToPdfConverter())
        self._register(DocxToTextConverter())
        self._register(DocxToHtmlConverter())

    # ---- availability --------------------------------------------------
    def _availability(self, src: str, tgt: str) -> Tuple[bool, str]:
        if src == tgt:
            return False, f"Source is already in {src.upper()} format."
        if (src, tgt) not in self._converters:
            label = _CATALOG_BY_KEY.get(tgt, (tgt.upper(), ""))[0]
            return False, (f"Converting {src.upper()} to {label} is not supported yet.")
        if (src, tgt) == ("docx", "pdf") and not self.has_office_renderer:
            return False, NO_OFFICE
        if (src, tgt) == ("pdf", "docx") and not self.has_msword:
            return False, NO_MSWORD
        return True, ""

    # ---- public API ----------------------------------------------------
    def get_converter(self, src_fmt: Optional[str], tgt_fmt: Optional[str]) -> Optional[BaseConverter]:
        """Converter instance (same object every time), or None if none exists."""
        return self._converters.get((normalize_format(src_fmt), normalize_format(tgt_fmt)))

    def get_target_options_for_source(self, source_fmt: Optional[str]) -> List[TargetOption]:
        src = normalize_format(source_fmt)
        options: List[TargetOption] = []
        for key, label, ext in TARGET_CATALOG:
            if not src or src in ("unknown", "empty"):
                enabled, reason = False, NO_FILE if not src else (
                    "This file type is not recognised, so it cannot be converted.")
            else:
                enabled, reason = self._availability(src, key)
            options.append(TargetOption(
                target_format=key,
                label=label,
                output_extension=ext,
                is_enabled=enabled,
                disabled_reason=reason,
                lossy_note=_lossy_note(src, key) if enabled else None,
            ))
        return options


# Shared instance used by the whole app
registry = ConversionRegistry()
