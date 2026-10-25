# rules.md — Development Rules and Engineering Standards
## QuickConvert: Fast Offline File Converter for Windows

**Version:** 1.0 | **Date:** 2026-10-24  
**Applies to:** All contributors, agents, and future development sessions.

> These rules are mandatory. Do not deviate without explicitly documenting the reason and getting confirmation.

---

## 1. Technology and Dependencies

### 1.1 Approved Stack
| Role | Library | Version Constraint |
|---|---|---|
| UI framework | PySide6 | `>=6.6.0` |
| PDF operations | PyMuPDF (`pymupdf`) | `>=1.23.0,<2.0.0` |
| Image operations | Pillow | `>=10.0.0` |
| PDF generation from text | ReportLab | `>=4.0.0` |
| Testing | pytest | `>=7.4.0` |
| Windows packaging | PyInstaller | `>=6.3.0` |
| Office conversions (optional) | LibreOffice `soffice` | System-detected, not bundled |

### 1.2 Dependency Rules
- **Declare every dependency** in `requirements.txt` with version constraints.
- **Pin tested major versions** — use `>=X.Y.0,<(X+1).0.0` for libraries with known breaking changes (e.g., PyMuPDF).
- **Do not add new dependencies** without justifying them in a comment and confirming no existing dependency already provides the same functionality.
- **Do not use** tkinter, wxPython, PyQt5, or other UI toolkits.
- **Do not use** cloud SDKs, upload libraries, or any library that makes network calls.
- **Do not use** OpenCV — Pillow is sufficient for raster image I/O.
- **Do not duplicate** PDF logic across PyMuPDF and another library.
- **Do not use paid APIs** — all conversion must be achievable with free, open-source libraries.

---

## 2. Code Organization

### 2.1 Layer Separation — MANDATORY
```
ui/          <- PySide6 widgets only. Never import converter logic directly.
services/    <- File detection and background workers.
converters/  <- Conversion implementations and registry. No Qt imports.
utils/       <- Stateless helpers: path sanitization, file size formatting, icon generation.
main.py      <- Entry point only: CLI parsing, DLL path setup, QApplication bootstrap.
tests/       <- Automated tests. No production logic.
docs/        <- Documentation only.
```

**Imports must flow downward:** `ui` → `services` + `converters` + `utils`. Never upward.

### 2.2 File Size and Responsibility
- **No file over ~400 lines** without a clear justification.
- Each class must have a single, named purpose.
- Each converter class handles exactly one `(source_format, target_format)` pair category.
- Do not duplicate conversion logic between converters.

### 2.3 Naming Conventions
- Classes: `PascalCase`
- Functions and variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Type hints: required on all function signatures in non-trivial code
- Docstrings: required on all public classes and non-obvious functions

### 2.4 Forbidden Patterns
- **No magic constants** — DPI values, quality settings, radii multipliers must be named
- **No circular imports** — enforced by the layer rule above
- **No hardcoded machine paths** — use `Path(__file__).resolve().parent` or `sys.prefix`
- **No `if True:` or `if False:` dead code** blocks
- **No commented-out code** committed to the repository

---

## 3. Conversion Rules

### 3.1 Registry — Single Source of Truth
- All converters **must be registered** in `ConversionRegistry._register_default_converters()`.
- A format **must not appear as enabled** in the UI unless a converter for it is registered.
- The UI wheel **must derive its enabled/disabled state from the registry**, never from hardcoded assumptions.
- `get_target_options_for_source()` is the only function that decides availability.

### 3.2 Converter Implementation Contract
Every converter that extends `BaseConverter` **must**:
1. Set `self.source_format`, `self.target_format`, `self.output_extension`, `self.display_name`.
2. Implement `convert(source_path, options, progress_cb)` → `ConversionResult`.
3. Report progress via `progress_cb(pct, message)` at meaningful intervals (not just 0 and 100).
4. Return `ConversionResult(success=False, error_message=...)` on failure — never raise an unhandled exception.
5. Clean up all partial output files on failure.
6. Verify that all output files exist and are non-empty before returning success.
7. **Never modify the source file.**
8. **Never overwrite an existing file** — always use `get_unique_output_path()` or `get_multipage_output_paths()`.

### 3.3 Multi-page Files
- Multi-page PDFs: produce one output image per page, numbered `_001`, `_002` …
- Multi-frame TIFFs and GIFs: produce one output image per frame, same naming.
- Single-frame to multi-page PDF: wrap all frames into one PDF using Pillow's `save_all=True`.

### 3.4 Transparency Handling
- PNG to JPEG: composite transparent pixels over white background — do **not** produce corrupt black images.
- PNG to WebP: preserve transparency using `lossless=True` mode.
- JPEG alpha: JPEG has no alpha channel; always convert mode to `RGB` before saving.

---

## 4. Error Handling

### 4.1 Mandatory Error Cases
Every converter and the FileDetector **must handle**:
- File does not exist
- File is 0 bytes
- File is encrypted (PDFs)
- File is corrupt or truncated
- File is an unsupported format passed with a misleading extension
- Disk write permission error
- Output path creation failure

