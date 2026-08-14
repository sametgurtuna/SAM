<div align="center">

# Changelog

All notable changes to **SAM** are documented in this file.

<img src="https://img.shields.io/badge/Keep%20a%20Changelog-1.1.0-e05735?style=flat-square" alt="Keep a Changelog">
<img src="https://img.shields.io/badge/SemVer-2.0.0-3776AB?style=flat-square" alt="Semantic Versioning">
<img src="https://img.shields.io/badge/Current-v0.4.7-22c55e?style=flat-square" alt="Current version">

</div>

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and SAM
follows [Semantic Versioning](https://semver.org/) once it reaches 1.0. Until then,
minor versions (`0.x.0`) may include breaking config or behavior changes. See
[ROADMAP.md](ROADMAP.md) for what is planned next.

---

## At a glance

| Version | Date | Highlight |
|:---|:---|:---|
| [Unreleased](#unreleased) | - | Screen/clipboard awareness, plugin system |
| [0.4.7](#047---2026-08-14) | 2026-08-14 | Major UI Revamp: Cyberpunk Dark Webview, Live Mic EQ, Ollama Tester & Smart Hotkeys |
| [0.4.6](#046---2026-08-13) | 2026-08-13 | Editable instant responses & a rebuilt settings window |
| [0.4.5](#045---2026-08-13) | 2026-08-13 | Instant predefined responses & zero-LLM command dispatch |
| [0.4.4](#044---2026-08-13) | 2026-08-13 | Real-time speech transcription & bilingual command routing fixes |
| [0.4.3](#043---2026-08-12) | 2026-08-12 | Fenerbahce RAG accuracy fixes (multilingual embeddings, strict grounding) |
| [0.4.2](#042---2026-08-11) | 2026-08-11 | Intent classification, RAG, conversation modes |
| [0.4.1](#041---2026-08-11) | 2026-08-11 | The always-on orb, typed input, installer |
| [0.3.6](#036---2026-07-09) | 2026-07-09 | Custom "Hey Sam" wake word |
| [0.3.5](#035---2026-07-07) | 2026-07-07 | Router & VAD performance pass |
| [0.3.0](#030---2026-07-07) | 2026-07-07 | Initial public release |

---

## [Unreleased]

Tracked in [ROADMAP.md](ROADMAP.md) - screen/clipboard awareness, productivity
features (reminders, scheduling), a plugin system, and a cross-platform command layer
are next up.

---

## [0.4.7] - 2026-08-14

> **Major UI Revamp: Cyberpunk Dark Webview Architecture, Live Diagnostics, and Native Windows Integration.**

### Added
- **Modern Webview Settings UI (Edge WebView2)**: Replaced PyQt's legacy QSS raster engine with a high-performance, pixel-perfect HTML5/CSS3/JS Webview interface. Powered by `pywebview` utilizing native Windows Edge Chromium for minimal memory overhead.
- **Cyberpunk Dark Design System**: Glassmorphism cards with `backdrop-filter: blur(12px)`, `#00D4AA` neon teal and `#38F2D8` accents, animated smooth pill toggle switches, and JetBrains Mono code styling.
- **Live Microphone & Audio Spectrum Tester**: Integrated Web Audio API frequency visualizer directly into the Speech tab with real-time 60 FPS equalizer bars and live input volume measurement.
- **Interactive Ollama Latency & Model Detector**: Built-in ping tool with roundtrip latency metrics (e.g. `Connected - 9ms`) and auto-discovery of locally installed LLM models directly populating the model selector.
- **Smart Interactive Hotkey Recorder**: Click-to-record voice and text shortcut fields with automatic modifier key capture and visual keycap badges.
- **Interactive Canvas Orb Preview**: Real-time breathing preview in the Appearance tab reacting dynamically to Diameter, Ring Width, and Opacity sliders.
- **Windows Single-Instance Mutex & Focus**: Integrated Windows Named Mutex (`SAM_Settings_Window_Mutex`) and Win32 `FindWindowW` / `SetForegroundWindow` API preventing duplicate settings windows and bringing existing window to front on repeated tray clicks.
- **Native AppUserModelID & Taskbar Branding**: Fixed Python taskbar grouping via `SetCurrentProcessExplicitAppUserModelID` and Windows `WM_SETICON`, giving SAM a dedicated taskbar identity with SAM's real logo.

### Changed
- **Fixed Golden Ratio Window Layout**: Locked settings window to a crisp `1020x690` resolution (`resizable=False`) preventing button clipping and awkward text wrapping.
- **Scrollbar Elimination**: Completely removed unsightly browser scrollbars while keeping mousewheel and touch navigation smooth.

---

## [0.4.6] - 2026-08-13

> **Instant responses you can actually edit, and a settings window that looks the part.**

### Added
- **Editable Instant Responses**: on first launch SAM now copies `knowledge/instant_responses.yaml` into the writable data directory (`%APPDATA%\SAM\knowledge\` in an installed build) and reads it from there, exactly like `config.yaml`.
- **Responses settings page**: a new sidebar page with an enable toggle, the resolved file path, **Edit Responses**, **Show Folder**, and **Reload** which re-reads the file into the running app without restarting SAM.
- **Live Transcription settings**: `stt.partial_model` and `stt.partial_interval_ms` are now editable from the Speech page instead of `config.yaml` only.
- **About page**: shows developer details, a GitHub link, and on-disk locations of config, logs and models, with an **Open Data Folder** button.

### Changed
- **Settings window redesign**: larger layout with a header and version pill, per-page titles and descriptions, card-style sections, and restyled controls.

### Fixed
- Buttons nested inside a settings page could render invisible due to inherited viewport styles. Scoped styles directly to the viewport.

---

## [0.4.5] - 2026-08-13

> **Instant responses and a fast command path skipping the LLM.**

### Added
- **Instant Responses**: a new `knowledge/instant_responses.yaml` file with ~130 predefined TR/EN phrases (greetings, thanks, time/date, small talk). A match is a fast dictionary lookup (`commands/instant.py`).
- **Fast Command Path**: recognized system commands and instant responses now skip the `THINKING` state entirely: `AppController._dispatch()` answers straight from `LISTENING` -> `SPEAKING`.
- **Fast-Path Transcription Skip**: if the live partial transcript already covers ~90% of the recorded audio and matches a known command, SAM acts on it immediately and skips the final Whisper decode.
- **Dedicated Live-Transcription Model**: partial captioning runs on its own small model (`stt.partial_model`, default `base`) instead of re-running the full-size model every ~300ms.

### Changed
- `commands/router.CommandRouter.try_handle()` takes a `vision` flag so the fast command path does not pay for unused screen captures.
- Live-decode cadence is rate-limited (`stt.partial_interval_ms`, default 400ms) instead of firing on every recorder chunk.

---

## [0.4.4] - 2026-08-13

> **Real-time live speech transcription and bilingual command routing.**

### Added
- **Live Partial Captioning**: Audio captured while speaking is decoded every ~300ms using fast greedy Whisper (`beam_size=1`) and streamed live to the UI overlay/orb in real-time.
- **Turkish Command Support**: Complete Turkish intent coverage for media, volume control, system actions, and application management.

### Fixed
- **Command Router Matching**: Stripped conversational filler words (`hey sam`, `please`, `lutfen`) to prevent system commands from falling through to the LLM.
- **Latency & Turnaround**: Tuned default silence detection duration from 900ms to 600ms for faster post-speech response.

---

## [0.4.3] - 2026-08-12

> **Fenerbahce RAG accuracy pass: less hallucination, more grounded answers.**

### Fixed
- Retrieval broke for Turkish questions against English knowledge files. Swapped embedding model to `paraphrase-multilingual-MiniLM-L12-v2` for cross-lingual TR/EN retrieval.
- Corrected championship numbers in knowledge files.

### Changed
- Rebalanced prompt instructions to prioritize factual precision over tone.
- Added strict factual grounding blocks in retrieved context.
- Increased `rag.top_k` from 3 to 5.

---

## [0.4.2] - 2026-08-11

> **Conversation intelligence: intent classification and RAG integration.**

### Added
- Intent classification (`llm/intent.py`): keyword and regex layer classifying messages as `NORMAL`, `FENERBAHCE`, or `COMPLEX`.
- Dynamic conversation modes (`llm/modes.py`): adaptive system prompts per-turn.
- RAG knowledge retrieval (`llm/rag.py`): sentence-transformers embeddings + ChromaDB.
- Prompt assembly pipeline (`llm/prompt_builder.py`): composed persona, behavior rules, mode instructions, and RAG context.
- Long-term memory interface stub (`llm/memory.py`).

---

## [0.4.1] - 2026-08-11

> **The orb overlay and native installer release.**

### Added
- The orb overlay (`ui/orb.py`): always-on desktop circle with reactive animations.
- Z-order presence control: orb rests at the bottom of the window stack until summoned (`ui/win32.py`).
- Typed input mode (`ui/text_input.py`): triggered via `Ctrl+Shift+Space` or clicking the orb.
- Ollama auto-start (`llm/ollama_service.py`): automatic local Ollama server discovery and startup.
- Inno Setup installer (`installer/SAM.iss`) and PyInstaller spec (`SAM.spec`).
- Named-mutex single-instance lock and path resolution (`core/paths.py`).

---

## [0.3.6] - 2026-07-09

### Added
- Custom "Hey Sam" wake word model (`assets/models/hey_sam.onnx`) set as default.
- Wake word model file browser in settings.
- Dynamic wake word and version display in CLI banner.

---

## [0.3.5] - 2026-07-07

### Changed
- Expanded command router pattern coverage and chained-command handling.
- Tuned VAD voice activity detection sensitivity.
- Polished state transition timings in `core/app.py`.

---

## [0.3.0] - 2026-07-07

### Added
- Initial public release of SAM.
- Floating overlay UI with live mic visualizer.
- Wake word detection via `openwakeword`.
- Local speech-to-text with `faster-whisper`.
- Local LLM chat via Ollama.
- Instant regex command router for OS controls.
- Spotify API integration.
- Speech synthesis with `edge-tts` and `pyttsx3`.

---

[Unreleased]: https://github.com/sametgurtuna/SAM/compare/v0.4.7...HEAD
[0.4.7]: https://github.com/sametgurtuna/SAM/compare/v0.4.6...v0.4.7
[0.4.6]: https://github.com/sametgurtuna/SAM/compare/v0.4.5...v0.4.6
[0.4.5]: https://github.com/sametgurtuna/SAM/compare/v0.4.4...v0.4.5
[0.4.4]: https://github.com/sametgurtuna/SAM/compare/v0.4.3...v0.4.4
[0.4.3]: https://github.com/sametgurtuna/SAM/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/sametgurtuna/SAM/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/sametgurtuna/SAM/compare/v0.3.6...v0.4.1
[0.3.6]: https://github.com/sametgurtuna/SAM/compare/v0.3.5...v0.3.6
[0.3.5]: https://github.com/sametgurtuna/SAM/compare/v0.3.0...v0.3.5
[0.3.0]: https://github.com/sametgurtuna/SAM/releases/tag/v0.3.0
