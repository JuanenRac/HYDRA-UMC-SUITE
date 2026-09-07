# =============================================================================
# HYDRA-UMC SUITE - ui/widgets/rotary_knob.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Custom-painted rotary knob, the desktop counterpart to HYDRA-UMC-STUDIO's
# own src/components/RotaryKnob.tsx (same idea: an arc gauge from min to
# max, a needle showing the live value, vertical-drag to change it) -
# reimplemented with QPainter rather than reused as-is, since that
# component is React/SVG and has no Python equivalent to import.
# =============================================================================
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

ARC_START_DEG = 225   # gauge sweeps from 225deg (bottom-left)...
ARC_SPAN_DEG = -270   # ...270deg clockwise to -45deg (bottom-right) - a 3/4 circle, leaving the bottom open


class RotaryKnob(QWidget):
    valueChanged = Signal(float)

    def __init__(self, minimum: float = -180.0, maximum: float = 180.0, value: float = 0.0, parent: QWidget | None = None):
        super().__init__(parent)
        self._min = minimum
        self._max = maximum
        self._value = max(minimum, min(maximum, value))
        self._dragging = False
        self._drag_start_y = 0.0
        self._drag_start_value = 0.0
        self.setMinimumSize(56, 56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def setRange(self, minimum: float, maximum: float) -> None:
        self._min, self._max = minimum, maximum
        self._value = max(minimum, min(maximum, self._value))
        self.update()

    def value(self) -> float:
        return self._value

    def setValue(self, value: float) -> None:
        clamped = max(self._min, min(self._max, value))
        if clamped != self._value:
            self._value = clamped
            self.update()

    def _fraction(self) -> float:
        span = self._max - self._min
        return 0.0 if span == 0 else (self._value - self._min) / span

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        side = min(self.width(), self.height())
        rect = QRectF((self.width() - side) / 2 + 4, (self.height() - side) / 2 + 4, side - 8, side - 8)

        # Track (full range, dim)
        pen = QPen(QColor("#1c232d"))
        pen.setWidth(max(2, side // 14))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, ARC_START_DEG * 16, ARC_SPAN_DEG * 16)

        # Filled portion (current value, cyan accent - matches the app's own QSS theme)
        pen.setColor(QColor("#21c6de"))
        painter.setPen(pen)
        filled_span = ARC_SPAN_DEG * self._fraction()
        painter.drawArc(rect, ARC_START_DEG * 16, int(filled_span * 16))

        # Center readout
        painter.setPen(QColor("#d6dee6"))
        font = painter.font()
        font.setPointSizeF(max(7.0, side / 7.0))
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self._value:.1f}")

        # Needle
        angle_deg = ARC_START_DEG + ARC_SPAN_DEG * self._fraction()
        angle_rad = math.radians(angle_deg)
        cx, cy = rect.center().x(), rect.center().y()
        r = rect.width() / 2 - pen.width()
        needle_end = QPointF(cx + r * math.cos(angle_rad), cy - r * math.sin(angle_rad))
        needle_pen = QPen(QColor("#4fe0f5"))
        needle_pen.setWidth(2)
        painter.setPen(needle_pen)
        painter.drawLine(rect.center(), needle_end)

    def mousePressEvent(self, event) -> None:
        self._dragging = True
        self._drag_start_y = event.position().y()
        self._drag_start_value = self._value

    def mouseMoveEvent(self, event) -> None:
        if not self._dragging:
            return
        # Vertical drag, same convention as most professional DAW/industrial
        # knob widgets (up = increase) - a full-height drag sweeps the
        # whole range, scaled by the widget's own size so a bigger knob
        # feels proportionally coarser per pixel, not finer.
        delta_px = self._drag_start_y - event.position().y()
        span = self._max - self._min
        sensitivity = span / max(120.0, self.height() * 2.0)
        self.setValue(self._drag_start_value + delta_px * sensitivity)
        self.valueChanged.emit(self._value)

    def mouseReleaseEvent(self, event) -> None:
        self._dragging = False

    def wheelEvent(self, event) -> None:
        span = self._max - self._min
        step = span / 200.0
        direction = 1 if event.angleDelta().y() > 0 else -1
        self.setValue(self._value + step * direction)
        self.valueChanged.emit(self._value)
