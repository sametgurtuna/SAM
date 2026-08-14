# SAM — Overlay Facade
# Owns the orb, the caption, and the typed-input box, and presents exactly the
# API AppController already used for FloatingBar:
#
#     activate() / dismiss() / set_state() / set_level()
#     set_transcript() / clear_transcript()
#
# so swapping the overlay is a two-line change in core/app.py.
#
# Semantics shift vs the old bar: the orb is ALWAYS visible, so activate() no
# longer shows a window (it energises the ring and reveals the caption) and
# dismiss() no longer hides one (it fades the caption and returns the orb to
# breathing). _start_listening / _reset_to_idle in the controller are unchanged.

import logging

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QGuiApplication

from core.config import config
from ui.caption import CaptionWindow
from ui.orb import OrbWindow
from ui.text_input import TextInputWindow

logger = logging.getLogger(__name__)


class SamOverlay(QObject):
    """
    Signals:
        text_submitted(str): The user typed a question and pressed Enter.
    """

    text_submitted = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()

        self._orb = OrbWindow()
        self._caption = CaptionWindow()
        self._input = TextInputWindow()

        self._caption_gap: int = config.get("ui", "orb", "caption_gap", default=18)

        # Child windows follow the orb as it moves
        self._orb.position_changed.connect(self._reposition_children)
        self._orb.clicked.connect(self.toggle_text_input)

        self._input.submitted.connect(self._on_text_submitted)
        self._input.cancelled.connect(self._on_text_cancelled)

        # Reposition if screen layout changes (displays added/removed/resized)
        app = QGuiApplication.instance()
        if app is not None:
            app.screenAdded.connect(self._on_screens_changed)
            app.screenRemoved.connect(self._on_screens_changed)
            app.primaryScreenChanged.connect(self._on_screens_changed)

        self._orb.show()
        self._reposition_children()

    # ─── FloatingBar-compatible API ───────────────────────────────

    def activate(self) -> None:
        """A session started — energise the orb and reveal the caption."""
        self._caption.fade_in()

    def dismiss(self) -> None:
        """Session over — fade the caption; the orb itself stays on screen."""
        self._caption.fade_out()
        self._close_text_input()

    def set_state(self, state: str) -> None:
        self._orb.set_state(state)

    def set_level(self, level: float) -> None:
        self._orb.set_level(level)

    def set_transcript(self, text: str) -> None:
        self._caption.set_text(text)
        if text and not self._caption.isVisible():
            self._caption.fade_in()
        self._reposition_children()

    def clear_transcript(self) -> None:
        self._caption.clear_text()

    def follow_to(self, start: int, end: int) -> None:
        """Scroll caption to character range currently spoken by TTS."""
        self._caption.follow_to(start, end)

    # ─── Text input ───────────────────────────────────────────────

    def show_text_input(self) -> None:
        # Disable orb hit testing while typing to avoid focus contention
        self._orb.set_interactive(False)
        self._orb.set_foreground_request(True)
        self._position_input()
        self._input.open()

    def hide_text_input(self) -> None:
        self._close_text_input()

    def toggle_text_input(self) -> None:
        if self._input.isVisible():
            self._close_text_input()
        else:
            self.show_text_input()

    @property
    def text_input_visible(self) -> bool:
        return self._input.isVisible()

    def _close_text_input(self) -> None:
        if self._input.isVisible():
            self._input.close_input()
        self._orb.set_interactive(True)
        self._orb.set_foreground_request(False)

    def _on_text_submitted(self, text: str) -> None:
        self._orb.set_interactive(True)
        self._orb.set_foreground_request(False)
        self.text_submitted.emit(text)

    def _on_text_cancelled(self) -> None:
        self._orb.set_interactive(True)
        self._orb.set_foreground_request(False)

    # ─── Geometry ─────────────────────────────────────────────────

    def _reposition_children(self) -> None:
        self._position_caption()
        if self._input.isVisible():
            self._position_input()

    def _below_orb_x(self, width: int) -> int:
        orb_geo = self._orb.geometry()
        centre_x = orb_geo.x() + orb_geo.width() // 2
        x = centre_x - width // 2

        # Clamp to screen bounds
        screen = self._orb.screen()
        if screen is not None:
            avail = screen.availableGeometry()
            x = max(avail.x() + 8, min(x, avail.x() + avail.width() - width - 8))
        return x

    def _below_orb_y(self, height: int) -> int:
        orb_geo = self._orb.geometry()
        y = orb_geo.y() + orb_geo.height() + self._caption_gap

        # If orb is near bottom of the screen, place caption above it
        screen = self._orb.screen()
        if screen is not None:
            avail = screen.availableGeometry()
            if y + height > avail.y() + avail.height() - 8:
                y = orb_geo.y() - self._caption_gap - height
                y = max(avail.y() + 8, y)
        return y

    def _position_caption(self) -> None:
        w = self._caption.width()
        h = self._caption.height()
        self._caption.move(self._below_orb_x(w), self._below_orb_y(h))

    def _position_input(self) -> None:
        w = self._input.width()
        h = self._input.height()
        self._input.move(self._below_orb_x(w), self._below_orb_y(h))

    def _on_screens_changed(self, *_args) -> None:
        # Screen geometry updates asynchronously; delay reposition slightly
        QTimer.singleShot(300, self._orb.reposition)

    # ─── Settings ─────────────────────────────────────────────────

    def apply_settings(self) -> None:
        """Live-apply config changes without a restart."""
        self._caption_gap = config.get("ui", "orb", "caption_gap", default=18)
        self._orb.apply_settings()
        self._caption.apply_settings()
        self._input.apply_settings()
        self._reposition_children()

    def reset_position(self) -> None:
        self._orb.reset_position()

    def shutdown(self) -> None:
        self._input.close()
        self._caption.close()
        self._orb.close()
