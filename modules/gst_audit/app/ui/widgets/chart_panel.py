from __future__ import annotations

from decimal import Decimal
from typing import Callable, Sequence

from PySide6.QtCore import QRect, Signal, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QPen
from PySide6.QtWidgets import QToolTip, QWidget


def _default_formatter(value: Decimal) -> str:
    abs_value = abs(value)
    if abs_value >= Decimal("10000000"):
        return f"₹{value / Decimal('10000000'):.2f}Cr"
    if abs_value >= Decimal("100000"):
        return f"₹{value / Decimal('100000'):.2f}L"
    return f"₹{value:,.0f}"


def _short_label(label: str, max_chars: int = 14) -> str:
    clean = str(label or "Unknown").strip() or "Unknown"
    return clean if len(clean) <= max_chars else clean[: max_chars - 1] + "…"


def _palette_color(widget: QWidget, role: QPalette.ColorRole, fallback: str) -> QColor:
    try:
        color = widget.palette().color(role)
        return color if color.isValid() else QColor(fallback)
    except Exception:
        return QColor(fallback)


def _chart_colors(widget: QWidget) -> dict[str, QColor]:
    """Resolve chart colors with a controlled light-dashboard palette.

    Native Windows palette roles can return very dark Mid/Light colors in some
    themes, which made chart cards look like old bordered desktop widgets. The
    chart therefore keeps text/accent from the app palette but uses explicit
    neutral card, border, and grid values for a softer dashboard appearance.
    """
    return {
        "panel": QColor("#FFFFFF"),
        "panel_alt": QColor("#F8FAFC"),
        "text": _palette_color(widget, QPalette.ColorRole.WindowText, "#0F172A"),
        "muted": QColor("#64748B"),
        "border": QColor("#D7DEE8"),
        "grid": QColor("#EEF2F7"),
        "axis": QColor("#D7DEE8"),
        "accent": _palette_color(widget, QPalette.ColorRole.Highlight, "#2563EB"),
    }


def _semantic_color(label: str, index: int, widget: QWidget) -> QColor:
    text = (label or "").upper()
    if "VALID" in text or "APPROVED" in text or "MATCH" in text:
        return QColor("#16A34A")
    if "REVIEW" in text or "WARNING" in text or "ROUND" in text:
        return QColor("#F59E0B")
    if "SKIP" in text or "ERROR" in text or "INVALID" in text or "MISMATCH" in text:
        return QColor("#EF4444")
    colors = _chart_colors(widget)
    palette = [
        QColor("#2563EB"),
        QColor("#38BDF8"),
        QColor("#1D4ED8"),
        QColor("#0891B2"),
        QColor("#60A5FA"),
    ]
    return palette[index % len(palette)]


