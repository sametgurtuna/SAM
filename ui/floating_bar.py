# SAM — Floating Bar Overlay
# The main visual interface: a slim, always-on-top, frosted-glass bar
# anchored to the bottom-center of the screen.

from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QPoint, QSize, pyqtProperty
)
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPainterPath, QBrush, QPen,
    QLinearGradient, QRadialGradient
)
from PyQt6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout,
    QFrame, QGraphicsOpacityEffect, QApplication
)

from core.config import config
from ui.waveform import WaveformWidget
from ui import styles


class StatusDot(QWidget):
    """
    Small glowing circle that changes color based on SAM's state.
    Cyan = listening, Amber = thinking, Green = speaking.
    """

    DOT_RADIUS = 6
    GLOW_RADIUS = 14

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(self.GLOW_RADIUS * 2, self.GLOW_RADIUS * 2)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._color = QColor(styles.Colors.accent_listening())
        self._pulse_alpha: float = 0.0
        self._pulse_dir: float = 1.0

        # Pulse animation timer
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_tick)
        self._pulse_timer.start(33)  # ~30fps

    def set_color(self, hex_color: str) -> None:
        """Change dot color (called on state transitions)."""
        self._color = QColor(hex_color)
        self.update()

    def _pulse_tick(self) -> None:
        """Animate the glow pulse."""
        self._pulse_alpha += 0.03 * self._pulse_dir
        if self._pulse_alpha >= 1.0:
            self._pulse_alpha = 1.0
            self._pulse_dir = -1.0
        elif self._pulse_alpha <= 0.3:
            self._pulse_alpha = 0.3
            self._pulse_dir = 1.0
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() // 2
        center_y = self.height() // 2

        # Outer glow
        glow_color = QColor(self._color)
        glow_color.setAlphaF(0.15 * self._pulse_alpha)
        glow_gradient = QRadialGradient(center_x, center_y, self.GLOW_RADIUS)
        glow_gradient.setColorAt(0.0, glow_color)
        glow_gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow_gradient))
        painter.drawEllipse(
            center_x - self.GLOW_RADIUS, center_y - self.GLOW_RADIUS,
            self.GLOW_RADIUS * 2, self.GLOW_RADIUS * 2
        )

        # Inner dot
        dot_color = QColor(self._color)
        dot_color.setAlphaF(0.7 + 0.3 * self._pulse_alpha)
        painter.setBrush(QBrush(dot_color))
        painter.drawEllipse(
            center_x - self.DOT_RADIUS, center_y - self.DOT_RADIUS,
            self.DOT_RADIUS * 2, self.DOT_RADIUS * 2
        )

        painter.end()


