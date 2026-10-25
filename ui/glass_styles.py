"""
Glassmorphic styling system for QuickConvert matching the official Windows 11 design spec.
Features:
- Windows 11 Mica / Acrylic inspired light backgrounds
- Gradient text and buttons
- Frosted cards with subtle borders
- Saturated icon badges
"""

PALETTE = {
    # Surfaces
    "bg_window": "#F1F5FB",
    "bg_sidebar": "rgba(255, 255, 255, 0.7)",
    "bg_card": "rgba(255, 255, 255, 0.85)",
    "bg_card_hover": "rgba(255, 255, 255, 0.96)",
    "bg_hub": "#FFFFFF",
    "bg_input": "#FFFFFF",
    
    # Borders
    "border_subtle": "#E2E8F0",
    "border_glass": "rgba(255, 255, 255, 0.9)",
    "border_focus": "#8B5CF6",
    
    # Brand Accents
    "primary_gradient_start": "#06B6D4",
    "primary_gradient_mid": "#3B82F6",
    "primary_gradient_end": "#8B5CF6",
    
    "purple": "#7C3AED",
    "blue": "#2563EB",
    "sky": "#0EA5E9",
    "teal": "#14B8A6",
    "mint": "#10B981",
    "orange": "#F97316",
    "amber": "#D97706",
    "red": "#EF4444",
    "pink": "#EC4899",
    
    # Text
    "text_primary": "#0F172A",
    "text_secondary": "#475569",
    "text_muted": "#94A3B8",
}

FORMAT_ACCENT_COLORS = {
    "png": ("#3B82F6", "#DBEAFE"),
    "jpeg": ("#F97316", "#FFEDD5"),
    "jpg": ("#F97316", "#FFEDD5"),
    "webp": ("#06B6D4", "#CFFAFE"),
    "pdf": ("#EF4444", "#FEE2E2"),
    "txt": ("#10B981", "#D1FAE5"),
    "html": ("#8B5CF6", "#EDE9FE"),
    "docx": ("#2563EB", "#DBEAFE"),
    "bmp": ("#6366F1", "#EEF2FF"),
    "tiff": ("#14B8A6", "#CCFBF1"),
    "gif": ("#EC4899", "#FCE7F3"),
}

# Rich format colors for nodes matching the design infographic
FORMAT_NODE_THEMES = {
    "pdf": {
        "bg_start": "#EF4444",
        "bg_end": "#DC2626",
        "halo": "rgba(239, 68, 68, 0.35)",
        "label": "PDF",
        "icon": "📄",
    },
    "jpeg": {
        "bg_start": "#38BDF8",
        "bg_end": "#0284C7",
        "halo": "rgba(56, 189, 248, 0.35)",
        "label": "JPG",
        "icon": "🖼️",
    },
    "png": {
        "bg_start": "#FB923C",
        "bg_end": "#EA580C",
        "halo": "rgba(251, 146, 60, 0.45)",
        "label": "PNG",
        "icon": "🌄",
    },
    "webp": {
        "bg_start": "#A855F7",
        "bg_end": "#7E22CE",
        "halo": "rgba(168, 85, 247, 0.35)",
        "label": "WebP",
        "icon": "✨",
    },
    "txt": {
        "bg_start": "#34D399",
        "bg_end": "#059669",
        "halo": "rgba(52, 211, 153, 0.35)",
        "label": "TXT",
        "icon": "📝",
    },
    "html": {
        "bg_start": "#F43F5E",
        "bg_end": "#BE123C",
        "halo": "rgba(244, 63, 94, 0.35)",
        "label": "HTML",
        "icon": "🌐",
    },
    "docx": {
        "bg_start": "#3B82F6",
        "bg_end": "#1D4ED8",
        "halo": "rgba(59, 130, 246, 0.35)",
        "label": "Word\n(DOCX)",
        "icon": "📘",
    },
    "xlsx": {
        "bg_start": "#F59E0B",
        "bg_end": "#B45309",
        "halo": "rgba(245, 158, 11, 0.35)",
        "label": "Excel\n(XLSX)",
        "icon": "📊",
    },
    "bmp": {
        "bg_start": "#6366F1",
        "bg_end": "#4338CA",
        "halo": "rgba(99, 102, 241, 0.35)",
        "label": "BMP",
        "icon": "🎨",
    },
    "tiff": {
        "bg_start": "#14B8A6",
        "bg_end": "#0F766E",
        "halo": "rgba(20, 184, 166, 0.35)",
        "label": "TIFF",
        "icon": "🎞️",
    },
    "gif": {
        "bg_start": "#EC4899",
        "bg_end": "#BE185D",
        "halo": "rgba(236, 72, 153, 0.35)",
        "label": "GIF",
        "icon": "🎬",
    },
}