class SimpleBarChart(QWidget):
    """Dependency-free dashboard chart widget.

    Supports bar, line, and donut render modes. The widget is display-only: it
    receives already-filtered data points and emits a label when the user clicks
    a visible chart element for dashboard drill-down.
    """

    point_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = "Dashboard Chart"
        self._points: list[tuple[str, Decimal]] = []
        self._formatter: Callable[[Decimal], str] = _default_formatter
        self._chart_mode = "Bar"
        self._hit_regions: list[tuple[QRect, str, Decimal]] = []
        self._subtitle = "Click a point to filter the table"
        self.setMinimumHeight(285)
        self.setObjectName("ChartPanel")
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

    def set_data(
        self,
        title: str,
        points: Sequence[tuple[str, Decimal]],
        formatter: Callable[[Decimal], str] | None = None,
        chart_mode: str = "Bar",
        subtitle: str | None = None,
    ) -> None:
        self._title = title
        self._points = list(points)
        self._formatter = formatter or _default_formatter
        self._chart_mode = chart_mode if chart_mode in {"Bar", "Line", "Donut"} else "Bar"
        self._subtitle = subtitle or "Click a point to filter the table"
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt API
        point = event.position().toPoint()
        for region, label, value in self._hit_regions:
            if region.contains(point):
                QToolTip.showText(event.globalPosition().toPoint(), f"{label}\n{self._formatter(value)}\nClick to filter", self)
                return
        QToolTip.hideText()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt API
        for region, label, _value in self._hit_regions:
            if region.contains(event.position().toPoint()):
                self.point_clicked.emit(label)
                break
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        colors = _chart_colors(self)
        rect = self.rect().adjusted(14, 14, -14, -14)
        self._hit_regions.clear()

        painter.setPen(QPen(colors["border"], 1))
        painter.setBrush(colors["panel"])
        painter.drawRoundedRect(rect, 20, 20)

        title_font = QFont("Segoe UI", 11)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(colors["text"])
        painter.drawText(rect.adjusted(16, 10, -16, -10), Qt.AlignLeft | Qt.AlignTop, self._title)

        subtitle_font = QFont("Segoe UI", 8)
        painter.setFont(subtitle_font)
        painter.setPen(colors["muted"])
        painter.drawText(rect.adjusted(16, 32, -16, -10), Qt.AlignLeft | Qt.AlignTop, self._subtitle)

        if not self._points:
            painter.setPen(colors["muted"])
            painter.drawText(rect, Qt.AlignCenter, "No chart data for the current filters")
            painter.end()
            return

        if self._chart_mode == "Donut":
            self._paint_donut(painter, rect, colors)
        else:
            self._paint_xy_chart(painter, rect, colors)
        painter.end()

    def _paint_xy_chart(self, painter: QPainter, rect: QRect, colors: dict[str, QColor]) -> None:
        # Keep a larger label zone so supplier names do not collide with the table below.
        chart_rect = rect.adjusted(52, 72, -24, -68)
        values = [abs(value) for _label, value in self._points]
        max_value = max(values) if values else Decimal("0")
        if max_value == 0:
            max_value = Decimal("1")

        tick_font = QFont("Segoe UI", 7)
        painter.setFont(tick_font)
        for i in range(5):
            ratio = Decimal(i) / Decimal(4)
            y = chart_rect.bottom() - int(chart_rect.height() * float(ratio))
            tick_value = max_value * ratio
            painter.setPen(QPen(colors["grid"], 1))
            painter.drawLine(chart_rect.left(), y, chart_rect.right(), y)
            painter.setPen(colors["muted"])
            painter.drawText(rect.left() + 8, y - 8, 40, 16, Qt.AlignRight, self._formatter(tick_value))

        bar_count = len(self._points)
        gap = max(6, min(12, int(chart_rect.width() / max(1, bar_count * 12))))
        raw_bar_width = int((chart_rect.width() - (bar_count - 1) * gap) / max(1, bar_count))
        # A single filtered supplier/month should not render as one crude full-width block.
        # Cap bar width and center the group to keep filtered dashboards visually polished.
        max_bar_width = 220 if bar_count == 1 else 170
        bar_width = max(14, min(max_bar_width, raw_bar_width))
        total_group_width = bar_count * bar_width + max(0, bar_count - 1) * gap
        start_x = chart_rect.left() + max(0, (chart_rect.width() - total_group_width) // 2)
        label_font = QFont("Segoe UI", 7 if bar_count > 8 else 8)
        painter.setFont(label_font)
        label_chars = 8 if bar_count > 8 else 12

        centers: list[tuple[int, int, str]] = []
        for index, (label, value) in enumerate(self._points):
            x = start_x + index * (bar_width + gap)
            height_ratio = float(abs(value) / max_value)
            bar_height = max(4, int(chart_rect.height() * height_ratio))
            y = chart_rect.bottom() - bar_height
            center_x = x + bar_width // 2
            center_y = y
            centers.append((center_x, center_y, label))
            hit_region = QRect(x - 5, y - 18, bar_width + 10, bar_height + 38)
            self._hit_regions.append((hit_region, label, value))

            color = _semantic_color(label, index, self)
            if self._chart_mode == "Bar":
                painter.setPen(Qt.NoPen)
                painter.setBrush(color)
                painter.drawRoundedRect(x, y, bar_width, bar_height, 8, 8)
                if bar_width >= 34 and bar_height >= 24:
                    painter.setPen(colors["text"])
                    painter.drawText(x - 10, y - 20, bar_width + 20, 16, Qt.AlignCenter, self._formatter(value))
            else:
                painter.setPen(QPen(color, 2))
                painter.setBrush(colors["panel"])
                painter.drawEllipse(center_x - 5, center_y - 5, 10, 10)
                painter.drawText(center_x - 35, center_y - 26, 70, 16, Qt.AlignCenter, self._formatter(value))

            painter.setPen(colors["text"])
            # Full labels are available in tooltip; axis labels stay intentionally short.
            painter.drawText(
                x - 18,
                chart_rect.bottom() + 14,
                bar_width + 36,
                42,
                Qt.AlignCenter | Qt.TextWordWrap,
                _short_label(label, label_chars),
            )

        if self._chart_mode == "Line" and len(centers) > 1:
            painter.setPen(QPen(colors["accent"], 2))
            for left, right in zip(centers, centers[1:]):
                painter.drawLine(left[0], left[1], right[0], right[1])

        painter.setPen(colors["muted"])
        painter.drawText(chart_rect.left(), rect.bottom() - 20, chart_rect.width(), 16, Qt.AlignLeft, f"Peak: {self._formatter(max_value)}")

    def _paint_donut(self, painter: QPainter, rect: QRect, colors: dict[str, QColor]) -> None:
        total = sum((abs(v) for _label, v in self._points), start=Decimal("0")) or Decimal("1")
        side = min(rect.width() // 2, rect.height() - 92)
        donut_rect = QRect(rect.left() + 34, rect.top() + 72, side, side)
        start_angle = 90 * 16
        center = donut_rect.center()
        radius = donut_rect.width() // 2
        for index, (label, value) in enumerate(self._points):
            span = int(float(abs(value) / total) * 360 * 16)
            color = _semantic_color(label, index, self)
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawPie(donut_rect, start_angle, -span)
            start_angle -= span

        inner = donut_rect.adjusted(radius // 2, radius // 2, -radius // 2, -radius // 2)
        painter.setBrush(colors["panel"])
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(inner)
        painter.setPen(colors["text"])
        painter.setFont(QFont("Segoe UI", 12, QFont.Bold))
        painter.drawText(inner, Qt.AlignCenter, self._formatter(total))

        legend_left = donut_rect.right() + 30
        legend_top = donut_rect.top()
        painter.setFont(QFont("Segoe UI", 8))
        for index, (label, value) in enumerate(self._points[:8]):
            y = legend_top + index * 24
            color = _semantic_color(label, index, self)
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(legend_left, y + 4, 12, 12, 3, 3)
            painter.setPen(colors["text"])
            pct = (abs(value) / total * Decimal("100")).quantize(Decimal("0.1"))
            legend_rect = QRect(legend_left - 4, y, rect.right() - legend_left - 18, 22)
            self._hit_regions.append((legend_rect, label, value))
            painter.drawText(legend_left + 18, y, rect.right() - legend_left - 22, 20, Qt.AlignVCenter, f"{_short_label(label, 24)} · {pct}%")

        painter.setPen(colors["muted"])
        painter.drawText(
            donut_rect.left(),
            rect.bottom() - 20,
            rect.width() - 36,
            16,
            Qt.AlignLeft,
            "Donut percentages use visible displayed groups; see subtitle for scope",
        )
