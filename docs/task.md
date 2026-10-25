# task.md — Phased Development Roadmap
## QuickConvert: Fast Offline File Converter for Windows

**Version:** 1.0 | **Last Updated:** 2026-10-24  
**Test Results:** 50/50 tests passing (as of 2026-10-24)

---

## Status Key
- `[x]` Completed and verified
- `[ ]` Not started
- `[/]` In progress (marked explicitly below)

---

## Phase 0 — Repository Audit and Setup

- [x] Inspect repository structure and existing files
- [x] Verify Python virtual environment (`.venv`, Python 3.11.3)
- [x] Confirm all declared dependencies are installed (PySide6, PyMuPDF, Pillow, ReportLab, pytest, PyInstaller)
- [x] Establish project folder structure:
  - `converters/`, `services/`, `ui/`, `utils/`, `tests/`, `assets/`, `docs/`
- [x] Confirm `requirements.txt` exists with version constraints
- [x] Create `docs/` folder with all six documentation files

---

## Phase 1 — Conversion Engine

### Registry
- [x] Design and implement `ConversionRegistry` singleton (`converters/registry.py`)
- [x] Implement format normalization (`jpg` → `jpeg`, case-insensitive)
- [x] Implement `get_target_options_for_source()` — returns all formats with enabled/disabled state
- [x] Implement LibreOffice detection (`shutil.which("soffice")` + common Windows paths)
- [x] Ensure no converter appears enabled without a registered implementation

### Base Classes
- [x] Define `BaseConverter` ABC with `convert()` contract (`converters/base.py`)
- [x] Define `ConversionOptions` dataclass (output_dir, name, quality, dpi, multipage_extract_all)
- [x] Define `ConversionResult` dataclass (success, source_file, output_files, error_message, details)
- [x] Define `TargetOption` dataclass (target_format, label, is_enabled, disabled_reason, is_multipage, converter)

### Image Converters
- [x] Implement `GenericImageConverter` (`converters/image_converters.py`)
  - [x] PNG to JPEG (with transparency → white composite)
  - [x] PNG to WebP (preserving transparency)
  - [x] JPEG to PNG
  - [x] JPEG to WebP
  - [x] WebP to PNG
  - [x] WebP to JPEG
  - [x] BMP to/from PNG, JPEG, WebP, TIFF, GIF
  - [x] TIFF to/from PNG, JPEG, WebP, BMP, GIF
  - [x] GIF to/from PNG, JPEG, WebP, BMP, TIFF
  - [x] Any image to PDF (single page)
  - [x] Multi-frame TIFF/GIF to multiple individual images
  - [x] Multi-frame TIFF to single multi-page PDF

### PDF Converters
- [x] Implement `PdfToImageConverter` — renders each page to PNG/JPEG/WebP at configurable DPI
- [x] Implement `PdfToTextConverter` — extracts embedded text with page headers

### Text Converters
- [x] Implement `TxtToPdfConverter` — ReportLab SimpleDocTemplate, line wrapping, Unicode
- [x] Implement `TxtToHtmlConverter` — standalone styled HTML, proper `html.escape`
- [x] Implement `HtmlToTxtConverter` — `HTMLParser`-based tag stripping

### Output Safety
- [x] Implement `sanitize_filename()` — strips Windows-invalid chars; returns `"converted"` for empty/blank input
- [x] Implement `get_unique_output_path()` — auto-increments to avoid collisions
- [x] Implement `get_multipage_output_paths()` — numbered series with collision handling
- [x] Verify source file is never modified by any converter
- [x] Verify partial output files are cleaned up on failure

### Tests
- [x] `test_pdf_to_png` — 2-page PDF produces 2 PNG files
- [x] `test_pdf_to_jpeg` — 2-page PDF produces 2 JPEG files
- [x] `test_pdf_to_txt` — text extraction includes page headers and content
- [x] `test_txt_to_pdf` — valid PDF with ≥1 page
- [x] `test_png_to_jpeg` — JPEG output, RGB mode
- [x] `test_jpeg_to_png` — PNG output
- [x] `test_png_and_jpeg_to_webp` — WebP output for both sources
- [x] `test_webp_to_png_and_jpeg` — correct format outputs
- [x] `test_bmp_to_png_and_jpeg` — correct outputs
- [x] `test_multipage_tiff_to_png` — 2 frames → 2 PNG files
- [x] `test_gif_to_png` — 2 frames → 2 PNG files
- [x] `test_image_to_pdf` — single-page PDF output
- [x] `test_txt_to_html_and_back` — HTML has DOCTYPE; TXT extraction has headings
- [x] `test_overwrite_protection` — second identical conversion produces `(1)` suffix
- [x] `test_encrypted_pdf_failure` — success=False, "password-protected" in message

---

## Phase 2 — UI and Design System

### Styles
- [x] Define `PALETTE` dict with all color tokens (`ui/glass_styles.py`)
- [x] Define `FORMAT_ACCENT_COLORS` dict (per-format accent + light bg)
- [x] Implement `MAIN_STYLESHEET` — all Qt widget styles for window, cards, buttons, input, progress bar, tooltip

