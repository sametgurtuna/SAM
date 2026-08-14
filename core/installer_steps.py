# SAM — Installer helper steps
# Invoked by the Inno Setup wizard as:
#     SAM.exe --install-models [--llm] [--whisper] [--progress-file PATH]
#
# Runs before QApplication is constructed (see main.py) so this stays a plain
# console-less script: no Qt, no UI, no audio devices.
#
# Reusing SAM.exe rather than shipping a second binary guarantees the installer
# and the app agree on the model names and the download paths — a separate
# script would drift the moment someone changes config.example.yaml.

import logging
import os
import subprocess
import sys

from core import paths
from core.config import config

logger = logging.getLogger(__name__)

CREATE_NO_WINDOW = 0x08000000


def _report(progress_file: str | None, percent: int, message: str) -> None:
    """Write progress for the wizard to poll, and echo it if we have a console."""
    line = f"{percent}|{message}"
    if sys.stdout is not None:
        print(line, flush=True)
    if not progress_file:
        return
    try:
        with open(progress_file, "w", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _find_ollama() -> str | None:
    """Same lookup order as llm/ollama_service.OllamaService.find_executable."""
    import shutil

    configured = config.get("llm", "ollama", "executable", default="")
    if configured and os.path.isfile(configured):
        return configured

    found = shutil.which("ollama")
    if found:
        return found

    for env_var in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(env_var)
        if not base:
            continue
        for candidate in (
            os.path.join(base, "Programs", "Ollama", "ollama.exe"),
            os.path.join(base, "Ollama", "ollama.exe"),
        ):
            if os.path.isfile(candidate):
                return candidate
    return None


def pull_llm_model(progress_file: str | None = None) -> bool:
    """`ollama pull <configured model>`, with no console window."""
    model = config.get("llm", "ollama", "model", default="qwen2.5:3b")
    executable = _find_ollama()
    if executable is None:
        _report(progress_file, 0, "Ollama not found — skipping model download")
        return False

    _report(progress_file, 5, f"Downloading language model {model}…")
    try:
        proc = subprocess.Popen(
            [executable, "pull", model],       # list format, no shell
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0,
            text=True,
            errors="replace",
        )
        # Read Ollama progress lines so the installation is not a black box.
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if line:
                _report(progress_file, 30, f"{model}: {line[:70]}")
        code = proc.wait()
        if code != 0:
            _report(progress_file, 50, f"Model download failed (exit {code})")
            return False
        _report(progress_file, 50, f"Language model {model} ready")
        return True
    except Exception as e:
        _report(progress_file, 50, f"Model download failed: {e}")
        return False


def download_whisper_model(progress_file: str | None = None) -> bool:
    """
    Pre-download the Whisper model into exactly the directory audio/stt.py
    reads from, so the first run has no silent multi-hundred-MB wait.
    """
    size = config.get("stt", "model", default="small")
    device = config.get("stt", "device", default="cpu")
    compute_type = config.get("stt", "compute_type", default="int8")
    download_root = os.path.join(paths.models_dir(), "whisper")

    _report(progress_file, 55, f"Downloading speech recognition model ({size})…")
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(
            size,
            device=device,
            compute_type=compute_type,
            download_root=download_root,
        )
        del model  # for download only — do not keep in RAM
        _report(progress_file, 100, f"Speech model {size} ready")
        return True
    except Exception as e:
        _report(progress_file, 100, f"Speech model download failed: {e}")
        return False


def run_install_steps(argv: list[str]) -> int:
    """
    Entry point for `SAM.exe --install-models`.

    Always exits 0: a failed optional download must not fail the whole
    installation. SAM degrades gracefully — it downloads on first use instead.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    config.load()

    progress_file = None
    if "--progress-file" in argv:
        idx = argv.index("--progress-file")
        if idx + 1 < len(argv):
            progress_file = argv[idx + 1]

    want_llm = "--llm" in argv
    want_whisper = "--whisper" in argv

    if want_llm:
        pull_llm_model(progress_file)
    if want_whisper:
        download_whisper_model(progress_file)

    _report(progress_file, 100, "Done")
    return 0
