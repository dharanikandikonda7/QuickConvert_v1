# memory.md — Persistent Project Memory
## QuickConvert: Fast Offline File Converter for Windows

**Last Updated:** 2026-10-24 23:43 IST  
**Current Phase:** Phase 4 Windows Integration complete → Phase 6 (Packaging) next

---

## Project Identity

| Field | Value |
|---|---|
| **Project Name** | QuickConvert |
| **Type** | Windows desktop GUI + CLI, offline file converter |
| **Primary Language** | Python 3.11 |
| **UI Framework** | PySide6 (Qt6) |
| **Entry Point** | `main.py` |
| **Project Root** | `d:\PROJECTS\QuickConvertMowa\` |
| **Virtual Env** | `.venv\` (Python 3.11.3, Windows) |

---

## Current Implementation Status

### ✅ VERIFIED AND WORKING

| Feature | How Verified |
|---|---|
| All converter implementations | 50/50 automated tests pass |
| PDF → PNG, JPEG, WebP (multi-page) | test_pdf_to_png, test_pdf_to_jpeg |
| PDF → TXT (text extraction) | test_pdf_to_txt |
| TXT → PDF (ReportLab) | test_txt_to_pdf |
| TXT → HTML (standalone styled) | test_txt_to_html_and_back |
| HTML → TXT (tag stripping) | test_txt_to_html_and_back |
| Image ↔ Image (all 30 pairs: PNG/JPEG/WebP/BMP/TIFF/GIF) | Multiple converter tests |
| Multi-frame TIFF/GIF → individual images | test_multipage_tiff_to_png, test_gif_to_png |
| Image → PDF | test_image_to_pdf |
| Overwrite protection (`_001`, `(1)` suffixes) | test_overwrite_protection |
| Transparent PNG → JPEG (white composite) | test_png_to_jpeg (mode=RGB verified) |
| Encrypted PDF rejection | test_encrypted_pdf_failure |
| Corrupt PDF rejection | test_detect_corrupt_pdf |
| Empty file (0 bytes) rejection | test_detect_empty_file |
| Magic-byte content detection | test_detect_misleading_extension |
| CLI mode (--cli --source --target) | test_cli_conversion_success |
| Context menu HKCU install/uninstall | install_context_menu.ps1 / uninstall script |
| Background thread conversion (QThread) | ConversionWorker — UI non-blocking |
| Conversion cancellation | worker.cancel() → InterruptedError |
| Open File / Open Folder buttons | QDesktopServices / subprocess explorer |
| Radial wheel keyboard navigation | Arrow keys cycle enabled targets |
| **Positional arg loading (spaces)** | test_path_with_spaces (PASS 2026-10-24) |
| **Positional arg loading (Unicode)** | test_path_with_unicode (PASS 2026-10-24) |
| **Multiple file positional args** | test_multiple_files_warning_for_nonexistent (PASS) |
| **Missing path → warning (no crash)** | test_nonexistent_path_returns_warning (PASS) |
| **Unicode filenames in CLI output** | _ensure_utf8_stdio() fix (PASS 2026-10-24) |
| **PyInstaller packaging & runtime** | test_packaged_executable (PASS 2026-10-25) |
| **Qt Platform Plugin resolution** | Bundled PySide6 plugins + qt.conf (PASS 2026-10-25) |

### ⬜ NOT YET VERIFIED / NOT IMPLEMENTED

| Feature | Status | Notes |
|---|---|---|
| Modern IExplorerCommand context menu (Win11 primary) | Not implemented | Future feature (legacy menu fully working) |
| DOCX/XLSX/PPTX conversion via LibreOffice | Not implemented | Requires external LibreOffice installation |
| Batch conversion in GUI | Not implemented | MVP is single-file; CLI supports scripting |
| OCR for scanned PDFs | Not implemented | Future feature |

---

## Latest Test Results

```
Command: .venv\Scripts\python.exe -m pytest tests/ -v
Date:    2026-10-25
Result:  62/62 PASSED in 42.51s
Python:  3.11.3
pytest:  9.1.1
```

All test categories pass:
- `tests/test_application_verification.py`: 6/6  ← Application verification suite
- `tests/test_cli.py`: 6/6
- `tests/test_context_menu_loading.py`: 15/15
- `tests/test_converters.py`: 19/19
- `tests/test_detector.py`: 10/10
- `tests/test_packaged_executable.py`: 1/1  ← Packaged executable integration test
- `tests/test_registry.py`: 5/5

---

## Bugs Fixed

| # | Date | Severity | Bug | File | Fix |
|---|---|---|---|---|---|
| 1 | 2026-10-24 | 🔴 Real | `sanitize_filename("")` returned `""` → file saved as `.ext` (hidden) | `utils/path_helpers.py` | Returns `"converted"` for empty/blank input |
| 2 | 2026-10-24 | 🔴 Real | Folder picker cancel reset previously selected folder | `ui/main_window.py` | Cancel is now a no-op; "Reset" button added for explicit clear |
| 3 | 2026-10-24 | 🟡 UX | Invalid file load left stale filename in output name field | `ui/main_window.py` | `name_input.clear()` called on invalid file load |
| 4 | 2026-10-24 | 🟡 UX | Radial wheel hit area (0.08) larger than visual radius (0.075) | `ui/radial_wheel.py` | Both set to `min_dim * 0.075` |
| 5 | 2026-10-24 | 🔴 Real | `UnicodeEncodeError` when printing Unicode filenames on cp1252 console | `main.py` | `_ensure_utf8_stdio()` reconfigures stdout/stderr to UTF-8 with backslashreplace |
| 6 | 2026-10-25 | 🔴 Real | `NameError: name '_trace' is not defined` during packaged app startup | `main.py` | Removed lingering diagnostic `_trace` references from `run_cli_conversion` and `main()` |
| 7 | 2026-10-25 | 🔴 Real | Silent PyInstaller failure & missing `base_library.zip` caused by locked exe | `build.ps1` | Added pre-build process termination, strict `$LASTEXITCODE` checks, and runtime verification |
| 8 | 2026-10-25 | 🔴 Real | Qt platform plugin error (`qwindows.dll` not found) in packaged exe | `build.ps1`, `main.py` | Bundled PySide6 plugins directory, deployed portable `qt.conf`, and added runtime library path resolution |

---

## Known Limitations

| Limitation | Impact | Workaround |
|---|---|---|
| Windows 11 context menu appears under "Show more options" | User needs extra click | Document in README |
| No DOCX/XLSX/PPTX support without python-docx/LibreOffice | Disabled in wheel with tooltip | Install python-docx |
| PDF text extraction = embedded text only (no OCR) | Scanned PDFs produce empty TXT | Planned: Tesseract |
| Multi-frame GIF → JPEG/WebP loses animation | Single frames as stills | Expected behavior |
| Very large PDFs may be slow | Memory + render time | Future: page-range selection |
| No batch conversion in radial view | One file at a time in MVP | Batch Convert sidebar tab available |

---

## Technology Stack

| Component | Library | Version |
|---|---|---|
| UI | PySide6 | `>=6.6.0` (installed: current) |
| PDF rendering + text | PyMuPDF (`pymupdf`) | `>=1.23.0,<2.0.0` |
| Image I/O | Pillow | `>=10.0.0` |
| PDF generation | ReportLab | `>=4.0.0` |
| Testing | pytest | `>=7.4.0` (installed: 9.1.1) |
| Packaging | PyInstaller | `>=6.3.0` |

All dependencies verified installed in `.venv`.

---

## Key Architecture Decisions

| Decision | Reason |
|---|---|
| `ConversionRegistry` singleton | Single source of truth; UI derives all availability from it |
| `FileDetector` uses magic bytes | Handles misleading extensions; more reliable than trusting `.ext` |
| `QThread` for conversions | UI never freezes; Qt signals cross thread safely |
| HKCU registry for context menu | No admin required; fully reversible |
| `sanitize_filename` returns `"converted"` for empty | Prevents hidden `.ext` files on Windows |
| Folder picker cancel = no-op | Preserves user's intentional folder choice |
| Node hit radius = visual radius | Click area matches what user sees |
| `_resolve_file_arg()` helper | Clean, testable path resolution for context-menu args |
| `_ensure_utf8_stdio()` | Prevents UnicodeEncodeError on narrow-codepage consoles |

---

## Important File Locations

| File | Purpose |
|---|---|
| `main.py` | Entry point: CLI dispatcher + GUI bootstrap + Windows DLL paths |
| `converters/registry.py` | ConversionRegistry singleton — register all converters here |
| `converters/base.py` | BaseConverter, ConversionOptions, ConversionResult dataclasses |
| `converters/image_converters.py` | GenericImageConverter (Pillow) |
| `converters/pdf_converters.py` | PdfToImageConverter, PdfToTextConverter (PyMuPDF) |
| `converters/text_converters.py` | TxtToPdf, TxtToHtml, HtmlToTxt (ReportLab / stdlib) |
| `services/detector.py` | FileDetector — magic bytes + deep validation |
| `services/worker.py` | ConversionWorker (QThread) |
| `ui/main_window.py` | MainWindow — state machine, signal connections |
| `ui/radial_wheel.py` | RadialWheel — custom QPainter widget |
| `ui/file_card.py` | FileCard — drag-drop zone |
| `ui/glass_styles.py` | PALETTE, FORMAT_ACCENT_COLORS, MAIN_STYLESHEET |
| `utils/path_helpers.py` | sanitize_filename, get_unique_output_path, get_multipage_output_paths |
| `utils/sample_generator.py` | Generates all test sample files |
| `install_context_menu.ps1` | HKCU context menu registration (no admin) — with verification |
| `uninstall_context_menu.ps1` | Removes HKCU context menu keys — with verification |
| `tests/test_context_menu_loading.py` | 12 tests for context-menu file-loading paths |
| `docs/` | All documentation (PRD, architecture, rules, design, task, memory) |

---

## Commands Reference

```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
.venv\Scripts\pip.exe install -r requirements.txt

