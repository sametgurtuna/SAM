<div align="center">

<img src="assets/sam-logo.png" alt="SAM Logo" width="120" />

# SAM — Smart Assistant Module

### The Local, Privacy-First, Zero-Latency Desktop Voice Companion

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e.svg?style=for-the-badge)](LICENSE)
[![Powered by Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-1a1a2e.svg?style=for-the-badge&logo=ollama)](https://ollama.ai)
[![UI: PyQt6](https://img.shields.io/badge/UI-PyQt6-41cd52.svg?style=for-the-badge&logo=qt)](https://www.riverbankcomputing.com/software/pyqt/)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-0078D6.svg?style=for-the-badge&logo=windows)](https://www.microsoft.com/windows)

> Your data is yours alone. SAM brings the power of modern Large Language Models and Voice Recognition directly to your desktop — with **zero cloud dependencies**, **zero telemetry**, and **zero latency constraints**. Fully offline, highly performant, and deeply integrated into your operating system.

---

[📖 Architecture](docs/ARCHITECTURE.md) · [⚙️ Configuration](#-configuration-deep-dive) · [🗺️ Roadmap](ROADMAP.md) · [📦 Setup Guide](setup.md) · [🤝 Contributing](#-contributing--code-of-conduct)

</div>

---

## Table of Contents

- [Philosophy & Vision](#-philosophy--vision)
- [Key Architecture & Features](#-key-architecture--features)
- [Local vs Cloud Comparison](#-the-sam-advantage-local-vs-cloud)
- [Hardware Recommendations](#-hardware-recommendations--benchmarks)
- [Prerequisites & System Setup](#-prerequisites--system-setup)
- [Installation Guide](#-installation-guide)
- [Usage Guide](#-usage-guide--interface-interaction)
- [Command Reference](#-comprehensive-command-reference)
- [Configuration Deep-Dive](#-configuration-deep-dive)
- [Developer Guide: Custom Commands](#-developer-guide-writing-custom-commands)
- [Troubleshooting](#-troubleshooting--diagnostics-matrix)
- [Project Structure](#-project-directory-layout)
- [Roadmap](#-roadmap)
- [Security & Privacy](#-security--privacy-audit-pledge)
- [Contributing](#-contributing--code-of-conduct)
- [License](#-license)

---

## 🌟 Philosophy & Vision

In an era where voice assistants listen constantly to harvest data, sell advertisements, and train proprietary cloud models, **SAM was built with a radical premise: What if your AI lived entirely on your hardware?**

SAM (Smart Assistant Module) is an open-source, highly optimized desktop companion designed to bridge the gap between local generative models and your operating system. It runs quietly in the background as a multi-threaded system service, monitoring the audio input buffer using localized TensorFlow Lite wake word models.

When summoned via the voice wake word or global keyboard hooks, SAM renders a hardware-accelerated, transparent PyQt6 visual overlay. It transcribes user speech using optimized CTranslate2 Whisper models, dynamically cleans input via spectral noise gating, and routes commands through an instantaneous regex execution router. If the request is conversational, SAM feeds it to a local Ollama instance with a custom system prompt, generating streaming responses in real time.

> **SAM does not require an active internet connection.** It safeguards your personal workspace while giving you developer-level control over your operating system.

---

## ✨ Key Architecture & Features

SAM is designed for power users who demand an autonomous desktop assistant that respects system resources.

### 🛡️ Absolute Privacy & Local Execution

| Capability | Details |
|:---|:---|
| Zero Cloud Leakage | No telemetry, no usage analytics, no remote data transfers |
| Offline TTS / STT | Audio processing, wake-word validation, noise removal, and transcription happen entirely on local CPU/GPU buffers |
| Local Context Database | Conversational memories are kept in volatile local RAM deques — no persistent cloud tracking |

### 🎙️ Advanced Audio DSP Pipeline

| Component | Technology | Description |
|:---|:---|:---|
| Wake Word Detection | `openwakeword` + TFLite | Real-time inference over a sliding audio buffer with negligible CPU utilization |
| Voice Activity Detection | NumPy RMS Analysis | Dynamically adjusts recording duration; stops precisely when you finish speaking |
| Spectral Noise Gate | `noisereduce` | Subtracts stationary environmental noise (fans, HVAC, wind) prior to transcription |

### ⚡ High-Performance Whisper Engine (STT)

- **CTranslate2 Optimization** — Uses `faster-whisper` with `int8` quantization, reducing model sizes by **4×** and increasing transcription speeds up to **400%** compared to standard PyTorch wrappers.
- **Accent & Dialect Biasing** — Custom `initial_prompt` seeding inside the decoding loop biases the transformer toward command vocabularies, eliminating phonetic errors from non-native accents.

### 💻 Instant OS Command Routing

- **Direct Subprocess / API Hooks** — For core intents (launching software, volume control, media playback, system lock), the Command Router triggers Windows API Virtual Key Codes, `ctypes`, or system process managers within **3–10 ms**.
- **Zero LLM Token Costs** — Bypassing the local LLM for simple actions saves battery, CPU cycles, and VRAM.

### 🧠 Dynamic Conversational LLM Engine

- **Ollama Integration** — Natively interfaces with Ollama's local HTTP endpoints, supporting models such as `qwen2.5:3b`, `llama3.2:3b`, `gemma2:2b`, and larger parameter networks.
- **Conversational Memory** — A rolling conversational history preserves context for multi-turn dialogues.
- **API Fallbacks** — Optionally configures fallback modules to connect to Claude (Anthropic) or GPT (OpenAI) for external reasoning.

### 🎨 Modern, Fluid Overlay & Settings UI

- **PyQt6 Overlay** — Frameless, click-through-capable floating window anchored to the lower desktop margin.
- **Dynamic Waveform Visualizer** — High-framerate sinusoidal and block audio waves mapping microphone amplitude to visual states.
- **System Tray** — Right-click for quick toggles (Mute, Clear Context); double-click to open the Settings Dashboard.
- **Settings Interface** — Sleek, dark-themed sidebar UI to configure hotkeys, LLM parameters, Spotify API keys, and UI aesthetics — no `.yaml` editing required.

---

## ⚖️ The SAM Advantage: Local vs Cloud

| Metric | SAM (100% Local) | Commercial Assistants | Cloud LLM APIs |
|:---|:---|:---|:---|
| **Privacy** | Absolute — zero external data transfer | Poor — continuous voice harvesting | Moderate — subject to API data policies |
| **System Integration** | Deep — controls registry, tasks, & local APIs | None — limited to smart-home ecosystems | None — restricted to sandbox environments |
| **Command Latency** | **3–10 ms** (instant local routing) | 1500–3000 ms (cloud roundtrip) | 1000–2000 ms (API request overhead) |
| **Cost** | Free forever — zero token fees | Indirect — proprietary hardware lock-in | Pay-per-token — accumulates fast |
| **Offline Support** | ✅ Fully operational without internet | ❌ Fails without network | ❌ Fails without network |
| **Customizability** | Total — open-source modular Python | Locked — no backend access | Limited — restricted to model prompts |

---

## 💻 Hardware Recommendations & Benchmarks

### Hardware Profiles

| Profile | CPU / GPU | RAM | Recommended Models | Expected Latency |
|:---|:---|:---|:---|:---|
| **Ultra-Light** | Intel i3 (10th Gen) / Ryzen 3 | 8 GB | STT: `tiny` · LLM: `gemma2:2b` (CPU) | ~2.5–3.5 s |
| **Standard** ⭐ | Intel i5 / Ryzen 5 | 16 GB | STT: `base` or `small` · LLM: `qwen2.5:3b` | ~0.8–1.5 s |
| **Pro / Creator** | Intel i7 / Ryzen 7 + RTX 3060+ | 16+ GB | STT: `small` (CUDA) · LLM: `qwen2.5:7b` (GPU) | **~0.2–0.5 s** |

### Resource Consumption (Idle)

| Mode | CPU | RAM |
|:---|:---|:---|
| Wake Word Detection | ~1.2% | ~110 MB |
| Active Transcription (STT Base) | Variable | ~350 MB |
| Active Conversation (Ollama) | Variable | Depends on model (e.g. Qwen 3B ≈ 2.2 GB) |

---

## 📦 Prerequisites & System Setup

### Operating System

| OS | Status | Notes |
|:---|:---|:---|
| **Windows 10/11** | ✅ Primary | Native virtual keycodes, taskkill commands, process handlers |
| **Linux** | ✅ Supported | Requires `portaudio19-dev`; X11 or Wayland-Xwayland compositor |
| **macOS** | ✅ Supported | Requires system accessibility permissions for keyboard shortcuts |

### Python Environment

- **Python 3.11** or **3.12** recommended. Some libraries (`openwakeword`) require specific TensorFlow/TFLite wheels most stable on these versions.

### Core External Dependencies

| Dependency | Purpose | Installation |
|:---|:---|:---|
| [Ollama](https://ollama.com) | Local LLM routing | Download from official website |
| [FFmpeg](https://ffmpeg.org) | Audio resampling for `faster-whisper` | Windows: `choco install ffmpeg` or `winget install Gstreamer.FFmpeg` <br> macOS: `brew install ffmpeg` <br> Linux: `sudo apt install ffmpeg` |

> **Important:** Ensure FFmpeg is added to your system `PATH`.

---

## 🚀 Installation Guide

> **Quick Start:** For a detailed, step-by-step walkthrough with troubleshooting, see the [Setup Guide](setup.md).

### 1. Clone the Repository

```bash
git clone https://github.com/sametgurtuna/SAM.git
cd SAM
```

### 2. Create a Virtual Environment

```bash
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Pull the Local LLM

Start the Ollama daemon, then pull your desired model:

```bash
ollama pull qwen2.5:3b
```

> **Tip:** Low on resources? Try `gemma2:2b`. Have 8 GB+ VRAM? Try `qwen2.5:7b` or `llama3.1:8b`.

### 5. Launch SAM

```bash
python main.py
```

On first launch, SAM automatically downloads the Whisper transcription model and the wake word model. This is a one-time process.

---

## 🎮 Usage Guide & Interface Interaction

Once initiated, SAM operates as a background task:

### Initialization Flow

```
Startup → Load config.yaml → Discover Audio Devices → Lazy-load Models → Enter Wake Word Monitor (Idle)
```

### Triggering the Assistant

| Method | How |
|:---|:---|
| 🎤 **Voice** | Say **"Hey Jarvis"** clearly. The wake word thread registers the phonetic pattern and activates the system. |
| ⌨️ **Keyboard** | Press **`Ctrl + Space`** globally (from any window) to bypass wake-word detection and open the mic buffer immediately. |

### UI States

| State | Behavior |
|:---|:---|
| **Idle** | UI hidden. SAM consumes negligible CPU while waiting for a trigger. |
| **Listening** | A sleek bar slides onto the bottom of the screen with an animated audio visualizer. |
| **Transcribing** | The visualizer shifts to a smooth loading animation while Whisper processes your speech. |
| **Responding** | Text streams onto the overlay in real time (LLM) or a command status is displayed (instant). |
| **Settings** | Double-click the system tray icon to open the full Settings Dashboard. |

---

## ⌨️ Comprehensive Command Reference

If SAM's transcription matches any of the patterns below, it intercepts the instruction and executes it locally — bypassing the LLM entirely.

### 🖥️ App Control

| Intent | Example Commands | OS Action |
|:---|:---|:---|
| **Launch** | `"open spotify"`, `"run chrome"`, `"launch notepad"` | Scans registry/environment paths to spawn the application |
| **Terminate** | `"close discord"`, `"kill steam"`, `"exit word"` | Forcefully terminates the process tree |

### 🔊 System & Media

| Intent | Example Commands | OS Action |
|:---|:---|:---|
| **Set Volume** | `"set volume to 50"`, `"volume 30 percent"` | PowerShell COM objects set absolute level |
| **Volume Up** | `"volume up"`, `"louder"`, `"volume up 20"` | Increases by specified or default 10% step |
| **Volume Down** | `"volume down"`, `"quieter"`, `"volume down 15"` | Decreases by specified or default 10% step |
| **Mute / Unmute** | `"mute"`, `"unmute"`, `"silence"` | Emits `VK_VOLUME_MUTE` (0xAD) |
| **Spotify Play** | `"play blinding lights on spotify"` | Spotipy API queries track ID and plays directly ¹ |
| **Media Playback** | `"play"`, `"pause"`, `"resume"` | Emits `VK_MEDIA_PLAY_PAUSE` (0xB3) |
| **Track Control** | `"next track"`, `"previous track"`, `"skip"` | Emits `VK_MEDIA_NEXT_TRACK` / `VK_MEDIA_PREV_TRACK` |

> ¹ Requires configuring Spotify Client ID / Secret via the Settings UI (Integrations tab).

### 🖥️ OS Session

| Intent | Example Commands | OS Action |
|:---|:---|:---|
| **Minimize All** | `"minimize all"`, `"show desktop"` | Triggers `Win + D` |
| **Lock Device** | `"lock screen"`, `"lock pc"` | Invokes `LockWorkStation` API |
| **Shutdown** | `"shutdown computer"`, `"turn off machine"` | 30-second countdown → `shutdown /s /t 30` |
| **Restart** | `"restart computer"`, `"reboot"` | 30-second countdown → `shutdown /r /t 30` |
| **Cancel** | `"cancel shutdown"`, `"stop reboot"` | Aborts with `shutdown /a` |

### 🌐 Web & Search

| Intent | Example Commands | OS Action |
|:---|:---|:---|
| **URL Navigation** | `"go to github.com"` | Opens URL in default browser |
| **Web Search** | `"search for local weather"`, `"google python"` | Formulates query and opens in default browser |

---

## ⚙️ Configuration Deep-Dive

All settings are exposed through `config.yaml` in the project root. Below is a fully annotated reference:

```yaml
# ═══════════════════════════════════════════════════════════════════
# SAM — Core Configuration
# ═══════════════════════════════════════════════════════════════════

app:
  name: "SAM"
  version: "0.3.5"
  debug: false                    # Enable raw audio energy and model logs to stdout

hotkey:
  trigger: "ctrl+space"           # Global shortcut to activate listening

# ── Audio Pipeline ───────────────────────────────────────────────
audio:
  sample_rate: 16000              # Required by Whisper / openwakeword (16 kHz)
  channels: 1                     # Mono — mandatory for DSP models
  chunk_size: 1024                # Buffer block size (lower = less latency, more CPU)
  silence_threshold: 350          # RMS threshold — below this is considered silence
  silence_duration_ms: 1800       # ms of silence before auto-transcription triggers
  max_record_seconds: 30          # Hard cutoff to prevent memory bloat
  noise_reduction:
    enabled: true                 # Spectral noise subtraction via noisereduce
    prop_decrease: 0.8            # Noise reduction ratio (0.0–1.0)
    n_fft: 512                    # FFT block size for noise profiling

# ── Wake Word ────────────────────────────────────────────────────
wake_word:
  model: "hey_jarvis"             # Wake-word model (.tflite, cached locally)
  threshold: 0.5                  # Confidence limit (lower for easier activation)
  check_interval_ms: 100          # Inference interval (smaller = faster, more CPU)

# ── Speech-to-Text ───────────────────────────────────────────────
stt:
  model: "small"                  # Options: tiny, base, small, medium, large-v3
  device: "cpu"                   # Compute device: cpu, cuda, or auto
  compute_type: "int8"            # Quantization: int8 (CPU), float16 (CUDA)
  language: "en"                  # ISO 639-1 code — prevents hallucinations
  beam_size: 5                    # Beam search width (higher = better quality, slower)
  initial_prompt: >-              # Decoder bias toward OS commands
    open spotify, close, volume up, volume down,
    mute, lock screen, shutdown, search for

# ── LLM Engine ───────────────────────────────────────────────────
llm:
  engine: "ollama"                # Primary: ollama | anthropic | openai
  context_window: 5               # Rolling memory — previous message cycles
  system_prompt: >-
    You are SAM, a fast, concise, and helpful desktop voice assistant.
    The user is speaking to you. Respond directly in a conversational,
    friendly manner. Keep your answers short, clear, and action-oriented.
    Do not write markdown formatting in your response.
  ollama:
    base_url: "http://localhost:11434"
    model: "qwen2.5:3b"           # Model pulled via `ollama pull`
    temperature: 0.7              # 0.0 (factual) → 1.0 (creative)
    max_tokens: 200               # Token cap for concise replies
  fallback:
    anthropic_key: ""             # Optional cloud fallback
    openai_key: ""                # Optional cloud fallback
```

---

## 🛠️ Developer Guide: Writing Custom Commands

SAM's modular architecture makes it straightforward to add new OS capabilities or custom macro routines.

### Step 1 — Define Intent Patterns

Add regex patterns in the Command Router module:

```python
# Türkçe / İngilizce VS Code açma intent'i
VSCODE_PATTERNS = [
    r"\bopen (vscode|vs code|code)\b",
    r"\b(vscode|kod) aç\b"
]
```

### Step 2 — Implement the Handler

Create a function in the `commands/` directory (e.g., `commands/vscode_control.py`):

```python
import subprocess
import os

def launch_vscode_at_project(project_path=None):
    """
    VS Code'u başlatır. Opsiyonel olarak bir proje dizini açar.
    """
    # Proje dizinini doğrula ve VS Code'u başlat
    try:
        command = ["code"]
        if project_path and os.path.exists(project_path):
            command.append(project_path)

        # UI kilitlenmesini önlemek için subprocess.Popen kullanıyoruz
        subprocess.Popen(command, shell=True)
        return "Visual Studio Code başarıyla başlatıldı."
    except Exception as e:
        return f"VS Code başlatılırken hata oluştu: {str(e)}"
```

### Step 3 — Register in the Router

Inside the main command router execution loop:

```python
for pattern in VSCODE_PATTERNS:
    if re.search(pattern, transcript_lowercase):
        # Varsayılan çalışma dizinini aç veya sadece VS Code başlat
        response = launch_vscode_at_project("C:\\Users\\samet\\Desktop\\SAM")
        return True, response
```

---

## 🚑 Troubleshooting & Diagnostics Matrix

| Symptom | Probable Cause | Resolution |
|:---|:---|:---|
| `No LLM engine found` | Ollama is offline or model not pulled | 1. Ensure Ollama is running in system tray <br> 2. Run `ollama run qwen2.5:3b` to verify <br> 3. Check `llm.ollama.base_url` matches port `11434` |
| Wake word doesn't trigger | Mic not active, low volume, or high threshold | 1. Verify input device in OS sound settings <br> 2. Set `app.debug: true` to monitor audio energy <br> 3. Lower `wake_word.threshold` to `0.35` |
| Whisper outputs gibberish | Processing silent ambient noise | 1. Increase `audio.silence_threshold` <br> 2. Ensure `noise_reduction.enabled: true` <br> 3. Set `stt.language` explicitly |
| `PortAudio` crash | PortAudio libraries missing | Windows: `pip install pipwin && pipwin install pyaudio` <br> Linux: `sudo apt install portaudio19-dev python3-pyaudio` |
| `Ctrl + Space` not working | Keyboard hook lacks permission | Run terminal / IDE as **Administrator** |
| CUDA error or slow STT | GPU drivers missing or CPU fallback | 1. Install CUDA Toolkit + cuDNN <br> 2. Set `stt.device: "cuda"` and `compute_type: "float16"` |

---

## 📂 Project Directory Layout

```
SAM/
├── assets/                       # Icons, sound chimes, static visual elements
├── audio/                        # Audio pipeline core
│   ├── wake_word.py              #   openwakeword detection thread (TFLite)
│   └── recorder.py               #   Voice Activity Detector (VAD) & recording
├── commands/                     # Direct OS command triggers
│   ├── system.py                 #   Windows user32, shell keycodes, power mgmt
│   └── router.py                 #   Regex-based intent routing
├── core/                         # Core application logic
│   ├── app.py                    #   AppController — central state machine
│   ├── stt.py                    #   Speech-to-Text engine
│   └── code_parser.py            #   LLM code block extractor
├── docs/                         # Developer documentation
│   └── ARCHITECTURE.md           #   Threading, design patterns, class reference
├── llm/                          # Generative LLM interfaces
│   ├── ollama_client.py          #   Local Ollama stream handler
│   └── cloud_fallbacks.py        #   Anthropic / OpenAI backup
├── logs/                         # Local diagnostic logs
├── ui/                           # Graphical interface
│   ├── floating_bar.py           #   PyQt6 frameless overlay bar
│   └── waveform.py               #   Audio level visualizer widget
├── config.yaml                   # Master configuration
├── main.py                       # Application entry point
├── requirements.txt              # Python dependencies
├── setup.md                      # Detailed setup guide
├── ROADMAP.md                    # Development roadmap
└── README.md                     # ← You are here
```

---

## 🗺️ Roadmap

SAM is under active development. See the full [Roadmap](ROADMAP.md) for detailed milestone plans.

**Upcoming highlights:**

| Milestone | Focus |
|:---|:---|
| **v0.4.0** | Visual & Workspace Intelligence — screen awareness, clipboard integration |
| **v0.5.0** | Desktop Productivity Suite — scheduling, calendar, meeting summarizer |
| **v0.6.0** | Local Knowledge Base & RAG — vector DB, document indexing |
| **v0.7.0** | Customization & Ecosystem — dynamic plugins, custom wake words, multi-platform |
| **v1.0.0** | Production Release — native installers, offline TTS, auto-updater |

---

## 🛡️ Security & Privacy Audit Pledge

SAM is built for users who prioritize privacy. The codebase maintains the following standards:

1. **No External Networking** — SAM does not connect to the internet unless configured for third-party fallback APIs (OpenAI, Anthropic). With local models, your network interface can be disabled and SAM remains fully operational.
2. **Local Audio Buffering** — Voice recordings are processed in-memory as NumPy arrays. They are cleared immediately after transcription and **never saved to disk**.
3. **Open-Source Auditing** — All subprocess calls, shell executions, and API requests are written in clear Python code. We encourage independent security audits.

---

## 🤝 Contributing & Code of Conduct

Contributions are welcome! Follow these steps:

1. **Fork** the repository and clone your fork locally
2. **Create a feature branch:** `git checkout -b feature/amazing-feature`
3. **Commit** your changes with clear, descriptive messages
4. **Push** to your fork: `git push origin feature/amazing-feature`
5. **Open a Pull Request** describing your changes and testing procedures

### Code Style

| Scope | Convention |
|:---|:---|
| Code formatting | PEP 8 |
| Documentation & README files | English |
| In-line code comments (`.py`) | Turkish (per project rules) |

---

## 📜 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Keep your data local. Keep your control native.**

*Built with passion. 🖤*

</div>
