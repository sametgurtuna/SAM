# SAM — HUD Toast Notification
# A sleek, ephemeral Cyberpunk badge appearing next to the orb for zero-LLM actions.
# Auto-fades after 1.6 seconds. Does not steal focus or interfere with user input.

import logging

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFontMetrics, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QWidget,
)

from core.config import config
from ui import styles

logger = logging.getLogger(__name__)


class ToastWindow(QWidget):
    """
    HUD Toast badge for quick feedback on system actions (volume, media, language, etc.).
    """

    def __init__(self) -> None:
        super().__init__()

        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._build_ui()

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_anim: QPropertyAnimation | None = None

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)

        self._bg_path: QPainterPath | None = None
        self._bg_key: tuple | None = None

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(8)

        self._icon_label = QLabel()
        self._icon_label.setObjectName("toastIcon")
        self._icon_label.setStyleSheet("font-size: 14px; background: transparent;")
        layout.addWidget(self._icon_label)

        self._text_label = QLabel()
        self._text_label.setObjectName("toastText")
        self._text_label.setStyleSheet(self._text_stylesheet())
        layout.addWidget(self._text_label)

        self.setFixedHeight(38)

    def _text_stylesheet(self) -> str:
        accent_bright = styles.Colors.accent_thinking()
        return f"""
            QLabel#toastText {{
                color: {styles.Colors.text_primary()};
                font-family: {styles.Fonts.transcript_family()};
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }}
        """

    # ─── Public API ───────────────────────────────────────────────

    def show_toast(self, icon: str, message: str, duration_ms: int = 1600) -> None:
        """
        Display toast notification with icon and message.
        If already visible, updates content smoothly and resets timer.
        """
        self._icon_label.setText(icon)
        self._text_label.setText(message)

        # Calculate snug width
        fm = QFontMetrics(self._text_label.font())
        text_w = fm.horizontalAdvance(message)
        total_w = text_w + 58  # margins + icon + spacing
        total_w = max(120, min(total_w, 400))
        self.setFixedWidth(total_w)
        self._bg_path = None
        self._bg_key = None

        self._hide_timer.stop()

        if self._fade_anim and self._fade_anim.state() == QPropertyAnimation.State.Running:
            self._fade_anim.stop()

        self.show()

        # Fade in
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(120)
        self._fade_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.start()

        self._hide_timer.start(duration_ms)

    def _fade_out(self) -> None:
        if self._fade_anim and self._fade_anim.state() == QPropertyAnimation.State.Running:
            self._fade_anim.stop()

        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(220)
        self._fade_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_anim.finished.connect(self._on_fade_out_finished)
        self._fade_anim.start()

    def _on_fade_out_finished(self) -> None:
        if self._opacity_effect.opacity() <= 0.01:
            self.hide()

    def dismiss(self) -> None:
        self._hide_timer.stop()
        if self.isVisible():
            self._fade_out()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        key = (self.width(), self.height())
        if self._bg_path is None or self._bg_key != key:
            path = QPainterPath()
            path.addRoundedRect(1.0, 1.0, self.width() - 2.0, self.height() - 2.0, 14.0, 14.0)
            self._bg_path = path
            self._bg_key = key

        bg_color = QColor(12, 16, 24, 240)
        border_color = QColor(styles.Colors.accent())
        border_color.setAlpha(120)

        painter.fillPath(self._bg_path, QBrush(bg_color))
        painter.setPen(QPen(border_color, 1.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self._bg_path)
