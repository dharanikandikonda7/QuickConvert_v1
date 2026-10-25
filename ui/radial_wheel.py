import math
from typing import List, Optional
from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QFont,
    QFontMetrics,
    QPainterPath,
    QRadialGradient,
    QLinearGradient,
    QCursor,
    QMouseEvent,
    QKeyEvent,
)
from PySide6.QtWidgets import QWidget, QToolTip

from converters.registry import TargetOption
from services.detector import FileInfo
from ui.glass_styles import FORMAT_NODE_THEMES, FORMAT_ACCENT_COLORS


class RadialWheel(QWidget):
    """
    Interactive radial conversion wheel matching the QuickConvert design specification.
    Features:
    - Frosted central hub with QuickConvert emblem and 'Convert to' label
    - Saturated gradient format nodes with custom icons and labels
    - Glowing hover halo around active/hovered node
    - Clear disabled states with tooltip explanations
    """

    target_selected = Signal(str)  # format key, e.g. 'png'
    more_formats_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(360, 360)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self.file_info: Optional[FileInfo] = None
        self.target_options: List[TargetOption] = []
        self.selected_target: Optional[str] = "png"
        self.hovered_index: Optional[int] = None
        self.show_all_formats: bool = False

    def set_file_info(self, info: Optional[FileInfo], targets: List[TargetOption]):
        self.file_info = info
        self.target_options = targets

        # Default select first available target if current selection is disabled
        enabled_keys = [t.target_format for t in targets if t.is_enabled]
        if self.selected_target not in enabled_keys:
            self.selected_target = enabled_keys[0] if enabled_keys else None
            if self.selected_target:
                self.target_selected.emit(self.selected_target)

        self.update()

    def set_selected_target(self, target_fmt: str):
        if self.selected_target != target_fmt:
            self.selected_target = target_fmt
            self.target_selected.emit(target_fmt)
            self.update()

    def _get_visible_targets(self) -> List[TargetOption]:
        if not self.target_options:
            return []
        if self.show_all_formats:
            return self.target_options
        # Primary 8 formats featured in the design
        primary_order = ["pdf", "jpeg", "png", "webp", "txt", "html", "xlsx", "docx"]
        filtered = []
        for key in primary_order:
            opt = next((t for t in self.target_options if t.target_format == key), None)
            if opt:
                filtered.append(opt)
        return filtered or self.target_options

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        width = self.width()
        height = self.height()
        cx = width / 2.0
        cy = height / 2.0
        min_dim = min(width, height)

        hub_radius = min_dim * 0.20
        orbit_radius = min_dim * 0.36
        node_radius = min_dim * 0.082

        # 1. Soft orbital ambient background
        self._draw_background(painter, cx, cy, orbit_radius)

        # 2. Draw format nodes
        targets = self._get_visible_targets()
        self._draw_nodes(painter, cx, cy, orbit_radius, node_radius, targets)

        # 3. Central "Convert to" Hub
        self._draw_hub(painter, cx, cy, hub_radius)

    def _draw_background(self, painter: QPainter, cx: float, cy: float, orbit_radius: float):
        # Soft outer purple/blue ambient gradient
        glow = QRadialGradient(cx, cy, orbit_radius * 1.35)
        glow.setColorAt(0.0, QColor(241, 245, 255, 160))
        glow.setColorAt(0.7, QColor(237, 233, 254, 90))
        glow.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QPointF(cx, cy), orbit_radius * 1.35, orbit_radius * 1.35)

        # Subtle thin circular track
        painter.setPen(QPen(QColor(226, 232, 240, 160), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), orbit_radius, orbit_radius)

    def _draw_hub(self, painter: QPainter, cx: float, cy: float, hub_radius: float):
        # Drop shadow
        shadow_grad = QRadialGradient(cx, cy + 6, hub_radius * 1.1)
        shadow_grad.setColorAt(0.6, QColor(100, 116, 139, 40))
        shadow_grad.setColorAt(1.0, QColor(100, 116, 139, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(shadow_grad))
        painter.drawEllipse(QRectF(cx - hub_radius, cy - hub_radius + 6, hub_radius * 2, hub_radius * 2))

        # Frosted central circle
        hub_rect = QRectF(cx - hub_radius, cy - hub_radius, hub_radius * 2, hub_radius * 2)
        hub_grad = QLinearGradient(hub_rect.topLeft(), hub_rect.bottomRight())
        hub_grad.setColorAt(0.0, QColor(255, 255, 255, 255))
        hub_grad.setColorAt(1.0, QColor(248, 250, 252, 250))

        painter.setPen(QPen(QColor(226, 232, 240, 220), 1.5))
        painter.setBrush(QBrush(hub_grad))
        painter.drawEllipse(hub_rect)

        if self.file_info and self.file_info.is_valid:
            # 1. Format Badge Pill
            src_fmt = self.file_info.detected_format.lower()
            theme_color, theme_bg = FORMAT_ACCENT_COLORS.get(src_fmt, ("#7C3AED", "#EDE9FE"))
            pill_text = src_fmt.upper()
            pill_font = QFont("Segoe UI", 9, QFont.Bold)
            fm = QFontMetrics(pill_font)
            pill_w = max(42.0, fm.horizontalAdvance(pill_text) + 14.0)
            pill_h = 18.0
            pill_rect = QRectF(cx - pill_w / 2.0, cy - 36, pill_w, pill_h)

            painter.setPen(QPen(QColor(theme_color), 1.0))
            painter.setBrush(QBrush(QColor(theme_bg)))
            painter.drawRoundedRect(pill_rect, 9, 9)

            painter.setFont(pill_font)
            painter.setPen(QColor(theme_color))
            painter.drawText(pill_rect, Qt.AlignCenter, pill_text)

            # 2. File Name (elided to fit hub)
            name_font = QFont("Segoe UI", 10, QFont.DemiBold)
            painter.setFont(name_font)
            painter.setPen(QColor("#0F172A"))
            fm_name = QFontMetrics(name_font)
            elided_name = fm_name.elidedText(self.file_info.path.name, Qt.ElideMiddle, int(hub_radius * 1.65))
            painter.drawText(QRectF(cx - hub_radius * 0.85, cy - 13, hub_radius * 1.7, 20), Qt.AlignCenter, elided_name)

            # 3. "Convert to"
            label_font = QFont("Segoe UI", 10, QFont.Bold)
            painter.setFont(label_font)
            painter.setPen(QColor("#7C3AED"))
            painter.drawText(QRectF(cx - hub_radius, cy + 9, hub_radius * 2, 18), Qt.AlignCenter, "Convert to")

            # 4. Metadata (size / pages / dims)
            meta_font = QFont("Segoe UI", 8)
            painter.setFont(meta_font)
            painter.setPen(QColor("#64748B"))
            size_b = self.file_info.size_bytes
            size_str = f"{size_b} B" if size_b < 1024 else (f"{size_b // 1024} KB" if size_b < 1024 * 1024 else f"{size_b / (1024*1024):.1f} MB")
            meta_parts = [size_str]
            if self.file_info.page_count and self.file_info.page_count > 1:
                meta_parts.append(f"{self.file_info.page_count} pgs")
            elif self.file_info.dimensions:
                w, h = self.file_info.dimensions
                meta_parts.append(f"{w}×{h}")
            meta_text = " • ".join(meta_parts)
            painter.drawText(QRectF(cx - hub_radius, cy + 28, hub_radius * 2, 16), Qt.AlignCenter, meta_text)

        elif self.file_info and not self.file_info.is_valid:
            warn_font = QFont("Segoe UI Emoji", 20)
            painter.setFont(warn_font)
            painter.drawText(QRectF(cx - hub_radius, cy - 28, hub_radius * 2, 28), Qt.AlignCenter, "⚠️")

            err_title_font = QFont("Segoe UI", 10, QFont.Bold)
            painter.setFont(err_title_font)
            painter.setPen(QColor("#DC2626"))
            painter.drawText(QRectF(cx - hub_radius, cy + 4, hub_radius * 2, 20), Qt.AlignCenter, "Invalid File")

            err_sub_font = QFont("Segoe UI", 8)
            painter.setFont(err_sub_font)
            painter.setPen(QColor("#94A3B8"))
            painter.drawText(QRectF(cx - hub_radius, cy + 24, hub_radius * 2, 16), Qt.AlignCenter, "Cannot convert")

        else:
            # Draw QuickConvert "C" Circular Logo in center when idle
            logo_r = hub_radius * 0.36
            logo_cx = cx
            logo_cy = cy - 14

            pen_logo = QPen()
            pen_logo.setWidthF(6.0)
            pen_logo.setCapStyle(Qt.RoundCap)

            logo_grad = QLinearGradient(logo_cx - logo_r, logo_cy, logo_cx + logo_r, logo_cy)
            logo_grad.setColorAt(0.0, QColor("#06B6D4"))  # Cyan
            logo_grad.setColorAt(0.5, QColor("#3B82F6"))  # Blue
            logo_grad.setColorAt(1.0, QColor("#8B5CF6"))  # Purple
            pen_logo.setBrush(QBrush(logo_grad))

            painter.setPen(pen_logo)
            painter.setBrush(Qt.NoBrush)
            painter.drawArc(
                QRectF(logo_cx - logo_r, logo_cy - logo_r, logo_r * 2, logo_r * 2),
                int(45 * 16),
                int(270 * 16),
            )

            label_font = QFont("Segoe UI", 12, QFont.Bold)
            painter.setFont(label_font)
            painter.setPen(QColor("#0F172A"))
            painter.drawText(QRectF(cx - hub_radius, cy + 12, hub_radius * 2, 28), Qt.AlignCenter, "Convert to")

    def _draw_nodes(
        self,
        painter: QPainter,
        cx: float,
        cy: float,
        orbit_radius: float,
        node_radius: float,
        targets: List[TargetOption],
    ):
        total = len(targets)
        for i, target in enumerate(targets):
            angle = (2 * math.pi * i / total) - (math.pi / 2.0)
            nx = cx + orbit_radius * math.cos(angle)
            ny = cy + orbit_radius * math.sin(angle)

            is_selected = (self.selected_target == target.target_format) and target.is_enabled
            is_hovered = (self.hovered_index == i)

            # Node size grows slightly on hover
            curr_r = node_radius + (3.5 if (is_hovered and target.is_enabled) else 0.0)
            node_rect = QRectF(nx - curr_r, ny - curr_r, curr_r * 2, curr_r * 2)

            theme = FORMAT_NODE_THEMES.get(
                target.target_format,
                {
                    "bg_start": "#6366F1",
                    "bg_end": "#4F46E5",
                    "halo": "rgba(99, 102, 241, 0.35)",
                    "label": target.label,
                    "icon": "📄",
                },
            )

            if target.is_enabled:
                # 1. Glowing Halo on hover / selection
                if is_hovered or is_selected:
                    halo_r = curr_r * 1.55
                    halo_grad = QRadialGradient(nx, ny, halo_r)
                    halo_color = QColor(theme["bg_start"])
                    halo_color.setAlpha(120 if is_selected else 85)
                    halo_grad.setColorAt(0.0, halo_color)
                    halo_grad.setColorAt(0.7, QColor(halo_color.red(), halo_color.green(), halo_color.blue(), 30))
                    halo_grad.setColorAt(1.0, QColor(255, 255, 255, 0))

                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QBrush(halo_grad))
                    painter.drawEllipse(QPointF(nx, ny), halo_r, halo_r)

                # 2. Saturated Gradient Node Card (Squircle)
                grad = QLinearGradient(node_rect.topLeft(), node_rect.bottomRight())
                grad.setColorAt(0.0, QColor(theme["bg_start"]))
                grad.setColorAt(1.0, QColor(theme["bg_end"]))

                border_pen = QPen(QColor("#FFFFFF"), 2.5 if is_selected else 1.5)
                painter.setPen(border_pen)
                painter.setBrush(QBrush(grad))
                painter.drawRoundedRect(node_rect, 18, 18)

                # 3. Node Icon
                icon_font = QFont("Segoe UI Emoji", 16 if curr_r > 32 else 14)
                painter.setFont(icon_font)
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(
                    QRectF(nx - curr_r, ny - curr_r + 6, curr_r * 2, curr_r),
                    Qt.AlignCenter,
                    theme["icon"],
                )

                # 4. Node Label
                label_font = QFont("Segoe UI", 9, QFont.Bold)
                painter.setFont(label_font)
                painter.drawText(
                    QRectF(nx - curr_r, ny + 2, curr_r * 2, curr_r - 4),
                    Qt.AlignCenter,
                    theme["label"],
                )

            else:
                # Dimmed unsupported / disabled node
                painter.setPen(QPen(QColor(226, 232, 240, 160), 1.0))
                painter.setBrush(QBrush(QColor(241, 245, 249, 130)))
                painter.drawRoundedRect(node_rect, 18, 18)

                dim_font = QFont("Segoe UI", 9, QFont.Medium)
                painter.setFont(dim_font)
                painter.setPen(QColor(148, 163, 184, 160))
                painter.drawText(node_rect, Qt.AlignCenter, theme["label"])

    def _get_node_at(self, pos: QPointF) -> Optional[int]:
        targets = self._get_visible_targets()
        if not targets:
            return None

        width = self.width()
        height = self.height()
        cx = width / 2.0
        cy = height / 2.0
        min_dim = min(width, height)
        orbit_radius = min_dim * 0.36
        node_radius = min_dim * 0.082
        total = len(targets)

        for i in range(total):
            angle = (2 * math.pi * i / total) - (math.pi / 2.0)
            nx = cx + orbit_radius * math.cos(angle)
            ny = cy + orbit_radius * math.sin(angle)

            dist = math.hypot(pos.x() - nx, pos.y() - ny)
            if dist <= node_radius * 1.15:
                return i

        return None

    def mouseMoveEvent(self, event: QMouseEvent):
        idx = self._get_node_at(event.position())
        if idx != self.hovered_index:
            self.hovered_index = idx
            self.update()

        targets = self._get_visible_targets()
        if idx is not None and idx < len(targets):
            target = targets[idx]
            if target.is_enabled:
                self.setCursor(Qt.PointingHandCursor)
                tip = f"Convert to {target.label} ({target.output_extension.upper()})"
                if getattr(target, "lossy_note", None):
                    tip += f"\nNote: {target.lossy_note}"
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    tip,
                    self,
                )
            else:
                self.setCursor(Qt.ForbiddenCursor)
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    target.disabled_reason or "This conversion is not supported for this file.",
                    self,
                )
        else:
            self.setCursor(Qt.ArrowCursor)
            QToolTip.hideText()

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            idx = self._get_node_at(event.position())
            targets = self._get_visible_targets()
            if idx is not None and idx < len(targets):
                target = targets[idx]
                if target.is_enabled:
                    self.set_selected_target(target.target_format)
                else:
                    QToolTip.showText(
                        event.globalPosition().toPoint(),
                        target.disabled_reason or "This conversion is not supported for this file.",
                        self,
                    )
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        targets = self._get_visible_targets()
        enabled_indices = [i for i, t in enumerate(targets) if t.is_enabled]
        if not enabled_indices:
            super().keyPressEvent(event)
            return

        all_enabled_fmts = [targets[i].target_format for i in enabled_indices]
        if event.key() in (Qt.Key_Right, Qt.Key_Down):
            if self.selected_target in all_enabled_fmts:
                next_i = (all_enabled_fmts.index(self.selected_target) + 1) % len(all_enabled_fmts)
                self.set_selected_target(all_enabled_fmts[next_i])
            else:
                self.set_selected_target(all_enabled_fmts[0])
            event.accept()
        elif event.key() in (Qt.Key_Left, Qt.Key_Up):
            if self.selected_target in all_enabled_fmts:
                prev_i = (all_enabled_fmts.index(self.selected_target) - 1) % len(all_enabled_fmts)
                self.set_selected_target(all_enabled_fmts[prev_i])
            else:
                self.set_selected_target(all_enabled_fmts[-1])
            event.accept()
        else:
            super().keyPressEvent(event)
