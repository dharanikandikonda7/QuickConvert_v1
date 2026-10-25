import os
import sys
import argparse
from pathlib import Path
from typing import Optional

# Robust Windows DLL resolution for PySide6 and Shiboken6
if sys.platform == "win32":
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        internal_dir = getattr(sys, "_MEIPASS", None)
        dll_candidates = [exe_dir]
        if internal_dir:
            p = Path(internal_dir)
            dll_candidates.extend([p, p / "PySide6", p / "shiboken6"])
        else:
            p = exe_dir / "_internal"
            dll_candidates.extend([p, p / "PySide6", p / "shiboken6"])

        for d in dll_candidates:
            if d.exists():
                try:
                    os.add_dll_directory(str(d))
                except (AttributeError, OSError):
                    pass
                os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")
    else:
        # Search sibling site-packages
        base_dir = Path(__file__).resolve().parent
        for candidate in [
            base_dir / ".venv" / "Lib" / "site-packages",
            Path(sys.prefix) / "Lib" / "site-packages",
        ]:
            if candidate.exists():
                pyside_dir = candidate / "PySide6"
                shiboken_dir = candidate / "shiboken6"
                if pyside_dir.exists():
                    try:
                        os.add_dll_directory(str(pyside_dir))
                    except (AttributeError, OSError):
                        pass
                    os.environ["PATH"] = str(pyside_dir) + os.pathsep + os.environ.get("PATH", "")
                if shiboken_dir.exists():
                    try:
                        os.add_dll_directory(str(shiboken_dir))
                    except (AttributeError, OSError):
                        pass
                    os.environ["PATH"] = str(shiboken_dir) + os.pathsep + os.environ.get("PATH", "")

    # In windowed PyInstaller executables, handle stdout/stderr cleanly:
    # 1. If output was redirected to a pipe or file, wrap the OS handle so
    #    subprocess.run / redirection captures output properly.
    # 2. If running interactively in a console, attach to parent console.
    # 3. Otherwise fall back to os.devnull.
    import ctypes
    import msvcrt
    import io
    kernel32 = ctypes.windll.kernel32

    for stream_name, std_id in (("stdout", -11), ("stderr", -12)):
        if getattr(sys, stream_name, None) is None:
            try:
                h = kernel32.GetStdHandle(std_id)
                ft = kernel32.GetFileType(h) if (h and h != -1 and h != 0xFFFFFFFFFFFFFFFF and h != 0xFFFFFFFF) else 0
                if ft in (1, 3):  # FILE_TYPE_DISK (1) or FILE_TYPE_PIPE (3)
                    fd = msvcrt.open_osfhandle(h, os.O_WRONLY)
                    raw_file = open(fd, "wb")
                    s = io.TextIOWrapper(raw_file, encoding="utf-8", errors="backslashreplace", line_buffering=True)
                    setattr(sys, stream_name, s)
            except Exception:
                pass

    if sys.stdout is None or sys.stderr is None:
        try:
            if kernel32.AttachConsole(0xFFFFFFFF):
                if sys.stdout is None:
                    try:
                        sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="backslashreplace")
                    except Exception:
                        pass
                if sys.stderr is None:
                    try:
                        sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="backslashreplace")
                    except Exception:
                        pass
        except Exception:
            pass

    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Configure Qt platform plugin path portably for frozen PyInstaller environment
if sys.platform == "win32" and getattr(sys, "frozen", False):
    exe_dir = Path(sys.executable).resolve().parent
    internal_dir = Path(getattr(sys, "_MEIPASS", exe_dir / "_internal"))
    for candidate in [
        internal_dir / "PySide6" / "plugins",
        internal_dir / "plugins",
        exe_dir / "PySide6" / "plugins",
        exe_dir / "_internal" / "PySide6" / "plugins",
    ]:
        if candidate.exists() and (candidate / "platforms" / "qwindows.dll").exists():
            os.environ["QT_PLUGIN_PATH"] = str(candidate)
            break

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QIcon

if getattr(sys, "frozen", False) and "QT_PLUGIN_PATH" in os.environ:
    try:
        QCoreApplication.addLibraryPath(os.environ["QT_PLUGIN_PATH"])
    except Exception:
        pass

from ui.main_window import MainWindow
from converters.registry import registry
from converters.base import ConversionOptions
from services.detector import FileDetector


