#worker.py 
from pathlib import Path
from typing import Optional, List
from PySide6.QtCore import QThread, Signal

from converters.base import BaseConverter, ConversionOptions, ConversionResult


class ConversionWorker(QThread):
    """
    Background worker thread to perform conversions without freezing the UI.
    Supports honest progress reporting and safe cancellation.
    """
    progress_changed = Signal(int, str)  # percent (0-100), message
    finished = Signal(object)           # ConversionResult

    def __init__(
        self,
        converter: BaseConverter,
        source_path: Path,
        options: ConversionOptions,
        parent=None,
    ):
        super().__init__(parent)
        self.converter = converter
        self.source_path = source_path
        self.options = options
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        def progress_callback(pct: int, msg: str):
            if self._is_cancelled:
                raise InterruptedError("Conversion cancelled by user.")
            self.progress_changed.emit(pct, msg)

        try:
            self.progress_changed.emit(5, "Initializing conversion...")
            result = self.converter.convert(
                self.source_path, self.options, progress_cb=progress_callback
            )
            self.finished.emit(result)
        except InterruptedError:
            self.finished.emit(
                ConversionResult(
                    success=False,
                    source_file=self.source_path,
                    error_message="Conversion was cancelled.",
                )
            )
        except Exception as e:
            self.finished.emit(
                ConversionResult(
                    success=False,
                    source_file=self.source_path,
                    error_message=f"Unexpected error: {str(e)}",
                )
            )
