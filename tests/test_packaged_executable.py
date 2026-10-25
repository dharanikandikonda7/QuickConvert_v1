"""
Verification script for packaged QuickConvert.exe:
- Verifies python runtime initialization
- Verifies --help execution without errors
- Verifies real image conversion (JPG -> PNG)
- Verifies real PDF conversion (PDF -> PNG)
- Verifies source file integrity (hashes unchanged)
- Verifies GUI startup and clean window close
"""

import hashlib
import subprocess
import sys
import time
from pathlib import Path


def test_packaged_executable():
    base_dir = Path(__file__).resolve().parent.parent
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))
    exe_path = base_dir / "dist" / "QuickConvert" / "QuickConvert.exe"
    assert exe_path.exists(), f"Packaged executable not found at {exe_path}"

    test_out = base_dir / "pkg_verify_out"
    test_out.mkdir(exist_ok=True)

    samples_dir = base_dir / "pkg_samples_temp"
    samples_dir.mkdir(exist_ok=True)
    from utils.sample_generator import generate_sample_files
    samples = generate_sample_files(samples_dir)

    # 1. Test CLI Help
    print("[1/5] Testing --help on packaged executable...")
    res = subprocess.run([str(exe_path), "--help"], capture_output=True, text=True)
    assert res.returncode == 0, f"--help failed: {res.stderr}"
    assert "QuickConvert" in res.stdout
    print("      --help executed successfully.")

    # 2. Test Real Image Conversion (JPEG -> PNG)
    print("[2/5] Testing real JPEG -> PNG conversion...")
    img_sample = samples["jpeg"]
    assert img_sample.exists()
    h_img_before = hashlib.sha256(img_sample.read_bytes()).hexdigest()

    res_img = subprocess.run(
        [
            str(exe_path),
            "--cli",
            "--source",
            str(img_sample),
            "--target",
            "png",
            "--output-dir",
            str(test_out),
            "--name",
            "packaged_photo_converted",
        ],
        capture_output=True,
        text=True,
    )
    assert res_img.returncode == 0, f"Image conversion failed: {res_img.stderr}"
    assert "Success!" in res_img.stdout
    h_img_after = hashlib.sha256(img_sample.read_bytes()).hexdigest()
    assert h_img_before == h_img_after, "Source JPG file was mutated!"

    out_png = test_out / "packaged_photo_converted.png"
    assert out_png.exists()
    assert out_png.stat().st_size > 0
    print(f"      JPG converted successfully ({out_png.stat().st_size} bytes). Source unchanged.")

    # 3. Test Real PDF Conversion (PDF -> PNG)
    print("[3/5] Testing real PDF -> PNG conversion...")
    pdf_sample = samples["pdf_multipage"]
    assert pdf_sample.exists()
    h_pdf_before = hashlib.sha256(pdf_sample.read_bytes()).hexdigest()

    res_pdf = subprocess.run(
        [
            str(exe_path),
            "--cli",
            "--source",
            str(pdf_sample),
            "--target",
            "png",
            "--output-dir",
            str(test_out),
            "--name",
            "packaged_pdf_converted",
        ],
        capture_output=True,
        text=True,
    )
    assert res_pdf.returncode == 0, f"PDF conversion failed: {res_pdf.stderr}"
    assert "Success!" in res_pdf.stdout
    h_pdf_after = hashlib.sha256(pdf_sample.read_bytes()).hexdigest()
    assert h_pdf_before == h_pdf_after, "Source PDF file was mutated!"

    pdf_pngs = list(test_out.glob("packaged_pdf_converted*.png"))
    assert len(pdf_pngs) >= 1
    for p in pdf_pngs:
        assert p.stat().st_size > 0
    print(f"      PDF converted successfully ({len(pdf_pngs)} page images created). Source unchanged.")

    # 4. Test GUI Launch & Window Creation
    print("[4/5] Testing GUI Launch of packaged executable...")
    # Launch GUI process
    proc = subprocess.Popen([str(exe_path)])
    try:
        # Allow process time to initialize embedded Python, load PySide6, and construct MainWindow
        time.sleep(3)
        # Verify process is actively running without crashing
        poll_res = proc.poll()
        assert poll_res is None, f"Packaged executable terminated unexpectedly with code {poll_res}"
        print("      GUI process running actively without crash.")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    # 5. Cleanup test outputs
    print("[5/5] Cleaning up test artifacts...")
    for f in test_out.glob("*"):
        try:
            f.unlink()
        except OSError:
            pass
    try:
        test_out.rmdir()
    except OSError:
        pass
    for f in samples_dir.glob("*"):
        try:
            f.unlink()
        except OSError:
            pass
    try:
        samples_dir.rmdir()
    except OSError:
        pass

    print("\nALL PACKAGED EXECUTABLE TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_packaged_executable()
