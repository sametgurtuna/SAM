# SAM — Typed Input
# A focusable pill input under the orb, for asking SAM something without
# speaking. Opened by the text hotkey or by clicking the orb.
# Includes live clipboard awareness badge for direct context injection.

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from commands.clipboard import get_clipboard_text
from core.config import config
from ui import styles, win32

logger = logging.getLogger(__name__)


class TextInputWindow(QWidget):
    """
    Signals:
        submitted(str, object): User pressed Enter with non-empty text, optionally with clipboard text.
        cancelled(): User pressed Escape or clicked away.
        geometry_changed(): Height or dimensions changed.
    """

    submitted = pyqtSignal(str, object)
    cancelled = pyqtSignal()
    geometry_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        self._width: int = config.get("ui", "orb", "caption_width", default=560)
        self._attached_clipboard: str | None = None
        self._corner_radius: float = 26.0

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

    def _build_ui(self) -> None:
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(20, 10, 20, 10)
        self._main_layout.setSpacing(6)

        self._edit = QLineEdit()
        self._edit.setObjectName("samInput")
        self._edit.setPlaceholderText("Ask SAM…")
        self._edit.setStyleSheet(self._edit_stylesheet())
        self._edit.returnPressed.connect(self._on_return)
        self._main_layout.addWidget(self._edit)

        # ─── Clipboard badge container ────────────────────────────
        self._badge_container = QWidget()
        self._badge_container.setObjectName("clipBadgeContainer")
        badge_layout = QHBoxLayout(self._badge_container)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.setSpacing(6)

        self._badge_label = QLabel()
        self._badge_label.setObjectName("clipBadge")
        self._badge_label.setText("📋 Clipboard attached")
        badge_layout.addWidget(self._badge_label)

        self._detach_btn = QPushButton("✕")
        self._detach_btn.setObjectName("clipDetachBtn")
        self._detach_btn.setToolTip("Detach clipboard")
        self._detach_btn.setFixedSize(18, 18)
        self._detach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._detach_btn.clicked.connect(self._detach_clipboard)
        badge_layout.addWidget(self._detach_btn)

        badge_layout.addStretch()
        self._badge_container.setStyleSheet(self._badge_stylesheet())
        self._badge_container.hide()
        self._main_layout.addWidget(self._badge_container)

        self.setFixedWidth(self._width)
        self._update_geometry()

    def _edit_stylesheet(self) -> str:
        accent = styles.Colors.accent()
        return f"""
            QLineEdit#samInput {{
                background-color: transparent;
                border: none;
                padding: 2px 2px;
                min-height: 28px;
                color: {styles.Colors.text_primary()};
                font-family: {styles.Fonts.transcript_family()};
                font-size: {styles.Fonts.size_transcript()}px;
                selection-background-color: {accent};
            }}
            QLineEdit#samInput:focus {{
                border: none;
            }}
        """

    def _badge_stylesheet(self) -> str:
        accent_bright = styles.Colors.accent_thinking()
        return f"""
            QWidget#clipBadgeContainer {{
                background: transparent;
                min-height: 24px;
            }}
            QLabel#clipBadge {{
                background-color: rgba(0, 212, 170, 0.12);
                border: 1px solid rgba(0, 212, 170, 0.45);
                border-radius: 6px;
                padding: 3px 8px;
                color: {accent_bright};
                font-size: 11px;
                font-family: {styles.Fonts.transcript_family()};
                font-weight: 500;
            }}
            QPushButton#clipDetachBtn {{
                background-color: rgba(255, 255, 255, 0.10);
                border: 1px solid rgba(255, 255, 255, 0.20);
                border-radius: 9px;
                color: #A0A0A0;
                font-size: 10px;
                font-weight: bold;
                padding: 0;
            }}
            QPushButton#clipDetachBtn:hover {{
                background-color: rgba(255, 70, 70, 0.35);
                border: 1px solid rgba(255, 70, 70, 0.60);
                color: #FF8888;
            }}
        """

    def _update_geometry(self) -> None:
        if self._badge_container.isVisible():
            total_h = 88
            radius = 18.0
        else:
            total_h = 52
            radius = 26.0

        self.setFixedHeight(total_h)
        self._corner_radius = radius
        self._bg_path = None
        self._bg_key = None
        self.geometry_changed.emit()

    def _detach_clipboard(self) -> None:
        """Detach the current clipboard text from this submission."""
        self._attached_clipboard = None
        self._badge_container.hide()
        self._update_geometry()
        logger.debug("Clipboard detached by user")

    # ─── Public API ───────────────────────────────────────────────

    def open(self) -> None:
        """Show, raise, check clipboard, steal focus, and put the caret in the field."""
        self._edit.clear()

        # Inspect clipboard for auto-attachment
        clip_text = get_clipboard_text()
        if clip_text:
            self._attached_clipboard = clip_text
            char_count = len(clip_text)
            
            # Format preview snippet
            first_line = clip_text.split("\n", 1)[0].strip()
            if len(first_line) > 30:
                preview = first_line[:30] + "…"
            else:
                preview = first_line
                
            self._badge_label.setText(f"📋 Attached: \"{preview}\" ({char_count} chars)")
            self._badge_container.show()
        else:
            self._attached_clipboard = None
            self._badge_container.hide()

        self._update_geometry()
        self.show()
        self.raise_()
        win32.force_foreground(int(self.winId()))
        self.activateWindow()
        self._edit.setFocus(Qt.FocusReason.OtherFocusReason)

    def close_input(self) -> None:
        self._edit.clear()
        self._attached_clipboard = None
        self._badge_container.hide()
        self._update_geometry()
        self.hide()

    def apply_settings(self) -> None:
        self._width = config.get("ui", "orb", "caption_width", default=560)
        self.setFixedWidth(self._width)
        self._edit.setStyleSheet(self._edit_stylesheet())
        self._badge_container.setStyleSheet(self._badge_stylesheet())
        self._bg_path = None
        self._bg_key = None
        self._update_geometry()

    # ─── Events ───────────────────────────────────────────────────

    def _on_return(self) -> None:
        text = self._edit.text().strip()
        clip = self._attached_clipboard
        self._edit.clear()
        self._attached_clipboard = None
        self._badge_container.hide()
        self._update_geometry()
        self.hide()

        if text:
            self.submitted.emit(text, clip)
        elif clip:
            # If user pressed enter with empty box but clipboard is attached, default to explain
            self.submitted.emit("Explain this", clip)
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

        key = (self.width(), self.height(), self._corner_radius)
        if self._bg_path is None or self._bg_key != key:
            path = QPainterPath()
            r = getattr(self, "_corner_radius", 26.0)
            path.addRoundedRect(1.0, 1.0, self.width() - 2.0, self.height() - 2.0, r, r)
            self._bg_path = path
            self._bg_key = key

        bg_color = QColor(12, 16, 24, 245)
        border_color = QColor(styles.Colors.accent())

        painter.fillPath(self._bg_path, QBrush(bg_color))
        painter.setPen(QPen(border_color, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self._bg_path)


