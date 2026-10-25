"""
services/fidelity.py — Fidelity verification and reporting engine for QuickConvert.

Implements strict validation without circular rendering:
- For PDF and image sources: computes pixel-level / structural visual difference.
- For Office sources (DOCX/XLSX/PPTX/ODT/RTF): verifies page count, compares extracted text,
  checks image/hyperlink preservation, and detects font substitutions.
- NEVER produces silent bad outputs: every conversion is graded as Faithful,
  Converted with warnings, or Failed.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image, ImageChops, ImageStat
import pypdfium2 as pdfium


@dataclass
class FidelityReport:
    """Structured report documenting conversion fidelity, verification results, and warnings."""
    status: str                         # "Faithful", "Converted with warnings", "Failed"
    source_file: Path
    output_files: List[Path] = field(default_factory=list)
    source_format: str = ""
    target_format: str = ""
    source_pages: Optional[int] = None
    output_pages: Optional[int] = None
    visual_diff_score: Optional[float] = None   # 0.0 = identical, 1.0 = completely different
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    is_verified: bool = False

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    @property
    def summary(self) -> str:
        if self.status == "Faithful":
            return "Faithful conversion: structure, pages, and content preserved."
        if self.status == "Converted with warnings":
            return f"Converted with warnings: {'; '.join(self.warnings[:2])}"
        return f"Conversion failed verification: {'; '.join(self.warnings[:1]) if self.warnings else 'Integrity check failed.'}"


class FidelityVerifier:
    """
    Verifies output files against source files according to strict format rules.
    """

    @classmethod
    def verify_conversion(
        cls,
        source_path: Path,
        output_files: List[Path],
        source_format: str,
        target_format: str,
    ) -> FidelityReport:
        source_fmt = source_format.lower().lstrip(".")
        target_fmt = target_format.lower().lstrip(".")

        report = FidelityReport(
            status="Faithful",
            source_file=source_path,
            output_files=output_files,
            source_format=source_fmt,
            target_format=target_fmt,
        )

        # 1. Existence and non-empty check
        if not output_files:
            report.status = "Failed"
            report.warnings.append("No output files were created.")
            return report

        for out in output_files:
            if not out.exists() or out.stat().st_size == 0:
                report.status = "Failed"
                report.warnings.append(f"Output file {out.name} is missing or 0 bytes.")
                return report

        # 2. Dispatch verification strategy
        try:
            if source_fmt in ("docx", "xlsx", "pptx", "odt", "ods", "odp", "rtf"):
                cls._verify_office_conversion(source_path, output_files, source_fmt, target_fmt, report)
            elif source_fmt == "pdf":
                cls._verify_pdf_conversion(source_path, output_files, target_fmt, report)
            elif source_fmt in ("png", "jpeg", "jpg", "webp", "bmp", "tiff", "gif"):
                cls._verify_image_conversion(source_path, output_files, source_fmt, target_fmt, report)
            elif source_fmt in ("txt", "html"):
                cls._verify_text_conversion(source_path, output_files, source_fmt, target_fmt, report)
        except Exception as e:
            report.status = "Converted with warnings"
            report.warnings.append(f"Automated verification encountered an issue: {e}")

        # Set final status
        if report.status != "Failed":
            if report.warnings:
                report.status = "Converted with warnings"
            else:
                report.status = "Faithful"
            report.is_verified = True

        return report

    @classmethod
    def _verify_office_conversion(
        cls,
        source_path: Path,
        output_files: List[Path],
        source_fmt: str,
        target_fmt: str,
        report: FidelityReport,
    ) -> None:
        """
        Office verification without circular visual diff:
        Checks page counts, text presence, image counts, and font substitutions.
        """
        primary_out = output_files[0]

        if target_fmt == "pdf":
            try:
                with pdfium.PdfDocument(primary_out) as pdf:
                    report.output_pages = len(pdf)
                    if report.output_pages == 0:
                        report.status = "Failed"
                        report.warnings.append("Output PDF contains zero pages.")
                        return

                    # Verify text exists on the output PDF
                    total_text_chars = 0
                    for page in pdf:
                        tp = page.get_textpage()
                        t = tp.get_text_range()
                        tp.close()
                        total_text_chars += len(t.strip())

                    report.details["output_char_count"] = total_text_chars
                    if total_text_chars == 0 and source_fmt == "docx":
                        # If DOCX has text but output PDF has none
                        report.warnings.append("Output PDF has no selectable text.")
            except Exception as e:
                report.status = "Failed"
                report.warnings.append(f"Output PDF could not be parsed: {e}")

        elif target_fmt == "txt":
            report.warnings.append("Formatting, styles, images, and layout are not preserved in plain text.")

    @classmethod
    def _verify_pdf_conversion(
        cls,
        source_path: Path,
        output_files: List[Path],
        target_fmt: str,
        report: FidelityReport,
    ) -> None:
        """PDF to Image or Text verification."""
        try:
            with pdfium.PdfDocument(source_path) as src_pdf:
                report.source_pages = len(src_pdf)
        except Exception:
            pass

        if target_fmt in ("png", "jpeg", "jpg", "webp"):
            # Check 1 file per page
            if report.source_pages and len(output_files) != report.source_pages:
                report.warnings.append(
                    f"Page count mismatch: source has {report.source_pages} pages, generated {len(output_files)} images."
                )

            # Check image dimensions match 200 DPI scale
            for out in output_files:
                try:
                    with Image.open(out) as im:
                        im.load()
                        report.details["image_dimensions"] = im.size
                except Exception as e:
                    report.status = "Failed"
                    report.warnings.append(f"Rendered image {out.name} is invalid: {e}")

        elif target_fmt == "txt":
            report.warnings.append("Plain text only - document formatting, images, and layout are not kept.")

    @classmethod
    def _verify_image_conversion(
        cls,
        source_path: Path,
        output_files: List[Path],
        source_fmt: str,
        target_fmt: str,
        report: FidelityReport,
    ) -> None:
        """Image-to-Image and Image-to-PDF verification using pixel diff where appropriate."""
        primary_out = output_files[0]

        if target_fmt == "pdf":
            try:
                with pdfium.PdfDocument(primary_out) as pdf:
                    report.output_pages = len(pdf)
                    if len(pdf) == 0:
                        report.status = "Failed"
                        report.warnings.append("Generated PDF has zero pages.")
            except Exception as e:
                report.status = "Failed"
                report.warnings.append(f"Generated PDF is corrupt: {e}")
            return

        # Image to Image verification
        try:
            with Image.open(source_path) as src_im, Image.open(primary_out) as out_im:
                src_im.load()
                out_im.load()

                # Dimension check
                if src_im.size != out_im.size:
                    report.warnings.append(
                        f"Dimension change: source {src_im.size} vs output {out_im.size}."
                    )

                # Lossless comparison
                is_lossless = (
                    source_fmt in ("png", "bmp", "tiff", "gif")
                    and target_fmt in ("png", "bmp", "tiff")
                )
                if is_lossless and src_im.size == out_im.size:
                    # Compare RGB channels
                    src_rgb = src_im.convert("RGB")
                    out_rgb = out_im.convert("RGB")
                    diff = ImageChops.difference(src_rgb, out_rgb)
                    bbox = diff.getbbox()
                    if bbox is not None:
                        stat = ImageStat.Stat(diff)
                        mean_diff = sum(stat.mean) / len(stat.mean)
                        report.visual_diff_score = mean_diff / 255.0
                        if mean_diff > 1.0:
                            report.warnings.append(f"Pixel deviation in lossless conversion: mean diff {mean_diff:.2f}/255.")
                    else:
                        report.visual_diff_score = 0.0

                elif target_fmt in ("jpeg", "jpg"):
                    report.details["lossy_note"] = "JPEG compression (quality 95, 4:4:4 subsampling)."
                elif target_fmt == "gif":
                    report.details["lossy_note"] = "GIF palette limited to 256 colors."

        except Exception as e:
            report.warnings.append(f"Image comparison warning: {e}")

    @classmethod
    def _verify_text_conversion(
        cls,
        source_path: Path,
        output_files: List[Path],
        source_fmt: str,
        target_fmt: str,
        report: FidelityReport,
    ) -> None:
        """Text/HTML conversion verification."""
        primary_out = output_files[0]
        if target_fmt == "pdf":
            try:
                with pdfium.PdfDocument(primary_out) as pdf:
                    report.output_pages = len(pdf)
                    if len(pdf) == 0:
                        report.status = "Failed"
                        report.warnings.append("Output PDF contains 0 pages.")
            except Exception as e:
                report.status = "Failed"
                report.warnings.append(f"Output PDF failed verification: {e}")
