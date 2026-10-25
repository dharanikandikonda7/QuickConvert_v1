# PRD.md — Product Requirements Document
## QuickConvert: Fast Offline File Converter for Windows

**Version:** 1.0  
**Date:** 2026-10-24  
**Status:** MVP In Progress

---

## 1. Product Overview

QuickConvert is a premium, offline-first, Windows 11 native desktop application for converting files between common formats. It integrates with Windows Explorer's context menu, letting users convert any supported file with a single right-click. It also runs as a standalone drag-and-drop GUI. All conversion happens locally — no internet required, no files leave the machine.

---

## 2. Problem Statement

Windows users regularly need to convert files between formats (PDF ↔ image, TXT ↔ PDF, image ↔ image). Existing tools either:
- Require cloud uploads (privacy risk)
- Are bloated or subscription-locked
- Lack Windows Explorer integration
- Show formats that aren't actually supported without clear feedback
- Produce cryptic error messages

QuickConvert solves these problems with a focused, offline, honest tool that only surfaces conversions it can actually perform.

---

## 3. Product Vision and Value Proposition

> **"Convert any supported file in three clicks — privately, instantly, and for free."**

- **Private by design** — 100% local processing, no telemetry, no network calls
- **Honest UI** — Only shows available conversions; disabled formats are explained, not hidden
- **Windows-native feel** — Context menu integration, Explorer-style folder pickers
- **Premium aesthetics** — Glassmorphic light theme, responsive radial wheel, smooth UX

---

## 4. Goals and Measurable Success Criteria

| Goal | Success Criterion |
|---|---|
| Offline operation | Zero network calls during any conversion |
| Format coverage | ≥ 15 unique conversion pairs working and tested |
| Context menu integration | Right-click → Convert in ≤ 2 clicks |
| Honest availability | 0 enabled conversions without a working implementation |
| Output safety | Source file never modified or overwritten |
| Collision safety | Duplicate output names auto-incremented, never silently overwritten |
| Test coverage | Automated test for every enabled conversion path |
| Packaging | Single-folder PyInstaller build that runs without Python installed |

---

## 5. Non-Goals and Scope Limitations

- **Not a batch converter** — MVP handles one file at a time per conversion run
- **Not a cloud service** — No sync, no sharing, no cloud storage integrations
- **Not a video converter** — No MP4, AVI, MOV, or audio formats
- **Not an OCR engine** — PDF text extraction uses embedded text only (no OCR)
- **Not a document editor** — No editing, annotation, or merging
- **No DOCX/XLSX/PPTX input or output** without LibreOffice (optional dependency)
- **No Linux or macOS** — Windows 11 (Windows 10 secondary) only

---

## 6. Target Users and Use Cases

### Primary Users
- Office workers who frequently convert PDFs to images or TXTs
- Developers and tech-savvy users who work in Windows Explorer
- Designers who need quick PNG ↔ WebP ↔ JPEG conversions
- Privacy-conscious users who refuse cloud upload tools

### User Personas

**Patricia — Office Manager, 45**
> "I receive PDFs from clients and need to email individual pages as JPEG images. I don't want to upload confidential documents to some website."

**Dev — Software Engineer, 29**
> "I right-click files constantly. If there's a context menu entry, I'll use it. I need conversions to be fast and reliable."

**Yuki — Graphic Designer, 33**
> "I convert between PNG, WebP, and JPEG constantly. I need transparent PNGs to flatten correctly to JPEG without turning black."

---

## 7. Core Features and Requirements

### 7.1 Windows Explorer Context Menu Integration
- Right-clicking a supported file shows **"Convert with QuickConvert"**
- App opens with that file pre-loaded
- Installation via HKCU registry (no admin required)
- Reversible via `uninstall_context_menu.ps1`

### 7.2 Standalone GUI Application
- Drag-and-drop file onto the window
- Browse button to pick a file
- File info card shows: filename, format, size, page count (if multi-page), transparency flag

### 7.3 Radial Conversion Wheel
- Displays all known target formats in a circular orbit
- Supported targets: bright, colored, clickable nodes
- Unsupported targets: visibly dimmed, with tooltip explaining why
- Selected target: glowing halo highlight
- Keyboard navigable (arrow keys + Enter)

### 7.4 Output Configuration
- Optional custom output filename input (pre-populated with `<stem>_Converted`)
- Output folder selector (defaults to same folder as source)
- Output folder "Reset" button to revert to default
- Auto-increments filenames to avoid collisions (`file (1).jpg`, `file (2).jpg`, …)

