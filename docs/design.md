# design.md — UI/UX and Visual Design System
## QuickConvert: Fast Offline File Converter for Windows

**Version:** 1.0 | **Date:** 2026-10-24

---

## 1. Design Principles

| Principle | Description |
|---|---|
| **Premium and minimal** | Every element earns its place. Decoration exists only when it aids comprehension or interaction. |
| **Honest availability** | Disabled states are visible and explained — no format is hidden, no false affordance exists. |
| **Interaction-first** | The most common action (select format, convert) requires the fewest interactions. |
| **Frosted glass light theme** | Warm off-white backgrounds, translucent card panels, soft lavender accents, delicate borders. |
| **Subtle motion** | Hover effects and hover transitions convey state, never distract from work. |
| **Accessible by default** | All interactive elements reachable via keyboard, with visible focus states and sufficient contrast. |
| **Responsive within bounds** | Minimum size 560×720. Radial wheel scales proportionally. |

---

## 2. Color Palette (Design Tokens)

### Surfaces
| Token | Hex | Usage |
|---|---|---|
| `bg_window` | `#F6F7FB` | Main window background (warm off-white) |
| `bg_card` | `rgba(255,255,255,0.85)` | Glass card panels (semi-transparent white) |
| `bg_card_hover` | `rgba(255,255,255,0.95)` | Card hover state |
| `bg_hub` | `rgba(255,255,255,0.92)` | Radial wheel hub center |
| `bg_input` | `rgba(255,255,255,0.90)` | Input fields |

### Borders
| Token | Hex | Usage |
|---|---|---|
| `border_subtle` | `rgba(226,232,240,0.85)` | Card edges, dividers |
| `border_focus` | `#8B5CF6` | Input field focus ring |
| `border_highlight` | `rgba(139,92,246,0.40)` | Hover border accent |

### Accents
| Token | Hex | Usage |
|---|---|---|
| `primary` | `#7C3AED` | Primary action button, selected node halo |
| `primary_hover` | `#6D28D9` | Button hover |
| `primary_light` | `#EDE9FE` | Badge backgrounds, tinted highlights |
| `powder_blue` | `#0284C7` | Secondary accent |
| `powder_blue_light` | `#E0F2FE` | Blue-tinted surfaces |
| `mint` | `#059669` | Success states |
| `mint_light` | `#D1FAE5` | Success banner background |
| `coral` | `#E11D48` | Error states |
| `coral_light` | `#FFE4E6` | Error banner background |

### Text
| Token | Hex | Usage |
|---|---|---|
| `text_primary` | `#0F172A` | Body, headings, filename |
| `text_secondary` | `#475569` | Labels, section headers |
| `text_muted` | `#94A3B8` | Placeholder, metadata |
| `text_dimmed` | `#CBD5E1` | Disabled text |

### Format Accent Colors (per-format nodes on radial wheel)
| Format | Accent | Light Bg |
|---|---|---|
| PNG | `#3B82F6` | `#DBEAFE` |
| JPEG | `#F97316` | `#FFEDD5` |
| WebP | `#06B6D4` | `#CFFAFE` |
| PDF | `#EF4444` | `#FEE2E2` |
| TXT | `#10B981` | `#D1FAE5` |
| HTML | `#8B5CF6` | `#EDE9FE` |
| BMP | `#6366F1` | `#EEF2FF` |
| TIFF | `#14B8A6` | `#CCFBF1` |
| GIF | `#EC4899` | `#FCE7F3` |
| DOCX | `#2563EB` | `#DBEAFE` |

---

## 3. Typography

