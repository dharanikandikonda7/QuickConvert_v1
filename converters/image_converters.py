import os
from pathlib import Path
from typing import List, Optional
from PIL import Image
import pypdfium2 as pdfium

from converters.base import BaseConverter, ConversionOptions, ConversionResult, ProgressCallback
from utils.path_helpers import (
    sanitize_filename,
    get_unique_output_path,
    get_multipage_output_paths,
)
from utils.image_helpers import (
    load_image_with_exif,
    get_image_dpi,
    composite_frames,
    save_image_with_fidelity,
    verify_output_image,
)


class GenericImageConverter(BaseConverter):
    """Handles raster image format conversions and image-to-PDF conversion using pypdfium2 and Pillow."""

    def __init__(self, source_fmt: str, target_fmt: str, ext: str, display: str):
        self.source_format = source_fmt
        self.target_format = target_fmt
        self.output_extension = ext
        self.display_name = display
        self.is_multipage_capable = source_fmt in ("tiff", "gif")

    def convert(
        self,
        source_path: Path,
        options: ConversionOptions,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        if progress_cb:
            progress_cb(10, f"Loading {self.source_format.upper()} image...")

        target_dir = options.output_dir or source_path.parent
        raw_name = options.custom_output_name or f"{source_path.stem}_Converted"
        base_name = sanitize_filename(raw_name)

        created_files: List[Path] = []
        try:
            with Image.open(source_path) as raw_im:
                im = load_image_with_exif(raw_im)
                frame_count = getattr(raw_im, "n_frames", 1)

                # ==============================================================
                # 1. Image -> PDF Conversion (via pypdfium2)
                # ==============================================================
                if self.target_format == "pdf":
                    if progress_cb:
                        progress_cb(30, "Compiling PDF document...")

                    out_path = get_unique_output_path(target_dir, base_name, self.output_extension)
                    pdf_doc = pdfium.PdfDocument.new()

                    if self.source_format in ("jpg", "jpeg"):
                        # JPEG source: embed raw bytes directly (zero re-encoding)
                        dpi_x, dpi_y = get_image_dpi(im)
                        w_pt = im.width / dpi_x * 72.0
                        h_pt = im.height / dpi_y * 72.0

                        page = pdf_doc.new_page(int(w_pt), int(h_pt))
                        img_obj = pdfium.PdfImage.new(pdf_doc)
                        img_obj.load_jpeg(str(source_path))
                        img_obj.set_matrix(pdfium.PdfMatrix(w_pt, 0, 0, h_pt, 0, 0))
                        page.insert_obj(img_obj)
                        page.gen_content()

                    elif frame_count > 1 and self.source_format in ("tiff", "gif"):
                        # Multi-frame TIFF/GIF -> one PDF page per frame in order
                        frames = composite_frames(raw_im)
                        for idx, frame in enumerate(frames):
                            dpi_x, dpi_y = get_image_dpi(frame)
                            w_pt = frame.width / dpi_x * 72.0
                            h_pt = frame.height / dpi_y * 72.0

                            page = pdf_doc.new_page(int(w_pt), int(h_pt))
                            bitmap = pdfium.PdfBitmap.from_pil(frame)
                            img_obj = pdfium.PdfImage.new(pdf_doc)
                            img_obj.set_bitmap(bitmap)
                            img_obj.set_matrix(pdfium.PdfMatrix(w_pt, 0, 0, h_pt, 0, 0))
                            page.insert_obj(img_obj)
                            page.gen_content()

                    else:
                        # Other lossless sources (PNG, BMP, WebP, etc.)
                        dpi_x, dpi_y = get_image_dpi(im)
                        w_pt = im.width / dpi_x * 72.0
                        h_pt = im.height / dpi_y * 72.0

                        page = pdf_doc.new_page(int(w_pt), int(h_pt))
                        bitmap = pdfium.PdfBitmap.from_pil(im)
                        img_obj = pdfium.PdfImage.new(pdf_doc)
                        img_obj.set_bitmap(bitmap)
                        img_obj.set_matrix(pdfium.PdfMatrix(w_pt, 0, 0, h_pt, 0, 0))
                        page.insert_obj(img_obj)
                        page.gen_content()

                    pdf_doc.save(str(out_path))
                    pdf_doc.close()

                    # Verification: reopen and verify valid PDF
                    if not out_path.exists() or out_path.stat().st_size == 0:
                        raise RuntimeError("PDF output verification failed: file is missing or 0 bytes.")

                    with pdfium.PdfDocument(out_path) as verify_pdf:
                        expected_pages = frame_count if (frame_count > 1 and self.source_format in ("tiff", "gif")) else 1
                        if len(verify_pdf) != expected_pages:
                            raise RuntimeError(f"PDF page count mismatch: got {len(verify_pdf)}, expected {expected_pages}.")

                    created_files.append(out_path)

                # ==============================================================
                # 2. Image -> Image (Multi-frame TIFF / GIF raster export)
                # ==============================================================
                elif frame_count > 1 and self.source_format in ("tiff", "gif"):
                    frames = composite_frames(raw_im)
                    total_frames = len(frames)
                    paths = get_multipage_output_paths(
                        target_dir, base_name, self.output_extension, total_frames
                    )

                    for idx, frame in enumerate(frames):
                        if progress_cb:
                            pct = 15 + int((idx / total_frames) * 75)
                            progress_cb(pct, f"Converting frame {idx + 1} of {total_frames}...")

                        out_path = paths[idx]
                        save_image_with_fidelity(
                            frame,
                            out_path,
                            target_format=self.target_format,
                            source_format=self.source_format,
                            jpeg_quality=options.jpeg_quality,
                        )
                        created_files.append(out_path)

                # ==============================================================
                # 3. Image -> Image (Single frame raster conversion)
                # ==============================================================
                else:
                    if progress_cb:
                        progress_cb(40, f"Encoding {self.target_format.upper()}...")

                    out_path = get_unique_output_path(target_dir, base_name, self.output_extension)
                    save_image_with_fidelity(
                        im,
                        out_path,
                        target_format=self.target_format,
                        source_format=self.source_format,
                        jpeg_quality=options.jpeg_quality,
                    )
                    created_files.append(out_path)

            if progress_cb:
                progress_cb(100, "Conversion complete.")

            return ConversionResult(
                success=True,
                source_file=source_path,
                output_files=created_files,
                details=f"Generated {len(created_files)} {self.target_format.upper()} file(s).",
            )

        except Exception as e:
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
                error_message=f"Image conversion failed: {str(e)}",
            )