### File Card
- [x] Implement `FileCard` widget with drag-and-drop (accepts file URLs)
- [x] Implement empty/idle state display
- [x] Implement valid file loaded state (filename, format, size, page count, transparency badge)
- [x] Implement invalid file state (red error display)
- [x] Implement drag-over visual highlight (dashed purple border)
- [x] "Browse Files" / "Change File" button with file filter
- [x] "✕" clear button — hidden when no file, visible when file loaded

### Radial Wheel
- [x] Implement `RadialWheel` as custom `QWidget` with `QPainter`
- [x] Orbital track ring (dashed, with outer glow)
- [x] Format nodes distributed evenly on orbit
- [x] Enabled node states: normal, hovered (+ 3px, accent colors), selected (gradient + glow halo)
- [x] Disabled node states: dimmed, semi-transparent
- [x] Hub center: empty / invalid / valid file states
- [x] Format badge pill on hub (accent color)
- [x] Filename display (elided) on hub
- [x] Metadata display (size, pages, transparency)
- [x] Mouse hover: cursor change + tooltip
- [x] Mouse click: select enabled target; tooltip for disabled
- [x] Keyboard navigation: arrow keys cycle through enabled targets
- [x] Accessibility: `setAccessibleName` + `setAccessibleDescription`
- [x] **Fix applied:** Hit detection radius aligned with visual radius (both `min_dim * 0.075`)

### Main Window
- [x] Implement `MainWindow` with header bar (title, subtitle, privacy badge)
- [x] File card integration (file_dropped → load_file)
- [x] Radial wheel integration (target_selected → _update_convert_button)
- [x] Output name input + Reset button
- [x] Save folder selector + Reset button
- [x] **Fix applied:** Folder picker cancel now preserves existing selection
- [x] **Fix applied:** Invalid file load clears the output name field (no stale name)
- [x] Progress section (hidden when idle)
- [x] Result banner (success green / error red)
- [x] Primary convert button (dynamic text, disabled/enabled states)
- [x] Initial `_refresh_targets()` call on startup

---

## Phase 3 — Conversion Workflow

- [x] Implement `ConversionWorker` (QThread) with `progress_changed` + `finished` signals
- [x] Implement cancellation via `_is_cancelled` flag and `InterruptedError`
- [x] Connect worker signals to MainWindow progress bar and result banner
- [x] Implement Open File button — `QDesktopServices.openUrl`
- [x] Implement Open Folder button — `subprocess.run(["explorer", "/select,", path])`
- [x] `_on_convert_clicked` builds `ConversionOptions` and starts worker
- [x] `_on_cancel_clicked` calls `worker.cancel()`
- [x] UI state: convert button disabled during conversion; re-enabled on finish

---

## Phase 4 — Windows Integration

- [x] Implement `--cli`, `--source`, `--target`, `--output-dir`, `--name` argument parsing
- [x] Implement `run_cli_conversion()` — headless conversion with print progress
- [x] Handle positional file paths from context menu (`%1` argument)
- [x] Implement `install_context_menu.ps1` — HKCU registry, no admin, supports dev + packaged exe
- [x] Implement `uninstall_context_menu.ps1` — removes only created keys
- [x] Handle Windows DLL resolution for PySide6 / shiboken6 in both dev and packaged modes

### Phase 4 Next Phase (Windows Explorer Integration) — 2026-10-24

- [x] **Audit `main.py` positional-arg handling for robustness** — reviewed and improved
- [x] **Fix: silent drop of non-existent path args** — now emits clear stderr warning
- [x] **Fix: stray surrounding quotes from some shells** — `_resolve_file_arg()` strips defensively
- [x] **Fix: relative path resolution** — resolved against CWD before checking existence
- [x] **Fix: UnicodeEncodeError on cp1252 consoles** — `_ensure_utf8_stdio()` reconfigures stdout/stderr to UTF-8
- [x] **Improve `install_context_menu.ps1`** — clear error with actionable fix, MUIVerb, post-write verification
- [x] **Improve `uninstall_context_menu.ps1`** — pre-check, post-removal verification, clear success/failure output
- [x] **Add `tests/test_context_menu_loading.py`** — 12 new tests (spaces, Unicode, missing, multiple files, stray quotes)
- [x] **Update README.md** — full context-menu section: How It Works, Installation, Verification, Troubleshooting, Uninstallation
- [x] **Run full test suite: 50/50 PASS** — no regressions (2026-10-24)

**Known limitation:** Context menu appears under "Show more options" on Windows 11 (legacy HKCU approach). Modern primary context menu requires `IExplorerCommand` COM registration — not yet implemented.

### CLI Tests
- [x] `test_cli_help` — `--help` exits 0 and prints "QuickConvert" and "--cli"
- [x] `test_cli_conversion_success` — PNG → JPEG produces 1 `.jpg` file
- [x] `test_cli_corrupt_file_failure` — exits non-zero, "corrupt" or "unreadable" in stderr
- [x] `test_cli_missing_args` — exits non-zero, "Error: CLI mode requires --source and --target"

