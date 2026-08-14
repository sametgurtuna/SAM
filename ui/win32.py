# SAM — Win32 window helpers
# Click-through overlays and foreground focus stealing, via ctypes.
#
# Everything here is a no-op on non-Windows platforms so the UI code can call
# it unconditionally.

import ctypes
import logging
import os

logger = logging.getLogger(__name__)

IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    import ctypes.wintypes

# ─── Win32 constants ──────────────────────────────────────────────
GWL_EXSTYLE = -20
GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

WM_NCHITTEST = 0x0084
HTTRANSPARENT = -1
HTCLIENT = 1

# ─── Z-order (SetWindowPos) ────────────────────────────────────────
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
# Special pseudo-handles: small negative integers that must be passed
# as unsigned bit patterns into c_void_p (see _pseudo_handle).
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
HWND_BOTTOM = 1

if IS_WINDOWS:
    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32

    # Define hwnd as c_void_p for 64-bit safety — default c_int signature
    # truncates to 32-bit causing silent failures.
    _user32.GetWindowLongW.argtypes = (ctypes.c_void_p, ctypes.c_int)
    _user32.GetWindowLongW.restype = ctypes.c_long
    _user32.SetWindowLongW.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_long)
    _user32.SetWindowLongW.restype = ctypes.c_long
    _user32.SetWindowPos.argtypes = (
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, ctypes.c_uint,
    )
    _user32.SetWindowPos.restype = ctypes.c_bool
else:
    _user32 = None
    _kernel32 = None


def _pseudo_handle(value: int) -> "ctypes.c_void_p":
    """Convert small negative pseudo-handles (e.g. HWND_TOPMOST/-BOTTOM)
    to the unsigned bit pattern expected by c_void_p."""
    return ctypes.c_void_p(value & 0xFFFFFFFFFFFFFFFF)


def set_zorder(hwnd: int, insert_after: int) -> None:
    """Adjust window z-order via SetWindowPos while preserving size and position."""
    if not IS_WINDOWS or not hwnd:
        return
    try:
        _user32.SetWindowPos(
            ctypes.c_void_p(hwnd), _pseudo_handle(insert_after),
            0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
        )
    except Exception as e:
        logger.debug("set_zorder failed: %s", e)


def bring_to_top(hwnd: int) -> None:
    """Temporarily bring window to topmost layer (HWND_TOPMOST)."""
    set_zorder(hwnd, HWND_TOPMOST)


def send_to_bottom(hwnd: int) -> None:
    """Send window to the bottom of the z-order hierarchy (HWND_BOTTOM)."""
    set_zorder(hwnd, HWND_BOTTOM)


def clear_topmost(hwnd: int) -> None:
    """Clear topmost state without positioning to a specific layer."""
    set_zorder(hwnd, HWND_NOTOPMOST)


def set_click_through(hwnd: int, enabled: bool) -> None:
    """
    Toggle WS_EX_TRANSPARENT so mouse input passes straight through the window
    to whatever is beneath it.

    Must be called AFTER the window has been shown — before that Qt has not
    created the native handle and the style is overwritten on realize.

    Note: a window with WS_EX_TRANSPARENT receives no mouse messages at all.
    Windows that need to be clickable use a WM_NCHITTEST hit test instead
    (see ui/orb.py).
    """
    if not IS_WINDOWS or not hwnd:
        return
    try:
        handle = ctypes.c_void_p(hwnd)
        ex_style = _user32.GetWindowLongW(handle, GWL_EXSTYLE)
        if enabled:
            new_style = ex_style | WS_EX_TRANSPARENT | WS_EX_LAYERED
        else:
            new_style = ex_style & ~WS_EX_TRANSPARENT
        if new_style != ex_style:
            _user32.SetWindowLongW(handle, GWL_EXSTYLE, new_style)
    except Exception as e:
        logger.debug("set_click_through failed: %s", e)


def force_foreground(hwnd: int) -> None:
    """
    Bring a window to the foreground and give it keyboard focus.

    SetForegroundWindow alone is refused by Windows' foreground lock when the
    calling process is not already in the foreground — which is exactly SAM's
    situation when a global hotkey fires. Attaching to the current foreground
    thread's input queue lifts the restriction for the duration of the call.
    """
    if not IS_WINDOWS or not hwnd:
        return
    try:
        handle = ctypes.c_void_p(hwnd)
        foreground = _user32.GetForegroundWindow()
        target_thread = _user32.GetWindowThreadProcessId(foreground, None)
        our_thread = _kernel32.GetCurrentThreadId()

        attached = False
        if target_thread and target_thread != our_thread:
            attached = bool(_user32.AttachThreadInput(target_thread, our_thread, True))
        try:
            _user32.BringWindowToTop(handle)
            _user32.SetForegroundWindow(handle)
            _user32.SetFocus(handle)
        finally:
            if attached:
                _user32.AttachThreadInput(target_thread, our_thread, False)
    except Exception as e:
        logger.debug("force_foreground failed: %s", e)


def foreground_is_fullscreen(exclude_hwnd: int = 0) -> bool:
    """
    True when the foreground window is a genuine fullscreen app (a game or a
    fullscreen video), so an always-on-top overlay should step aside.

    A merely *maximized* window must NOT count — it still has a title bar and
    the user expects the orb to stay visible. The standard heuristic is
    therefore: the window covers a whole monitor AND it is borderless
    (no WS_CAPTION / WS_THICKFRAME), which is what fullscreen apps look like.
    Shell windows are excluded so the desktop itself never counts.
    """
    if not IS_WINDOWS:
        return False
    try:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd or hwnd == exclude_hwnd:
            return False

        # Ignore desktop / shell windows.
        buf = ctypes.create_unicode_buffer(256)
        _user32.GetClassNameW(hwnd, buf, 256)
        if buf.value in ("Progman", "WorkerW", "Shell_TrayWnd", "Button"):
            return False

        style = _user32.GetWindowLongW(ctypes.c_void_p(hwnd), GWL_STYLE)
        if style & (WS_CAPTION | WS_THICKFRAME):
            return False  # Has caption/border => maximized, not fullscreen

        rect = ctypes.wintypes.RECT()
        if not _user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False

        from PyQt6.QtGui import QGuiApplication
        for screen in QGuiApplication.screens():
            g = screen.geometry()
            if (rect.left <= g.x() and rect.top <= g.y()
                    and rect.right >= g.x() + g.width()
                    and rect.bottom >= g.y() + g.height()):
                return True
        return False
    except Exception:
        return False


def decode_hittest_point(lparam: int) -> tuple[int, int]:
    """
    Extract signed screen coordinates from a WM_NCHITTEST lParam.

    The coordinates are SIGNED 16-bit values. On a multi-monitor setup with a
    display to the left of or above the primary one they are negative, and
    reading them as unsigned wraps them to ~65000 — every hit test then fails.
    """
    x = ctypes.c_short(lparam & 0xFFFF).value
    y = ctypes.c_short((lparam >> 16) & 0xFFFF).value
    return x, y


def message_from_qt(message: object) -> object | None:
    """Turn PyQt's nativeEvent `message` argument into a Win32 MSG struct."""
    if not IS_WINDOWS:
        return None
    try:
        return ctypes.wintypes.MSG.from_address(int(message))
    except Exception:
        return None
