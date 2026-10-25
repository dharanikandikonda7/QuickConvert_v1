"""
utils/image_helpers.py — Shared image processing and verification pipeline for QuickConvert.

Ensures strict fidelity:
- Exif orientation preservation via ImageOps.exif_transpose
- Mode normalization (CMYK -> RGB, I;16 -> scaled 8-bit, alpha -> white composite)
- DPI and ICC profile preservation
- Frame composition for multi-frame TIFF and GIF
- Post-write verification (reopen and check non-empty and valid)
"""

from pathlib import Path
from typing import List, Optional, Tuple, Union, Any, Dict
from PIL import Image, ImageOps, ImageSequence


def get_image_dpi(im: Image.Image, default: float = 72.0) -> Tuple[float, float]:
    """Extracts DPI from image info, with safe fallback."""
    raw_dpi = im.info.get("dpi")
    if raw_dpi:
        try:
            if isinstance(raw_dpi, (int, float)):
                d = float(raw_dpi)
                if d > 0:
                    return (d, d)
            elif isinstance(raw_dpi, (tuple, list)) and len(raw_dpi) >= 2:
                dx, dy = float(raw_dpi[0]), float(raw_dpi[1])
                if dx > 0 and dy > 0:
                    return (dx, dy)
        except (ValueError, TypeError, ZeroDivisionError):
            pass
    return (default, default)


def has_alpha_channel(im: Image.Image) -> bool:
    """Checks whether an image has transparency or alpha channel."""
    if im.mode in ("RGBA", "LA", "PA", "RGBa"):
        return True
    if im.mode == "P" and "transparency" in im.info:
        return True
    return False


def normalize_image_mode(im: Image.Image) -> Image.Image:
    """
    Normalizes exotic modes:
    - CMYK -> RGB
    - I;16 or 16-bit integer -> scaled to 8-bit L properly without clipping to black
    """
    if im.mode == "CMYK":
        return im.convert("RGB")
    if im.mode.startswith("I;16") or im.mode == "I":
        # Scale 16-bit to 8-bit properly
        return im.point(lambda i: i * (255.0 / 65535.0)).convert("L")
    return im


def flatten_alpha_on_white(im: Image.Image) -> Image.Image:
    """
    Composites any image with alpha onto a pure white (255, 255, 255) background.
    If the image has no alpha, normalizes CMYK / I;16 and converts to RGB.
    """
    im = normalize_image_mode(im)

    if has_alpha_channel(im):
        rgba = im.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        alpha = rgba.split()[3]
        background.paste(rgba.convert("RGB"), mask=alpha)
        return background

    if im.mode not in ("RGB", "L"):
        return im.convert("RGB")

    return im


def load_image_with_exif(source: Union[Path, str, Image.Image]) -> Image.Image:
    """
    Loads an image and applies EXIF orientation transpose so dimensions
    and pixel data are upright and correct.
    """
    if isinstance(source, (str, Path)):
        im = Image.open(source)
    else:
        im = source

    try:
        im = ImageOps.exif_transpose(im)
    except Exception:
        pass

    return im


def composite_frames(im: Image.Image) -> List[Image.Image]:
    """
    Extracts all frames of a multi-frame image (GIF / TIFF), fully compositing
    each frame in order to avoid delta/disposal artifacts.
    """
    frames: List[Image.Image] = []
    last_canvas: Optional[Image.Image] = None
    palette = im.getpalette()

    for frame in ImageSequence.Iterator(im):
        # Preserve palette on P mode frames if missing
        if frame.mode == "P" and not frame.getpalette() and palette:
            frame.putpalette(palette)

        rgba_frame = frame.convert("RGBA")
        disposal = frame.info.get("disposal", 1)

        if last_canvas is None or disposal == 2:
            canvas = Image.new("RGBA", im.size, (0, 0, 0, 0))
            canvas.paste(rgba_frame, (0, 0), rgba_frame)
        else:
            canvas = last_canvas.copy()
            canvas.paste(rgba_frame, (0, 0), rgba_frame)

        frames.append(canvas.copy())
        last_canvas = canvas

    return frames if frames else [im.copy()]


