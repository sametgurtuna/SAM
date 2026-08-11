# SAM — Caption Window
# The transcript / streaming LLM response that appears beneath the orb.
#
# Always click-through: it is pure output, never an input target.
# Its top edge is fixed and it grows downward, so streaming tokens never make
# the text jitter around a vertical centre.

import logging

from PyQt6.QtCore import QPropertyAnimation, QTimer, Qt
from PyQt6.QtGui import QBrush, QColor, QFontMetrics, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget

from core.config import config
from ui import styles, win32

logger = logging.getLogger(__name__)

_PADDING_H = 18
_PADDING_V = 12


class CaptionWindow(QWidget):
    """Frameless, click-through text panel positioned under the orb."""

    def __init__(self) -> None:
        super().__init__()

        self._read_config()

        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        # Caption sadece bir oturum aktifken gorunur, o yuzden "auto" ve
        # "topmost" icin ayni davranir: gosterildigi surece en ustte.
        if config.get("ui", "orb", "layer", default="auto") != "normal":
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._build_ui()

        # Cached backdrop — invalidated on resize (unlike the old bar, this
        # widget really does change size).
        self._bg_path: QPainterPath | None = None
        self._bg_key: tuple | None = None
        self._bg_brush: QBrush | None = None
        self._border_pen: QPen | None = None

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)
        self._fade_anim: QPropertyAnimation | None = None

        # LLM token akisinda her token icin bir QLabel relayout + pencere
        # resize olmasin diye guncellemeler tek-atimlik timer'da birlestirilir.
        self._pending_text: str | None = None
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.timeout.connect(self._flush_text)
        self._flush_interval: int = config.get(
            "ui", "animation", "text_stream_interval_ms", default=45
        )

        self._current_text: str = ""

    def _read_config(self) -> None:
        self._width: int = config.get("ui", "orb", "caption_width", default=560)
        self._max_lines: int = config.get("ui", "orb", "caption_max_lines", default=6)
        self._fade_ms: int = config.get("ui", "animation", "fade_duration_ms", default=180)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(_PADDING_H, _PADDING_V, _PADDING_H, _PADDING_V)
        layout.setSpacing(0)

        self._label = QLabel("")
        self._label.setObjectName("captionLabel")
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._label.setStyleSheet(self._label_stylesheet())
        layout.addWidget(self._label)

        self.setFixedWidth(self._width)

    def _label_stylesheet(self) -> str:
        return f"""
            QLabel#captionLabel {{
                color: {styles.Colors.text_primary()};
                font-family: {styles.Fonts.transcript_family()};
                font-size: {styles.Fonts.size_transcript()}px;
                font-weight: 400;
                background: transparent;
            }}
        """

    # ─── Public API ───────────────────────────────────────────────

    def set_text(self, text: str) -> None:
        """Queue a text update. Coalesced to avoid one relayout per token."""
        if text == self._current_text and self._pending_text is None:
            return
        self._pending_text = text
        if not self._flush_timer.isActive():
            self._flush_timer.start(self._flush_interval)

    def clear_text(self) -> None:
        self._flush_timer.stop()
        self._pending_text = None
        self._current_text = ""
        self._label.setText("")

    def _flush_text(self) -> None:
        if self._pending_text is None:
            return
        text = self._pending_text
        self._pending_text = None
        if text == self._current_text:
            return
        self._current_text = text
        self._label.setText(self._elide(text))
        self._resize_to_content()

    def _elide(self, text: str) -> str:
        """
        Clamp to max_lines. Long streaming replies get their HEAD trimmed so the
        newest words stay visible.
        """
        if not text:
            return text
        metrics = QFontMetrics(self._label.font())
        available = self._width - 2 * _PADDING_H
        max_height = metrics.lineSpacing() * self._max_lines

        bounding = metrics.boundingRect(
            0, 0, available, 0,
            int(Qt.TextFlag.TextWordWrap), text,
        )
        if bounding.height() <= max_height:
            return text

        # Bastan kirp: kuyruk (en yeni kelimeler) gorunur kalsin.
        words = text.split()
        low, high = 0, len(words)
        while low < high:
            mid = (low + high) // 2
            candidate = "… " + " ".join(words[mid:])
            h = metrics.boundingRect(
                0, 0, available, 0, int(Qt.TextFlag.TextWordWrap), candidate
            ).height()
            if h <= max_height:
                high = mid
            else:
                low = mid + 1
        return "… " + " ".join(words[low:]) if low else text

    def _resize_to_content(self) -> None:
        height = self._label.heightForWidth(self._width - 2 * _PADDING_H)
        if height <= 0:
            height = self._label.sizeHint().height()
        self.setFixedHeight(max(1, height) + 2 * _PADDING_V)

    def fade_in(self) -> None:
        if not self.isVisible():
            self.show()
            win32.set_click_through(int(self.winId()), True)
        self._animate_opacity(1.0)

    def fade_out(self) -> None:
        if not self.isVisible():
            return
        self._animate_opacity(0.0, hide_when_done=True)

    def _animate_opacity(self, target: float, hide_when_done: bool = False) -> None:
        if self._fade_anim is not None:
            self._fade_anim.stop()
        anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        anim.setDuration(self._fade_ms)
        anim.setStartValue(self._opacity_effect.opacity())
        anim.setEndValue(target)
        if hide_when_done:
            # Gizlenince hicbir sey boyanmaz — bos caption CPU harcamasin.
            anim.finished.connect(self._on_fade_out_finished)
        self._fade_anim = anim
        anim.start()

    def _on_fade_out_finished(self) -> None:
        if self._opacity_effect.opacity() <= 0.01:
            self.hide()
            self.clear_text()

    def apply_settings(self) -> None:
        self._read_config()
        self.setFixedWidth(self._width)
        self._label.setStyleSheet(self._label_stylesheet())
        self._flush_interval = config.get(
            "ui", "animation", "text_stream_interval_ms", default=45
        )
        self._bg_path = None
        self._bg_key = None
        self._resize_to_content()

    # ─── Painting ─────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        key = (self.width(), self.height())
        if self._bg_path is None or self._bg_key != key:
            path = QPainterPath()
            path.addRoundedRect(0.5, 0.5, self.width() - 1.0, self.height() - 1.0, 14.0, 14.0)
            self._bg_path = path
            self._bg_key = key
        if self._bg_brush is None:
            self._bg_brush = QBrush(QColor(10, 12, 18, 165))
        if self._border_pen is None:
            border = QColor(styles.Colors.accent())
            border.setAlpha(45)
            self._border_pen = QPen(border, 1.0)

        painter.fillPath(self._bg_path, self._bg_brush)
        painter.setPen(self._border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self._bg_path)
