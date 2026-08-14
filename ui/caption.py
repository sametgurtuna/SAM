# SAM — Caption Window
# The transcript / streaming LLM response that appears beneath the orb.
#
# Its top edge is fixed and it grows downward, so streaming tokens never make
# the text jitter around a vertical centre. Long replies no longer get their
# head silently cut off — the text scrolls (mouse wheel or scrollbar), and
# auto-follows the newest tokens while streaming and the current TTS chunk
# while speaking, unless the user has manually scrolled away to read back.

import logging

from PyQt6.QtCore import QPropertyAnimation, QTimer, Qt
from PyQt6.QtGui import (
    QBrush, QColor, QFontMetrics, QPainter, QPainterPath, QPen,
    QTextCharFormat, QTextCursor,
)
from PyQt6.QtWidgets import (
    QGraphicsOpacityEffect, QTextEdit, QVBoxLayout, QWidget,
)

from core.config import config
from ui import styles

logger = logging.getLogger(__name__)

_PADDING_H = 18
_PADDING_V = 12
# Slop tolerance in pixels for scrollbar bottom detection
_BOTTOM_SLOP_PX = 4


class CaptionWindow(QWidget):
    """Frameless text panel positioned under the orb. Scrollable, auto-following."""

    def __init__(self) -> None:
        super().__init__()

        self._read_config()

        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        # Caption is shown only while a session is active; stays on top when visible.
        if config.get("ui", "orb", "layer", default="auto") != "normal":
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        # Not click-through (unlike the orb): the panel needs to accept mouse
        # wheel / scrollbar drag so long replies can be scrolled and re-read.
        # It only exists on screen while a session is active, so this doesn't
        # steal clicks from other windows at idle.

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

        # Coalesce streaming tokens into single-shot timer to avoid relayout per token
        self._pending_text: str | None = None
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.timeout.connect(self._flush_text)
        self._flush_interval: int = config.get(
            "ui", "animation", "text_stream_interval_ms", default=45
        )

        self._current_text: str = ""

        # ─── Scroll / auto-follow state ───────────────────────────
        # When True: automatically scroll to bottom on new tokens / TTS chunks.
        # Set to False when user scrolls up manually; re-enabled when back at bottom.
        self._auto_follow: bool = True
        self._programmatic_scroll: bool = False
        self._last_follow_range: tuple[int, int] | None = None

        bar = self._text_edit.verticalScrollBar()
        bar.valueChanged.connect(self._on_scroll_changed)

    def _read_config(self) -> None:
        self._width: int = config.get("ui", "orb", "caption_width", default=560)
        self._max_lines: int = config.get("ui", "orb", "caption_max_lines", default=6)
        self._fade_ms: int = config.get("ui", "animation", "fade_duration_ms", default=180)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(_PADDING_H, _PADDING_V, _PADDING_H, _PADDING_V)
        layout.setSpacing(0)

        self._text_edit = QTextEdit()
        self._text_edit.setObjectName("captionText")
        self._text_edit.setReadOnly(True)
        self._text_edit.setFrameStyle(0)  # QFrame.Shape.NoFrame
        self._text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._text_edit.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._text_edit.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._text_edit.setStyleSheet(self._text_stylesheet())
        self._text_edit.viewport().setAutoFillBackground(False)
        layout.addWidget(self._text_edit)

        self.setFixedWidth(self._width)

    def _text_stylesheet(self) -> str:
        accent = styles.Colors.accent()
        return f"""
            QTextEdit#captionText {{
                color: {styles.Colors.text_primary()};
                font-family: {styles.Fonts.transcript_family()};
                font-size: {styles.Fonts.size_transcript()}px;
                font-weight: 400;
                background: transparent;
                border: none;
                selection-background-color: {accent};
                selection-color: #0a0c12;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 50);
                border-radius: 3px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(255, 255, 255, 90);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
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
        self._text_edit.clear()
        self._last_follow_range = None
        self._auto_follow = True

    def follow_to(self, start: int, end: int) -> None:
        """
        Highlight the [start, end) character range currently spoken by TTS,
        and scroll into view if auto-follow is active.
        """
        self._last_follow_range = (start, end)
        self._apply_highlight(start, end)
        if self._auto_follow:
            self._scroll_cursor_to(end)

    # ─── Internal: text flush ───────────────────────────────────────

    def _flush_text(self) -> None:
        if self._pending_text is None:
            return
        text = self._pending_text
        self._pending_text = None
        if text == self._current_text:
            return

        is_new_response = not self._current_text and text
        self._current_text = text

        self._text_edit.setPlainText(text)
        if self._last_follow_range:
            self._apply_highlight(*self._last_follow_range)
        self._resize_to_content()

        if is_new_response:
            # New response starting — reset auto-follow to track from bottom
            self._auto_follow = True

        if self._auto_follow:
            self._scroll_to_bottom()

    def _apply_highlight(self, start: int, end: int) -> None:
        """Apply subtle accent background to the currently spoken character range."""
        doc = self._text_edit.document()
        count = doc.characterCount()
        if count <= 1:
            return
        start = max(0, min(start, count - 1))
        end = max(start, min(end, count - 1))

        cursor = QTextCursor(doc)
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        selection = QTextEdit.ExtraSelection()
        selection.cursor = cursor
        fmt = QTextCharFormat()
        accent = QColor(styles.Colors.accent())
        accent.setAlpha(45)
        fmt.setBackground(accent)
        selection.format = fmt
        self._text_edit.setExtraSelections([selection])

    def _scroll_cursor_to(self, position: int) -> None:
        """Move cursor to target position without modifying selection and ensure visibility."""
        doc = self._text_edit.document()
        count = doc.characterCount()
        if count <= 1:
            return
        position = max(0, min(position, count - 1))

        cursor = QTextCursor(doc)
        cursor.setPosition(position)

        self._programmatic_scroll = True
        self._text_edit.setTextCursor(cursor)
        self._text_edit.ensureCursorVisible()
        self._programmatic_scroll = False

    def _scroll_to_bottom(self) -> None:
        bar = self._text_edit.verticalScrollBar()
        self._programmatic_scroll = True
        bar.setValue(bar.maximum())
        self._programmatic_scroll = False

    def _on_scroll_changed(self, _value: int) -> None:
        if self._programmatic_scroll:
            return
        # User manually scrolled — keep following if at bottom, pause if reading back
        bar = self._text_edit.verticalScrollBar()
        self._auto_follow = bar.value() >= bar.maximum() - _BOTTOM_SLOP_PX

    # ─── Internal: sizing ───────────────────────────────────────────

    def _max_content_height(self) -> int:
        metrics = QFontMetrics(self._text_edit.font())
        return metrics.lineSpacing() * self._max_lines

    def _resize_to_content(self) -> None:
        doc = self._text_edit.document()
        doc.setTextWidth(self._width - 2 * _PADDING_H)
        content_height = int(doc.size().height())
        if content_height <= 0:
            content_height = QFontMetrics(self._text_edit.font()).lineSpacing()

        capped = min(content_height, self._max_content_height())
        capped = max(capped, QFontMetrics(self._text_edit.font()).lineSpacing())

        self._text_edit.setFixedHeight(capped)
        self.setFixedHeight(capped + 2 * _PADDING_V)

    # ─── Fade in/out ──────────────────────────────────────────────

    def fade_in(self) -> None:
        if not self.isVisible():
            self.show()
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
            # Hide completely when opacity drops to zero to eliminate idle paints
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
        self._text_edit.setStyleSheet(self._text_stylesheet())
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
