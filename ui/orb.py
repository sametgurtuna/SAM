# SAM — Orb Overlay
# An always-visible circular overlay that sits on the desktop like part of the
# wallpaper: "SAM" in the centre, a reactive ring that responds to state and
# live mic level.
#
# Performance is a first-class concern here — unlike the old floating bar this
# widget is on screen 24/7. The rules:
#   * one timer, started in showEvent and stopped in hideEvent
#   * idle runs at a low fps (breathing only); active states step up to full fps
#   * with idle_animation off the timer stops entirely once settled — 0 paints
#   * zero allocation in paintEvent: every path/gradient/pen/font is cached and
#     only rebuilt when its inputs actually change (alpha is bucketed)

import logging
import math

from PyQt6.QtCore import (
    QPoint, QPointF, QRectF, QTimer, Qt, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QConicalGradient, QFont, QPainter, QPainterPath,
    QPen, QRadialGradient, QStaticText,
)
from PyQt6.QtWidgets import QApplication, QWidget

from core.config import config
from ui import styles, win32

logger = logging.getLogger(__name__)

# Ring rendering modes per state
RING_IDLE = "idle"
RING_SWEEP = "sweep"      # thinking — rotating comet arc
RING_SPIKES = "spikes"    # listening / speaking — radial level bars

_STATE_RING = {
    "idle": RING_IDLE,
    "listening": RING_SPIKES,
    "thinking": RING_SWEEP,
    "speaking": RING_SPIKES,
}

_LEVEL_LERP = 0.35        # matches WaveformWidget's smoothing
_REST_EPSILON = 0.01


