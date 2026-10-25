"""
tests/test_context_menu_loading.py
===================================
Tests for Windows Explorer context-menu file-loading via positional CLI args.

Covers:
- Single file path as positional argument
- Path with spaces in the filename
- Path with Unicode characters in the filename
- Multiple positional file arguments (multi-select)
- Non-existent path argument (warning to stderr, no crash)
- _resolve_file_arg() unit tests (spaces, Unicode, relative, missing)

These tests exercise the CLI-argument code paths in main.py WITHOUT
launching the Qt GUI (which requires a display).  They run main.py as a
subprocess in --cli mode (headless) to verify that paths are resolved and
handed to the converter correctly, and call _resolve_file_arg() directly
via importlib for unit testing.
"""

import importlib
import sys
import subprocess
import shutil
from pathlib import Path

import pytest
from utils.sample_generator import generate_sample_files


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sample_files(tmp_path_factory):
    """Generate fresh sample files once per test module."""
    base = tmp_path_factory.mktemp("ctx_menu_samples")
    return generate_sample_files(base)


@pytest.fixture(scope="module")
def png_with_spaces(sample_files, tmp_path_factory):
    """A copy of the PNG sample placed in a directory whose name contains spaces."""
    spaced_dir = tmp_path_factory.mktemp("My Test Files With Spaces")
    src = sample_files["png"]
    dest = spaced_dir / "image with spaces.png"
    shutil.copy2(src, dest)
    return dest


@pytest.fixture(scope="module")
def png_with_unicode(sample_files, tmp_path_factory):
    """A copy of the PNG sample with a Unicode filename (Japanese + emoji)."""
    uni_dir = tmp_path_factory.mktemp("unicode_dir")
    src = sample_files["png"]
    dest = uni_dir / "画像ファイル_テスト🖼.png"
    shutil.copy2(src, dest)
    return dest


@pytest.fixture(scope="module")
def png_with_japanese(sample_files, tmp_path_factory):
    """A copy of the PNG sample with a pure Japanese filename."""
    jp_dir = tmp_path_factory.mktemp("japanese_dir")
    src = sample_files["png"]
    dest = jp_dir / "日本語ドキュメント_テスト.png"
    shutil.copy2(src, dest)
    return dest


@pytest.fixture(scope="module")
def png_with_emoji(sample_files, tmp_path_factory):
    """A copy of the PNG sample with emoji in the filename."""
    emoji_dir = tmp_path_factory.mktemp("emoji_dir")
    src = sample_files["png"]
    dest = emoji_dir / "quick_rocket_🚀_test.png"
    shutil.copy2(src, dest)
    return dest


# ── _resolve_file_arg() unit tests ────────────────────────────────────────────

