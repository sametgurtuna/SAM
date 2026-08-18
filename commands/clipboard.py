# SAM — Clipboard Utility
# Safely reads, validates, and truncates text from the Windows clipboard.

import logging

logger = logging.getLogger(__name__)

# Maximum characters to extract to preserve LLM token context & performance
DEFAULT_MAX_CHARS = 4000


def get_clipboard_text(max_chars: int = DEFAULT_MAX_CHARS) -> str | None:
    """
    Safely retrieves unicode text from the system clipboard.
    
    Handles locked clipboard, non-text formats (images, files), and
    normalizes line endings. Truncates if text exceeds max_chars.
    
    Returns:
        Cleaned text string, or None if clipboard is empty or non-text.
    """
    text: str | None = None

    # Primary method: win32clipboard (fast, robust, thread-safe on Windows)
    try:
        import win32clipboard
        import win32con

        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                if isinstance(data, str) and data.strip():
                    text = data.strip()
        finally:
            win32clipboard.CloseClipboard()
    except ImportError:
        logger.debug("win32clipboard not available — attempting fallback")
    except Exception as e:
        logger.debug("Failed to read clipboard via win32clipboard: %s", e)

    # Fallback method: pyperclip / tkinter / PyQt if win32clipboard failed
    if text is None:
        try:
            import pyperclip
            data = pyperclip.paste()
            if isinstance(data, str) and data.strip():
                text = data.strip()
        except Exception:
            pass

    if not text:
        return None

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return None

    # Truncate if exceeds max_chars
    if len(text) > max_chars:
        truncated_count = len(text) - max_chars
        text = text[:max_chars] + f"\n... [metin kısaltıldı / truncated {truncated_count} chars]"
        logger.debug("Clipboard text truncated to %d chars", max_chars)

    return text


def has_clipboard_text() -> bool:
    """Check if there is non-empty text content in clipboard."""
    text = get_clipboard_text(max_chars=50)
    return text is not None and len(text) > 0
