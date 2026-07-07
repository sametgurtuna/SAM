# SAM — Animated Waveform Widget
# Renders a smooth audio-reactive waveform using sinusoidal bar animations.
# Driven by QPainter at 30fps for efficient rendering.

import math
import random

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QLinearGradient
from PyQt6.QtWidgets import QWidget

from core.config import config


class WaveformWidget(QWidget):
    """
    Animated waveform visualizer with vertical bars.
    
    States:
        - active=True:  Bars pulse with sinusoidal animation (listening/speaking)
        - active=False: Bars collapse to minimum height (idle)
    """

    # Animation constants
    PHASE_SPEED = 0.08          # How fast the wave moves
    AMPLITUDE_LERP = 0.08       # Smoothing factor for amplitude transitions
    IDLE_AMPLITUDE = 0.0        # Target amplitude when inactive
    ACTIVE_AMPLITUDE = 1.0      # Target amplitude when active

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Load config
        self._bar_count: int = config.get("waveform", "bar_count", default=35)
        self._fps: int = config.get("waveform", "fps", default=30)
        self._min_h: int = config.get("waveform", "min_height", default=3)
        self._max_h: int = config.get("waveform", "max_height", default=32)
        self._bar_w: int = config.get("waveform", "bar_width", default=3)
        self._bar_gap: int = config.get("waveform", "bar_gap", default=2)
        self._color_hex: str = config.get("waveform", "color", default="#00D4AA")

        # Animation state
        self._active: bool = False
        self._amplitude: float = 0.0       # Current amplitude (lerped)
        self._phase: float = 0.0           # Wave phase offset
        self._time: float = 0.0            # Monotonic time counter

        # Per-bar random seeds for organic variation
        self._seeds: list[float] = [random.uniform(0.5, 1.5) for _ in range(self._bar_count)]
        self._phase_offsets: list[float] = [random.uniform(0, math.tau) for _ in range(self._bar_count)]

        # Fixed size based on bar count
        total_width = self._bar_count * (self._bar_w + self._bar_gap) - self._bar_gap
        self.setFixedSize(total_width, self._max_h + 4)

        # Transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000 // self._fps)

    def set_active(self, active: bool) -> None:
        """Enable or disable waveform animation."""
        self._active = active

    def set_color(self, color_hex: str) -> None:
        """Change the waveform bar color dynamically."""
        self._color_hex = color_hex

    def _tick(self) -> None:
        """Animation frame — update phase and amplitude, trigger repaint."""
        self._time += 1.0 / self._fps

        # Smooth amplitude transition
        target = self.ACTIVE_AMPLITUDE if self._active else self.IDLE_AMPLITUDE
        self._amplitude += (target - self._amplitude) * self.AMPLITUDE_LERP

        # Advance wave phase
        self._phase += self.PHASE_SPEED

        self.update()

    def paintEvent(self, event) -> None:
        """Render waveform bars using QPainter."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        base_color = QColor(self._color_hex)
        widget_h = self.height()

        for i in range(self._bar_count):
            # Compute bar height from layered sine waves for organic feel
            sin_val = (
                math.sin(self._phase + self._phase_offsets[i]) * 0.5
                + math.sin(self._phase * 1.7 + i * 0.4) * 0.3
                + math.sin(self._phase * 0.6 + i * 0.8) * 0.2
            )
            # Normalize to [0, 1] range
            normalized = (sin_val + 1.0) / 2.0
            # Apply per-bar seed variation
            normalized *= self._seeds[i]
            normalized = min(normalized, 1.0)

            # Scale by current amplitude
            bar_h = self._min_h + (self._max_h - self._min_h) * normalized * self._amplitude
            bar_h = max(bar_h, self._min_h)

            # Position — bars are bottom-anchored, centered vertically
            x = i * (self._bar_w + self._bar_gap)
            y = (widget_h - bar_h) / 2

            # Gradient: full color at center, faded at tips
            gradient = QLinearGradient(x, y, x, y + bar_h)
            alpha_edge = int(80 * self._amplitude) + 40
            alpha_center = int(200 * self._amplitude) + 55

            color_edge = QColor(base_color)
            color_edge.setAlpha(alpha_edge)
            color_center = QColor(base_color)
            color_center.setAlpha(alpha_center)

            gradient.setColorAt(0.0, color_edge)
            gradient.setColorAt(0.5, color_center)
            gradient.setColorAt(1.0, color_edge)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(gradient)
            painter.drawRoundedRect(int(x), int(y), self._bar_w, int(bar_h), 1.5, 1.5)

        painter.end()
