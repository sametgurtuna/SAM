# SAM — Animated Waveform Widget
# Renders a smooth audio-reactive waveform using sinusoidal bar animations.
# Driven by QPainter, and only while the widget is actually visible.

import math
import random

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QGradient
from PyQt6.QtWidgets import QWidget

from core.config import config


class WaveformWidget(QWidget):
    """
    Animated waveform visualizer with vertical bars.

    States:
        - active=True:  Bars pulse with sinusoidal animation (listening/speaking)
        - active=False: Bars collapse to minimum height (idle)

    The animation timer only runs while the widget is visible, and stops
    entirely once the bars have settled at rest — an idle SAM does no painting.
    """

    # Animation constants
    PHASE_SPEED = 0.08          # How fast the wave moves
    AMPLITUDE_LERP = 0.18       # Smoothing factor for amplitude transitions
    LEVEL_LERP = 0.35           # Smoothing for live mic level
    IDLE_AMPLITUDE = 0.0        # Target amplitude when inactive
    ACTIVE_AMPLITUDE = 1.0      # Target amplitude when active
    REST_EPSILON = 0.004        # Below this, treat the animation as settled

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Load config
        self._bar_count: int = config.get("waveform", "bar_count", default=35)
        self._fps: int = config.get("waveform", "fps", default=60)
        self._min_h: int = config.get("waveform", "min_height", default=3)
        self._max_h: int = config.get("waveform", "max_height", default=32)
        self._bar_w: int = config.get("waveform", "bar_width", default=3)
        self._bar_gap: int = config.get("waveform", "bar_gap", default=2)
        self._color_hex: str = config.get("waveform", "color", default="#00D4AA")

        # Animation state
        self._active: bool = False
        self._amplitude: float = 0.0       # Current amplitude (lerped)
        self._level: float = 0.0           # Live mic level (lerped, 0.0–1.0)
        self._level_target: float = 0.0
        self._phase: float = 0.0           # Wave phase offset

        # Per-bar random seeds for organic variation
        self._seeds: list[float] = [random.uniform(0.5, 1.5) for _ in range(self._bar_count)]
        self._phase_offsets: list[float] = [random.uniform(0, math.tau) for _ in range(self._bar_count)]

        # Bar x positions never change — precalculate and cache
        self._xs: list[int] = [i * (self._bar_w + self._bar_gap) for i in range(self._bar_count)]

        # Fixed size based on bar count
        total_width = self._bar_count * (self._bar_w + self._bar_gap) - self._bar_gap
        self.setFixedSize(total_width, self._max_h + 4)

        # Transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Single gradient object reused across all bars via ObjectBoundingMode
        self._gradient = QLinearGradient(0.0, 0.0, 0.0, 1.0)
        self._gradient.setCoordinateMode(QGradient.CoordinateMode.ObjectBoundingMode)
        self._gradient_alpha_key: tuple[str, int] | None = None

        # Animation timer — only runs while visible (see showEvent/hideEvent)
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._interval_ms = max(8, 1000 // self._fps)

    # ─── Visibility-driven timer ──────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._start_timer()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._timer.stop()

    def _start_timer(self) -> None:
        if not self._timer.isActive() and self.isVisible():
            self._timer.start(self._interval_ms)

    # ─── Public API ───────────────────────────────────────────────

    def set_active(self, active: bool) -> None:
        """Enable or disable waveform animation."""
        if active == self._active:
            return
        self._active = active
        if not active:
            self._level_target = 0.0
        # Restart animation timer on state transition
        self._start_timer()

    def set_color(self, color_hex: str) -> None:
        """Change the waveform bar color dynamically."""
        if color_hex == self._color_hex:
            return
        self._color_hex = color_hex
        self._gradient_alpha_key = None  # Invalidate cached gradient
        self._start_timer()

    def set_level(self, level: float) -> None:
        """
        Feed the live microphone level (0.0–1.0) so the bars react to the
        user's actual voice instead of only running a canned sine loop.
        """
        self._level_target = max(0.0, min(1.0, level))
        self._start_timer()

    # ─── Animation ────────────────────────────────────────────────

    def _tick(self) -> None:
        """Animation frame — update phase and amplitude, trigger repaint."""
        target = self.ACTIVE_AMPLITUDE if self._active else self.IDLE_AMPLITUDE
        self._amplitude += (target - self._amplitude) * self.AMPLITUDE_LERP
        self._level += (self._level_target - self._level) * self.LEVEL_LERP

        self._phase += self.PHASE_SPEED

        # Stop timer once settled at rest — avoid idle 60fps repaints
        if (not self._active
                and abs(self._amplitude - target) < self.REST_EPSILON
                and self._level < self.REST_EPSILON):
            self._amplitude = target
            self._level = 0.0
            self._timer.stop()

        self.update()

    def _bar_gradient(self) -> QLinearGradient:
        """Shared linear gradient updated for current amplitude."""
        # Quantize alpha into 8-step buckets to avoid rebuilding gradient every frame
        bucket = int(self._amplitude * 255) // 8
        key = (self._color_hex, bucket)
        if key == self._gradient_alpha_key:
            return self._gradient

        base = QColor(self._color_hex)
        edge = QColor(base)
        edge.setAlpha(int(80 * self._amplitude) + 40)
        center = QColor(base)
        center.setAlpha(int(200 * self._amplitude) + 55)

        self._gradient.setColorAt(0.0, edge)
        self._gradient.setColorAt(0.5, center)
        self._gradient.setColorAt(1.0, edge)
        self._gradient_alpha_key = key
        return self._gradient

    def paintEvent(self, event) -> None:
        """Render waveform bars using QPainter."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._bar_gradient())

        widget_h = self.height()
        span = self._max_h - self._min_h
        phase = self._phase
        # Live microphone level creates baseline; sine wave adds organic texture
        voice = 0.35 + 0.65 * self._level

        for i in range(self._bar_count):
            # Compute bar height from layered sine waves for organic feel
            sin_val = (
                math.sin(phase + self._phase_offsets[i]) * 0.5
                + math.sin(phase * 1.7 + i * 0.4) * 0.3
                + math.sin(phase * 0.6 + i * 0.8) * 0.2
            )
            # Normalize to [0, 1] range, apply per-bar seed variation
            normalized = min((sin_val + 1.0) * 0.5 * self._seeds[i], 1.0)

            bar_h = self._min_h + span * normalized * self._amplitude * voice
            if bar_h < self._min_h:
                bar_h = self._min_h

            y = (widget_h - bar_h) * 0.5
            painter.drawRoundedRect(
                self._xs[i], int(y), self._bar_w, int(bar_h), 1.5, 1.5
            )

        painter.end()
