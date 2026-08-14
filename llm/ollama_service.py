# SAM — Ollama Server Lifecycle
# Finds the ollama executable, starts "ollama serve" in the background if it is
# not already running, and reports readiness.
#
# This is deliberately separate from llm/ollama_engine.py: that module is a pure
# HTTP client, this one owns the process. Nothing here touches a widget — all
# blocking work runs on a daemon thread and reports back via signals, matching
# every other engine in the codebase.

import logging
import os
import shutil
import subprocess
import threading
import time

import requests
from PyQt6.QtCore import QObject, pyqtSignal

from core.config import config

logger = logging.getLogger(__name__)

# Windows process creation flags.
#
# NOTE: DETACHED_PROCESS is intentionally omitted. Per CreateProcess documentation,
# combining DETACHED_PROCESS and CREATE_NO_WINDOW is invalid; DETACHED takes precedence
# and "ollama serve" starts console-less, causing child processes (llama-server.exe)
# to spawn visible console windows.
#
# CREATE_NO_WINDOW alone gives the server an invisible console that child processes inherit.
# CREATE_NEW_PROCESS_GROUP prevents Ctrl+C/Ctrl+Break signals from propagating from SAM to Ollama.
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200

# Reasons emitted with the `unavailable` signal
REASON_NOT_INSTALLED = "not-installed"
REASON_TIMEOUT = "timeout"
REASON_SPAWN_FAILED = "spawn-failed"

_POLL_INTERVAL_S = 0.5
# 3.0s ping timeout accounts for IPv6/IPv4 fallback delay on local socket binding
_PING_TIMEOUT_S = 3.0


