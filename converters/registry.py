"""
converters/registry.py

Single place that decides which conversions exist and whether they are enabled.
Rule from the PRD: NEVER enable a conversion that has no working implementation.

NOTE: I could not see your original registry.py. The public methods below
(can_convert / availability / targets_for / get_converter) are my best guess.
If your UI calls different method names, keep those names and move the logic over,
or send me your old registry.py and I will match it exactly.
"""
from __future__ import annotations

import inspect

from .office_converters import detect_msword, find_libreoffice

# Wheel order (matches PRD matrix)
ALL_FORMATS = ["png", "jpeg", "webp", "pdf", "txt", "html", "bmp", "tiff", "gif", "docx"]
IMAGE_FORMATS = {"png", "jpeg", "webp", "bmp", "tiff", "gif"}

_ALIASES = {"jpg": "jpeg", "tif": "tiff", "htm": "html", "doc": "docx"}

NO_MSWORD = "Requires Microsoft Word 2013 or newer to be installed."
NO_OFFICE = ("Requires Microsoft Word or LibreOffice to be installed "
             "(needed to keep fonts, colors and layout exactly).")
NOT_SUPPORTED = "This conversion is not supported."
SAME_FORMAT = "Source is already in this format."


def norm(fmt: str) -> str:
    fmt = (fmt or "").lower().lstrip(".")
    return _ALIASES.get(fmt, fmt)


class ConversionRegistry:
    def __init__(self):
        # Detect once (registry lookups happen on every UI refresh)
        self._has_msword = detect_msword()
        self._has_libreoffice = find_libreoffice() is not None
        # (src, tgt) -> factory returning a converter instance
        self._factories: dict[tuple[str, str], callable] = {}
        self._build()

    # ---- renderer availability ------------------------------------------
    @property
    def has_msword(self) -> bool:
        return self._has_msword

    @property
    def has_libreoffice(self) -> bool:
        return self._has_libreoffice

    @property
    def has_office_renderer(self) -> bool:
        """Word OR LibreOffice -> DOCX->PDF can be enabled."""
        return self._has_msword or self._has_libreoffice

    # ---- table ------------------------------------------------------------
    def _build(self) -> None:
        add = self._factories.__setitem__

        # image <-> image, image -> pdf
        for s in IMAGE_FORMATS:
            for t in IMAGE_FORMATS | {"pdf"}:
                if s != t:
                    add((s, t), self._image_factory(s, t))

        # pdf -> images / txt / docx
        for t in ("png", "jpeg", "webp"):
            add(("pdf", t), self._make("pdf_converters", "PdfToImageConverter", t))
        add(("pdf", "txt"), self._make("pdf_converters", "PdfToTextConverter"))
        add(("pdf", "docx"), self._make("office_converters", "PdfToDocxConverter"))

        # text / html
        add(("txt", "pdf"), self._make("text_converters", "TxtToPdfConverter"))
        add(("txt", "html"), self._make("text_converters", "TxtToHtmlConverter"))
        add(("html", "txt"), self._make("text_converters", "HtmlToTxtConverter"))

        # office
        add(("docx", "pdf"), self._make("office_converters", "DocxToPdfConverter"))
        add(("docx", "txt"), self._make("office_converters", "DocxToTextConverter"))
        add(("docx", "html"), self._make("office_converters", "DocxToHtmlConverter"))

    # ---- factories (lazy imports avoid circular imports) -----------------
    @staticmethod
    def _instantiate(cls, *args):
        """Create cls(*args) if its __init__ accepts them, else cls()."""
        try:
            params = [p for p in inspect.signature(cls.__init__).parameters.values()
                      if p.name != "self"
                      and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
            if len(params) >= len(args):
                return cls(*args)
        except (TypeError, ValueError):
            pass
        return cls()

    def _make(self, module: str, cls_name: str, *args):
        def factory():
            mod = __import__(f"{__package__}.{module}", fromlist=[cls_name])
            return self._instantiate(getattr(mod, cls_name), *args)
        return factory

    def _image_factory(self, src: str, tgt: str):
        def factory():
            from .image_converters import GenericImageConverter
            return self._instantiate(GenericImageConverter, src, tgt)
        return factory

    # ---- public API --------------------------------------------------------
    def availability(self, src: str, tgt: str) -> tuple[bool, str]:
        """(enabled, reason_if_disabled). Used by the wheel for tooltips."""
        src, tgt = norm(src), norm(tgt)
        if src == tgt:
            return False, SAME_FORMAT
        if (src, tgt) not in self._factories:
            return False, NOT_SUPPORTED
        if (src, tgt) == ("docx", "pdf") and not self.has_office_renderer:
            return False, NO_OFFICE
        if (src, tgt) == ("pdf", "docx") and not self.has_msword:
            return False, NO_MSWORD
        return True, ""

    def can_convert(self, src: str, tgt: str) -> bool:
        return self.availability(src, tgt)[0]

    def targets_for(self, src: str) -> dict[str, tuple[bool, str]]:
        """Every wheel format -> (enabled, reason). Disabled ones are kept so the
        UI can show them dimmed with a tooltip, as the PRD requires."""
        src = norm(src)
        return {t: self.availability(src, t) for t in ALL_FORMATS}

    def get_converter(self, src: str, tgt: str):
        """Return a converter instance. Refuses disabled conversions (AC-02)."""
        ok, reason = self.availability(src, tgt)
        if not ok:
            raise ValueError(reason)
        return self._factories[(norm(src), norm(tgt))]()

    def warning_for(self, src: str, tgt: str) -> str:
        """Honest note shown after conversion for inherently approximate/lossy pairs."""
        src, tgt = norm(src), norm(tgt)
        if (src, tgt) == ("pdf", "docx"):
            return ("PDF to Word is approximate: layout, columns and fonts may shift, "
                    "and scanned PDFs are not turned into editable text.")
        if (src, tgt) == ("pdf", "txt"):
            return "Plain text only - formatting is not kept."
        if tgt == "gif" and src != "gif":
            return "GIF is limited to 256 colors."
        if tgt in ("jpeg", "webp") and src in ("png", "bmp", "tiff", "gif", "pdf"):
            return "JPEG/WebP are lossy formats; tiny quality differences are possible."
        return ""


_registry: ConversionRegistry | None = None


def get_registry() -> ConversionRegistry:
    """Shared instance (detection runs once)."""
    global _registry
    if _registry is None:
        _registry = ConversionRegistry()
    return _registry