| Role | Font | Size | Weight | Line Height |
|---|---|---|---|---|
| App title | Segoe UI | 20px | 700 Bold | 1.2 |
| Subtitle | Segoe UI | 12px | 400 Regular | 1.4 |
| Section label | Segoe UI | 12px | 600 SemiBold | 1.3 |
| Body / metadata | Segoe UI | 12px | 400 Regular | 1.5 |
| Small / helper | Segoe UI | 11px | 400 Regular | 1.4 |
| Primary button | Segoe UI | 14px | 600 SemiBold | 1.0 |
| Secondary button | Segoe UI | 13px | 500 Medium | 1.0 |
| Wheel hub filename | Segoe UI | 11px | 600 DemiBold | 1.2 |
| Wheel hub metadata | Segoe UI | 9px | 400 Regular | 1.2 |
| Wheel node label | Segoe UI | 9–10px | 700 Bold | 1.0 |
| Tooltip | Segoe UI | 12px | 400 Regular | 1.4 |

**Fallback family:** `-apple-system, BlinkMacSystemFont, Roboto, sans-serif`

---

## 4. Component Specifications

### 4.1 Application Window
- **Size:** 680×840 default; minimum 560×720
- **Background:** `#F6F7FB`
- **Layout:** Single-column VBox with 28px horizontal / 20px top / 24px bottom margins
- **Font:** Applied globally via `MAIN_STYLESHEET` on the root `QWidget`

### 4.2 Header Bar
- Left: App title (⚡ QuickConvert, 20px/700) + subtitle (12px/400 muted)
- Right: Privacy badge — "🛡️ 100% Offline" pill, `#EDE9FE` background, `#6D28D9` text, rounded-12, border `#DDD6FE`
- No window chrome or menu bar

### 4.3 File Card (`FileCard`)

**States:**

| State | Display |
|---|---|
| **Empty** | 📂 icon, "Drag & drop any file here", format list subtitle, "Browse Files" button |
| **Valid file loaded** | 📄 icon, filename (bold), metadata (FORMAT • size • pages • transparency), "Change File" button, "✕" clear button |
| **Invalid file loaded** | ⚠️ icon, filename in red (`#DC2626`), error description in red, "Change File" + "✕" buttons |

**Drag-over state:** `background-color: #EDE9FE; border: 2px dashed #8B5CF6`

**Container:** `QFrame#glassCard` — `border-radius: 16px`, min-height 84px

### 4.4 Radial Conversion Wheel (`RadialWheel`)
See Section 5 for detailed specification.

### 4.5 Output Configuration Panel

**Container:** `QFrame#glassCard`, 16px content padding

**Output Name Row:**
- Label: "Output name:" (12px/600, `#475569`, min-width 80px)
- Input: `QLineEdit` — rounded-10, 8px 14px padding, 13px, placeholder "Auto-generated..."
- Reset button: `QPushButton#secondaryBtn` — "Reset"
- Focus ring: `1.5px solid #8B5CF6`

**Save Folder Row:**
- Label: "Save folder:" (12px/600)
- Display: current folder path or "Same folder as source" (12px muted)
- "Change Folder" button: `QPushButton#secondaryBtn`
- "Reset" button: `QPushButton#secondaryBtn` — reverts to source folder
- Cancel on folder picker: preserves existing selection (no reset on cancel)

### 4.6 Progress Section (hidden when idle)
- Status label: `12px/500 #475569` + "Cancel" secondary button (right-aligned)
- Progress bar: 8px height, rounded-6, gradient `#8B5CF6` → `#06B6D4`
- Visible only during active conversion

### 4.7 Result Banner

**Success state:**
- Background: `#ECFDF5`, border: `1px solid #A7F3D0`, `border-radius: 14px`
- Icon: ✨ (20px), text: "Successfully converted! Generated N file(s)." (`#047857`)
- Buttons: "Open File" and "Open Folder" (both `#secondaryBtn`)

**Error state:**
- Background: `#FEF2F2`, border: `1px solid #FECACA`, `border-radius: 14px`
- Icon: ❌, text: "Failed: [readable error message]" (`#B91C1C`)
- Buttons hidden

### 4.8 Primary Convert Button
- `QPushButton#primaryBtn`
- Gradient: `#7C3AED` → `#6366F1` (left to right)
- 14px/600, 12px 28px padding, `border-radius: 12px`
- Disabled: `#E2E8F0` background, `#94A3B8` text
- Hover: darker gradient `#6D28D9` → `#4F46E5`
- Label dynamically updated: "Select a format to convert" / "Convert to JPEG (JPG)" / "Cannot convert invalid file"

