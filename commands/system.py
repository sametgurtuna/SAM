# SAM — System Commands
# Directly executes OS-level operations:
# application launching/closing, volume control, screen locking, etc.

import ctypes
import logging
import os
import re
import subprocess
import time
import urllib.parse
from typing import Optional, Dict, Any

from core import paths

logger = logging.getLogger(__name__)

# ─── Windows API Constants ────────────────────────────────────

# Virtual key codes for volume control
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT = 0xB0
VK_MEDIA_PREV = 0xB1

KEYEVENTF_KEYUP = 0x0002


# ─── Security ─────────────────────────────────────────────────
# Transcript text originates from STT and is passed to OS APIs.
# Reject any string containing shell metacharacters — only allow
# alphanumeric, spaces, and safe punctuation.
_SAFE_APP_NAME_RE = re.compile(r"^[\w .'-]{1,64}$", re.UNICODE)


def _is_safe_name(name: str) -> bool:
    """Check whether application name is safe to pass to OS routines."""
    return bool(_SAFE_APP_NAME_RE.match(name.strip()))


def _user_cache_dir() -> str:
    """SAM's user-specific cache directory (OAuth tokens stored here)."""
    return paths.cache_dir()


# ─── Known Applications ───────────────────────────────────────
# Key: lowercase name → dictionary with start details
# Priority: shell start (finds from Start Menu) > direct path

# Applications that must NEVER be opened via voice/text commands (shell/terminals).
# Prevents accidental terminal launch on STT hallucination.
_BLOCKED_APP_NAMES = frozenset({
    "cmd", "command prompt", "terminal", "windows terminal",
    "powershell", "power shell", "pwsh", "wt", "bash", "wsl",
    "windows subsystem for linux", "git bash", "conemu",
})

KNOWN_APPS: Dict[str, Dict[str, Any]] = {
    # Browsers
    "chrome": {
        "exe": "chrome.exe",
        "start": "chrome",
        "aliases": ["chrome", "google chrome"],
    },
    "firefox": {
        "exe": "firefox.exe",
        "start": "firefox",
        "aliases": ["firefox", "fire fox"],
    },
    "edge": {
        "exe": "msedge.exe",
        "start": "msedge",
        "aliases": ["edge", "microsoft edge"],
    },
    "brave": {
        "exe": "brave.exe",
        "start": "brave",
        "aliases": ["brave"],
    },
    # Music / Video
    "spotify": {
        "exe": "Spotify.exe",
        "start": "spotify",
        "protocol": "spotify:",
        "aliases": ["spotify"],
    },
    "vlc": {
        "exe": "vlc.exe",
        "start": "vlc",
        "aliases": ["vlc", "media player"],
    },
    # Messaging
    "discord": {
        "exe": "Discord.exe",
        "start": "discord",
        "aliases": ["discord"],
    },
    "telegram": {
        "exe": "Telegram.exe",
        "start": "telegram",
        "aliases": ["telegram"],
    },
    "whatsapp": {
        "exe": "WhatsApp.exe",
        "start": "whatsapp",
        "aliases": ["whatsapp", "whats app"],
    },
    # Microsoft Office
    "word": {
        "exe": "WINWORD.EXE",
        "start": "winword",
        "aliases": ["word", "microsoft word"],
    },
    "excel": {
        "exe": "EXCEL.EXE",
        "start": "excel",
        "aliases": ["excel", "microsoft excel"],
    },
    "powerpoint": {
        "exe": "POWERPNT.EXE",
        "start": "powerpnt",
        "aliases": ["powerpoint", "power point"],
    },
    # Developer tools
    "vscode": {
        "exe": "Code.exe",
        "start": "code",
        "aliases": ["vscode", "vs code", "visual studio code", "code"],
    },
    # System utilities
    "notepad": {
        "exe": "notepad.exe",
        "start": "notepad",
        "aliases": ["notepad"],
    },
    "calculator": {
        "exe": "calc.exe",
        "start": "calc",
        "aliases": ["calculator", "calc"],
    },
    "explorer": {
        "exe": "explorer.exe",
        "start": "explorer",
        "aliases": ["file explorer", "explorer"],
    },
    "settings": {
        "exe": "ms-settings:",
        "start": "ms-settings:",
        "aliases": ["settings", "windows settings"],
    },
    "task manager": {
        "exe": "taskmgr.exe",
        "start": "taskmgr",
        "aliases": ["task manager", "taskmgr"],
    },
    "paint": {
        "exe": "mspaint.exe",
        "start": "mspaint",
        "aliases": ["paint", "ms paint"],
    },
    # Gaming
    "steam": {
        "exe": "steam.exe",
        "start": "steam",
        "protocol": "steam:",
        "aliases": ["steam"],
    },
    "epic": {
        "exe": "EpicGamesLauncher.exe",
        "start": "com.epicgames.launcher:",
        "aliases": ["epic", "epic games"],
    },
}