class OrbWindow(QWidget):
    """
    The circular SAM overlay.

    Signals:
        clicked(): The circle was clicked (not dragged).
        position_changed(): The orb moved — dependent windows should follow.
    """

    clicked = pyqtSignal()
    position_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        self._read_config()

        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool          # no taskbar entry
        )
        # "topmost" = permanently above all windows.
        # "auto" (default) and "normal" do not set Qt-level topmost hint;
        # "auto" manages z-order dynamically via Win32 SetWindowPos.
        if self._layer == "topmost":
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.setFixedSize(self._window_size, self._window_size)

        # ─── Animation state ──────────────────────────────────────
        self._state: str = "idle"
        self._ring_mode: str = RING_IDLE
        self._phase: float = 0.0          # breathing phase, radians
        self._sweep_deg: float = 0.0      # thinking comet rotation
        self._level: float = 0.0          # smoothed mic level
        self._level_target: float = 0.0
        self._energy: float = 0.0         # 0 idle .. 1 engaged
        self._energy_target: float = 0.0

        # ─── Cached paint resources ───────────────────────────────
        self._color = QColor(styles.Colors.accent())
        self._disc_path: QPainterPath | None = None
        self._disc_brush: QBrush | None = None
        self._glow_brush: QBrush | None = None
        self._glow_key: tuple | None = None
        self._sweep_pen: QPen | None = None
        self._sweep_key: str | None = None
        self._rim_pen: QPen | None = None
        self._rim_key: tuple | None = None
        self._spike_pen: QPen | None = None
        self._spike_key: tuple | None = None
        self._label_static: QStaticText | None = None
        self._label_font: QFont | None = None
        self._label_pos: QPointF | None = None

        # Spike trig tables — computed once, reused every frame
        self._cos: list[float] = []
        self._sin: list[float] = []
        self._spike_seeds: list[float] = []
        self._build_spike_tables()

        # ─── Interaction ──────────────────────────────────────────
        self._interactive: bool = True     # False => whole window is click-through
        self._drag_origin: QPoint | None = None
        self._press_pos: QPoint | None = None
        self._save_timer: QTimer | None = None

        # ─── Animation timer ──────────────────────────────────────
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._set_tempo(active=False)

        # ─── Fullscreen watchdog ──────────────────────────────────
        self._fullscreen_timer: QTimer | None = None
        self._hidden_for_fullscreen: bool = False

        # ─── Dynamic z-order ("auto" layer) ───────────────────────
        # When idle, orb rests at the bottom of the z-order (above wallpaper,
        # below active windows); temporarily brought to front during interaction.
        self._zorder_applied: bool | None = None   # None = not yet applied
        self._foreground_request: bool = False

        self._position_on_screen()

    # ─── Config ───────────────────────────────────────────────────

    def _read_config(self) -> None:
        self._size: int = config.get("ui", "orb", "size", default=120)
        self._glow_padding: int = config.get("ui", "orb", "glow_padding", default=28)
        self._ring_width: int = config.get("ui", "orb", "ring_width", default=3)
        self._opacity: float = config.get("ui", "orb", "opacity", default=0.95)
        self._label: str = config.get("ui", "orb", "label", default="SAM")
        self._idle_fps: int = max(1, config.get("ui", "orb", "idle_fps", default=12))
        self._active_fps: int = max(1, config.get("ui", "orb", "active_fps", default=60))
        self._idle_animation: bool = config.get("ui", "orb", "idle_animation", default=True)
        self._breathe_ms: int = config.get("ui", "orb", "breathe_period_ms", default=4000)
        self._spike_count: int = config.get("ui", "orb", "spike_count", default=36)
        self._layer: str = config.get("ui", "orb", "layer", default="auto")
        self._click_through: bool = config.get("ui", "orb", "click_through", default=True)
        self._hide_on_fullscreen: bool = config.get(
            "ui", "orb", "hide_on_fullscreen", default=True
        )

        self._window_size = self._size + 2 * self._glow_padding
        self._cx = self._window_size / 2.0
        self._cy = self._window_size / 2.0
        self._radius = self._size / 2.0
        # Hit test radius — a bit beyond the disc so the orb is comfortable to hit
        self._hit_radius_sq = (self._radius + 6.0) ** 2

        # Ring sits just outside the disc
        self._ring_radius = self._radius + 8.0
        self._ring_rect = QRectF(
            self._cx - self._ring_radius, self._cy - self._ring_radius,
            self._ring_radius * 2, self._ring_radius * 2,
        )
        self._glow_rect = QRectF(0, 0, self._window_size, self._window_size)

    def _build_spike_tables(self) -> None:
        """Precompute per-spike trig and organic seeds (done once)."""
        n = max(3, self._spike_count)
        self._cos = []
        self._sin = []
        self._spike_seeds = []
        for i in range(n):
            angle = (2.0 * math.pi * i) / n
            self._cos.append(math.cos(angle))
            self._sin.append(math.sin(angle))
            # Deterministic pseudo-random phase so the ring looks organic but
            # is stable between runs.
            self._spike_seeds.append((i * 2.399963) % (2.0 * math.pi))

    # ─── Positioning ──────────────────────────────────────────────

    def _target_screen(self):
        """The screen the orb should live on, honouring a saved screen name."""
        saved_name = config.get("ui", "orb", "position", "screen", default=None)
        if saved_name:
            for screen in QApplication.screens():
                if screen.name() == saved_name:
                    return screen
        return QApplication.primaryScreen()

    def _position_on_screen(self) -> None:
        """Place the orb from config: a saved point, or an anchored corner."""
        screen = self._target_screen()
        if screen is None:
            return
        geo = screen.availableGeometry()

        anchor = config.get("ui", "orb", "position", "anchor", default="bottom-right")
        margin = config.get("ui", "orb", "position", "margin", default=48)

        if anchor == "custom":
            x = config.get("ui", "orb", "position", "x", default=None)
            y = config.get("ui", "orb", "position", "y", default=None)
            if x is not None and y is not None and self._point_is_visible(int(x), int(y)):
                self.move(int(x), int(y))
                return
            # Saved position is off-screen (monitor disconnected, resolution changed) — fall back
            logger.info("Saved orb position is off-screen — falling back to anchor")

        if anchor == "bottom-center":
            x = geo.x() + (geo.width() - self._window_size) // 2
        else:  # bottom-right
            x = geo.x() + geo.width() - self._window_size - margin
        y = geo.y() + geo.height() - self._window_size - margin
        self.move(x, y)

    def _point_is_visible(self, x: int, y: int) -> bool:
        """True if the orb's centre would land inside some screen's work area."""
        centre = QPoint(x + self._window_size // 2, y + self._window_size // 2)
        return any(s.availableGeometry().contains(centre) for s in QApplication.screens())

    def reposition(self) -> None:
        """Re-run placement — call when the screen layout changes."""
        self._position_on_screen()
        self.position_changed.emit()

    # ─── Public API ───────────────────────────────────────────────

    def set_state(self, state: str) -> None:
        """Switch visual state and animation tempo."""
        state = (state or "idle").lower()
        if state == self._state:
            return
        self._state = state
        self._ring_mode = _STATE_RING.get(state, RING_IDLE)

        if state == "listening":
            color = styles.Colors.accent_listening()
        elif state == "thinking":
            color = styles.Colors.accent_thinking()
        elif state == "speaking":
            color = styles.Colors.accent_speaking()
        else:
            color = styles.Colors.accent()

        new_color = QColor(color)
        if new_color != self._color:
            self._color = new_color
            self._invalidate_color_cache()

        active = state != "idle"

        # If hidden for fullscreen and SAM is triggered, restore immediately
        if active and self._hidden_for_fullscreen:
            self._hidden_for_fullscreen = False
            self.show()

        self._energy_target = 1.0 if active else 0.0
        self._set_tempo(active)
        self._start_timer()
        self._sync_zorder()

    def set_level(self, level: float) -> None:
        """Feed the live mic RMS (0..1). Smoothed in _tick."""
        self._level_target = max(0.0, min(1.0, float(level)))
        self._start_timer()

    def set_interactive(self, interactive: bool) -> None:
        """
        Enable/disable hit testing. When False the whole window reports
        HTTRANSPARENT and every click falls through to the desktop.
        """
        self._interactive = interactive

    def set_foreground_request(self, wanted: bool) -> None:
        """
        A caller other than the state machine (the typed-input box) wants the
        orb lifted to the front — or is done wanting that. The final z-order
        is "in front if EITHER the session is active OR this is set".
        """
        if wanted == self._foreground_request:
            return
        self._foreground_request = wanted
        if wanted and self._hidden_for_fullscreen:
            self._hidden_for_fullscreen = False
            self.show()
        self._sync_zorder()

    def _sync_zorder(self) -> None:
        """
        Apply the "auto" layer policy: sit at the very bottom of the z-order
        (below normal windows, above only the wallpaper) while idle, and jump
        to the very top only while SAM is actually engaged. "topmost" and
        "normal" are static — nothing to do here for them.
        """
        if self._layer != "auto" or not win32.IS_WINDOWS:
            return
        want_front = (self._state != "idle") or self._foreground_request
        if want_front == self._zorder_applied:
            return
        self._zorder_applied = want_front
        if not self.isVisible():
            return  # native handle may not exist yet — showEvent applies it
        hwnd = int(self.winId())
        if want_front:
            win32.bring_to_top(hwnd)
        else:
            win32.send_to_bottom(hwnd)

    def apply_settings(self) -> None:
        """Re-read config and rebuild everything that depends on it."""
        was_visible = self.isVisible()
        self._read_config()
        self.setFixedSize(self._window_size, self._window_size)
        self._build_spike_tables()
        self._invalidate_color_cache()
        self._disc_path = None
        self._disc_brush = None
        self._label_static = None
        self._label_font = None
        self._label_pos = None
        self._set_tempo(self._state != "idle")
        self._position_on_screen()
        self._apply_click_through()
        self._sync_fullscreen_watchdog()
        # Apply z-order policy immediately on layer change
        self._zorder_applied = None
        self._sync_zorder()
        if was_visible:
            self.update()
            self._start_timer()
        self.position_changed.emit()

    # ─── Timer discipline ─────────────────────────────────────────

    def _set_tempo(self, active: bool) -> None:
        fps = self._active_fps if active else self._idle_fps
        self._timer.setInterval(max(1, 1000 // fps))

    def _start_timer(self) -> None:
        if self.isVisible() and not self._timer.isActive():
            self._timer.start()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._timer.start()
        # Click-through must be applied after the native handle exists.
        self._apply_click_through()
        self._sync_fullscreen_watchdog()
        # Native handle now exists — apply the initial z-order (bottom, unless
        # a session/text-input is already active at first show).
        self._zorder_applied = None
        self._sync_zorder()

    def hideEvent(self, event) -> None:
        self._timer.stop()
        if self._fullscreen_timer is not None:
            self._fullscreen_timer.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        # Breathing phase
        period_s = max(0.2, self._breathe_ms / 1000.0)
        self._phase += (2.0 * math.pi) * (self._timer.interval() / 1000.0) / period_s
        if self._phase > 2.0 * math.pi:
            self._phase -= 2.0 * math.pi

        # Comet rotation (thinking)
        if self._ring_mode == RING_SWEEP:
            self._sweep_deg = (self._sweep_deg + 260.0 * (self._timer.interval() / 1000.0)) % 360.0

        # Smooth level and energy toward their targets
        self._level += (self._level_target - self._level) * _LEVEL_LERP
        self._energy += (self._energy_target - self._energy) * 0.18

        self.update()

        # Rest detection — when idle and nothing is moving, stop painting
        # entirely. This is what makes an always-on overlay honest about CPU.
        if self._state == "idle" and not self._idle_animation:
            settled = (
                abs(self._energy - self._energy_target) < _REST_EPSILON
                and abs(self._level - self._level_target) < _REST_EPSILON
                and self._level_target < _REST_EPSILON
            )
            if settled:
                self._energy = self._energy_target
                self._level = self._level_target
                self.update()
                self._timer.stop()

    # ─── Fullscreen watchdog ──────────────────────────────────────

    def _sync_fullscreen_watchdog(self) -> None:
        """
        A topmost orb would sit on top of fullscreen games and video. Poll the
        foreground window cheaply (every 2s) and step aside when it covers a
        whole monitor. Only meaningful for layers that can BE topmost while
        idle ("topmost" always; "auto" only while engaged, which the check
        below already exempts) — "normal" never needs this.
        """
        need = (
            self._hide_on_fullscreen
            and self._layer in ("topmost", "auto")
            and win32.IS_WINDOWS
        )
        if not need:
            if self._fullscreen_timer is not None:
                self._fullscreen_timer.stop()
            return

        if self._fullscreen_timer is None:
            self._fullscreen_timer = QTimer(self)
            self._fullscreen_timer.setInterval(2000)
            self._fullscreen_timer.timeout.connect(self._check_fullscreen)
        self._fullscreen_timer.start()

    def _check_fullscreen(self) -> None:
        # Do not hide if SAM is actively engaged or requested by text input
        if self._state != "idle" or self._foreground_request:
            if self._hidden_for_fullscreen:
                self._hidden_for_fullscreen = False
                self.show()
            return

        fullscreen = win32.foreground_is_fullscreen(exclude_hwnd=int(self.winId()))
        if fullscreen and not self._hidden_for_fullscreen:
            logger.debug("Fullscreen app in foreground — hiding orb")
            self._hidden_for_fullscreen = True
            self.hide()
        elif not fullscreen and self._hidden_for_fullscreen:
            self._hidden_for_fullscreen = False
            self.show()

    # ─── Click-through / hit testing ──────────────────────────────

    def _apply_click_through(self) -> None:
        """
        The orb itself is NOT WS_EX_TRANSPARENT — that would make it impossible
        to click or drag. Instead nativeEvent answers WM_NCHITTEST per pixel,
        so only the circle is solid and the rest of the square window lets
        clicks reach the desktop.
        """
        self.set_interactive(True)

    def nativeEvent(self, event_type, message):
        # NOTE: Do NOT call super().nativeEvent(...). In PyQt6, QWidget's
        # default implementation can return an invalid pointer, leading to access violation.
        # Returning (False, 0) for unhandled events is the correct behaviour.
        if win32.IS_WINDOWS and event_type == b"windows_generic_MSG":
            msg = win32.message_from_qt(message)
            if msg is not None and msg.message == win32.WM_NCHITTEST:
                if not self._interactive:
                    return True, win32.HTTRANSPARENT
                if not self._click_through:
                    # click_through disabled: entire window is clickable
                    return True, win32.HTCLIENT

                x, y = win32.decode_hittest_point(msg.lParam)
                local = self.mapFromGlobal(QPoint(x, y))
                dx = local.x() - self._cx
                dy = local.y() - self._cy
                if dx * dx + dy * dy > self._hit_radius_sq:
                    return True, win32.HTTRANSPARENT
                return True, win32.HTCLIENT
        return False, 0

    # ─── Mouse: click to type, Ctrl+drag to move ──────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._drag_origin = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            self._press_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_origin is None:
            return
        self.move(event.globalPosition().toPoint() - self._drag_origin)
        self.position_changed.emit()

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_origin is not None:
            self._drag_origin = None
            self.unsetCursor()
            self._schedule_position_save()
            return

        if self._press_pos is not None:
            moved = (event.globalPosition().toPoint() - self._press_pos).manhattanLength()
            self._press_pos = None
            if moved < 6:
                self.clicked.emit()

    def _schedule_position_save(self) -> None:
        """Debounce the config write — save() rewrites the whole YAML file."""
        if self._save_timer is None:
            self._save_timer = QTimer(self)
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self._persist_position)
        self._save_timer.start(500)

    def _persist_position(self) -> None:
        pos = self.pos()
        screen = self.screen()
        config.set("ui", "orb", "position", "anchor", value="custom")
        config.set("ui", "orb", "position", "x", value=pos.x())
        config.set("ui", "orb", "position", "y", value=pos.y())
        config.set("ui", "orb", "position", "screen",
                   value=screen.name() if screen is not None else None)
        if config.save():
            logger.debug("Orb position saved: (%d, %d)", pos.x(), pos.y())

    def reset_position(self) -> None:
        """Forget the custom position and snap back to the default anchor."""
        config.set("ui", "orb", "position", "anchor", value="bottom-right")
        config.set("ui", "orb", "position", "x", value=None)
        config.set("ui", "orb", "position", "y", value=None)
        config.set("ui", "orb", "position", "screen", value=None)
        config.save()
        self._position_on_screen()
        self.position_changed.emit()

    # ─── Painting ─────────────────────────────────────────────────

    def _invalidate_color_cache(self) -> None:
        self._glow_brush = None
        self._glow_key = None
        self._sweep_pen = None
        self._sweep_key = None
        self._rim_pen = None
        self._rim_key = None
        self._spike_pen = None
        self._spike_key = None

    def _breath(self) -> float:
        """Breathing curve in 0..1."""
        if not self._idle_animation and self._state == "idle":
            return 0.55
        return 0.5 + 0.5 * math.sin(self._phase)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        breath = self._breath()
        # Idle breathes gently; active states are driven by mic level.
        intensity = 0.35 + 0.30 * breath + 0.35 * self._energy * self._level

        self._paint_glow(painter, intensity)
        self._paint_disc(painter)

        if self._ring_mode == RING_SWEEP:
            self._paint_sweep(painter)
        elif self._ring_mode == RING_SPIKES:
            self._paint_spikes(painter, breath)
        else:
            self._paint_rim(painter, breath)

        self._paint_label(painter, breath)

    def _paint_glow(self, painter: QPainter, intensity: float) -> None:
        # Alpha bucketing: only rebuild radial gradient when alpha changes noticeably
        alpha = int(max(0.0, min(1.0, intensity)) * 90)
        key = (self._color.rgb(), alpha // 8)
        if self._glow_brush is None or self._glow_key != key:
            gradient = QRadialGradient(self._cx, self._cy, self._window_size / 2.0)
            inner = QColor(self._color)
            inner.setAlpha(alpha)
            mid = QColor(self._color)
            mid.setAlpha(alpha // 3)
            outer = QColor(self._color)
            outer.setAlpha(0)
            gradient.setColorAt(0.0, inner)
            gradient.setColorAt(0.45, mid)
            gradient.setColorAt(1.0, outer)
            self._glow_brush = QBrush(gradient)
            self._glow_key = key
        painter.fillRect(self._glow_rect, self._glow_brush)

    def _paint_disc(self, painter: QPainter) -> None:
        if self._disc_path is None:
            self._disc_path = QPainterPath()
            self._disc_path.addEllipse(
                QPointF(self._cx, self._cy), self._radius, self._radius
            )
        if self._disc_brush is None:
            gradient = QRadialGradient(
                self._cx, self._cy - self._radius * 0.25, self._radius * 1.4
            )
            a = int(max(0.0, min(1.0, self._opacity)) * 255)
            gradient.setColorAt(0.0, QColor(18, 22, 30, a))
            gradient.setColorAt(0.7, QColor(10, 12, 18, a))
            gradient.setColorAt(1.0, QColor(6, 8, 12, a))
            self._disc_brush = QBrush(gradient)
        painter.fillPath(self._disc_path, self._disc_brush)

    def _paint_rim(self, painter: QPainter, breath: float) -> None:
        alpha = int((0.25 + 0.45 * breath) * 255)
        key = (self._color.rgb(), alpha // 8)
        if self._rim_pen is None or self._rim_key != key:
            color = QColor(self._color)
            color.setAlpha(alpha)
            self._rim_pen = QPen(color, float(self._ring_width))
            self._rim_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            self._rim_key = key
        painter.setPen(self._rim_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(self._ring_rect)

    def _paint_sweep(self, painter: QPainter) -> None:
        # Rebuilding conical gradients per frame is slow; rotate painter transform instead
        key = self._color.name()
        if self._sweep_pen is None or self._sweep_key != key:
            gradient = QConicalGradient(self._cx, self._cy, 0.0)
            head = QColor(self._color)
            head.setAlpha(255)
            mid = QColor(self._color)
            mid.setAlpha(90)
            tail = QColor(self._color)
            tail.setAlpha(0)
            gradient.setColorAt(0.0, head)
            gradient.setColorAt(0.18, mid)
            gradient.setColorAt(0.55, tail)
            gradient.setColorAt(1.0, tail)
            pen = QPen(QBrush(gradient), float(self._ring_width))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            self._sweep_pen = pen
            self._sweep_key = key

        painter.save()
        painter.translate(self._cx, self._cy)
        painter.rotate(-self._sweep_deg)
        painter.translate(-self._cx, -self._cy)
        painter.setPen(self._sweep_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(self._ring_rect, 0, 360 * 16)
        painter.restore()

    def _paint_spikes(self, painter: QPainter, breath: float) -> None:
        alpha = int((0.45 + 0.55 * (0.3 + 0.7 * self._level)) * 255)
        alpha = max(0, min(255, alpha))
        key = (self._color.rgb(), alpha // 8)
        if self._spike_pen is None or self._spike_key != key:
            color = QColor(self._color)
            color.setAlpha(alpha)
            pen = QPen(color, float(self._ring_width))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            self._spike_pen = pen
            self._spike_key = key
        painter.setPen(self._spike_pen)

        r_in = self._ring_radius
        base_len = 3.0
        span = (self._glow_padding - 8.0) * 0.9
        voice = 0.30 + 0.70 * self._level

        for i in range(len(self._cos)):
            seed = self._spike_seeds[i]
            # Layered sines give an organic, non-uniform ring (waveform idiom).
            organic = (
                0.55 * math.sin(self._phase * 2.1 + seed)
                + 0.30 * math.sin(self._phase * 3.7 + seed * 1.7)
                + 0.15 * math.sin(self._phase * 5.3 + seed * 2.3)
            )
            normalized = 0.5 + 0.5 * organic
            length = base_len + span * normalized * voice * self._energy
            cos_a = self._cos[i]
            sin_a = self._sin[i]
            painter.drawLine(
                QPointF(self._cx + cos_a * r_in, self._cy + sin_a * r_in),
                QPointF(self._cx + cos_a * (r_in + length),
                        self._cy + sin_a * (r_in + length)),
            )

    def _paint_label(self, painter: QPainter, breath: float) -> None:
        # QStaticText caches glyph layout to eliminate per-frame text shaping overhead
        if self._label_static is None:
            font = QFont(styles.Fonts.primary())
            font.setPixelSize(max(11, int(self._size * 0.22)))
            font.setWeight(QFont.Weight.DemiBold)
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
            self._label_font = font

            static = QStaticText(self._label)
            static.setTextFormat(Qt.TextFormat.PlainText)
            static.prepare(painter.transform(), font)
            self._label_static = static

            size = static.size()
            self._label_pos = QPointF(
                self._cx - size.width() / 2.0,
                self._cy - size.height() / 2.0,
            )

        color = QColor(styles.Colors.text_primary())
        color.setAlpha(int((0.65 + 0.35 * breath) * 255))
        painter.setFont(self._label_font)
        painter.setPen(color)
        painter.drawStaticText(self._label_pos, self._label_static)