# Run all tests
.venv\Scripts\python.exe -m pytest tests/ -v

# Run only context-menu tests
.venv\Scripts\python.exe -m pytest tests/test_context_menu_loading.py -v

# Run the application (GUI)
.venv\Scripts\python.exe main.py

# Run GUI with a preloaded file (simulates context-menu)
.venv\Scripts\python.exe main.py "C:\path\to\file with spaces.png"

# Run CLI conversion
.venv\Scripts\python.exe main.py --cli --source file.pdf --target png

# Install context menu (no admin)
powershell -ExecutionPolicy Bypass -File install_context_menu.ps1

# Verify context menu installation
Get-ItemProperty 'HKCU:\Software\Classes\*\shell\QuickConvert\command'

# Uninstall context menu
powershell -ExecutionPolicy Bypass -File uninstall_context_menu.ps1

# Generate test samples
.venv\Scripts\python.exe utils/sample_generator.py

# Build with PyInstaller (Phase 6 — NOT YET RUN)
.venv\Scripts\pyinstaller QuickConvert.spec
```

---

## Context Menu Integration Details (2026-10-24)

### Registry path written
```
HKCU\Software\Classes\*\shell\QuickConvert           (default) = "Convert with QuickConvert"
                                                      MUIVerb   = "Convert with QuickConvert"
                                                      Icon      = <exe or icon.ico path>