def _start_menu_shortcut(name: str) -> Optional[str]:
    """
    Search for application in Start Menu shortcut directories.
    Handles apps installed in user profile or ProgramData.
    """
    roots = [
        os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
    ]
    target = name.lower().strip()
    fallback: Optional[str] = None

    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                if not fn.lower().endswith(".lnk"):
                    continue
                stem = os.path.splitext(fn)[0].lower()
                if stem == target:
                    return os.path.join(dirpath, fn)
                # Keep partial match as fallback if no exact match found
                if fallback is None and target in stem:
                    fallback = os.path.join(dirpath, fn)

    return fallback


def _press_key(vk_code: int) -> None:
    """Simulate a key press and release using Windows API."""
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


# ─── Volume Control ───────────────────────────────────────────

def volume_up(percentage: int = 10) -> str:
    """Increase system volume by percentage."""
    steps = max(1, round(percentage / 2))
    for _ in range(steps):
        _press_key(VK_VOLUME_UP)
    logger.info("Volume up (%d%%, %d steps)", percentage, steps)
    return f"Done, volume up by {percentage}%."


def volume_down(percentage: int = 10) -> str:
    """Decrease system volume by percentage."""
    steps = max(1, round(percentage / 2))
    for _ in range(steps):
        _press_key(VK_VOLUME_DOWN)
    logger.info("Volume down (%d%%, %d steps)", percentage, steps)
    return f"Done, volume down by {percentage}%."


def set_volume_absolute(percentage: int) -> str:
    """Set absolute system volume (0-100) using pycaw."""
    percentage = max(0, min(100, percentage))
    
    # Initialize COM threading model for cross-thread calls
    com_initialized = False
    try:
        ctypes.windll.ole32.CoInitialize(None)
        com_initialized = True
    except Exception:
        pass

    try:
        from pycaw.pycaw import AudioUtilities

        devices = AudioUtilities.GetSpeakers()
        volume = devices.EndpointVolume
        
        # SetMasterVolumeLevelScalar takes a float between 0.0 and 1.0
        volume.SetMasterVolumeLevelScalar(percentage / 100.0, None)
        
        logger.info("Set absolute volume to %d%%", percentage)
        return f"Volume set to {percentage}%."
    except ImportError as e:
        logger.error("Volume control dependency missing (pycaw/comtypes): %s", e)
        return "Volume control requires pycaw and comtypes. Please install them."
    except Exception as e:
        logger.error("Failed to set absolute volume: %s", e)
        return f"Sorry, I couldn't set the volume: {e}"
    finally:
        # Clean up COM threading model
        if com_initialized:
            try:
                ctypes.windll.ole32.CoUninitialize()
            except Exception:
                pass


def volume_mute() -> str:
    """Toggle system mute state."""
    _press_key(VK_VOLUME_MUTE)
    logger.info("Volume mute toggled")
    return "Done, mute toggled."


def media_play_pause() -> str:
    """Toggle media play / pause."""
    _press_key(VK_MEDIA_PLAY_PAUSE)
    logger.info("Media play/pause")
    return "Done."


def media_next() -> str:
    """Skip to next media track."""
    _press_key(VK_MEDIA_NEXT)
    logger.info("Media next track")
    return "Next track."


def media_prev() -> str:
    """Skip to previous media track."""
    _press_key(VK_MEDIA_PREV)
    logger.info("Media previous track")
    return "Previous track."