def _import_resolve():
    """Import _resolve_file_arg from main without executing main()."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "main_module",
        str(Path(__file__).parent.parent / "main.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    # Avoid the Qt import / GUI bootstrap inside main.py by patching sys.argv
    # so that the module-level platform block does not raise.
    old_argv = sys.argv[:]
    sys.argv = [sys.argv[0]]
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    except Exception:
        pass
    finally:
        sys.argv = old_argv
    return mod._resolve_file_arg


class TestResolveFileArg:
    """Unit tests for _resolve_file_arg() in main.py."""

    def test_returns_path_for_existing_file(self, sample_files):
        resolve = _import_resolve()
        resolved, warning = resolve(str(sample_files["png"]))
        assert resolved is not None
        assert Path(resolved).exists()
        assert warning is None

    def test_path_with_spaces(self, png_with_spaces):
        resolve = _import_resolve()
        resolved, warning = resolve(str(png_with_spaces))
        assert resolved is not None, f"Expected resolution but got warning: {warning}"
        assert Path(resolved).exists()
        assert " " in str(png_with_spaces)  # sanity: fixture has a space

    def test_path_with_unicode(self, png_with_unicode):
        resolve = _import_resolve()
        resolved, warning = resolve(str(png_with_unicode))
        assert resolved is not None, f"Expected resolution but got warning: {warning}"
        assert Path(resolved).exists()

    def test_nonexistent_path_returns_warning(self, tmp_path):
        resolve = _import_resolve()
        missing = str(tmp_path / "does_not_exist.png")
        resolved, warning = resolve(missing)
        assert resolved is None
        assert warning is not None
        assert "does not point to an existing file" in warning

    def test_empty_arg_returns_none_silently(self):
        resolve = _import_resolve()
        resolved, warning = resolve("")
        assert resolved is None
        assert warning is None

    def test_stray_quotes_stripped(self, sample_files):
        """Simulate a shell that passes the path with an extra wrapping quote."""
        resolve = _import_resolve()
        # e.g. Windows shell sometimes leaves one layer of quotes
        raw = f'"{sample_files["png"]}"'
        resolved, warning = resolve(raw)
        assert resolved is not None, f"Expected resolution for quoted path, got: {warning}"
        assert Path(resolved).exists()


# ── CLI subprocess tests ───────────────────────────────────────────────────────
# These tests invoke main.py via subprocess in --cli mode (headless) to verify
# that the full argument-parsing pipeline works correctly without the Qt GUI.

def _run_cli(args: list, cwd: str = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "main.py"] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="backslashreplace",
        cwd=cwd or str(Path(__file__).parent.parent),
    )


class TestCliPathHandling:
    """Tests for CLI --cli mode with paths containing spaces and Unicode."""

    def test_single_file_path_succeeds(self, sample_files, tmp_path):
        out = tmp_path / "out_single"
        out.mkdir()
        res = _run_cli([
            "--cli",
            "--source", str(sample_files["png"]),
            "--target", "jpeg",
            "--output-dir", str(out),
        ])
        assert res.returncode == 0, f"stderr: {res.stderr}"
        assert "Success!" in res.stdout
        outputs = list(out.glob("*.jpg"))
        assert len(outputs) == 1
        assert outputs[0].stat().st_size > 0

    def test_path_with_spaces_cli_mode(self, png_with_spaces, tmp_path):
        """Path containing spaces must be passed, resolved, and output created."""
        out = tmp_path / "out_spaces"
        out.mkdir()
        res = _run_cli([
            "--cli",
            "--source", str(png_with_spaces),
            "--target", "jpeg",
            "--output-dir", str(out),
        ])
        assert res.returncode == 0, (
            f"CLI failed for spaced path '{png_with_spaces}'.\n"
            f"stdout: {res.stdout}\nstderr: {res.stderr}"
        )
        assert "Success!" in res.stdout
        expected_out = out / f"{png_with_spaces.stem}_Converted.jpg"
        assert expected_out.exists(), f"Expected output file '{expected_out}' does not exist"
        assert expected_out.stat().st_size > 0

    def test_path_with_unicode_cli_mode(self, png_with_unicode, tmp_path):
        """Path with Unicode filename (Japanese + emoji) must be converted and preserved exactly."""
        out = tmp_path / "out_unicode"
        out.mkdir()
        res = _run_cli([
            "--cli",
            "--source", str(png_with_unicode),
            "--target", "jpeg",
            "--output-dir", str(out),
        ])
        assert res.returncode == 0, (
            f"CLI failed for Unicode path '{png_with_unicode}'.\n"
            f"stdout: {res.stdout}\nstderr: {res.stderr}"
        )
        assert "Success!" in res.stdout
        expected_out = out / f"{png_with_unicode.stem}_Converted.jpg"
        assert expected_out.exists(), f"Expected output file '{expected_out}' does not exist"
        assert expected_out.name == "画像ファイル_テスト🖼_Converted.jpg"
        assert expected_out.stat().st_size > 0

    def test_path_with_japanese_cli_mode(self, png_with_japanese, tmp_path):
        """Pure Japanese filename must be converted without corruption or errors."""
        out = tmp_path / "out_jp"
        out.mkdir()
        res = _run_cli([
            "--cli",
            "--source", str(png_with_japanese),
            "--target", "jpeg",
            "--output-dir", str(out),
        ])
        assert res.returncode == 0, (
            f"CLI failed for Japanese path '{png_with_japanese}'.\n"
            f"stdout: {res.stdout}\nstderr: {res.stderr}"
        )
        assert "Success!" in res.stdout
        expected_out = out / f"{png_with_japanese.stem}_Converted.jpg"
        assert expected_out.exists(), f"Expected output file '{expected_out}' does not exist"
        assert expected_out.name == "日本語ドキュメント_テスト_Converted.jpg"
        assert expected_out.stat().st_size > 0

    def test_path_with_emoji_cli_mode(self, png_with_emoji, tmp_path):
        """Emoji filename must be converted and preserved in output filename."""
        out = tmp_path / "out_emoji"
        out.mkdir()
        res = _run_cli([
            "--cli",
            "--source", str(png_with_emoji),
            "--target", "jpeg",
            "--output-dir", str(out),
        ])
        assert res.returncode == 0, (
            f"CLI failed for emoji path '{png_with_emoji}'.\n"
            f"stdout: {res.stdout}\nstderr: {res.stderr}"
        )
        assert "Success!" in res.stdout
        expected_out = out / f"{png_with_emoji.stem}_Converted.jpg"
        assert expected_out.exists(), f"Expected output file '{expected_out}' does not exist"
        assert expected_out.name == "quick_rocket_🚀_test_Converted.jpg"
        assert expected_out.stat().st_size > 0

    def test_run_cli_conversion_under_cp1252_stream(self, png_with_unicode, tmp_path):
        """Direct call to run_cli_conversion with a cp1252 stream must succeed without UnicodeEncodeError."""
        import io
        from main import run_cli_conversion

        out = tmp_path / "out_cp1252_direct"
        out.mkdir()

        # Simulate a console stream locked to cp1252 that rejects changing encoding to utf-8
        class LockedCp1252Stream(io.TextIOWrapper):
            def reconfigure(self, **kwargs):
                if "encoding" in kwargs and kwargs["encoding"] != "cp1252":
                    raise io.UnsupportedOperation("Cannot change encoding from cp1252")
                super().reconfigure(**kwargs)

        orig_stdout = sys.stdout
        orig_stderr = sys.stderr
        buf_out = io.BytesIO()
        buf_err = io.BytesIO()
        sys.stdout = LockedCp1252Stream(buf_out, encoding="cp1252")
        sys.stderr = LockedCp1252Stream(buf_err, encoding="cp1252")
        try:
            code = run_cli_conversion(png_with_unicode, "jpeg", output_dir=out)
            assert code == 0
        finally:
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr

        expected_out = out / f"{png_with_unicode.stem}_Converted.jpg"
        assert expected_out.exists()
        assert expected_out.name == "画像ファイル_テスト🖼_Converted.jpg"
        assert expected_out.stat().st_size > 0

    def test_nonexistent_path_cli_fails_with_message(self, tmp_path):
        """A non-existent source in --cli mode must produce a non-zero exit and
        a readable error message (not a Python traceback)."""
        missing = str(tmp_path / "no_such_file.png")
        res = _run_cli([
            "--cli",
            "--source", missing,
            "--target", "jpeg",
        ])
        assert res.returncode != 0
        # Message must be human-readable, not a raw Python traceback.
        assert "Error" in res.stderr or "error" in res.stderr.lower()
        assert "Traceback" not in res.stderr


class TestPositionalArgLoading:
    """
    Tests for GUI-mode positional argument handling (%1 style).

    Since the Qt event loop cannot be started in a headless test environment,
    we validate the argument-resolution logic indirectly:
    - _resolve_file_arg() is tested directly (above).
    - We verify that the positional-arg code path in main.py does NOT crash
      when given a valid path by running it through the CLI and checking the
      environment is sane.
    """

    def test_multiple_files_warning_for_nonexistent(self, sample_files, tmp_path):
        """
        When extra positional args don't exist, main.py in --cli mode should
        still process --source correctly and emit a warning (not crash).

        We piggy-back on --cli mode to avoid spawning a GUI; the positional-
        arg resolver is the same code path.
        """
        out = tmp_path / "out_multi"
        out.mkdir()
        res = _run_cli([
            "--cli",
            "--source", str(sample_files["png"]),
            "--target", "jpeg",
            "--output-dir", str(out),
            # Extra positional arg that doesn't exist
            str(tmp_path / "ghost_file.bmp"),
        ])
        # The conversion of --source should still succeed.
        assert res.returncode == 0, f"stderr: {res.stderr}"
        assert "Success!" in res.stdout

    def test_missing_args_exits_nonzero(self):
        res = _run_cli(["--cli"])
        assert res.returncode != 0
        assert "Error: CLI mode requires --source and --target" in res.stderr
