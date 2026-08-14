# -*- mode: python ; coding: utf-8 -*-
# SAM — PyInstaller build spec (onedir)
#
#     pyinstaller SAM.spec
#
# Produces dist/SAM/, which installer/SAM.iss packages into SAM-Setup-x.y.z.exe.
#
# Build from a clean tree. The security assertion below refuses to bundle
# config.yaml or any token cache, but the first line of defence is not building
# from a working directory that contains your secrets.

import os
from PyInstaller.utils.hooks import (
    collect_data_files, collect_dynamic_libs, collect_submodules,
)

block_cipher = None
ROOT = os.path.abspath(os.getcwd())

# ─── Data files ───────────────────────────────────────────────────
datas = [
    ("assets/activation.wav", "assets"),
    ("assets/icon.ico", "assets"),
    ("assets/icon.png", "assets"),
    ("config.example.yaml", "."),
    # RAG knowledge base — located under resource_root()/knowledge
    ("knowledge", "knowledge"),
    # Modern Webview Settings UI
    ("ui/web", "ui/web"),
]

# ─── Pre-download embedding model ─────────────────────────────────
# Pre-download and bundle sentence-transformers model at build time
# so RAG works fully offline in frozen builds.
_EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
_EMBED_LOCAL = os.path.join(ROOT, "assets", "models", "embedding", _EMBED_MODEL)
if not os.path.isdir(_EMBED_LOCAL):
    print(f"[SAM.spec] downloading embedding model to {_EMBED_LOCAL}...")
    from sentence_transformers import SentenceTransformer as _ST
    _m = _ST(_EMBED_MODEL)
    _m.save(_EMBED_LOCAL)
    print("[SAM.spec] embedding model cached.")
datas += [(_EMBED_LOCAL, f"assets/models/embedding/{_EMBED_MODEL}")]

# Wake word model — gitignored (*.onnx) so it must exist locally at build time.
_wake_model = os.path.join(ROOT, "assets", "models", "hey_sam.onnx")
if not os.path.isfile(_wake_model):
    raise SystemExit(
        "assets/models/hey_sam.onnx is missing.\n"
        "It is excluded from git, so copy it into the build tree before "
        "running PyInstaller or the wake word will be dead in the installed app."
    )
datas += [("assets/models/hey_sam.onnx", "assets/models")]

# openwakeword ships melspectrogram.onnx / embedding_model.onnx as package data
datas += collect_data_files("openwakeword")
# faster-whisper ships the Silero VAD onnx as package data
datas += collect_data_files("faster_whisper")
datas += collect_data_files("certifi")
datas += collect_data_files("language_tags")   # edge-tts dependency
# RAG dependencies — package data for sentence-transformers and chromadb
datas += collect_data_files("sentence_transformers")
datas += collect_data_files("chromadb")
datas += collect_data_files("tokenizers")
datas += collect_data_files("transformers")
datas += collect_data_files("webview")

# ─── Native libraries ─────────────────────────────────────────────
# PyInstaller regularly misses these; without them Whisper and the wake word
# engine fail to import at runtime in the frozen app.
binaries = []
binaries += collect_dynamic_libs("ctranslate2")
binaries += collect_dynamic_libs("onnxruntime")
binaries += collect_dynamic_libs("sounddevice")   # portaudio

# ─── Hidden imports ───────────────────────────────────────────────
hiddenimports = [
    "win32com.client", "pythoncom", "pywintypes",
    "pyttsx3.drivers", "pyttsx3.drivers.sapi5",
    "comtypes.stream",
    "sounddevice", "_cffi_backend",
    "yaml", "requests", "charset_normalizer",
    "bottle", "proxy_tools", "pythonnet", "clr_loader",
]
hiddenimports += collect_submodules("pycaw")
hiddenimports += collect_submodules("webview")
# RAG submodules — explicitly collected since llm/rag.py imports lazily
hiddenimports += collect_submodules("sentence_transformers")
hiddenimports += collect_submodules("chromadb")
hiddenimports += collect_submodules("tokenizers")
hiddenimports += collect_submodules("huggingface_hub")
# Additional runtime submodules imported dynamically by chromadb
hiddenimports += ["onnxruntime", "posthog", "pypika", "tenacity"]

# NOTE: `anthropic` is deliberately absent. llm/claude_engine.py imports it
# lazily inside its methods and treats ImportError as "Claude unavailable", so
# the local-only build works without it. Add it here if you ship Claude support.

excludes = [
    # Exclude unused heavyweight dependencies
    # Note: scipy and av are required at runtime:
    #   scipy -> openwakeword dependency
    #   av    -> faster_whisper.audio module dependency
    # Note: torch is needed for sentence-transformers embedding runtime.
    "torchaudio",
    "pandas",
    "tkinter", "matplotlib", "IPython", "pytest", "notebook",
    "PySide6", "PyQt5",
    "PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtQml", "PyQt6.QtQuick", "PyQt6.Qt3DCore",
    "PyQt6.QtMultimedia", "PyQt6.QtBluetooth", "PyQt6.QtNetworkAuth",
    "PyQt6.QtPositioning", "PyQt6.QtSql", "PyQt6.QtTest",
]

# ─── SECURITY: never ship user secrets ────────────────────────────
# The repo root normally holds a real config.yaml (Spotify client id/secret)
# and a .cache file with a live Spotify OAuth token.
_FORBIDDEN_NAMES = {
    "config.yaml", ".cache", ".spotipyoauthcache",
    "spotify_token.json", "sam.log",
}
for _src, _dest in list(datas) + list(binaries):
    _base = os.path.basename(str(_src)).lower()
    if _base in _FORBIDDEN_NAMES:
        raise SystemExit(f"refusing to bundle user secret: {_src}")
    if "oauth" in _base or _base.endswith(".log"):
        raise SystemExit(f"refusing to bundle sensitive file: {_src}")


a = Analysis(
    ["main.py"],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SAM",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX corrupts onnxruntime / ctranslate2 DLLs — never enable it here.
    upx=False,
    console=False,          # background app; main.py guards sys.stdout is None
    disable_windowed_traceback=False,
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="SAM",
)