def play_on_spotify(song_name: str) -> str:
    """Search for track/artist on Spotify and start playback via Web API."""
    from core.config import config

    # Environment variables override config.yaml
    client_id = os.environ.get("SPOTIFY_CLIENT_ID") or config.get("spotify", "client_id")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET") or config.get("spotify", "client_secret")
    redirect_uri = config.get("spotify", "redirect_uri", default="http://localhost:8080")

    if not client_id or not client_secret:
        logger.warning("Spotify Client ID/Secret not configured.")
        return "Please configure your Spotify Client ID and Secret in settings."

    try:
        # Lazy load to avoid startup delay if spotipy is missing or not used
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth

        scope = "user-read-playback-state,user-modify-playback-state"
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            open_browser=True,
            # Store OAuth token in user cache dir
            cache_path=os.path.join(_user_cache_dir(), "spotify_token.json"),
        )
        
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        # 1. Search for track (ranked by popularity)
        results = sp.search(q=song_name, limit=5, type='track')
        items = results.get('tracks', {}).get('items', [])
        
        if not items:
            return f"I couldn't find '{song_name}' on Spotify."
            
        # Sort by popularity to avoid weird covers
        items.sort(key=lambda x: x.get('popularity', 0), reverse=True)
        best_track = items[0]
            
        track_uri = best_track['uri']
        track_name = best_track['name']
        artist_name = best_track['artists'][0]['name']
        
        # 2. Find active device
        devices = sp.devices()
        active_device = None
        
        for d in devices.get('devices', []):
            if d['is_active']:
                active_device = d['id']
                break
                
        # If no active device, take first available
        if not active_device and devices.get('devices'):
            active_device = devices['devices'][0]['id']
            
        # If no devices are open, launch Spotify protocol URI
        if not active_device:
            logger.info("No active Spotify devices. Opening Spotify app.")
            os.startfile(track_uri)
            return f"I couldn't find an active device, but I opened {track_name} for you."
            
        # 3. Start playback
        sp.start_playback(device_id=active_device, uris=[track_uri])
        logger.info("Spotify API play successful: %s by %s", track_name, artist_name)
        return f"Playing {track_name} by {artist_name} on Spotify."
        
    except ImportError:
        logger.error("spotipy module missing")
        return "Spotipy library is missing. Please run pip install spotipy."
    except Exception as e:
        logger.error("Spotify API play failed: %s", e)
        # Search fallback on error
        query = urllib.parse.quote(song_name)
        os.startfile(f"spotify:search:{query}")
        return f"There was a connection issue, but I searched for {song_name} on Spotify."


# ─── App Launching ───────────────────────────────────────────

def open_app(app_name: str) -> str:
    """
    Launch application from known apps list or Start Menu search.
    
    Args:
        app_name: Name of the application (cleaned)
    
    Returns:
        Confirmation message for the user
    """
    app_lower = app_name.lower().strip()

    # Block opening shells via voice/text commands
    if app_lower in _BLOCKED_APP_NAMES:
        logger.info("Refused to open a shell via voice/text command: %r", app_name)
        return "Sorry, I can't open a command prompt for security reasons."

    # Look up in known apps list
    for key, info in KNOWN_APPS.items():
        aliases = info.get("aliases", [])
        if app_lower in aliases or app_lower == key:
            return _launch_app(key, info)

    # Unknown application — validate name, then try without a shell
    if not _is_safe_name(app_name):
        logger.warning("Rejected unsafe app name: %r", app_name)
        return f"Sorry, I can't open {app_name}."

    return _launch_unknown(app_name)


def _launch_app(name: str, info: Dict[str, Any]) -> str:
    """Launch a known application with predefined config."""
    try:
        target = info.get("protocol") or info.get("start", name)
        os.startfile(target)
        logger.info("Launched %s via ShellExecute: %s", name, target)
        return f"Opening {name}."

    except OSError:
        # Fallback to Start Menu shortcut
        shortcut = _start_menu_shortcut(name)
        if shortcut:
            try:
                os.startfile(shortcut)
                logger.info("Launched %s via Start Menu shortcut: %s", name, shortcut)
                return f"Opening {name}."
            except Exception as e:
                logger.error("Shortcut launch failed for %s: %s", name, e)
        logger.warning("Could not resolve %s to an executable", name)
        return f"Sorry, I couldn't find {name} on this computer."

    except Exception as e:
        logger.error("Failed to launch %s: %s", name, e)
        return f"Sorry, I couldn't open {name}."


def _launch_unknown(app_name: str) -> str:
    """Launch an unknown application via ShellExecute without invoking a shell."""
    try:
        os.startfile(app_name)
        logger.info("Launched unknown app via ShellExecute: %s", app_name)
        return f"Opening {app_name}."
    except OSError:
        shortcut = _start_menu_shortcut(app_name)
        if shortcut:
            try:
                os.startfile(shortcut)
                logger.info("Launched %s via Start Menu shortcut: %s", app_name, shortcut)
                return f"Opening {app_name}."
            except Exception as e:
                logger.error("Shortcut launch failed for %s: %s", app_name, e)
        logger.info("Unknown app not found: %s", app_name)
        return f"Sorry, I couldn't find {app_name} on this computer."
    except Exception as e:
        logger.error("Failed to launch unknown app %s: %s", app_name, e)
        return f"Sorry, I couldn't open {app_name}."


# ─── App Closing ─────────────────────────────────────────────

