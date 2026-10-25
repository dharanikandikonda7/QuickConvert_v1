from pathlib import Path
from typing import List, Optional
import pypdfium2 as pdfium
from PIL import Image

from converters.base import BaseConverter, ConversionOptions, ConversionResult, ProgressCallback
from utils.path_helpers import (
    sanitize_filename,
    get_unique_output_path,
    get_multipage_output_paths,
)
from utils.image_helpers import verify_output_image


class PdfToImageConverter(BaseConverter):
    """Renders PDF pages to raster images (PNG, JPEG, WebP) using pypdfium2 (permissive license)."""

    def __init__(self, target_fmt: str, ext: str, display: str):
        self.source_format = "pdf"
        self.target_format = target_fmt
        self.output_extension = ext
        self.display_name = display
        self.is_multipage_capable = True

    def convert(
        self,
        source_path: Path,
        options: ConversionOptions,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        if progress_cb:
            progress_cb(5, "Opening PDF document...")

        target_dir = options.output_dir or source_path.parent
        raw_name = options.custom_output_name or f"{source_path.stem}_Converted"
        base_name = sanitize_filename(raw_name)

        created_files: List[Path] = []
        doc = None
        try:
            try:
                doc = pdfium.PdfDocument(source_path)
            except Exception as e:
                err_str = str(e).lower()
                if "password" in err_str or "encrypted" in err_str:
                    return ConversionResult(
                        success=False,
                        source_file=source_path,
                        error_message="Cannot convert: PDF is password-protected or encrypted.",
                    )
                raise

            page_count = len(doc)
            if page_count == 0:
                doc.close()
                return ConversionResult(
                    success=False,
                    source_file=source_path,
                    error_message="PDF contains no pages.",
                )

            # Generate output filenames: <stem>_page_<NNN>.<ext>
            paths = get_multipage_output_paths(
                target_dir, base_name, self.output_extension, page_count, infix="page_"
            )

            # Base DPI default = 200
            requested_dpi = options.dpi if (options.dpi and options.dpi > 0) else 200

            for i in range(page_count):
                if progress_cb:
                    pct = 10 + int((i / page_count) * 80)
                    progress_cb(pct, f"Rendering page {i + 1} of {page_count}...")

                page = doc[i]
                w_pt, h_pt = page.get_size()

                # Calculate dimensions and cap longest side at 8000 px
                longest_side_pt = max(w_pt, h_pt)
                actual_dpi = float(requested_dpi)
                estimated_px = (longest_side_pt / 72.0) * actual_dpi
                if estimated_px > 8000:
                    actual_dpi = (8000.0 * 72.0) / longest_side_pt
                    if progress_cb:
                        progress_cb(
                            pct,
                            f"Page {i + 1} exceeds 8000 px; capping DPI to {int(actual_dpi)}.",
                        )

                scale = actual_dpi / 72.0
                bitmap = page.render(scale=scale, rotation=0, draw_annots=True)
                img = bitmap.to_pil()

                out_path = paths[i]
                dpi_tuple = (int(actual_dpi), int(actual_dpi))

                target = self.target_format.lower()
                if target in ("jpeg", "jpg"):
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    img.save(
                        out_path,
                        "JPEG",
                        quality=95,
                        subsampling=0,
                        optimize=True,
                        dpi=dpi_tuple,
                    )
                elif target == "webp":
                    img.save(
                        out_path,
                        "WEBP",
                        lossless=True,
                        quality=100,
                        method=6,
                        dpi=dpi_tuple,
                    )
                else:  # PNG
                    img.save(
                        out_path,
                        "PNG",
                        optimize=True,
                        dpi=dpi_tuple,
                    )

                # Verification
                verify_output_image(out_path, expected_size=img.size)
                created_files.append(out_path)

            doc.close()
            doc = None

            if progress_cb:
                progress_cb(100, "Rendering complete.")

            return ConversionResult(
                success=True,
                source_file=source_path,
                output_files=created_files,
                details=f"Extracted {page_count} page(s) to {self.target_format.upper()}.",
            )

        except Exception as e:
            if doc:
                try:
                    doc.close()
                except Exception:
                    pass
            for f in created_files:
                try:
                    if f.exists():
                        f.unlink()
                except OSError:
                    pass
            return ConversionResult(
                success=False,
                source_file=source_path,
                output_files=[],
                error_message=f"PDF rendering failed: {str(e)}",
            )


class PdfToTextConverter(BaseConverter):
    """Extracts embedded text from PDF pages using pypdfium2 with strict layout preservation."""

    def __init__(self):
        self.source_format = "pdf"
        self.target_format = "txt"
        self.output_extension = "txt"
        self.display_name = "Text Document (TXT)"
        self.is_multipage_capable = True

    def convert(
        self,
        source_path: Path,
        options: ConversionOptions,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        if progress_cb:
            progress_cb(10, "Extracting text from PDF...")

        target_dir = options.output_dir or source_path.parent
        raw_name = options.custom_output_name or f"{source_path.stem}_Converted"
        base_name = sanitize_filename(raw_name)
        out_path = get_unique_output_path(target_dir, base_name, self.output_extension)

        doc = None
        try:
            try:
                doc = pdfium.PdfDocument(source_path)
            except Exception as e:
                err_str = str(e).lower()
                if "password" in err_str or "encrypted" in err_str:
                    return ConversionResult(
                        success=False,
                        source_file=source_path,
                        error_message="Cannot convert: PDF is password-protected or encrypted.",
                    )
                raise

            page_count = len(doc)
            if page_count == 0:
                doc.close()
                return ConversionResult(
                    success=False,
                    source_file=source_path,
                    error_message="PDF contains no pages.",
                )

            extracted_sections: List[str] = []
            has_embedded_text = False

            for i in range(page_count):
                if progress_cb:
                    pct = 15 + int((i / max(1, page_count)) * 75)
                    progress_cb(pct, f"Extracting page {i + 1} of {page_count}...")

                page = doc[i]
                tp = page.get_textpage()
                text = tp.get_text_range()
                tp.close()

                # Normalize CRLF to LF
                normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
                if normalized_text.strip():
                    has_embedded_text = True
                extracted_sections.append(normalized_text)

            doc.close()
            doc = None

            # Detect scanned / image-only PDFs with no embedded text
            if not has_embedded_text:
                return ConversionResult(
                    success=False,
                    source_file=source_path,
                    error_message="No embedded text found (scanned PDF? OCR is not supported).",
                )

            # Separate pages with exact separator: \n\n----- Page N -----\n\n
            parts: List[str] = []
            for i, section in enumerate(extracted_sections):
                parts.append(f"----- Page {i + 1} -----\n\n{section}")
            full_text = "\n\n".join(parts)

            # Write with utf-8-sig encoding
            with open(out_path, "w", encoding="utf-8-sig") as f:
                f.write(full_text)

            # Verification: reopen and check non-empty
            if not out_path.exists() or out_path.stat().st_size == 0:
                raise RuntimeError("Extracted text file verification failed.")

            with open(out_path, "r", encoding="utf-8-sig") as f:
                verified_content = f.read()
                if not verified_content:
                    raise RuntimeError("Verification failed: output text file is empty.")

            if progress_cb:
                progress_cb(100, "Text extraction complete.")

            return ConversionResult(
                success=True,
                source_file=source_path,
                output_files=[out_path],
                details="Plain text only - formatting is not kept.",
            )

        except Exception as e:
            if doc:
                try:
                    doc.close()
                except Exception:
                    pass
            if out_path.exists():
                try:
                    out_path.unlink()
                except OSError:
                    pass
            return ConversionResult(
                success=False,
                source_file=source_path,
                output_files=[],
                error_message=f"PDF text extraction failed: {str(e)}",
            )