### 7.5 Conversion Engine
- Background thread execution (UI never freezes)
- Honest progress reporting (0–100%)
- Cancellable conversions
- Source file never touched
- Incomplete outputs cleaned up on failure

### 7.6 Result State
- Success banner with file count, Open File, and Open Folder buttons
- Error banner with clear, human-readable error message
- Explorer opened with the output file selected (via `explorer /select,`)

---

## 8. Functional Requirements

| ID | Requirement |
|---|---|
| FR-01 | App loads a file from CLI argument or drag-and-drop |
| FR-02 | App detects file type using magic bytes, not extension |
| FR-03 | Wheel displays correct enabled/disabled state per detected format |
| FR-04 | Disabled formats show a tooltip explaining why they're unsupported |
| FR-05 | User can select any enabled target format |
| FR-06 | User can set a custom output filename |
| FR-07 | User can pick a custom output folder |
| FR-08 | Conversion runs in a background thread |
| FR-09 | Progress bar updates continuously during conversion |
| FR-10 | User can cancel in-progress conversion |
| FR-11 | Success banner shows output file count and provides Open File / Open Folder |
| FR-12 | Error banner shows a specific, readable error message |
| FR-13 | Source file is never modified |
| FR-14 | Output filename collisions are resolved automatically |
| FR-15 | Multi-page PDFs produce one image file per page |
| FR-16 | Multi-frame TIFFs and GIFs produce one image file per frame |
| FR-17 | Empty, encrypted, and corrupt files are rejected with a clear message |
| FR-18 | Misleading file extensions are handled using content detection |

---

## 9. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Privacy** | Zero network traffic during operation |
| **Performance** | UI responds within 100ms of user interaction |
| **Reliability** | No conversion silently claims success on failure |
| **Safety** | Source files preserved; incomplete outputs deleted on failure |
| **Accessibility** | Full keyboard navigation on radial wheel |
| **Portability** | Single-folder PyInstaller build, no Python install required |
| **Compatibility** | Windows 10 (1903+), Windows 11 |
| **Security** | HKCU registry only; no admin elevation |

---

## 10. Main User Journey

### Context Menu Flow
```
1. User right-clicks file.png in Windows Explorer
2. Clicks "Convert with QuickConvert"
3. QuickConvert opens; file.png pre-loaded in File Card
4. Radial wheel shows: JPEG, WebP, BMP, TIFF, GIF, PDF enabled; TXT, HTML, DOCX disabled
5. User clicks JPEG node (selected, glowing)
6. User optionally types custom name in "Output name" field
7. User clicks "Convert to JPG"
8. Progress bar animates 0% -> 100%
9. Success banner: "✨ Successfully converted! Generated 1 file."
10. User clicks "Open File" -> image opens in default viewer
```

### Standalone Flow
```
1. User launches QuickConvert.exe
2. Drags a PDF onto the drop zone (or clicks Browse)
3. Wheel shows PNG, JPEG, WebP, TXT enabled; others disabled
4. User selects PNG; multi-page badge shown on PDF hub
5. User clicks "Convert to PNG"
6. Progress shows per-page rendering
7. Success: "Generated 2 files." (for 2-page PDF)
8. User clicks "Open Folder" -> Explorer opens with all files highlighted
```

---

## 11. File Format and Conversion Compatibility Matrix

| Source \ Target | PNG | JPEG | WebP | PDF | TXT | HTML | BMP | TIFF | GIF | DOCX |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **PDF** | ✅ | ✅ | ✅ | — | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **PNG** | — | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| **JPEG** | ✅ | — | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| **WebP** | ✅ | ✅ | — | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| **BMP** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | — | ✅ | ✅ | ❌ |
| **TIFF** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | — | ✅ | ❌ |
| **GIF** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | — | ❌ |
| **TXT** | ❌ | ❌ | ❌ | ✅ | — | ✅ | ❌ | ❌ | ❌ | ❌ |
| **HTML** | ❌ | ❌ | ❌ | ❌ | ✅ | — | ❌ | ❌ | ❌ | ❌ |

✅ = Implemented and tested | ❌ = Not supported | — = Same format (disabled)

**DOCX:** Available only if LibreOffice is detected on the system.

---

## 12. Error Handling and Edge Cases