MAIN_STYLESHEET = """
QWidget {
    font-family: "Segoe UI Variable Text", "Segoe UI", -apple-system, Roboto, sans-serif;
    color: #0F172A;
}

QMainWindow {
    background-color: #F1F5FB;
}

/* Glass Card */
QFrame#glassCard {
    background-color: rgba(255, 255, 255, 0.88);
    border: 1px solid rgba(226, 232, 240, 0.9);
    border-radius: 18px;
}

/* Sidebar Frame */
QFrame#sidebarFrame {
    background-color: rgba(255, 255, 255, 0.7);
    border-right: 1px solid #E2E8F0;
    border-radius: 0px;
}

/* Sidebar Navigation Buttons */
QPushButton#navBtn {
    background-color: transparent;
    border: none;
    border-radius: 10px;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 500;
    color: #475569;
    text-align: left;
}

QPushButton#navBtn:hover {
    background-color: rgba(241, 245, 249, 0.8);
    color: #0F172A;
}

QPushButton#navBtn[active="true"] {
    background-color: #EDE9FE;
    color: #6D28D9;
    font-weight: 600;
}

/* Input Fields */
QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 9px 14px;
    font-size: 13px;
    color: #0F172A;
}

QLineEdit:focus {
    border: 1.5px solid #8B5CF6;
    background-color: #FFFFFF;
}

/* Gradient Primary Action Button */
QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06B6D4, stop:0.5 #3B82F6, stop:1 #8B5CF6);
    color: #FFFFFF;
    font-weight: 600;
    font-size: 14px;
    border: none;
    border-radius: 14px;
    padding: 12px 28px;
}

QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0891B2, stop:0.5 #2563EB, stop:1 #7C3AED);
}

QPushButton#primaryBtn:pressed {
    background: #1D4ED8;
}

QPushButton#primaryBtn:disabled {
    background-color: #E2E8F0;
    color: #94A3B8;
}

/* Secondary Button */
QPushButton#secondaryBtn {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    color: #475569;
    font-size: 13px;
    font-weight: 500;
    border-radius: 10px;
    padding: 8px 16px;
}

QPushButton#secondaryBtn:hover {
    background-color: #F8FAFC;
    border-color: #CBD5E1;
    color: #0F172A;
}

/* Progress Bar */
QProgressBar {
    background-color: #E2E8F0;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    border: none;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:0.6 #8B5CF6, stop:1 #06B6D4);
    border-radius: 6px;
}

/* Drop Zone Frame */
QFrame#dropZone {
    background-color: rgba(248, 250, 252, 0.7);
    border: 2px dashed #CBD5E1;
    border-radius: 16px;
}

QFrame#dropZone:hover {
    background-color: #EDE9FE;
    border-color: #8B5CF6;
}

/* Badge Pills */
QLabel#badgePill {
    background-color: #EDE9FE;
    color: #6D28D9;
    font-size: 11px;
    font-weight: 600;
    padding: 5px 12px;
    border-radius: 12px;
    border: 1px solid #DDD6FE;
}

QLabel#featurePill {
    background-color: #FFFFFF;
    color: #475569;
    font-size: 11px;
    font-weight: 500;
    padding: 5px 12px;
    border-radius: 12px;
    border: 1px solid #E2E8F0;
}
"""
