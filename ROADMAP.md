<div align="center">

# 🗺️ SAM — Project Roadmap

**Development roadmap for SAM (Smart Assistant Module)**

[![Current Version](https://img.shields.io/badge/Current-v0.3.6-22c55e?style=flat-square)](#v036--custom-wake-word--brand-update-current-release)
[![Next Target](https://img.shields.io/badge/Next-v0.4.0-3b82f6?style=flat-square)](#v040--visual--workspace-intelligence-target-q3-2026)

</div>

---

## Vision & Development Philosophy

SAM is designed around three core pillars:

| Pillar | Principle |
|:---|:---|
| 🛡️ **Absolute Privacy** | Your data belongs to you. Audio capture, transcription, processing, and generation remain entirely local — no hidden telemetry or cloud leakage. |
| ⚡ **Zero-Latency Orchestration** | Direct desktop controls execute in milliseconds. The UI remains highly responsive, separating heavy model inference from visual loops. |
| 🧩 **Modular Extensibility** | Developers can extend SAM's features easily — adding custom commands, integrations, and local models. |

---

## Milestone Overview

```
v0.1.0 ──→ v0.2.0 ──→ v0.3.0 ──→ v0.3.6 (current) ──→ v0.4.0 ──→ v0.5.0 ──→ v0.6.0 ──→ v0.7.0 ──→ v1.0.0
 Core       Audio       LLM + UI    Wake Word Upgrade   Vision     Productivity  RAG        Ecosystem   Production
```

| Version | Status | Focus Area | Core Technologies |
|:---|:---|:---|:---|
| **v0.1.0** | ✅ Completed | Pipeline Architecture & GUI | PyQt6, keyboard hooks, mock engines |
| **v0.2.0** | ✅ Completed | Local Audio Processing | openwakeword, faster-whisper, edge-tts |
| **v0.3.0** | ✅ Completed | LLM Integration & System Tray | Ollama client, ctypes system commands, QSystemTrayIcon |
| **v0.3.6** | ✅ Completed | Custom Wake Word & Brand Update | `hey_sam` ONNX integration, Settings File Dialog, Dynamic CLI |
| **v0.4.0** | 📅 Planned | Visual & Workspace Intelligence | Local vision LLM, clipboard parsing, smart parser |
| **v0.5.0** | 📅 Planned | Desktop Productivity Suite | Local scheduler, calendar hooks, summarizers |
| **v0.6.0** | 📅 Planned | Local Knowledge Base & RAG | ChromaDB, local embeddings, PDF/markdown indexer |
| **v0.7.0** | 📅 Planned | Customization & Ecosystem | Dynamic plugins, custom wake words, multi-platform |
| **v1.0.0** | 📅 Planned | Production Release | NSIS packaging, offline TTS, auto-updater |

---

## Completed Versions

### v0.1.0 — Core Proof of Concept

> Established the foundation of the assistant, focusing on UI response times and event loops.

- [x] **PyQt6 Floating Bar UI** — Frameless, transparent floating overlay with smooth slide-in / slide-out animations
- [x] **Global Keyboard Hooks** — `keyboard` library for global hotkeys (`Ctrl + Space`)
- [x] **Mock Engine Simulators** — Simulated transcription and generation loops for event transition testing
- [x] **State Machine** — Centralized state management in `AppController` (`STATE_IDLE`, `STATE_LISTENING`, `STATE_THINKING`, `STATE_SPEAKING`)

---

### v0.2.0 — Local Audio Pipeline

> Replaced mock modules with local audio capturing, processing, and synthesis.

- [x] **Continuous Wake Word Detection** — Daemon thread running `openwakeword` with TensorFlow Lite inference
- [x] **Voice Activity Detection (VAD)** — Energy-based VAD in `audio/recorder.py` using NumPy RMS analysis with automatic silence detection
- [x] **Fast Local Transcription (STT)** — CTranslate2-based `faster-whisper` with `int8` quantization for offline speech-to-text
- [x] **Voice Synthesis (TTS)** — `edge-tts` integration for high-fidelity, natural voice responses
- [x] **Audio Level Visualization** — Custom `QPainter` widget drawing real-time waveform bars from microphone input

---

### v0.3.6 — Custom Wake Word & Brand Update *(Current Release)*

> Rebranded default wake word to "Hey Sam" using a custom-trained model and upgraded Settings UI.

- [x] **"Hey Sam" Wake Word Model** — Replaced default "Hey Jarvis" with custom-trained `hey_sam.onnx` under `assets/models/`
- [x] **Custom Wake Word File Dialog** — Interactive "Browse..." button added in Settings Window to load any openWakeWord `.onnx` or `.tflite` model
- [x] **Dynamic CLI Instructions** — Terminal instructions dynamically formatting the wake word name and version
- [x] **Default Code Cleanup** — Version defaults moved from `0.3.5` to `0.3.6` across the codebase

---

### v0.3.0 — Local LLM Integration & Desktop Automation *(Previous Release)*

> Enabled generative capabilities, native system automation, and user-friendly system tray.

- [x] **Local LLM Integration** — Ollama APIs with lightweight models (`qwen2.5:3b`, `llama3.2:3b`) and context memory
- [x] **Instant Command Router** — Regex pattern matching bypasses LLM token latency for system actions (< 10 ms)
- [x] **Native OS Automation:**
  - [x] App launcher and process terminator
  - [x] Volume adjustments (mute, scaling) via Windows `user32` virtual key codes / `ctypes`
  - [x] Media control keys (play, pause, next, previous)
  - [x] Power management (lock, shutdown, restart, cancel)
  - [x] Snipping Tool trigger
  - [x] Local browser search queries
- [x] **Automatic Code Generation** — Parser extracts markdown code blocks from LLM responses and auto-saves to Desktop
- [x] **System Tray Icon** — `QSystemTrayIcon` for background operation with quick menu controls
- [x] **Settings Dashboard** — Dark-themed Qt Settings Dialog with dynamic config persistence

---

## Planned Milestones

### v0.4.0 — Visual & Workspace Intelligence *(Target: Q3 2026)*

> Expanding SAM's inputs to include screen context and clipboard data.

**Screen Awareness**
- [ ] Implement screen capture command (e.g., *"SAM, analyze my screen"*)
- [ ] Feed images to a local vision model (`llava`, `minicpm-v`) via Ollama
- [ ] Enable multi-modal questions (*"What error code is in this terminal?"*)

**Clipboard Integration**
- [ ] Clipboard listener for text hooks on activation with modifier key
- [ ] Quick actions: *"explain this code"*, *"translate this text"* using copied content

**Smart Code File Naming**
- [ ] LLM-generated meaningful filenames for saved scripts (e.g., `basic_movement.cs` instead of `code_20260615_1652.cs`)
- [ ] Desktop notifications pointing to created files

**Multi-Language STT**
- [ ] Language auto-detection or quick UI tray toggling
- [ ] Optimized Whisper parameters for non-English command vocabularies

---

### v0.5.0 — Desktop Productivity Suite *(Target: Q4 2026)*

> Transforming SAM into an active productivity companion.

**Scheduling & Alarms**
- [ ] Voice-triggered reminders (*"remind me to check the oven in 15 minutes"*)
- [ ] Background scheduler thread with desktop notifications and audio chimes

**Calendar Integration**
- [ ] Parse and display daily agendas from local `.ics` files or Outlook calendars

**Meeting Summarizer**
- [ ] Continuous audio recording mode with noise cleaning and local model summarization

**Email Drafting**
- [ ] Natural language email drafts saved to clipboard or opened in default email client

---

### v0.6.0 — Local Knowledge Base & RAG *(Target: Q1 2027)*

> Grounding the conversational engine in the user's personal documents.

**Vector Database**
- [ ] Bundle a lightweight vector DB (ChromaDB or LanceDB) with the installation

**Document Parser**
- [ ] Background indexers for markdown, text files, and PDFs in configured workspaces
- [ ] Local embedding models (`nomic-embed-text`) via Ollama for semantic representations

**Context-Grounded Q&A**
- [ ] Retrieval-Augmented Generation (RAG) — *"What were my notes on the API design?"* retrieves relevant blocks and injects them into the LLM prompt

**Web Search Integration**
- [ ] Local DuckDuckGo scraping for real-time fact retrieval and summary synthesis

---

### v0.7.0 — Customization & Ecosystem *(Target: Q2 2027)*

> Opening the architecture for community plugins and custom configurations.

**Dynamic Plugin Loader**
- [ ] Standard plugin templates (`BasePlugin`) with lifecycle hooks
- [ ] `/plugins` directory scanning at startup — no core file editing required

**Custom Wake Word Training**
- [x] Templates and scripts for training custom `openwakeword` models (*"Hey SAM"*, *"Computer"*) using personal recordings

**Multi-Platform Support**
- [ ] Port `commands/system.py` to Linux (DBus / systemd / amixer) and macOS (AppleScript / PyObjC)

**Offline TTS**
- [ ] Fully offline speech synthesis via [Piper](https://github.com/rhasspy/piper) or [Kokoro](https://github.com/hexgrad/Kokoro) — removes `edge-tts` server dependency

---

### v1.0.0 — Production Release *(Target: Q3 2027)*

> Stable, optimized, and easy to install for end users.

**Native Installers**
- [ ] Windows: NSIS installer with all model binaries and pre-compiled libraries
- [ ] Linux: `.deb` and `.rpm` packages
- [ ] macOS: Signed `.dmg` bundles

**Auto-Updater**
- [ ] Secure, local-check auto-update for code patches and model updates

**First-Run Setup Wizard**
- [ ] Guided wizard for audio device selection, Ollama availability check, model downloads, and microphone calibration

**Benchmarking Suite**
- [ ] Performance tests for memory consumption and CPU usage across platforms

---

## Long-Term Vision

Beyond v1.0.0, SAM will evolve from a passive command executor into a **fully autonomous local agent** capable of multi-step desktop reasoning. We envision SAM utilizing local agentic frameworks (LangChain, LangGraph) to manage directories, coordinate complex workflows, and learn from user interactions — all while maintaining strict local-only privacy guarantees.

---

## Contributing to the Roadmap

We believe the best roadmap is built with the community. If you have feature requests, architectural suggestions, or want to help implement planned milestones:

1. **Submit an Issue** — Describe the feature, its value, and how it aligns with SAM's local-first philosophy
2. **Join RFC Discussions** — Participate in architectural design discussions (RAG setups, plugin loaders, etc.)
3. **Submit a PR** — Check the issue board for tasks marked `help wanted` or `good first issue`

---

<div align="center">

**Keep your data local. Keep your control native.**

*Built with passion. 🖤*

</div>
