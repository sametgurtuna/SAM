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

# Windows process creation flags — keep the server console completely hidden
# and detached, so it neither flashes a window nor dies with SAM.
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008

# Reasons emitted with the `unavailable` signal
REASON_NOT_INSTALLED = "not-installed"
REASON_TIMEOUT = "timeout"
REASON_SPAWN_FAILED = "spawn-failed"

_POLL_INTERVAL_S = 0.5
_PING_TIMEOUT_S = 1.0


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
            "llm", "ollama", "base_url", default="http://localhost:11434"
        ).rstrip("/")
        self._timeout: int = config.get(
            "llm", "ollama", "startup_timeout_seconds", default=20
        )

        self._process: subprocess.Popen | None = None
        # Yalnizca SAM'in kendi baslattigi sunucu kapatilabilir.
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
        # 1. Zaten calisiyor mu?
        if self._ping():
            logger.info("Ollama server already running — leaving it alone")
            self._we_started = False
            self.ready.emit()
            return

        # 2. Kurulu mu?
        executable = self.find_executable()
        if executable is None:
            logger.warning(
                "Ollama is not installed. Local LLM disabled — "
                "install it from https://ollama.com/download"
            )
            self.unavailable.emit(REASON_NOT_INSTALLED)
            return

        # 3. Kurulu ama kapali — baslat.
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

    def _spawn(self, executable: str) -> bool:
        """Launch `ollama serve` with no console window. Returns success."""
        creationflags = 0
        startupinfo = None
        if os.name == "nt":
            creationflags = CREATE_NO_WINDOW | DETACHED_PROCESS
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        try:
            self._process = subprocess.Popen(
                [executable, "serve"],          # liste formu — shell=True yok
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
