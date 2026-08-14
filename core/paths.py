# SAM — Path Resolution
# Single source of truth for "where do files live?", both when running from
# source and when running as a PyInstaller-frozen executable.
#
# Two roots matter:
#   resource_root()  — read-only bundled payload (assets, config.example.yaml)
#   user_data_dir()  — writable per-user state (config.yaml, logs, models)
#
# In development user_data_dir() IS the repo root, so behaviour is identical to
# what it has always been. Only the frozen build relocates to %APPDATA%\SAM.

import os
import sys

__all__ = [
    "is_frozen",
    "resource_root",
    "resource_path",
    "user_data_dir",
    "config_path",
    "example_config_path",
    "logs_dir",
    "models_dir",
    "cache_dir",
    "resolve_asset",
    "single_instance_lock",
]


def is_frozen() -> bool:
    """True when running from a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def _dev_root() -> str:
    """Repo root — this file lives in <root>/core/paths.py."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ensure(path: str) -> str:
    """makedirs + return the path. Never raises on an existing dir."""
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path


# ─── Read-only bundled resources ──────────────────────────────────

def resource_root() -> str:
    """
    Root of the read-only payload.

    Frozen onedir  → <app>\\_internal  (sys._MEIPASS)
    Frozen onefile → the temp extraction dir
    Source         → the repo root
    """
    return getattr(sys, "_MEIPASS", None) or _dev_root()


def resource_path(*parts: str) -> str:
    """Join a path inside the bundled payload."""
    return os.path.join(resource_root(), *parts)


# ─── Writable per-user data ───────────────────────────────────────

def user_data_dir() -> str:
    """
    Writable application data directory.

    Source build stays in the repo root so existing installs are untouched and
    no migration is needed; the frozen build uses %APPDATA%\\SAM because the
    payload directory is read-only (and may be under Program Files).
    """
    if not is_frozen():
        return _dev_root()
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return _ensure(os.path.join(base, "SAM"))


def config_path() -> str:
    """The config.yaml SAM reads and writes."""
    return os.path.join(user_data_dir(), "config.yaml")


def example_config_path() -> str:
    """The committed template, used to seed a fresh install."""
    return resource_path("config.example.yaml")


def logs_dir() -> str:
    return _ensure(os.path.join(user_data_dir(), "logs"))


def models_dir() -> str:
    """Downloaded model weights (Whisper). The installer pre-seeds this path."""
    return _ensure(os.path.join(user_data_dir(), "models"))


def cache_dir() -> str:
    """
    Volatile per-user cache — OAuth tokens, generated sounds.
    %LOCALAPPDATA%\\SAM, matching what commands/system.py already used.
    """
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return _ensure(os.path.join(base, "SAM"))


# ─── Config-supplied paths ────────────────────────────────────────

def single_instance_lock() -> bool:
    """
    Claim a system-wide named mutex. Returns True if this process is the only
    SAM, False if another instance already holds it.

    Required once SAM installs a Windows startup entry: otherwise launching it
    manually gives you two orbs, two wake-word microphone streams, and two
    processes fighting over the same global hotkey.

    The handle is intentionally leaked — it must live for the process lifetime
    and Windows releases it automatically on exit.
    """
    if os.name != "nt":
        return True
    try:
        import ctypes

        ERROR_ALREADY_EXISTS = 183
        kernel32 = ctypes.windll.kernel32
        # "Local\\" scope: per-session, so two different logged-in users can
        # each run their own SAM.
        handle = kernel32.CreateMutexW(None, False, "Local\\SAM_SingleInstance")
        if not handle:
            return True  # do not block if mutex could not be created
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            return False
        _LOCKS.append(handle)
        return True
    except Exception:
        return True


_LOCKS: list = []


def resolve_asset(rel: str) -> str:
    """
    Resolve a path that came from config.yaml.

    Config values may be absolute, or relative to either the user data dir or
    the bundled payload. Historically these were resolved against the process
    CWD, which broke whenever SAM was launched from a shortcut.

    Returns the first candidate that exists; otherwise the bundle-relative path
    so callers still get a usable, loggable path in the error case.
    """
    if not rel:
        return rel
    if os.path.isabs(rel):
        return rel
    for root in (user_data_dir(), resource_root()):
        candidate = os.path.join(root, rel)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(resource_root(), rel)
