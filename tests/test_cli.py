import subprocess
import sys
from pathlib import Path
import pytest
from utils.sample_generator import generate_sample_files


@pytest.fixture(scope="session")
def sample_files(tmp_path_factory):
    dir_path = tmp_path_factory.mktemp("cli_test_samples")
    return generate_sample_files(dir_path)


def test_cli_help():
    res = subprocess.run(
        [sys.executable, "main.py", "--help"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "QuickConvert" in res.stdout
    assert "--cli" in res.stdout


def test_cli_conversion_success(sample_files, tmp_path):
    out_dir = tmp_path / "cli_out"
    out_dir.mkdir()

    res = subprocess.run(
        [
            sys.executable,
            "main.py",
            "--cli",
            "--source",
            str(sample_files["png"]),
            "--target",
            "jpeg",
            "--output-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "Success!" in res.stdout
    outputs = list(out_dir.glob("*.jpg"))
    assert len(outputs) == 1
    assert outputs[0].stat().st_size > 0


def test_cli_corrupt_file_failure(sample_files):
    res = subprocess.run(
        [
            sys.executable,
            "main.py",
            "--cli",
            "--source",
            str(sample_files["corrupt_pdf"]),
            "--target",
            "png",
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    assert "corrupt" in res.stderr.lower() or "unreadable" in res.stderr.lower()


def test_cli_missing_args():
    res = subprocess.run(
        [sys.executable, "main.py", "--cli"],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    assert "Error: CLI mode requires --source and --target" in res.stderr
    assert "NameError" not in res.stderr
    assert "_trace" not in res.stderr


def test_main_function_direct_invocation_no_name_error(monkeypatch):
    """Directly invoke main.main() to ensure all module symbols resolve without NameError."""
    import main

    monkeypatch.setattr(sys, "argv", ["main.py", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        main.main()
    assert exc_info.value.code == 0


def test_run_cli_conversion_direct_invocation_no_name_error(sample_files, tmp_path):
    """Directly invoke run_cli_conversion to ensure no undefined symbols like _trace exist."""
    import main

    out_dir = tmp_path / "direct_cli_out"
    out_dir.mkdir()
    code = main.run_cli_conversion(
        source_path=sample_files["png"],
        target_format="jpeg",
        output_dir=out_dir,
    )
    assert code == 0
    outputs = list(out_dir.glob("*.jpg"))
    assert len(outputs) == 1