### Context-Menu Loading Tests (new — 2026-10-24)
- [x] `TestResolveFileArg::test_returns_path_for_existing_file`
- [x] `TestResolveFileArg::test_path_with_spaces`
- [x] `TestResolveFileArg::test_path_with_unicode`
- [x] `TestResolveFileArg::test_nonexistent_path_returns_warning`
- [x] `TestResolveFileArg::test_empty_arg_returns_none_silently`
- [x] `TestResolveFileArg::test_stray_quotes_stripped`
- [x] `TestCliPathHandling::test_single_file_path_succeeds`
- [x] `TestCliPathHandling::test_path_with_spaces_cli_mode`
- [x] `TestCliPathHandling::test_path_with_unicode_cli_mode`
- [x] `TestCliPathHandling::test_nonexistent_path_cli_fails_with_message`
- [x] `TestPositionalArgLoading::test_multiple_files_warning_for_nonexistent`
- [x] `TestPositionalArgLoading::test_missing_args_exits_nonzero`

---

## Phase 5 — Testing and Reliability

- [x] Execute all 50 automated tests — **50/50 PASS** (2026-10-24)
- [x] Fix Bug #1: `sanitize_filename("")` returning `""` → hidden `.ext` file
- [x] Fix Bug #2: folder picker cancel resetting previously selected folder
- [x] Fix Bug #3: invalid file load leaving stale name in output name field
- [x] Fix Bug #4: radial wheel hit radius (`0.08`) larger than visual radius (`0.075`)
- [x] Fix Bug #5: UnicodeEncodeError on cp1252 consoles when printing Unicode filenames
- [x] Verify source files are never modified
- [x] Verify output file verification step rejects empty outputs

### Detector Tests
- [x] `test_detect_multipage_pdf` — format=pdf, page_count=2, is_encrypted=False
- [x] `test_detect_encrypted_pdf` — is_encrypted=True, is_valid=False
- [x] `test_detect_empty_file` — detected_format=empty, size=0, is_valid=False
- [x] `test_detect_corrupt_pdf` — is_valid=False, "corrupt" in error
- [x] `test_detect_misleading_extension` — JPEG content detected despite .png name
- [x] `test_detect_png_with_transparency` — has_transparency=True, dimensions=(200,200)
- [x] `test_detect_multipage_tiff` — page_count=2
- [x] `test_detect_animated_gif` — page_count=2
- [x] `test_detect_text` — detected_format=txt
- [x] `test_detect_html` — detected_format=html

### Registry Tests
- [x] `test_registry_has_converters` — len(converters) > 0
- [x] `test_supported_targets_for_pdf` — PNG/JPEG/WebP/TXT enabled; PDF/DOCX disabled
- [x] `test_supported_targets_for_png` — all image formats enabled; PNG itself disabled
- [x] `test_empty_or_unknown_source` — all disabled, "no valid file" in reason
- [x] `test_normalization` — JPG and jpeg resolve to same converter

---

## Phase 6 — Packaging

- [x] Determine correct PyInstaller spec or command for QuickConvert
  - Requires: `--windowed`, `--icon assets/icon.ico`, `--add-data "assets;assets"`, `--add-data "$pysidePluginsDir;PySide6/plugins"`
  - Bundled: PySide6 (core, gui, widgets, plugins/platforms/qwindows.dll), PyMuPDF, Pillow, ReportLab, docx, markdown
  - Automatic `qt.conf` and `platforms/qwindows.dll` deployment
- [x] Run PyInstaller build and verify `dist/QuickConvert/QuickConvert.exe` exists
- [x] Test packaged exe launches GUI correctly without crashing or platform plugin errors
- [x] Test packaged exe works with CLI mode (`--help`, `--cli`) and real conversions
- [x] Verify `assets/icon.ico` exists — **YES** (4534 bytes, confirmed)
- [x] Test packaged exe in isolated environment (stripped PATH without Python/Anaconda)
- [x] Document `dist/QuickConvert/` size (~11.2 MB executable, ~150 MB distribution)

---

## Phase 7 — Release Readiness

- [x] Write user-facing `README.md` with setup, usage, and context menu install instructions (updated 2026-10-25)
- [x] Confirm all acceptance criteria from `PRD.md` are met
- [x] Document known limitations clearly:
  - [x] Legacy context menu on Windows 11 ("Show more options") — documented
  - [x] No DOCX without python-docx — documented
  - [x] No OCR for scanned PDFs — documented
  - [x] No batch conversion in radial view — documented
- [x] Final automated test run on release build — **62/62 PASSED**
- [ ] Tag release version in git

---

## Future / Backlog

- [ ] Batch conversion mode (multiple files queue)
- [ ] LibreOffice bridge for DOCX/XLSX/PPTX
- [ ] OCR support via Tesseract (optional dependency)
- [ ] SVG input support
- [ ] PDF page range selection in UI
- [ ] Modern Windows 11 IExplorerCommand context menu
- [ ] Dark mode theme
- [ ] DPI/quality controls exposed in UI panel
- [ ] System tray icon