def close_app(app_name: str) -> str:
    """Terminate application process via taskkill."""
    app_lower = app_name.lower().strip()

    # Find exe name in known apps
    exe_name: Optional[str] = None
    for key, info in KNOWN_APPS.items():
        aliases = info.get("aliases", [])
        if app_lower in aliases or app_lower == key:
            exe_name = info.get("exe")
            break

    if not exe_name:
        # Validate unknown app name before passing to taskkill
        if not _is_safe_name(app_lower):
            logger.warning("Rejected unsafe app name for close: %r", app_name)
            return f"Sorry, I can't close {app_name}."
        exe_name = f"{app_lower}.exe"

    try:
        subprocess.run(
            ["taskkill", "/IM", exe_name, "/F"],
            capture_output=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        logger.info("Closed app: %s (%s)", app_name, exe_name)
        return f"Closed {app_name}."
    except Exception as e:
        logger.error("Failed to close %s: %s", app_name, e)
        return f"Sorry, I couldn't close {app_name}."


# ─── System Commands ─────────────────────────────────────────

def lock_screen() -> str:
    """Lock the Windows desktop workstation."""
    ctypes.windll.user32.LockWorkStation()
    logger.info("Screen locked")
    return "Locking screen."


def open_url(url: str) -> str:
    """Open URL in default web browser."""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    os.startfile(url)
    logger.info("Opened URL: %s", url)
    return f"Opening {url}."


def web_search(query: str) -> str:
    """Perform Google web search in default browser."""
    search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    os.startfile(search_url)
    logger.info("Web search: %s", query)
    return f"Searching for {query}."


def screenshot() -> str:
    """Open Windows Snipping Tool."""
    try:
        os.startfile("ms-screenclip:")
        logger.info("Screenshot tool opened")
        return "Opening screenshot tool."
    except Exception:
        # Fallback for older Windows builds
        try:
            os.startfile("snippingtool")
            return "Opening screenshot tool."
        except Exception as e:
            logger.error("Screenshot failed: %s", e)
            return "Sorry, couldn't open screenshot tool."


def minimize_all() -> str:
    """Minimize all open windows (Win+D)."""
    ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)  # Win key down
    ctypes.windll.user32.keybd_event(0x44, 0, 0, 0)  # D key down
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(0x44, 0, KEYEVENTF_KEYUP, 0)
    ctypes.windll.user32.keybd_event(0x5B, 0, KEYEVENTF_KEYUP, 0)
    logger.info("All windows minimized")
    return "Done, all windows minimized."


# Two-step power confirmation to prevent accidental shutdowns
_PENDING_POWER_ACTION: Optional[str] = None
_PENDING_POWER_TIME: float = 0.0
_POWER_CONFIRM_WINDOW_S: float = 30.0

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _arm_power_action(action: str, label: str) -> str:
    """Arm a power action and await confirmation within time window."""
    global _PENDING_POWER_ACTION, _PENDING_POWER_TIME
    _PENDING_POWER_ACTION = action
    _PENDING_POWER_TIME = time.time()
    logger.info("Power action armed, awaiting confirmation: %s", action)
    return f"Are you sure you want to {label}? Say confirm to proceed."


def shutdown_pc() -> str:
    """Arm PC shutdown (requires confirmation)."""
    return _arm_power_action("shutdown", "shut down the computer")


def restart_pc() -> str:
    """Arm PC restart (requires confirmation)."""
    return _arm_power_action("restart", "restart the computer")


def confirm_power_action() -> str:
    """Confirm pending power action and schedule 30-second shutdown/restart timer."""
    global _PENDING_POWER_ACTION

    if _PENDING_POWER_ACTION is None:
        return "There's nothing to confirm."

    if time.time() - _PENDING_POWER_TIME > _POWER_CONFIRM_WINDOW_S:
        _PENDING_POWER_ACTION = None
        return "That confirmation expired. Please ask again."

    action = _PENDING_POWER_ACTION
    _PENDING_POWER_ACTION = None

    flag = "/s" if action == "shutdown" else "/r"
    subprocess.Popen(["shutdown", flag, "/t", "30"], creationflags=_NO_WINDOW)
    logger.info("Power action confirmed and scheduled: %s (30s)", action)
    verb = "Shutting down" if action == "shutdown" else "Restarting"
    return f"{verb} in 30 seconds. Say cancel shutdown to abort."


def cancel_shutdown() -> str:
    """Abort scheduled shutdown or restart."""
    global _PENDING_POWER_ACTION
    _PENDING_POWER_ACTION = None
    subprocess.Popen(["shutdown", "/a"], creationflags=_NO_WINDOW)
    logger.info("Shutdown cancelled")
    return "Shutdown cancelled."
