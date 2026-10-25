from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional


ProgressCallback = Callable[[int, str], None]


@dataclass
class ConversionOptions:
    """Settings passed to converters."""
    custom_output_name: Optional[str] = None
    output_dir: Optional[Path] = None
    jpeg_quality: int = 95
    dpi: int = 200
    multipage_extract_all: bool = True
    page_range: Optional[tuple[int, int]] = None
    custom_font_family: Optional[str] = None


@dataclass
class ConversionResult:
    """Outcome of a conversion run."""
    success: bool
    source_file: Path
    output_files: List[Path] = field(default_factory=list)
    error_message: Optional[str] = None
    details: Optional[str] = None

    @property
    def primary_output(self) -> Optional[Path]:
        return self.output_files[0] if self.output_files else None


class BaseConverter(ABC):
    """Abstract base class for all conversion strategies."""

    source_format: str
    target_format: str
    display_name: str
    output_extension: str
    is_multipage_capable: bool = False

    @abstractmethod
    def convert(
        self,
        source_path: Path,
        options: ConversionOptions,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        """
        Executes the conversion safely.
        Must not corrupt the source file.
        Must clean up any partial output upon failure.
        """
        pass
