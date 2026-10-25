import re
from pathlib import Path
from typing import List, Tuple, Optional


INVALID_WIN_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_filename(name: str) -> str:
    """Removes or replaces invalid Windows filename characters."""
    if not name:
        return "converted"
    sanitized = INVALID_WIN_CHARS.sub("_", name).strip(". ")
    return sanitized or "converted"


def get_unique_output_path(target_dir: Path, base_name: str, extension: str) -> Path:
    """
    Returns a non-colliding file path in target_dir.
    Example: base_name.ext -> base_name (1).ext -> base_name (2).ext
    """
    ext = extension.lstrip(".")
    candidate = target_dir / f"{base_name}.{ext}"
    if not candidate.exists():
        return candidate

    counter = 1
    while True:
        candidate = target_dir / f"{base_name} ({counter}).{ext}"
        if not candidate.exists():
            return candidate
        counter += 1


def get_multipage_output_paths(
    target_dir: Path, base_name: str, extension: str, page_count: int, infix: str = ""
) -> List[Path]:
    """
    Generates numbered unique paths for multipage conversions.
    Example: Report_Converted_001.png or Report_Converted_page_001.png
    If files already exist, an indexed prefix/suffix is applied to avoid overwrites.
    """
    ext = extension.lstrip(".")
    if page_count <= 0:
        return []
    
    pad_len = max(3, len(str(page_count)))
    tag = infix if infix else ""
    
    # Check if direct name collides with any page
    base_candidate = base_name
    collision = False
    for i in range(1, page_count + 1):
        num_str = str(i).zfill(pad_len)
        if (target_dir / f"{base_candidate}_{tag}{num_str}.{ext}").exists():
            collision = True
            break
            
    if collision:
        counter = 1
        while True:
            base_candidate = f"{base_name} ({counter})"
            sub_collision = False
            for i in range(1, page_count + 1):
                num_str = str(i).zfill(pad_len)
                if (target_dir / f"{base_candidate}_{tag}{num_str}.{ext}").exists():
                    sub_collision = True
                    break
            if not sub_collision:
                break
            counter += 1
            
    paths = []
    for i in range(1, page_count + 1):
        num_str = str(i).zfill(pad_len)
        paths.append(target_dir / f"{base_candidate}_{tag}{num_str}.{ext}")
    return paths


def format_file_size(size_bytes: int) -> str:
    """Human-readable file size string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