### 4.9 Buttons

**Primary Button (`#primaryBtn`):**
```
background: linear-gradient(→, #7C3AED, #6366F1)
color: white | weight 600 | 14px | radius 12 | padding 12 28
hover: #6D28D9 → #4F46E5
disabled: #E2E8F0 bg, #94A3B8 text
```

**Secondary Button (`#secondaryBtn`):**
```
background: rgba(255,255,255,0.9) | border: 1px #E2E8F0
color: #475569 | weight 500 | 13px | radius 10 | padding 8 16
hover: white bg, border #CBD5E1, text #1E293B
```

**Icon Button (`#iconBtn`):**
```
background: transparent | no border | radius 8 | padding 6
color: #64748B
hover: #F1F5F9 bg, border #E2E8F0, text #0F172A
```

### 4.10 Tooltips
```
background: #1E293B | color: #F8FAFC
border: none | radius 8 | padding 6 10 | 12px
```

---

## 5. Radial Conversion Wheel — Detailed Specification

### 5.1 Geometry (scales with widget size)

| Property | Formula | At 400px |
|---|---|---|
| Hub radius | `min_dim × 0.22` | 88px |
| Orbit radius | `min_dim × 0.38` | 152px |
| Node radius | `min_dim × 0.075` | 30px |
| Node hit radius | `min_dim × 0.075` | 30px (matches visual exactly) |
| Hovered node bonus | +3px radius | 33px |

**Minimum widget size:** 400×400px

