# Set explicit Windows AppUserModelID so taskbar groups under SAM and displays SAM's icon
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("sam.assistant.settings.1.0")
except Exception:
    pass

import logging
import os
import platform
import subprocess
import sys
import time
import threading

# Ensure project root is on sys.path when executed directly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import webview

from core.config import config
from core import paths

logger = logging.getLogger(__name__)

# Ensure config is loaded
if config._config_path is None:
    config.load()

APP_START_TIME = time.time()
INDEX_HTML = paths.resource_path("ui/web/index.html")
if not os.path.exists(INDEX_HTML):
    INDEX_HTML = os.path.abspath(os.path.join(os.path.dirname(__file__), "web", "index.html"))

_active_window = None
_settings_subprocess = None
_settings_mutex = None


class SettingsApi:
    """Python API exposed directly to JavaScript in the webview."""

    def __init__(self, controller=None, window=None):
        self._controller = controller
        self._window = window

    def set_window(self, window):
        self._window = window

    def get_state(self) -> dict:
        """Loads and returns complete state + system diagnostics."""
        try:
            # Diagnostics
            cuda_status = "CPU Mode"
            try:
                import torch
                if torch.cuda.is_available():
                    cuda_status = f"Available ({torch.version.cuda})"
            except Exception:
                pass

            elapsed = int(time.time() - APP_START_TIME)
            uptime_str = f"{elapsed // 3600:02d}:{(elapsed % 3600) // 60:02d}:{elapsed % 60:02d}"

            instant_count = 130
            if self._controller and hasattr(self._controller, "_instant") and self._controller._instant:
                instant_count = self._controller._instant.count

            # Safely extract all config sections with defaults
            hotkey_data = {
                "trigger": config.get("hotkey", "trigger", default="ctrl+space"),
                "text_input": config.get("hotkey", "text_input", default="ctrl+shift+space"),
            }
            wake_data = {
                "model": config.get("wake_word", "model", default="assets/models/hey_sam.onnx"),
                "threshold": config.get("wake_word", "threshold", default=0.40),
            }
            stt_data = {
                "model": config.get("stt", "model", default="base"),
                "language": config.get("stt", "language", default=None),
                "device": config.get("stt", "device", default="cpu"),
                "partial_model": config.get("stt", "partial_model", default="base"),
                "partial_interval_ms": config.get("stt", "partial_interval_ms", default=400),
            }
            tts_data = {
                "engine": config.get("tts", "engine", default="edge-tts"),
                "voice": config.get("tts", "voice", default="en-US-GuyNeural"),
                "rate": config.get("tts", "rate", default="+0%"),
                "auto_language": config.get("tts", "auto_language", default=True),
                "voices": {
                    "tr": config.get("tts", "voices", "tr", default="tr-TR-EmelNeural"),
                    "en": config.get("tts", "voices", "en", default="en-US-JennyNeural"),
                }
            }
            instant_data = {
                "enabled": config.get("instant", "enabled", default=True),
                "file": config.get("instant", "file", default="knowledge/instant_responses.yaml"),
            }
            llm_data = {
                "context_window": config.get("llm", "context_window", default=8),
                "ollama": {
                    "base_url": config.get("llm", "ollama", "base_url", default="http://127.0.0.1:11434"),
                    "model": config.get("llm", "ollama", "model", default="qwen2.5:3b"),
                    "temperature": config.get("llm", "ollama", "temperature", default=0.70),
                    "max_tokens": config.get("llm", "ollama", "max_tokens", default=256),
                    "autostart": config.get("llm", "ollama", "autostart", default=True),
                    "executable": config.get("llm", "ollama", "executable", default=""),
                    "stop_on_exit": config.get("llm", "ollama", "stop_on_exit", default=False),
                }
            }
            ui_data = {
                "overlay": {
                    "style": config.get("ui", "overlay", "style", default="orb"),
                },
                "orb": {
                    "size": config.get("ui", "orb", "size", default=120),
                    "ring_width": config.get("ui", "orb", "ring_width", default=3),
                    "opacity": config.get("ui", "orb", "opacity", default=0.95),
                    "click_through": config.get("ui", "orb", "click_through", default=True),
                    "idle_animation": config.get("ui", "orb", "idle_animation", default=True),
                    "idle_fps": config.get("ui", "orb", "idle_fps", default=12),
                },
                "auto_hide": {
                    "delay_seconds": config.get("ui", "auto_hide", "delay_seconds", default=4),
                }
            }
            spotify_data = {
                "client_id": config.get("spotify", "client_id", default=""),
                "client_secret": config.get("spotify", "client_secret", default=""),
                "redirect_uri": config.get("spotify", "redirect_uri", default="http://127.0.0.1:8080"),
            }

            data = {
                "version": config.get("app", "version", default="0.4.8"),
                "hotkey": hotkey_data,
                "wake_word": wake_data,
                "stt": stt_data,
                "tts": tts_data,
                "instant": instant_data,
                "instant_count": instant_count,
                "llm": llm_data,
                "ui": ui_data,
                "spotify": spotify_data,
                "paths": {
                    "config": str(paths.config_path()),
                    "logs": str(paths.logs_dir()),
                    "models": str(paths.models_dir()),
                    "user_data": str(paths.user_data_dir()),
                },
                "diagnostics": {
                    "python": sys.version.split()[0],
                    "os": f"{platform.system()} {platform.machine()}",
                    "cuda": cuda_status,
                    "uptime": uptime_str,
                }
            }
            return data
        except Exception as e:
            logger.error("Failed to get settings state: %s", e)
            return {}

    def save_state(self, new_data: dict) -> bool:
        """Updates and persists new configuration from frontend."""
        try:
            for section, values in new_data.items():
                if isinstance(values, dict):
                    for k, v in values.items():
                        if isinstance(v, dict):
                            for sub_k, sub_v in v.items():
                                config.set(section, k, sub_k, value=sub_v)
                        else:
                            config.set(section, k, value=v)
                else:
                    config.set(section, value=values)

            success = config.save()
            if success:
                logger.info("Settings saved via Webview UI")
                if self._controller and hasattr(self._controller, "apply_settings"):
                    self._controller.apply_settings()
                return True
            return False
        except Exception as e:
            logger.error("Failed to save state from Webview: %s", e)
            return False

    def test_ollama(self, base_url: str = "") -> dict:
        """Pings Ollama server, measures latency, and returns installed models."""
        import requests
        if not base_url:
            base_url = config.get("llm", "ollama", "base_url", default="http://127.0.0.1:11434")
        base_url = base_url.rstrip("/")
        start = time.perf_counter()
        try:
            resp = requests.get(f"{base_url}/api/tags", timeout=3.0)
            latency = max(1, int((time.perf_counter() - start) * 1000))
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                return {
                    "status": "connected",
                    "latency_ms": latency,
                    "models": models,
                }
            return {"status": "error", "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "offline", "error": "Server not reachable"}

    def browse_wake_model(self) -> str:
        """Opens file dialog for Wake Word model."""
        if not self._window:
            return ""
        file_types = ('Wake Word Models (*.onnx;*.tflite)', 'All files (*.*)')
        result = self._window.create_file_dialog(webview.OPEN_DIALOG, file_types=file_types)
        if result and len(result) > 0:
            return result[0].replace("\\", "/")
        return ""

    def browse_ollama_exe(self) -> str:
        """Opens file dialog for ollama.exe."""
        if not self._window:
            return ""
        file_types = ('Executables (*.exe)', 'All files (*.*)')
        result = self._window.create_file_dialog(webview.OPEN_DIALOG, file_types=file_types)
        if result and len(result) > 0:
            return result[0].replace("\\", "/")
        return ""

    def open_instant_file(self):
        """Opens instant_responses.yaml in default text editor."""
        from commands.instant import InstantResponder, DEFAULT_FILE
        file_path = config.get("instant", "file", default=None) or DEFAULT_FILE
        resolved = InstantResponder._resolve_path(file_path)
        if os.path.exists(resolved):
            try:
                os.startfile(resolved)
            except OSError:
                subprocess.Popen(["notepad.exe", resolved])

    def open_instant_folder(self):
        """Opens folder containing instant_responses.yaml in Explorer."""
        from commands.instant import InstantResponder, DEFAULT_FILE
        file_path = config.get("instant", "file", default=None) or DEFAULT_FILE
        resolved = InstantResponder._resolve_path(file_path)
        folder = os.path.dirname(resolved)
        if os.path.exists(folder):
            os.startfile(folder)

    def reload_instant(self) -> dict:
        """Reloads instant responses into running SAM controller."""
        if self._controller and hasattr(self._controller, "_instant") and self._controller._instant:
            try:
                self._controller._instant.reload()
                return {"count": self._controller._instant.count}
            except Exception as e:
                logger.error("Reload instant failed: %s", e)
        return {"count": 130}

    def reset_orb_position(self):
        """Snaps Orb back to default bottom-right."""
        if self._controller and hasattr(self._controller, "_bar") and hasattr(self._controller._bar, "reset_position"):
            self._controller._bar.reset_position()
        else:
            config.set("ui", "orb", "position", "anchor", value="bottom-right")
            config.set("ui", "orb", "position", "x", value=None)
            config.set("ui", "orb", "position", "y", value=None)
            config.save()

    def open_user_data_folder(self):
        """Opens %APPDATA%/SAM in Explorer."""
        data_dir = paths.user_data_dir()
        if os.path.exists(data_dir):
            os.startfile(data_dir)

    def open_github(self):
        """Opens GitHub repo in default browser."""
        import webbrowser
        webbrowser.open("https://github.com/sametgurtuna/SAM")

    def close_window(self):
        """Closes the settings window."""
        global _active_window
        if self._window:
            self._window.destroy()
            _active_window = None


def bring_existing_settings_to_front() -> bool:
    """Finds existing SAM Settings window on Windows and brings it to front."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, "SAM Settings")
        if hwnd:
            user32.ShowWindow(hwnd, 9)  # 9 = SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            return True
    except Exception:
        pass
    return False


def check_single_instance() -> bool:
    """Uses a Windows Named Mutex to prevent duplicate Settings processes."""
    global _settings_mutex
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        ERROR_ALREADY_EXISTS = 183

        _settings_mutex = kernel32.CreateMutexW(None, True, "Local\\SAM_Settings_Window_Mutex")
        last_error = kernel32.GetLastError()

        if last_error == ERROR_ALREADY_EXISTS:
            time.sleep(0.15)
            bring_existing_settings_to_front()
            return False
        return True
    except Exception:
        return True


def _apply_window_icon():
    """Applies assets/icon.ico to the SAM Settings window once created."""
    icon_path = paths.resource_path("assets/icon.ico")
    if not os.path.exists(icon_path):
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico"))
    if not os.path.exists(icon_path):
        return

    def _worker():
        try:
            import ctypes
            user32 = ctypes.windll.user32
            for _ in range(40):
                time.sleep(0.1)
                hwnd = user32.FindWindowW(None, "SAM Settings")
                if hwnd:
                    IMAGE_ICON = 1
                    LR_LOADFROMFILE = 0x00000010
                    WM_SETICON = 0x0080
                    ICON_SMALL = 0
                    ICON_BIG = 1
                    GCLP_HICON = -14
                    GCLP_HICONSM = -34

                    h_icon_big = user32.LoadImageW(None, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                    h_icon_small = user32.LoadImageW(None, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)

                    if h_icon_big:
                        user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon_big)
                        try:
                            user32.SetClassLongPtrW(hwnd, GCLP_HICON, h_icon_big)
                        except Exception:
                            pass
                    if h_icon_small:
                        user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon_small)
                        try:
                            user32.SetClassLongPtrW(hwnd, GCLP_HICONSM, h_icon_small)
                        except Exception:
                            pass
                    break
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()


def launch_web_settings(controller=None):
    """
    Spawns or brings to front the Webview-based Settings window.
    Guarantees a strictly single-instance window.
    """
    global _settings_subprocess

    # 1. If window is already open on Windows, bring it to front
    if bring_existing_settings_to_front():
        return

    # 2. If called from running PyQt app, ensure only one subprocess is active
    if controller is not None:
        if _settings_subprocess is not None and _settings_subprocess.poll() is None:
            bring_existing_settings_to_front()
            return
        if paths.is_frozen():
            cmd = [sys.executable, "--settings"]
        else:
            cmd = [sys.executable, os.path.abspath(__file__)]
        _settings_subprocess = subprocess.Popen(cmd)
        return

    # 3. Direct launch with mutex protection
    if not check_single_instance():
        sys.exit(0)

    _apply_window_icon()
    api = SettingsApi(controller=controller)
    window = webview.create_window(
        title="SAM Settings",
        url=INDEX_HTML,
        js_api=api,
        width=1020,
        height=690,
        resizable=False,
        background_color="#0a0a0f",
        text_select=True,
    )
    api.set_window(window)
    webview.start(gui="edgechromium", debug=False)


if __name__ == "__main__":
    launch_web_settings()