def get_resource_path(relative_path: str) -> Path:
    """Resolve a path relative to the app root, handling PyInstaller bundles."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).resolve().parent / relative_path


def _ensure_utf8_stdio() -> None:
    """
    Make stdout and stderr encoding-safe for CLI and console output.

    Prefers UTF-8 where appropriate, with backslashreplace error handling
    as a safe fallback for consoles/streams that do not support UTF-8.
    """
    import io
    for attr in ("stdout", "stderr"):
        stream = getattr(sys, attr, None)
        if stream is None:
            continue
        try:
            if hasattr(stream, "reconfigure"):
                try:
                    stream.reconfigure(encoding="utf-8", errors="backslashreplace")
                except Exception:
                    try:
                        stream.reconfigure(errors="backslashreplace")
                    except Exception:
                        pass
            elif hasattr(stream, "buffer") and stream.buffer:
                line_buff = getattr(stream, "line_buffering", False)
                try:
                    new_stream = io.TextIOWrapper(
                        stream.buffer,
                        encoding="utf-8",
                        errors="backslashreplace",
                        line_buffering=line_buff,
                    )
                    setattr(sys, attr, new_stream)
                except Exception:
                    enc = getattr(stream, "encoding", None) or "utf-8"
                    new_stream = io.TextIOWrapper(
                        stream.buffer,
                        encoding=enc,
                        errors="backslashreplace",
                        line_buffering=line_buff,
                    )
                    setattr(sys, attr, new_stream)
        except Exception:
            pass


def safe_console_str(s: str, stream=None) -> str:
    """
    Safely format a string for presentation on stream (default sys.stdout).
    If the target stream's encoding cannot represent characters in s, escape
    unencodable characters using backslashreplace rather than hiding them
    with '?' (replace) or raising UnicodeEncodeError.
    """
    target = stream or sys.stdout
    enc = getattr(target, "encoding", None) or "utf-8"
    try:
        s.encode(enc)
        return s
    except (UnicodeEncodeError, LookupError):
        try:
            return s.encode(enc, errors="backslashreplace").decode(enc)
        except Exception:
            return s.encode("ascii", errors="backslashreplace").decode("ascii")


def safe_print(*args, file=None, **kwargs):
    """Print arguments safely to stream, handling unencodable characters at the presentation layer."""
    target = file if file is not None else sys.stdout
    safe_args = [safe_console_str(str(arg), stream=target) for arg in args]
    print(*safe_args, file=target, **kwargs)


# Initialize stdio encoding safety early
_ensure_utf8_stdio()


def run_cli_conversion(source_path: Path, target_format: str, output_name: str = None, output_dir: Path = None) -> int:
    """Headless CLI conversion engine."""
    _ensure_utf8_stdio()

    info = FileDetector.detect(source_path)
    if not info.is_valid:
        safe_print(f"Error: {info.validation_error or 'Invalid file.'}", file=sys.stderr)
        return 1

    converter = registry.get_converter(info.detected_format, target_format)
    if not converter:
        safe_print(f"Error: No converter available from {info.detected_format.upper()} to {target_format.upper()}.", file=sys.stderr)
        return 1

    opts = ConversionOptions(
        custom_output_name=output_name,
        output_dir=output_dir or source_path.parent,
    )

    def print_progress(pct, msg):
        safe_print(f"[{pct}%] {msg}")

    safe_print(f"Converting '{source_path.name}' ({info.detected_format.upper()}) to {target_format.upper()}...")
    result = converter.convert(source_path, opts, progress_cb=print_progress)

    if result.success:
        safe_print(f"Success! Created {len(result.output_files)} file(s):")
        for f in result.output_files:
            safe_print(f"  -> {f}")
        return 0
    else:
        safe_print(f"Conversion failed: {result.error_message}", file=sys.stderr)
        return 1


def _resolve_file_arg(raw_arg: str) -> tuple[str | None, str | None]:
    """
    Resolve a raw command-line argument to an absolute file path.

    Returns (resolved_path_str, None) on success, or (None, warning_message)
    if the argument does not resolve to an existing file.

    Handles:
    - Paths with spaces and Unicode characters (Python already receives the
      full string after Windows shell expansion; no re-joining is needed).
    - Stray surrounding quotes added by some callers (belt-and-suspenders).
    - Relative paths (resolved against the current working directory).
    - Long paths (no truncation; Path handles them transparently on Python 3.6+).
    """
    # Strip stray surrounding quotes. Python on Windows already receives
    # unquoted strings from CreateProcess, but some callers (e.g., cmd.exe
    # forwarding) may leave one layer of quotes intact.
    candidate = raw_arg.strip().strip('"').strip("'").strip()
    if not candidate:
        return None, None  # Empty arg; skip silently.

    candidate_path = Path(candidate)
    if not candidate_path.is_absolute():
        candidate_path = Path.cwd() / candidate_path
    # Resolve symlinks and normalise separators without requiring the path to exist yet.
    try:
        candidate_path = candidate_path.resolve()
    except OSError:
        pass  # Very long path or permission issue; proceed with the unresolved form.

    if candidate_path.exists() and candidate_path.is_file():
        return str(candidate_path), None

    warning = (
        f"Warning: argument '{raw_arg}' does not point to an existing file and was ignored. "
        f"(Resolved: '{candidate_path}')"
    )
    return None, warning


def main():
    # ── Argument Parsing ──────────────────────────────────────────────────────
    parser = argparse.ArgumentParser(
        description="QuickConvert — Fast Offline File Converter for Windows 11",
        add_help=False,
    )
    parser.add_argument("--cli", action="store_true", help="Run conversion headlessly in command-line mode.")
    parser.add_argument("--popup", "--quick-action", dest="popup", action="store_true", help="Show the compact radial popup (from Explorer context menu / quick action).")
    parser.add_argument("-s", "--source", type=str, help="Source file path.")
    parser.add_argument("-t", "--target", type=str, help="Target format (e.g. png, jpg, pdf, txt, webp).")
    parser.add_argument("-o", "--output-dir", type=str, help="Custom output directory.")
    parser.add_argument("-n", "--name", type=str, help="Custom output base filename.")
    parser.add_argument("-h", "--help", action="store_true", help="Show help message.")

    known_args, remaining_args = parser.parse_known_args()

    if known_args.help:
        parser.print_help()
        sys.exit(0)

    _ensure_utf8_stdio()

    # ── Headless CLI Mode ─────────────────────────────────────────────────────
    if known_args.cli:
        if not known_args.source or not known_args.target:
            safe_print("Error: CLI mode requires --source and --target.", file=sys.stderr)
            parser.print_help()
            sys.exit(1)
        src = Path(known_args.source)
        out_dir = Path(known_args.output_dir) if known_args.output_dir else None
        code = run_cli_conversion(src, known_args.target, known_args.name, out_dir)
        sys.exit(code)

    initial_files: list = []

    # ── Popup Mode (from context menu / quick action) ─────────────────────────
    if known_args.popup:
        popup_files: list[str] = []
        if known_args.source:
            resolved, warning = _resolve_file_arg(known_args.source)
            if resolved:
                popup_files.append(resolved)
            elif warning:
                safe_print(warning, file=sys.stderr)
        for raw_arg in remaining_args:
            resolved, warning = _resolve_file_arg(raw_arg)
            if resolved:
                popup_files.append(resolved)
            elif warning:
                safe_print(warning, file=sys.stderr)

        if len(popup_files) > 1:
            # When multiple files are selected, seamlessly open the full application
            # in batch mode so the user can use the batch conversion workflow.
            initial_files = popup_files
        else:
            popup_file: Optional[Path] = Path(popup_files[0]) if popup_files else None

            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
            app = QApplication(sys.argv)
            app.setApplicationName("QuickConvert")
            app.setOrganizationName("QuickConvert")

            icon_path = get_resource_path("assets/icon.ico")
            if icon_path.exists():
                app_icon = QIcon(str(icon_path))
                app.setWindowIcon(app_icon)

            from ui.popup_window import ConversionPopup
            popup = ConversionPopup(file_path=popup_file)
            popup.show()
            popup.raise_()
            popup.activateWindow()

            sys.exit(app.exec())

    # ── GUI Mode ──────────────────────────────────────────────────────────────
    # Collect file paths passed from Windows Explorer context menu (%1 / %*),
    # direct CLI invocation with a file path, or --source flag.
    #
    # Windows Shell passes each selected file as a separate, already-expanded
    # positional argument. Paths may contain spaces, Unicode characters, and
    # very long paths.  Python on Windows receives each argument as a distinct
    # element in sys.argv (no further splitting is needed or correct).
    if not initial_files:
        if known_args.source:
            resolved, warning = _resolve_file_arg(known_args.source)
            if resolved:
                initial_files.append(resolved)
            elif warning:
                safe_print(warning, file=sys.stderr)

        for raw_arg in remaining_args:
            resolved, warning = _resolve_file_arg(raw_arg)
            if resolved:
                initial_files.append(resolved)
            elif warning:
                # Emit diagnostic but do NOT crash — GUI opens normally.
                safe_print(warning, file=sys.stderr)

    # ── Qt Application Bootstrap ──────────────────────────────────────────────
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("QuickConvert")
    app.setOrganizationName("QuickConvert")

    icon_path = get_resource_path("assets/icon.ico")
    if icon_path.exists():
        app_icon = QIcon(str(icon_path))
        app.setWindowIcon(app_icon)

    window = MainWindow(initial_files=initial_files)
    if icon_path.exists():
        window.setWindowIcon(app_icon)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
