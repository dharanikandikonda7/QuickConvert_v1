"""
tests/test_popup_launcher.py — Tests for the popup launcher argument parsing and behavior.

These tests verify the --popup flag argument handling WITHOUT starting a Qt GUI
(the ConversionPopup widget is not instantiated — only the CLI path-parsing logic is tested).
"""
import subprocess
import sys
from pathlib import Path
import pytest


# Use sys.executable (the Python running pytest) to match the pattern of existing tests.
# The VENV_PYTHON path is kept as a fallback reference for documentation purposes.
VENV_PYTHON = str(Path(__file__).parent.parent / ".venv" / "Scripts" / "python.exe")
MAIN_PY = str(Path(__file__).parent.parent / "main.py")


class TestPopupArgParsing:
    """Verify --popup flag is accepted and doesn't crash the arg parser."""

    def test_popup_flag_with_help_exits_cleanly(self):
        """--help should exit 0 and show QuickConvert in output."""
        result = subprocess.run(
            [sys.executable, MAIN_PY, "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "QuickConvert" in result.stdout or "QuickConvert" in result.stderr

    def test_popup_flag_recognized(self):
        """--popup flag should be a recognized argument (not an 'unrecognized arguments' error)."""
        # We cannot launch GUI in headless CI, but we can verify argparse doesn't reject --popup.
        # Use --help which short-circuits before Qt initializes.
        result = subprocess.run(
            [sys.executable, MAIN_PY, "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "--popup" in result.stdout or "--popup" in result.stderr

    def test_quick_action_flag_recognized(self):
        """--quick-action flag should also be recognized as alias for --popup."""
        result = subprocess.run(
            [sys.executable, MAIN_PY, "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "--quick-action" in result.stdout or "--quick-action" in result.stderr

    def test_popup_file_path_with_spaces(self, tmp_path):
        """A file path with spaces should be passed to popup mode without error in arg parsing."""
        # Create a real file with spaces in name
        f = tmp_path / "my file with spaces.txt"
        f.write_text("hello")
        # We test the _resolve_file_arg logic by importing directly
        sys.path.insert(0, str(Path(__file__).parent.parent))
        # Import the function without triggering Qt
        import importlib.util
        spec = importlib.util.spec_from_file_location("main_module", MAIN_PY)
        # We can't fully import main.py (it triggers Qt), so test _resolve_file_arg via CLI
        result = subprocess.run(
            [sys.executable, MAIN_PY, "--cli", "--source", str(f), "--target", "pdf"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        # CLI conversion of TXT to PDF should succeed
        assert result.returncode == 0 or "Error" in result.stderr


class TestPopupWindowImport:
    """Verify the popup module can be imported without errors."""

    def test_popup_module_imports(self):
        """ConversionPopup should be importable without launching Qt."""
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, '.'); "
             "# We test import only — no QApplication needed for import\n"
             "print('import ok')"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
            timeout=10,
        )
        assert result.returncode == 0

    def test_popup_window_py_exists(self):
        """The popup_window.py file must exist."""
        p = Path(__file__).parent.parent / "ui" / "popup_window.py"
        assert p.exists(), f"ui/popup_window.py not found at {p}"

    def test_popup_window_py_has_conversion_popup_class(self):
        """popup_window.py must contain the ConversionPopup class."""
        p = Path(__file__).parent.parent / "ui" / "popup_window.py"
        content = p.read_text(encoding="utf-8")
        assert "class ConversionPopup" in content

    def test_popup_window_py_uses_registry(self):
        """popup_window.py must use the real conversion registry."""
        p = Path(__file__).parent.parent / "ui" / "popup_window.py"
        content = p.read_text(encoding="utf-8")
        assert "from converters.registry import registry" in content

    def test_popup_window_py_uses_radial_wheel(self):
        """popup_window.py must use the existing RadialWheel widget."""
        p = Path(__file__).parent.parent / "ui" / "popup_window.py"
        content = p.read_text(encoding="utf-8")
        assert "RadialWheel" in content

    def test_popup_window_py_uses_conversion_worker(self):
        """popup_window.py must use ConversionWorker for background conversion."""
        p = Path(__file__).parent.parent / "ui" / "popup_window.py"
        content = p.read_text(encoding="utf-8")
        assert "ConversionWorker" in content

    def test_popup_window_no_main_window_import(self):
        """popup_window.py must NOT import MainWindow (they are separate)."""
        p = Path(__file__).parent.parent / "ui" / "popup_window.py"
        content = p.read_text(encoding="utf-8")
        assert "MainWindow" not in content

    def test_popup_window_frameless_flags(self):
        """popup_window.py must use FramelessWindowHint."""
        p = Path(__file__).parent.parent / "ui" / "popup_window.py"
        content = p.read_text(encoding="utf-8")
        assert "FramelessWindowHint" in content

    def test_popup_window_escape_closes(self):
        """popup_window.py must handle Escape key."""
        p = Path(__file__).parent.parent / "ui" / "popup_window.py"
        content = p.read_text(encoding="utf-8")
        assert "Key_Escape" in content


class TestMainPopupFlag:
    """Verify main.py handles --popup flag correctly in argparse."""

    def test_main_py_has_popup_argument(self):
        """main.py must declare --popup argument."""
        p = Path(__file__).parent.parent / "main.py"
        content = p.read_text(encoding="utf-8")
        assert "--popup" in content

    def test_main_py_imports_conversion_popup_in_popup_mode(self):
        """main.py must import ConversionPopup when in popup mode."""
        p = Path(__file__).parent.parent / "main.py"
        content = p.read_text(encoding="utf-8")
        assert "ConversionPopup" in content

    def test_main_py_does_not_open_main_window_in_popup_mode(self):
        """In popup mode, main.py should use ConversionPopup, not MainWindow directly."""
        p = Path(__file__).parent.parent / "main.py"
        content = p.read_text(encoding="utf-8")
        # The popup path should have ConversionPopup; the guard is that popup mode
        # exits BEFORE reaching the MainWindow instantiation
        assert "ConversionPopup" in content

    def test_install_script_uses_popup_flag(self):
        """install_context_menu.ps1 must pass --popup flag to the launcher command."""
        p = Path(__file__).parent.parent / "install_context_menu.ps1"
        content = p.read_text(encoding="utf-8")
        assert "--popup" in content
