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
    ("config.example.yaml", "."),
]

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
]
hiddenimports += collect_submodules("pycaw")

# NOT: collect_submodules("openwakeword") KULLANILMIYOR. openwakeword'un
# egitim/torch tabanli alt modullerini de topluyor ve pakete 320 MB torch
# ekliyordu. audio/wake_word.py inference_framework="onnx" ile calisiyor,
# yani calisma zamaninda torch'a hic ihtiyac yok.

# NOTE: `anthropic` is deliberately absent. llm/claude_engine.py imports it
# lazily inside its methods and treats ImportError as "Claude unavailable", so
# the local-only build works without it. Add it here if you ship Claude support.

excludes = [
    # SAM'in kodunun hicbiri bunlari import etmiyor; hepsi gecisli bagimlilik
    # olarak geliyordu ve pakete ~460 MB ekliyorlardi.
    #   torch/torchvision : openwakeword'un opsiyonel torch backend'i.
    #                       inference_framework="onnx" kullandigimiz icin
    #                       calisma zamaninda hic gerekmiyor (~330 MB).
    # DIKKAT: scipy ve av BURAYA EKLENMEZ. Ikisi de dolayli ama ZORUNLU:
    #   scipy -> openwakeword import ederken gerekiyor
    #   av    -> faster_whisper.audio modul seviyesinde import ediyor
    # Bunlari dislamak wake word ve STT'yi frozen build'de sessizce oldurur.
    "torch", "torchvision", "torchaudio",
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