class OllamaService(QObject):
    """
    Ensures a local Ollama server is running.

    Signals:
        ready(): The server answered /api/tags.
        unavailable(str): Could not reach a server. Payload is one of the
            REASON_* constants above.
    """

    ready = pyqtSignal()
    unavailable = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()

        self._base_url: str = config.get(
            "llm", "ollama", "base_url", default="http://127.0.0.1:11434"
        ).rstrip("/")
        self._timeout: int = config.get(
            "llm", "ollama", "startup_timeout_seconds", default=45
        )
        self._existing_grace: int = config.get(
            "llm", "ollama", "existing_server_grace_seconds", default=8
        )

        self._process: subprocess.Popen | None = None
        # Only servers spawned by SAM will be terminated on exit
        self._we_started: bool = False
        self._thread: threading.Thread | None = None

    # ─── Detection ────────────────────────────────────────────────

    def _ping(self) -> bool:
        """True if an Ollama server answers on the configured base URL."""
        try:
            resp = requests.get(f"{self._base_url}/api/tags", timeout=_PING_TIMEOUT_S)
            return resp.status_code == 200
        except Exception:
            return False

    def find_executable(self) -> str | None:
        """
        Locate ollama.exe. Config first, then PATH, then the two locations the
        official Windows installer uses.
        """
        configured = config.get("llm", "ollama", "executable", default="")
        if configured and os.path.isfile(configured):
            return configured

        found = shutil.which("ollama")
        if found:
            return found

        candidates = []
        for env_var in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
            base = os.environ.get(env_var)
            if not base:
                continue
            candidates.append(os.path.join(base, "Programs", "Ollama", "ollama.exe"))
            candidates.append(os.path.join(base, "Ollama", "ollama.exe"))

        for path in candidates:
            if os.path.isfile(path):
                return path
        return None

    def find_desktop_app(self) -> str | None:
        """
        Locate "ollama app.exe" (Ollama's tray application).
        Preferred over spawning CLI directly since it starts clean background child processes.
        """
        executable = self.find_executable()
        if executable is None:
            return None
        app = os.path.join(os.path.dirname(executable), "ollama app.exe")
        return app if os.path.isfile(app) else None

    @property
    def is_installed(self) -> bool:
        return self.find_executable() is not None

    # ─── Startup ──────────────────────────────────────────────────

    def ensure_running(self) -> None:
        """Kick off detection/startup on a daemon thread. Returns immediately."""
        if self._thread is not None and self._thread.is_alive():
            logger.debug("Ollama startup already in progress")
            return

        self._thread = threading.Thread(
            target=self._ensure_running_worker, daemon=True, name="OllamaService"
        )
        self._thread.start()

    def _ensure_running_worker(self) -> None:
        # 1. Is an Ollama instance already running?
        if self._wait_for_existing_server():
            logger.info("Ollama server already running — leaving it alone")
            self._we_started = False
            self.ready.emit()
            return

        # 2. Is Ollama installed?
        executable = self.find_executable()
        if executable is None:
            logger.warning(
                "Ollama is not installed. Local LLM disabled — "
                "install it from https://ollama.com/download"
            )
            self.unavailable.emit(REASON_NOT_INSTALLED)
            return

        # 3. Installed but stopped — launch it.
        # Prefer the desktop tray app; fall back to CLI serve.
        desktop_app = self.find_desktop_app()
        if desktop_app is not None:
            logger.info("Starting Ollama desktop app: %s", desktop_app)
            if not self._launch_desktop_app(desktop_app):
                self.unavailable.emit(REASON_SPAWN_FAILED)
                return
        else:
            logger.info("Starting Ollama server: %s serve", executable)
            if not self._spawn(executable):
                self.unavailable.emit(REASON_SPAWN_FAILED)
                return

        # 4. Hazir olana kadar yokla.
        deadline = time.time() + self._timeout
        while time.time() < deadline:
            if self._ping():
                elapsed = self._timeout - (deadline - time.time())
                logger.info("Ollama server ready after %.1fs", elapsed)
                self.ready.emit()
                return
            time.sleep(_POLL_INTERVAL_S)

        logger.error("Ollama server did not become ready within %ds", self._timeout)
        self.unavailable.emit(REASON_TIMEOUT)

    def _wait_for_existing_server(self) -> bool:
        """
        Ping for up to `_existing_grace` seconds, waiting for a server somebody
        else (the Ollama desktop app's own autostart) is bringing up.
        """
        deadline = time.time() + self._existing_grace
        while True:
            if self._ping():
                return True
            if time.time() >= deadline:
                return False
            time.sleep(_POLL_INTERVAL_S)

    def _launch_desktop_app(self, app_path: str) -> bool:
        """Launch Ollama desktop app without opening a console."""
        try:
            os.startfile(app_path)
            self._we_started = False
            return True
        except Exception as e:
            logger.error("Failed to start the Ollama desktop app: %s", e)
            return False

    def _spawn(self, executable: str) -> bool:
        """Launch `ollama serve` with no console window. Returns success."""
        creationflags = 0
        startupinfo = None
        if os.name == "nt":
            creationflags = CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        try:
            self._process = subprocess.Popen(
                [executable, "serve"],          # List form without shell=True
                creationflags=creationflags,
                startupinfo=startupinfo,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
            self._we_started = True
            return True
        except Exception as e:
            logger.error("Failed to start Ollama server: %s", e)
            self._process = None
            return False

    # ─── Shutdown ─────────────────────────────────────────────────

    def shutdown(self) -> None:
        """
        Stop the server only if SAM started it AND the user opted in.

        Default is to leave it running: the user may be using Ollama from
        another client, and reloading a multi-GB model is expensive.
        """
        if not self._we_started or self._process is None:
            return
        if not config.get("llm", "ollama", "stop_on_exit", default=False):
            logger.debug("Leaving Ollama server running (stop_on_exit is false)")
            return

        logger.info("Stopping Ollama server (we started it)")
        try:
            self._process.terminate()
            self._process.wait(timeout=5)
        except Exception as e:
            logger.warning("Could not stop Ollama server cleanly: %s", e)
        finally:
            self._process = None
            self._we_started = False