class FloatingBar(QWidget):
    """
    The main SAM overlay — a slim floating bar at the bottom of the screen.
    
    Features:
        - Frameless, always-on-top, translucent window
        - Status dot (color-coded by state)
        - Animated waveform (listening/speaking)
        - Live transcript / response text
        - Slide-up/down + fade animations
        - Escape to dismiss
    """

    def __init__(self) -> None:
        super().__init__()

        # Window configuration — frameless, always on top, transparent
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # Prevents taskbar entry
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Dimensions from config
        self._bar_width: int = config.get("ui", "bar", "width", default=800)
        self._bar_height: int = config.get("ui", "bar", "height", default=80)
        self._border_radius: int = config.get("ui", "bar", "border_radius", default=16)
        self._margin_bottom: int = config.get("ui", "bar", "margin_bottom", default=40)

        self.setFixedSize(self._bar_width, self._bar_height)

        # Animation settings
        self._slide_ms: int = config.get("ui", "animation", "slide_duration_ms", default=350)
        self._fade_ms: int = config.get("ui", "animation", "fade_duration_ms", default=250)

        # Opacity effect for fade animations
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)

        # Build internal layout
        self._build_ui()

        # Position off-screen initially
        self._position_on_screen(hidden=True)

    def _build_ui(self) -> None:
        """Construct the bar's internal widget layout."""
        # Main container frame with styled background
        self._container = QFrame(self)
        self._container.setObjectName("barContainer")
        self._container.setFixedSize(self._bar_width, self._bar_height)
        self._container.setStyleSheet(styles.floating_bar_stylesheet())

        # Horizontal layout: [dot] [waveform + text] [close area]
        main_layout = QHBoxLayout(self._container)
        main_layout.setContentsMargins(20, 0, 20, 0)
        main_layout.setSpacing(12)

        # Left: Status dot
        self._status_dot = StatusDot()
        main_layout.addWidget(self._status_dot, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Center: Vertical stack — status label on top, transcript below
        center_layout = QVBoxLayout()
        center_layout.setContentsMargins(0, 12, 0, 12)
        center_layout.setSpacing(2)

        # Status label (LISTENING / THINKING / SPEAKING)
        self._status_label = QLabel("LISTENING")
        self._status_label.setObjectName("statusLabel")
        self._status_label.setStyleSheet(styles.status_label_stylesheet())
        center_layout.addWidget(self._status_label)

        # Transcript / response text
        self._transcript_label = QLabel("")
        self._transcript_label.setObjectName("transcriptLabel")
        self._transcript_label.setStyleSheet(styles.transcript_label_stylesheet())
        self._transcript_label.setWordWrap(False)
        center_layout.addWidget(self._transcript_label)

        main_layout.addLayout(center_layout, stretch=1)

        # Right: Waveform animation
        self._waveform = WaveformWidget()
        main_layout.addWidget(self._waveform, alignment=Qt.AlignmentFlag.AlignVCenter)

    def _position_on_screen(self, hidden: bool = False) -> None:
        """Place the bar at bottom-center of the primary screen."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return

        screen_geo = screen.availableGeometry()
        x = screen_geo.x() + (screen_geo.width() - self._bar_width) // 2

        if hidden:
            # Position below screen (hidden)
            y = screen_geo.y() + screen_geo.height() + 10
        else:
            # Position at bottom with margin
            y = screen_geo.y() + screen_geo.height() - self._bar_height - self._margin_bottom

        self.move(x, y)

    # ─── Public API ───────────────────────────────────────────────

    def activate(self) -> None:
        """Show the bar with a slide-up animation."""
        self._position_on_screen(hidden=True)
        self._opacity_effect.setOpacity(1.0)
        self.show()
        self.raise_()

        # Compute target Y position
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        screen_geo = screen.availableGeometry()
        target_y = screen_geo.y() + screen_geo.height() - self._bar_height - self._margin_bottom

        # Slide-up animation
        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._slide_anim.setDuration(self._slide_ms)
        self._slide_anim.setStartValue(self.pos())
        self._slide_anim.setEndValue(QPoint(self.x(), target_y))
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide_anim.start()

        # Start waveform
        self._waveform.set_active(True)

    def dismiss(self) -> None:
        """Hide the bar with a slide-down + fade-out animation."""
        self._waveform.set_active(False)

        # Compute off-screen Y
        screen = QApplication.primaryScreen()
        if screen is None:
            self.hide()
            return
        screen_geo = screen.availableGeometry()
        offscreen_y = screen_geo.y() + screen_geo.height() + 10

        # Slide down
        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._slide_anim.setDuration(self._slide_ms)
        self._slide_anim.setStartValue(self.pos())
        self._slide_anim.setEndValue(QPoint(self.x(), offscreen_y))
        self._slide_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._slide_anim.finished.connect(self.hide)
        self._slide_anim.start()

        # Fade out simultaneously
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(self._slide_ms)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self._fade_anim.start()

    def set_state(self, state: str) -> None:
        """
        Update visual state of the bar.
        
        Args:
            state: One of 'listening', 'thinking', 'speaking', 'idle'
        """
        state = state.lower()

        color_map = {
            "listening": styles.Colors.accent_listening(),
            "thinking": styles.Colors.accent_thinking(),
            "speaking": styles.Colors.accent_speaking(),
            "idle": styles.Colors.accent(),
        }
        label_map = {
            "listening": "LISTENING",
            "thinking": "THINKING",
            "speaking": "SPEAKING",
            "idle": "",
        }

        self._status_dot.set_color(color_map.get(state, styles.Colors.accent()))
        self._status_label.setText(label_map.get(state, ""))
        self._waveform.set_color(color_map.get(state, styles.Colors.accent()))

        # Waveform is active during listening and speaking
        self._waveform.set_active(state in ("listening", "speaking"))

    def set_transcript(self, text: str) -> None:
        """Update the transcript/response text displayed in the bar."""
        self._transcript_label.setText(text)

    def clear_transcript(self) -> None:
        """Clear the transcript text."""
        self._transcript_label.setText("")

    # ─── Keyboard Handling ────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        """Escape key dismisses the bar."""
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss()
        else:
            super().keyPressEvent(event)

    # ─── Custom Painting ──────────────────────────────────────────

    def paintEvent(self, event) -> None:
        """
        Paint the frosted glass background with rounded corners.
        This runs BEHIND the container frame for the translucent effect.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Rounded rect path
        path = QPainterPath()
        path.addRoundedRect(
            0.0, 0.0,
            float(self.width()), float(self.height()),
            self._border_radius, self._border_radius
        )

        # Dark frosted glass fill
        bg_color = QColor(10, 10, 15, int(255 * 0.88))
        painter.fillPath(path, QBrush(bg_color))

        # Subtle top highlight for depth
        highlight = QLinearGradient(0, 0, 0, 8)
        highlight.setColorAt(0.0, QColor(255, 255, 255, 12))
        highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillPath(path, QBrush(highlight))

        # Border
        border_color = QColor(styles.Colors.accent())
        border_color.setAlpha(25)
        painter.setPen(QPen(border_color, 1.0))
        painter.drawPath(path)

        painter.end()