def prepare_for_gif(im: Image.Image) -> Tuple[Image.Image, Dict[str, Any]]:
    """
    Prepares an image for GIF saving per specifications:
    - 256 colors max.
    - If source has <= 256 unique colors, keep exact palette with no dithering.
    - Otherwise median-cut quantize with Floyd-Steinberg dithering.
    - Keep transparency.
    """
    has_alpha = has_alpha_channel(im)
    extra_kwargs: Dict[str, Any] = {}

    if has_alpha:
        im_rgba = im.convert("RGBA")
        colors = im_rgba.getcolors(maxcolors=257)
        if colors is not None and len(colors) <= 256:
            # <= 256 unique colors: exact palette without dithering
            quantized = im_rgba.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
        else:
            # > 256 colors: dithering
            quantized = im_rgba.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.FLOYDSTEINBERG)
        trans_idx = quantized.info.get("transparency")
        if trans_idx is not None:
            extra_kwargs["transparency"] = trans_idx
        return quantized, extra_kwargs

    # No alpha
    im_rgb = normalize_image_mode(im)
    if im_rgb.mode not in ("RGB", "L"):
        im_rgb = im_rgb.convert("RGB")

    colors = im_rgb.getcolors(maxcolors=257)
    if colors is not None and len(colors) <= 256:
        quantized = im_rgb.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    else:
        quantized = im_rgb.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)

    return quantized, extra_kwargs


def save_image_with_fidelity(
    im: Image.Image,
    out_path: Path,
    target_format: str,
    source_format: str = "",
    jpeg_quality: int = 95,
) -> None:
    """
    Saves an image to out_path according to exact format fidelity rules.
    Preserves DPI and ICC profile wherever supported.
    """
    target = target_format.lower().lstrip(".")
    source_fmt = source_format.lower().lstrip(".")

    dpi = get_image_dpi(im)
    icc = im.info.get("icc_profile")

    save_kwargs: Dict[str, Any] = {}
    if dpi:
        save_kwargs["dpi"] = dpi
    if icc:
        save_kwargs["icc_profile"] = icc

    im = normalize_image_mode(im)

    if target in ("jpg", "jpeg"):
        # JPEG: quality=95, subsampling=0, optimize=True, flatten alpha on white, keep ICC and DPI
        flat = flatten_alpha_on_white(im)
        save_kwargs["quality"] = max(95, jpeg_quality)
        save_kwargs["subsampling"] = 0
        save_kwargs["optimize"] = True
        flat.save(out_path, "JPEG", **save_kwargs)

    elif target == "png":
        # PNG: lossless, optimize=True, keep alpha, ICC, DPI
        save_kwargs["optimize"] = True
        im.save(out_path, "PNG", **save_kwargs)

    elif target == "webp":
        # WebP: lossless source (PNG/BMP/TIFF/GIF) -> lossless=True, quality=100, method=6, exact=True, keep alpha.
        # JPEG source -> quality=95, method=6.
        is_lossless_src = source_fmt in ("png", "bmp", "tiff", "gif", "")
        if is_lossless_src:
            save_kwargs["lossless"] = True
            save_kwargs["quality"] = 100
            save_kwargs["method"] = 6
            save_kwargs["exact"] = True
        else:
            save_kwargs["lossless"] = False
            save_kwargs["quality"] = max(95, jpeg_quality)
            save_kwargs["method"] = 6
        im.save(out_path, "WEBP", **save_kwargs)

    elif target == "bmp":
        # BMP: 24-bit RGB, flatten alpha on white
        flat = flatten_alpha_on_white(im)
        if flat.mode != "RGB":
            flat = flat.convert("RGB")
        flat.save(out_path, "BMP")

    elif target == "tiff":
        # TIFF: compression tiff_lzw, keep alpha, DPI, ICC
        save_kwargs["compression"] = "tiff_lzw"
        im.save(out_path, "TIFF", **save_kwargs)

    elif target == "gif":
        # GIF: 256 colors max, transparency preserved
        q_img, gif_args = prepare_for_gif(im)
        save_kwargs.update(gif_args)
        q_img.save(out_path, "GIF", **save_kwargs)

    else:
        im.save(out_path, **save_kwargs)

    # Verification: reopen and verify immediately
    verify_output_image(out_path, expected_size=im.size)


def verify_output_image(path: Path, expected_size: Optional[Tuple[int, int]] = None) -> None:
    """
    Reopens the saved output image and verifies it is valid and non-empty.
    Deletes the output and raises RuntimeError upon failure.
    """
    if not path.exists() or path.stat().st_size == 0:
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
        raise RuntimeError(f"Output verification failed: {path.name} is missing or 0 bytes.")

    try:
        with Image.open(path) as verified:
            verified.load()
            if expected_size is not None and verified.size != expected_size:
                raise RuntimeError(
                    f"Output verification failed: dimensions {verified.size} do not match expected {expected_size}."
                )
    except Exception as e:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass
        raise RuntimeError(f"Output image is corrupted or invalid: {e}") from e