HKCU\Software\Classes\*\shell\QuickConvert\command   (default) = "<launcher>" "%1"
```

### Dev mode command
```
"D:\PROJECTS\QuickConvertMowa\.venv\Scripts\pythonw.exe" "D:\PROJECTS\QuickConvertMowa\main.py" "%1"
```

### Packaged mode command
```
"D:\PROJECTS\QuickConvertMowa\dist\QuickConvert\QuickConvert.exe" "%1"
```

### How `%1` is passed to the app
Windows Shell expands `"%1"` to the full quoted path of each selected file.
Python on Windows receives each argument as an already-expanded, distinct
element in `sys.argv` — no further string splitting is needed.
`_resolve_file_arg()` in `main.py` handles edge cases (stray quotes,
relative paths, missing files).

---

## Next Recommended Actions (Priority Order)

1. **[Phase 6] Run PyInstaller build** — execute `.venv\Scripts\pyinstaller QuickConvert.spec`; check `dist/QuickConvert/`
2. **[Phase 6] Test packaged exe launches GUI correctly** — `dist\QuickConvert\QuickConvert.exe`
3. **[Phase 6] Test context menu with packaged exe** — run installer, right-click a file
4. **[Phase 7] Confirm all acceptance criteria from PRD.md are met**
5. **[Phase 7] Tag release version in git**
6. **[Future] Implement batch conversion** — file list widget, worker queue
7. **[Future] LibreOffice bridge** — add DOCX converter class to registry

---

## Discrepancies Between Docs and Code

| Item | Intended (Docs) | Actual (Code) | Status |
|---|---|---|---|
| Modern Win11 context menu | `IExplorerCommand` (future) | HKCU legacy shell key | Documented limitation |
| Batch conversion | Phase 2 future | Batch sidebar tab available | Partial |
| Dark mode theme | Future enhancement | Not implemented | Not yet started |
| DPI/quality controls in UI | Future enhancement | Options exist in ConversionOptions; sliders in Settings page | Partial |
