# SAM — Typed Input
# A focusable pill input under the orb, for asking SAM something without
# speaking. Opened by the text hotkey or by clicking the orb.
#
# Unlike the orb and caption this window MUST take keyboard focus, so it does
# not set WA_ShowWithoutActivating and it calls force_foreground() — otherwise
# Windows' foreground lock silently sends the user's keystrokes to whatever app
# was focused when the hotkey fired.

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush
from PyQt6.QtWidgets import QLineEdit, QVBoxLayout, QWidget

from core.config import config
from ui import styles, win32

logger = logging.getLogger(__name__)

_PADDING = 0


class TextInputWindow(QWidget):
    """
    Signals:
        submitted(str): User pressed Enter with non-empty text.
        cancelled(): User pressed Escape or clicked away.
    """

    submitted = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        self._width: int = config.get("ui", "orb", "caption_width", default=560)

        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        if config.get("ui", "orb", "layer", default="auto") != "normal":
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # WA_ShowWithoutActivating intentionally omitted — input field requires active keyboard focus.

        self._build_ui()

        self._bg_path: QPainterPath | None = None
        self._bg_key: tuple | None = None
        self._bg_brush: QBrush | None = None
        self._border_pen: QPen | None = None

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)

        self._edit = QLineEdit()
        self._edit.setObjectName("samInput")
        self._edit.setPlaceholderText("Ask SAM…")
        self._edit.setStyleSheet(self._edit_stylesheet())
        self._edit.returnPressed.connect(self._on_return)
        layout.addWidget(self._edit)

        self.setFixedWidth(self._width)
        self.setFixedHeight(self._edit.sizeHint().height() + 12 + 20)

    def _edit_stylesheet(self) -> str:
        accent = styles.Colors.accent()
        return f"""
            QLineEdit#samInput {{
                background-color: rgba(14, 17, 24, 235);
                border: 1px solid {accent};
                border-radius: 20px;
                padding: 10px 18px;
                color: {styles.Colors.text_primary()};
                font-family: {styles.Fonts.transcript_family()};
                font-size: {styles.Fonts.size_transcript()}px;
                selection-background-color: {accent};
            }}
            QLineEdit#samInput:focus {{
                border: 1px solid {accent};
            }}
        """

    # ─── Public API ───────────────────────────────────────────────

    def open(self) -> None:
        """Show, raise, steal focus, and put the caret in the field."""
        self._edit.clear()
        self.show()
        self.raise_()
        win32.force_foreground(int(self.winId()))
        self.activateWindow()
        self._edit.setFocus(Qt.FocusReason.OtherFocusReason)

    def close_input(self) -> None:
        self._edit.clear()
        self.hide()

    def apply_settings(self) -> None:
        self._width = config.get("ui", "orb", "caption_width", default=560)
        self.setFixedWidth(self._width)
        self._edit.setStyleSheet(self._edit_stylesheet())
        self._bg_path = None
        self._bg_key = None
        self._border_pen = None

    # ─── Events ───────────────────────────────────────────────────

    def _on_return(self) -> None:
        text = self._edit.text().strip()
        self._edit.clear()
        self.hide()
        if text:
            self.submitted.emit(text)
        else:
            self.cancelled.emit()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_input()
            self.cancelled.emit()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        # User clicked outside or switched apps — dismiss input box
        if self.isVisible() and not self.isActiveWindow():
            self.close_input()
            self.cancelled.emit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        key = (self.width(), self.height())
        if self._bg_path is None or self._bg_key != key:
            path = QPainterPath()
            path.addRoundedRect(0.5, 0.5, self.width() - 1.0, self.height() - 1.0, 24.0, 24.0)
            self._bg_path = path
            self._bg_key = key
        if self._bg_brush is None:
            self._bg_brush = QBrush(QColor(10, 12, 18, 120))
        if self._border_pen is None:
            border = QColor(styles.Colors.accent())
            border.setAlpha(35)
            self._border_pen = QPen(border, 1.0)

        painter.fillPath(self._bg_path, self._bg_brush)
        painter.setPen(self._border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self._bg_path)