| Scenario | Expected Behavior |
|---|---|
| File not found | "File not found: filename.ext" |
| 0-byte file | "File is 0 bytes (empty file)." |
| Encrypted PDF | "PDF is password-protected or encrypted." |
| Corrupt file | "Corrupt or unreadable [format]: [detail]" |
| Misleading extension (JPEG named .png) | Detected as JPEG, handled correctly |
| Unsupported format | Format shown as disabled in wheel with tooltip |
| Output path collision | Auto-incremented: `file (1).jpg`, `file (2).jpg` |
| Permission error on write | "Cannot write output: [OS error]" |
| Conversion cancelled | "Conversion was cancelled." — partial files cleaned up |
| Empty output produced | Verification step raises RuntimeError, reported as failure |

---

## 13. Privacy, Security, and Offline Requirements

- **No internet access** required at any point
- **No telemetry** or usage tracking of any kind
- **No file content is logged** — only filenames and format types for diagnostics
- **No cloud upload** — all processing is local CPU/disk
- Context menu registration uses **HKCU only** (no HKLM, no admin elevation)
- Subprocess calls use **argument list form** (no shell string concatenation)
- Input files are read-only; output goes to a separate path

---

## 14. Windows Compatibility Requirements

| Requirement | Detail |
|---|---|
| Minimum OS | Windows 10 version 1903 (May 2019 Update) |
| Primary Target | Windows 11 (22H2+) |
| DPI Awareness | High-DPI scaling via `Qt.HighDpiScaleFactorRoundingPolicy.PassThrough` |
| Context Menu Style | Legacy HKCU shell extension (visible via "Show more options" on Windows 11) |
| Admin Rights | Never required — installation uses HKCU |
| Packaging | Single-folder PyInstaller dist — no Python install required |

> **Note:** Windows 11's primary (modern) context menu requires a COM-based `IExplorerCommand` implementation. The current implementation uses the legacy HKCU shell key, visible via "Show more options." A future enhancement could implement the modern IExplorerCommand approach.

---

## 15. MVP Scope vs. Future Enhancements

### MVP (Current — Verified)
- [x] Image <-> Image (PNG, JPEG, WebP, BMP, TIFF, GIF)
- [x] PDF -> PNG, JPEG, WebP, TXT
- [x] TXT -> PDF, HTML
- [x] HTML -> TXT
- [x] Radial wheel UI
- [x] Context menu (HKCU legacy)
- [x] Multi-page PDF / TIFF / GIF support
- [x] Background thread conversion with cancel
- [x] Output collision protection

### Future Enhancements
- [ ] DOCX / XLSX / PPTX support (via LibreOffice)
- [ ] Batch conversion (multiple files at once)
- [ ] OCR — scanned PDF to searchable text (e.g., via Tesseract)
- [ ] SVG support
- [ ] PDF merging and splitting
- [ ] Modern Windows 11 IExplorerCommand context menu
- [ ] Output quality/DPI controls exposed in UI
- [ ] App icon in system tray
- [ ] Dark mode theme

---

## 16. Acceptance Criteria

| ID | Criterion | Status |
|---|---|---|
| AC-01 | All listed ✅ conversions produce valid output files | ✅ Verified (34/34 tests pass) |
| AC-02 | Disabled conversions cannot be triggered | ✅ Verified |
| AC-03 | Source files are never modified after conversion | ✅ Verified |
| AC-04 | Output filename collisions are auto-incremented | ✅ Verified |
| AC-05 | Encrypted PDFs are rejected gracefully | ✅ Verified |
| AC-06 | Corrupt files are rejected gracefully | ✅ Verified |
| AC-07 | Empty files (0 bytes) are rejected gracefully | ✅ Verified |
| AC-08 | Misleading extensions are handled by content detection | ✅ Verified |
| AC-09 | All 34 automated tests pass | ✅ Verified (34/34) |
| AC-10 | App works from context menu with path argument | ✅ Verified |
| AC-11 | UI never freezes during conversion | ✅ Verified (QThread) |
| AC-12 | PyInstaller build produces a runnable executable | ⬜ Not yet verified |

---

## 17. Known Risks, Assumptions, and Constraints

| Risk/Assumption | Mitigation/Note |
|---|---|
| PyMuPDF API changes between versions | Version pinned: `>=1.23.0,<2.0.0` |
| Pillow dropping older format support | Version pinned: `>=10.0.0` |
| Windows 11 showing legacy context menu under "Show more options" | Documented limitation; IExplorerCommand is future work |
| Very large PDFs (100+ pages) may be slow | DPI governs render time; future: page-range selection |
| LibreOffice not detected on user machines | DOCX target disabled gracefully with a clear tooltip |
| HiDPI screens with non-integer scale factors | Mitigated via PassThrough DPI policy |
