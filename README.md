# ⚡ QuickConvert — Windows 11 File Converter

> **Private, local, offline file converter with a light-glassmorphism radial UI and seamless Windows Explorer integration.**

![QuickConvert Banner](assets/icon.ico)

[![Platform: Windows 11](https://img.shields.io/badge/Platform-Windows%2011%20%7C%2010-0078D4?logo=windows)](https://microsoft.com)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?logo=python)](https://python.org)
[![GUI: PySide6](https://img.shields.io/badge/GUI-PySide6%20%28Qt6%29-41CD52?logo=qt)](https://qt.io)
[![Privacy: 100% Offline](https://img.shields.io/badge/Privacy-100%25%20Offline-10B981)](#offline-first-architecture)
[![Tests: 50 Passed](https://img.shields.io/badge/Tests-50%20Passing-success)](#testing)

---

## Overview

![QuickConvert — Effortless File Conversion](https://raw.githubusercontent.com/dharanikandikonda7/QuickConvert_v1/master/QuickConvert_%20Effortless%20File%20Conversion.png)



## 🌟 Highlights

- **🎯 Interactive Radial Format Wheel**: Supported target formats are vibrantly highlighted with pastel badges, interactive hover effects, and keyboard navigation. Unsupported pairs are dimmed with explanatory tooltips.
- **🛡️ 100% Offline & Private**: Zero cloud uploads, zero external telemetry, zero paid APIs. All processing stays strictly on your local machine.
- **🔍 Content-Based Type Detection**: Inspects magic bytes and file structure rather than trusting misleading file extensions. Safely flags encrypted PDFs, 0-byte files, and corrupt inputs.
- **⚡ Windows Explorer Context Menu**: Right-click any file in Windows Explorer → *"Show more options"* → *"Convert with QuickConvert"* to launch directly with your file preloaded.
- **🛡️ Overwrite Protection & Multipage Safety**: Never overwrites existing files silently (appends `(1)`, `(2)`). Multipage PDFs and TIFFs render into sequentially numbered files (`_001.png`, `_002.png`).
- **💻 Dual Mode (GUI & Headless CLI)**: Use the modern glassmorphic desktop GUI or automate conversions headlessly via CLI flags.

---

## 🎨 Visual Design System

QuickConvert implements a light-glassmorphism UI inspired by modern Windows 11 design guidelines:

- **Surfaces**: Warm off-white (`#F6F7FB`) background, frosted white card surfaces (`rgba(255, 255, 255, 0.85)`), and delicate 1px translucent borders (`#E2E8F0`).
- **Color Accents**: Pastel lavender (`#7C3AED`), powder blue (`#0284C7`), mint emerald (`#059669`), and restrained coral (`#EF4444`).
- **Central Hub**: Displays live file metadata (detected format badge, truncated filename, file size, page count, transparency).
- **Responsive & Accessible**: Full mouse hover halos, Arrow/Enter keyboard navigation, and high-DPI scaling awareness.

---

## 🔄 Supported Conversions Matrix

QuickConvert uses a centralized `ConversionRegistry` as the single source of truth. Formats are never enabled with placeholder implementations.

| Source Format | Target Formats | Implementation Engine | Notes |
| :--- | :--- | :--- | :--- |
| **PDF** | PNG, JPEG, WebP, TXT | PyMuPDF (`pymupdf`) | Multipage rendering (`_001`, `_002`), custom DPI & JPEG quality |
| **PNG** | JPEG, WebP, BMP, TIFF, GIF, PDF | Pillow (`PIL`) | Alpha channel composited over white for JPEG |
| **JPEG / JPG** | PNG, WebP, BMP, TIFF, GIF, PDF | Pillow (`PIL`) | Lossless / high quality export |
| **WebP** | PNG, JPEG, BMP, TIFF, PDF | Pillow (`PIL`) | Full transparency preservation for PNG |
| **BMP** | PNG, JPEG, WebP, TIFF, PDF | Pillow (`PIL`) | Direct decompression & re-encoding |
| **TIFF** | PNG, JPEG, WebP, BMP, PDF | Pillow (`PIL`) | Multipage TIFF frames extracted or merged into PDF |
| **GIF** | PNG, JPEG, WebP, BMP, PDF | Pillow (`PIL`) | All animation frames extracted |
| **TXT / MD** | PDF, HTML, DOCX | ReportLab, python-docx | Line wrapping, page breaks, Unicode, Word export |
| **HTML** | TXT | `html.parser` | Clean tag stripping and entity unescaping |
| **DOCX (Word)** | PDF, TXT, HTML | `python-docx`, ReportLab | Extracts paragraphs, tables, headings to PDF, TXT, HTML |
| **XLSX / PPTX** | *LibreOffice required* | Registry check | Displays requirement tooltip if LibreOffice is missing |

---

## 🚀 Quick Start & Installation

### 1. Prerequisites
- **Operating System**: Windows 11 / Windows 10 (64-bit)
- **Python**: Version 3.11 or 3.12 installed

### 2. Setup Local Environment
Clone or navigate to the project directory and create the local virtual environment:

```powershell
# Open PowerShell in the project directory
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install pinned dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🖱️ Windows Explorer Context Menu

QuickConvert includes safe, per-user PowerShell scripts that configure the Windows Explorer right-click menu **without requiring administrator privileges** (`HKCU`).

### How It Works

When you right-click a file in Windows Explorer and choose *"Convert with QuickConvert"*, Windows reads the registry key:

```
HKCU\Software\Classes\*\shell\QuickConvert\command
```

and launches the configured executable, passing the full file path as an argument:

```
"<QuickConvert.exe>" "%1"
```

QuickConvert receives the path as a command-line argument, resolves it to an absolute path, and preloads the file into the conversion UI automatically.

**Supports:**
- Paths with spaces (e.g., `My Documents\Report Final v2.pdf`)
- Unicode filenames (e.g., `画像ファイル_テスト.png`)
- Long paths (no truncation)
- Multiple files selected (opens Batch Convert mode)

> **Windows 11 Note:** This entry appears in the **legacy context menu**, accessible via *"Show more options"*. The Windows 11 primary context menu requires a COM-based `IExplorerCommand` extension, which is not yet implemented (future roadmap).

---

### Installation

```powershell
powershell -ExecutionPolicy Bypass -File .\install_context_menu.ps1
```

The installer automatically detects and prefers:
1. `dist\QuickConvert\QuickConvert.exe` (packaged build — no Python needed)
2. `.venv\Scripts\pythonw.exe main.py` (development environment)

**Expected output:**
```
Launcher : Python virtual environment
           D:\PROJECTS\QuickConvertMowa\.venv\Scripts\pythonw.exe

Registering context menu under HKCU\Software\Classes\*\shell\QuickConvert ...

SUCCESS: QuickConvert context menu installed.

HOW TO USE:
  1. Open Windows Explorer and right-click any supported file.
  2. On Windows 11: click 'Show more options' to reveal the legacy menu.
  3. Click 'Convert with QuickConvert'.
```

---

### Verification

After installation, verify the registry entry was written correctly:

```powershell
# Check that the key exists and shows the correct command
Get-ItemProperty 'HKCU:\Software\Classes\*\shell\QuickConvert\command'
```

Expected output (dev mode):
```
(default) : "C:\..\.venv\Scripts\pythonw.exe" "C:\..\main.py" "%1"
```

Or for a packaged build:
```
(default) : "C:\..\dist\QuickConvert\QuickConvert.exe" "%1"
```

You can also verify by right-clicking any file in Windows Explorer:
1. Right-click any file (e.g., a `.png` or `.pdf`)
2. Click **"Show more options"** (Windows 11) or scroll down (Windows 10)
3. You should see **"Convert with QuickConvert"** in the menu

---

### Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| *"Convert with QuickConvert" not visible* | Not yet installed, or on Windows 11 primary menu | Run installer; on Win11 click "Show more options" |
| *Installer says "Cannot find a valid launcher"* | Neither packaged exe nor .venv exists | Run `python -m venv .venv && pip install -r requirements.txt` |
| *App opens but file is not preloaded* | Path resolution failure (rare) | Check stderr output; ensure path exists and is readable |
| *App opens but shows "Invalid File"* | The selected file is corrupt, empty, or unsupported | This is expected behaviour; QuickConvert detected an issue |
| *Menu disappeared after Windows update* | Registry reset (very rare) | Re-run the installer |
| *"Access denied" on uninstall* | Registry key locked by another process | Wait and retry, or delete manually via `regedit` |

#### Manual Registry Inspection

To inspect or delete the key manually:
1. Open `regedit.exe`
2. Navigate to `HKEY_CURRENT_USER\Software\Classes\*\shell\QuickConvert`
3. Right-click → **Delete** to remove

---

### Uninstallation

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall_context_menu.ps1
```

Removes **only** the `HKCU\Software\Classes\*\shell\QuickConvert` key tree.  
No other registry entries are modified. Safe to run even if already uninstalled.

**Expected output:**
```
Removing QuickConvert context menu from HKCU\Software\Classes\*\shell\QuickConvert ...
SUCCESS: QuickConvert context menu removed.

To reinstall later:
  powershell -ExecutionPolicy Bypass -File .\install_context_menu.ps1
```

---

## 💻 Usage

### GUI Mode
Launch the application:
```powershell
.\.venv\Scripts\python.exe main.py
```
Or launch directly with a preloaded file:
```powershell
.\.venv\Scripts\python.exe main.py "C:\path\to\document.pdf"
```

Multiple files open in Batch Convert mode:
```powershell
.\.venv\Scripts\python.exe main.py "C:\file1.png" "C:\file2.pdf"
```

1. **Select File**: Drag and drop any file onto the window, or click **Browse Files**.
2. **Choose Output Format**: Click any highlighted format on the radial wheel (or use Arrow keys + Enter).
3. **Optional Output Settings**: Customize output base name or select a custom output directory.
4. **Convert**: Click **Convert to [FORMAT]**.
5. **Open**: Click **Open File** or **Open Folder** once complete.

### Headless CLI Mode
QuickConvert can also run batch conversions from scripts or the terminal:

```powershell
# Convert PDF to PNG
.\.venv\Scripts\python.exe main.py --cli --source sample.pdf --target png --output-dir ./output

# Convert Text document to PDF
.\.venv\Scripts\python.exe main.py --cli --source notes.txt --target pdf

# Convert PNG to WebP with custom name
.\.venv\Scripts\python.exe main.py --cli --source logo.png --target webp --name brand_logo

# Paths with spaces (use quotes)
.\.venv\Scripts\python.exe main.py --cli --source "My Documents\report.pdf" --target png
```

#### CLI Arguments:
- `--cli`: Enable headless mode.
- `-s, --source <path>`: Source file to convert.
- `-t, --target <format>`: Target format (`png`, `jpeg`, `webp`, `pdf`, `txt`, `html`, `bmp`, `tiff`, `gif`).
- `-o, --output-dir <dir>`: Optional destination folder.
- `-n, --name <name>`: Optional custom base filename.

---

## 🧪 Testing

QuickConvert includes a full automated test suite covering all converters, magic byte detection, encrypted PDFs, zero-byte files, corrupted inputs, misleading extensions, overwrite prevention, and Windows Explorer context-menu file-loading.

Run tests with pytest:
```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

### Test Suite Overview:

| File | Tests | Coverage |
|---|---|---|
| `test_application_verification.py` | 6 | Main window, radial wheel registry sync, real PDF & Image conversion, collision suffixing |
| `test_converters.py` | 19 | All supported conversion pairs, multipage rendering, overwrite collision, DOCX |
| `test_detector.py` | 10 | Content detection, encrypted/corrupt/empty file rejection |
| `test_registry.py` | 5 | Registry consistency, format normalization |
| `test_cli.py` | 6 | CLI argument validation, headless conversion, symbol resolution regression |
| `test_context_menu_loading.py` | 15 | File-loading via positional args: spaces, Unicode, Japanese/emoji paths, cp1252 stream safety |
| `test_packaged_executable.py` | 1 | Packaged executable verification (help, JPEG/PDF conversion, GUI launch, source integrity) |

**Total: 62 tests passing**

### Context-Menu-Specific Tests:

```powershell
# Run only context-menu integration tests
.\.venv\Scripts\python.exe -m pytest tests/test_context_menu_loading.py -v
```

Tests cover:
- `_resolve_file_arg()` unit tests (spaces, Unicode, relative paths, missing files, stray quotes)
- CLI subprocess tests: path with spaces → conversion succeeds
- CLI subprocess tests: Unicode filename → conversion succeeds (UTF-8 stdout handling)
- Non-existent path emits warning, does not crash
- Multiple positional args, one missing → valid file still converts

### Generate Test Sample Files:
```powershell
.\.venv\Scripts\python.exe utils\sample_generator.py
```
Creates sample files (valid documents, multipage PDFs, transparent PNGs, encrypted PDFs, corrupted files) in `test_samples/`.

---

## 📦 Building Executable (PyInstaller)

To compile a standalone, windowed Windows executable:

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

The compiled application will be generated in:
```
dist\QuickConvert\QuickConvert.exe
```

When `dist\QuickConvert\QuickConvert.exe` exists, `install_context_menu.ps1` will automatically configure Windows Explorer to launch the compiled executable directly without needing Python installed!

---

## 📁 Project Architecture

```
QuickConvert/
│
├── main.py                     # Application entrypoint (GUI, CLI, argument parsing)
├── build.ps1                   # Standalone PyInstaller build script
├── install_context_menu.ps1    # Per-user Explorer context menu installer
├── uninstall_context_menu.ps1  # Context menu removal script
├── requirements.txt            # Pinned tested dependencies
├── README.md                   # Complete documentation
│
├── ui/                         # Presentation Layer
│   ├── main_window.py          # Main application window, layouts, signals
│   ├── radial_wheel.py         # Custom painted radial conversion wheel
│   ├── file_card.py            # Drag-and-drop zone and file preview card
│   └── glass_styles.py         # Glassmorphism tokens, QSS styling, palette
│
├── converters/                 # Business Logic & Conversion Engine
│   ├── base.py                 # Converter base class, options, result dataclasses
│   ├── registry.py             # Centralized ConversionRegistry (single source of truth)
│   ├── pdf_converters.py       # PDF to image (PNG/JPEG/WebP) and PDF to text
│   ├── image_converters.py     # Pillow image transformations & Image to PDF
│   └── text_converters.py      # TXT to PDF, TXT to HTML, HTML to TXT
│
├── services/                   # Service Layer
│   ├── detector.py             # Content magic bytes inspection & validation
│   └── worker.py               # Background QThread worker with cancellation
│
├── utils/                      # Utilities
│   ├── path_helpers.py         # Filename sanitization, collision avoidance
│   ├── icon_generator.py       # Multi-resolution ICO generator
│   └── sample_generator.py     # Test file generator
│
├── tests/                      # Automated Test Suite (50 tests)
│   ├── test_converters.py      # 19 conversion tests
│   ├── test_detector.py        # 10 detection tests
│   ├── test_registry.py        # 5 registry tests
│   ├── test_cli.py             # 4 CLI tests
│   └── test_context_menu_loading.py  # 12 context-menu file-loading tests
│
└── assets/                     # Application Assets
    └── icon.ico                # App icon (256x256 down to 16x16)
```

---

## 🔒 Security & Privacy Model

- **Local Execution**: No network connections are opened.
- **HKCU Only**: Context menu registration uses `HKCU` (per-user, no admin elevation needed). Never writes to `HKLM`.
- **Integrity**: Source files are strictly opened in read-only mode and are never modified or overwritten.
- **Fail-Safe Cleanup**: If a conversion fails mid-operation, partial files are automatically removed so incomplete outputs are never presented as successful.
- **Shell Injection Prevention**: All external calls use safe list arguments rather than shell strings. The installer uses `Microsoft.Win32.Registry` .NET API (not `Set-ItemProperty` with string concatenation).
- **Reversible**: The uninstaller removes only the exact keys the installer created — no more, no less.

---

## ⚠️ Known Limitations

| Limitation | Impact | Notes |
|---|---|---|
| Windows 11 context menu shows under "Show more options" | Extra click required | Modern `IExplorerCommand` support is on the future roadmap |
| No DOCX/XLSX/PPTX without python-docx | Disabled in wheel with tooltip | Enabled automatically if `python-docx` is installed |
| PDF text extraction = embedded text only | Scanned PDFs produce empty TXT | OCR via Tesseract is planned |
| No batch conversion in radial view | One file at a time | Batch Convert dashboard available via sidebar |
| Very large PDFs may be slow | Memory & render time | Future: page-range selection |

---

## 📄 License

MIT License. Free for personal and commercial use.