### 4.2 User-Facing Error Messages
- Error messages **must be readable by a non-technical user**.
- Messages **must be specific** — "Cannot convert: PDF is password-protected" not "Error".
- Messages **must not expose internal stack traces** to the UI.
- Stack traces may be printed to stderr for debugging but must not appear in the GUI.

### 4.3 Forbidden Patterns
```python
# FORBIDDEN: silent failure
except Exception:
    pass

# FORBIDDEN: generic "something went wrong"
return ConversionResult(success=False, error_message="Error occurred")

# FORBIDDEN: swallowing errors in validation
try:
    validate()
except:
    pass
```

---

## 5. Security and Privacy

### 5.1 Network
- **Zero network calls** — no HTTP, no socket, no DNS lookup, no telemetry.
- Do not import `requests`, `urllib`, `httpx`, or any network library.

### 5.2 File Handling
- Open input files with **read-only** intent (`open(path, "rb")` or `open(path, "r")`).
- Never write to the source file path.
- Validate that `output_path != source_path` before writing.
- Sanitize all output filenames with `sanitize_filename()` before building paths.

### 5.3 Subprocess
- **Never use `shell=True`** in `subprocess.run()` or `subprocess.Popen()`.
- Always pass arguments as a list: `["explorer", "/select,", file_path]`.
- Never concatenate user input into shell strings.

### 5.4 Windows Registry
- Write only to `HKCU\Software\Classes\*\shell\QuickConvert` and its sub-keys.
- Never write to `HKLM` (requires admin and is system-wide).
- The uninstaller **must remove** exactly the keys the installer created — no more, no less.
- Use the .NET `Microsoft.Win32.Registry` API, not PowerShell `Set-ItemProperty` with `HKCR:` paths.

### 5.5 Logging
- Never log file **contents** — only filenames, format types, and error summaries.
- Diagnostic output goes to stderr, not a persistent log file (no PII retention).

---

## 6. Testing and Quality

### 6.1 Test Coverage Requirements
- **Every enabled conversion pair** must have at least one automated test.
- **Every disabled/unsupported case** must have a test confirming it is properly rejected.
- **Every edge case** must have a test: empty file, encrypted PDF, corrupt file, misleading extension.
- **Multipage export** must be tested: page count, individual file existence, file validity.
- **Overwrite protection** must be tested: two conversions with the same name must produce two distinct files.
- **Source preservation** must be tested: source file must exist and be unmodified after conversion.

### 6.2 Test Organization
- All tests go in `tests/`.
- Use `pytest` fixtures and `tmp_path` / `tmp_path_factory` for isolation.
- Use `sample_generator.py` to generate fresh test files — never commit binary test files.
- Tests must be runnable with: `.venv\Scripts\python.exe -m pytest tests/ -v`
- All tests must pass before committing any change to a converter or the registry.

### 6.3 Forbidden Test Patterns
- **Never fabricate test results** — only mark `[x]` in `task.md` after running and confirming.
- **Never assert `True`** as a substitute for a real assertion.
- **Never skip tests** with `pytest.mark.skip` without a dated comment explaining why.

---

## 7. UI and Design Rules

### 7.1 Widget Responsibility
- `FileCard` is responsible only for displaying file info and emitting signals.
- `RadialWheel` is responsible only for painting and emitting `target_selected`.
- `MainWindow` is responsible for state management and connecting signals to slots.
- UI widgets **must not** perform I/O or conversion logic directly.

### 7.2 Thread Safety
- **All UI updates must happen on the main thread.** 
- `ConversionWorker` communicates with `MainWindow` only via Qt Signals (queued connection).
- Never call `QWidget` methods directly from a worker thread.

### 7.3 Radial Wheel
- Format availability must always come from `registry.get_target_options_for_source()`.
- The wheel must never hardcode which formats are enabled or disabled.
- Hit detection radius must match the visual radius exactly (both `min_dim * 0.075`).
- Disabled nodes must show a tooltip explaining the specific reason.

### 7.4 Style System
- Use `MAIN_STYLESHEET` from `glass_styles.py` — do not apply inline styles except for dynamic state changes (e.g., success/error banner color).
- Use named `objectName` properties for styled widgets: `"primaryBtn"`, `"secondaryBtn"`, `"glassCard"`, `"iconBtn"`.
- Do not hardcode colors in widget code — reference `PALETTE` or `FORMAT_ACCENT_COLORS`.

---

## 8. Agent Workflow Rules

When implementing or modifying QuickConvert:

1. **Read first.** Before writing code, read `memory.md`, `task.md`, and the relevant source files.
2. **Understand before changing.** Inspect errors before applying fixes.
3. **Do not rewrite working code** without a documented reason.
4. **Run affected tests** after every change to converters, registry, detector, or path helpers.
5. **Update `task.md`** as tasks are started (`[/]`) and completed (`[x]`).
6. **Update `memory.md`** after meaningful milestones — test runs, bug fixes, packaging.
7. **Update `PRD.md` or `architecture.md`** if requirements or architecture change.
8. **Do not mark a feature complete** unless its acceptance criterion has been verified.
9. **Report discrepancies** between documentation and code honestly — do not silently adjust requirements to match an incomplete implementation.
10. **Ask before broad refactors** — do not reorganize the entire codebase to add one feature.