### 5.2 Node Layout
- Format nodes are distributed evenly on the orbit circle
- Starting angle: −90° (top, 12 o'clock position)
- Direction: clockwise
- Total nodes: 10 (one per `PRIMARY_FORMATS` entry)

### 5.3 Node States

| State | Background | Border | Text | Extra |
|---|---|---|---|---|
| **Enabled — normal** | White → light accent color gradient | `#CBD5E1` 1.5px | `#0F172A` dark | — |
| **Enabled — hovered** | White → light accent color gradient | Accent color 2px | Accent color | +3px radius |
| **Enabled — selected** | `#7C3AED` → `#6366F1` gradient | `#FFFFFF` 2.5px | `#FFFFFF` | Radial glow halo |
| **Disabled** | `rgba(241,245,249,0.55)` flat | `rgba(226,232,240,0.63)` 1px | `rgba(148,163,184,0.63)` | No hover effect |

### 5.4 Hub Center States

**No file loaded:**
- 📂 icon (24px), "Drop a file here" label, "or click Browse" subtitle
- All muted/placeholder colors

**Invalid file loaded:**
- ⚠️ icon, filename in muted text, validation error elided
- All nodes disabled

**Valid file loaded:**
- Format badge pill (e.g., "PDF") with format accent color on light bg
- Filename (elided to fit hub width, DemiBold)
- Metadata: "1.2 MB • 4 pgs" or "245 KB • Transparent"

### 5.5 Radial Glow (selected node)
```python
glow = QRadialGradient(nx, ny, curr_r * 1.5)
glow.setColorAt(0.0, QColor(124, 58, 237, 90))   # violet, 35% opacity
glow.setColorAt(1.0, QColor(124, 58, 237, 0))    # transparent
# Drawn at 1.45× node radius
```

### 5.6 Orbital Track
- Dashed ring: `QPen(QColor(226,232,240,180), 1.5, Qt.DashLine)`
- Outer glow: radial gradient, `rgba(243,240,255,120)` → transparent, radius 1.25× orbit

### 5.7 Interaction Behavior

| Interaction | Behavior |
|---|---|
| Hover over enabled node | Cursor: PointingHandCursor, +3px radius, accent border/text, tooltip "Convert to JPEG (JPG)" |
| Hover over disabled node | Cursor: ForbiddenCursor, tooltip with `disabled_reason` |
| Left click enabled node | `set_selected_target(fmt)`, glowing selection applied |
| Left click disabled node | Tooltip with `disabled_reason` (no selection change) |
| Arrow Right / Down | Advance to next enabled target in clockwise order |
| Arrow Left / Up | Go to previous enabled target |
| Enter / Space | (Not currently implemented — future: confirm selection) |
| Window resize | All radii scale proportionally; layout adapts |

### 5.8 Wheel Availability Rule
The wheel always calls `registry.get_target_options_for_source(fmt)` to determine format availability. The wheel widget contains **no hardcoded format availability logic** of its own.

---

## 6. Layout Spacing and Sizing Tokens

| Token | Value | Usage |
|---|---|---|
| `margin_window_h` | 28px | Window left/right margin |
| `margin_window_top` | 20px | Window top margin |
| `margin_window_bottom` | 24px | Window bottom margin |
| `gap_section` | 16px | Vertical gap between sections |
| `gap_row` | 10px | Vertical gap within a card |
| `gap_buttons` | 8–10px | Horizontal gap between buttons |
| `radius_card` | 16px | Glass card border radius |
| `radius_btn_primary` | 12px | Primary button radius |
| `radius_btn_secondary` | 10px | Secondary button radius |
| `radius_input` | 10px | Input field radius |
| `radius_tooltip` | 8px | Tooltip border radius |
| `radius_badge` | 11–12px | Badge pill radius |
| `min_window_w` | 560px | Minimum window width |
| `min_window_h` | 720px | Minimum window height |

---

## 7. Motion and Animation Guidelines

| Element | Animation | Duration | Easing |
|---|---|---|---|
| Node hover radius | +3px on hover | Instant (QPainter repaint on mouse move) | — |
| Hover border color | Instant repaint | — | — |
| Progress bar fill | Animated by Qt automatically | Smooth | Qt default |
| Result banner appear | `setVisible(True)` — instant | — | — |
| Drag-over highlight | `setStyleSheet()` on dragEnter | Instant | — |

> QuickConvert does not use QPropertyAnimation or explicit timers for motion. All visual state changes occur on repaint triggered by mouse events or signal handlers. This keeps motion subtle and avoids distracting transitions.

---

## 8. Empty States

| Context | Message | Visual |
|---|---|---|
| No file loaded | "Drop a file here / or click Browse" | 📂 icon in hub center |
| Unsupported format source | All wheel nodes disabled with reasons | ⚠️ icon in hub |
| Conversion in progress | Progress bar + status message | Cancel button visible |
| No result yet | Result banner hidden | — |

---

## 9. Accessibility Requirements

- **Keyboard navigation:** Full radial wheel keyboard support (arrow keys)
- **Focus policy:** `Qt.StrongFocus` on radial wheel
- **Screen reader hint:** `setAccessibleName("Format Selection Radial Wheel")` + `setAccessibleDescription`
- **Cursor feedback:** `Qt.PointingHandCursor` on hoverable elements, `Qt.ForbiddenCursor` on disabled nodes
- **Text contrast:** All body text on glass cards: `#0F172A` on `rgba(255,255,255,0.85)` — passes WCAG AA
- **Error messages:** Shown in red (`#DC2626`) with sufficient contrast on white/light card background
- **Tooltip trigger:** Both hover and click show tooltip on disabled nodes

---

## 10. Implementation Notes (PySide6)

- All styling applied via `setStyleSheet(MAIN_STYLESHEET)` on root `QWidget`
- Dynamic state changes (success/error banner) use `setStyleSheet()` on the specific frame
- `RadialWheel` is a custom `QWidget` using `QPainter` — no Qt layout manager inside it
- `FileCard` uses `QHBoxLayout` internally
- Glassmorphic frosted effect is approximated using semi-transparent backgrounds — not a true platform blur (requires Win32 DWM API, not available in PySide6 without extensions)
- The design is fully implementable in PySide6 without any browser-based framework
