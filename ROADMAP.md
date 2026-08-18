<div align="center">

# SAM Roadmap

[![Current Version](https://img.shields.io/badge/Current-v0.4.8-22c55e?style=flat-square)](#v048---the-clipboard--audio-agility-pass-current-release)

</div>

---

## Principles

| Pillar | Meaning |
|:---|:---|
| **Local-first** | Voice capture, transcription, and (with Ollama) the language model itself run on your machine. No telemetry, ever. |
| **Instant where it can be** | Anything that does not need a language model (opening an app, volume, power) is a regex match away, not an LLM round-trip. |
| **Out of your way** | An always-on assistant has to earn its place on your screen. It should not sit on top of your work, and it should not do anything alarming on its own. |

---

## Milestones

| Version | Status | Focus |
|:---|:---|:---|
| v0.1.0 | Done | Floating-bar UI, state machine, mock engines |
| v0.2.0 | Done | Real audio pipeline: wake word, VAD, faster-whisper, edge-tts |
| v0.3.0 | Done | Ollama integration, OS command router, system tray |
| v0.3.6 | Done | Custom "Hey Sam" wake word model, wake-word file browser |
| v0.4.0 | Done | Always-on orb overlay, typed input, Ollama auto-start, installer |
| v0.4.1 - v0.4.4 | Done | Intent classification, RAG, conversation modes, real-time live captioning |
| v0.4.5 | Done | Instant predefined responses, zero-LLM command dispatch, dedicated live-transcription model |
| v0.4.6 | Done | Editable instant responses (seeded to user data dir), rebuilt settings window |
| v0.4.7 | Done | Major UI Revamp: Cyberpunk Dark Webview, Live Mic Spectrum, Ollama Detector, Smart Hotkeys |
| **v0.4.8** | **Current** | Clipboard awareness, instant language switcher, Cyberpunk SFX, HUD toast notifications |
| v0.5.0 | Planned | Screen awareness (vision) |
| v0.6.0 | Planned | Productivity: reminders, scheduling |
| v0.7.0 | Planned | Local knowledge base (RAG) |
| v0.8.0 | Planned | Plugin system, cross-platform command layer |
| v1.0.0 | Planned | Auto-updater, first-run wizard, signed builds |

---

## v0.4.8 - The Clipboard & Audio-Agility Pass *(current release)*

> Perfecting SAM's grip on desktop text and language before diving into heavier vision
> models. Full details in [CHANGELOG.md](CHANGELOG.md#unreleased).

- [x] **Clipboard awareness & quick actions**: voice/typed triggers ("explain this", "translate this", "özetle") send the copied text to the LLM as context; `commands/clipboard.py` reads it safely via `win32clipboard` with a `pyperclip` fallback.
- [x] **Live clipboard badge**: the typed-input box (`Ctrl+Shift+Space`) shows a one-click-detachable "📋 Attached" badge whenever there is clipboard text to use.
- [x] **Instant language switcher**: "Türkçe konuş" / "Switch to English" / "auto language" lock STT + TTS to a language immediately; also available from the tray as `🌐 Language: Auto | TR | EN`.
- [x] **Cyberpunk SFX engine** (`audio/sounds.py`): procedurally synthesized micro sound effects (wake blip, success chime, warning tone) with no bundled audio files, toggle + volume in Settings.
- [x] **HUD toast notifications** (`ui/toast.py`): a translucent badge beside the orb for zero-LLM feedback (volume, Spotify track changes, language switches, errors) that auto-fades in 1.6s.

---

## v0.4.7 - Major UI Revamp

> State-of-the-art Cyberpunk Dark Webview architecture powered by Windows Edge WebView2,
> Modern cyberpunk design tokens, interactive diagnostic tools, and native Windows branding.
> Full details in [CHANGELOG.md](CHANGELOG.md#047---2026-08-14).

- [x] **Webview-powered settings**: Replaced legacy PyQt QSS with a modern HTML5/CSS3/JS Webview interface (`pywebview`).
- [x] **Cyberpunk Dark design system**: Glassmorphism cards (`backdrop-filter: blur(12px)`), neon teal `#00D4AA`, and smooth switches.
- [x] **Live Mic Spectrum tester**: Web Audio API frequency visualizer with real-time 60 FPS equalizer bars and volume meter.
- [x] **Ollama Latency & Model detector**: In-app ping tool with latency measurement and auto-population of local models.
- [x] **Smart Hotkey recorder**: Click-to-record voice and text shortcut inputs with keycap badges.
- [x] **Live Canvas Orb preview**: 60 FPS interactive preview reacting to size, ring, and opacity sliders.
- [x] **Single-Instance window & Windows branding**: Windows Named Mutex, `AppUserModelID`, and `WM_SETICON` taskbar branding.

---

## v0.4.6 - Editable instant responses + rebuilt settings

> The phrase list is now a file installed users own and can edit, and the settings window
> was rebuilt around it. Full details in [CHANGELOG.md](CHANGELOG.md#046---2026-08-13).

- [x] **Seeded, editable response file**: copied to the writable data dir on first launch (`%APPDATA%\SAM\knowledge\`), read from there, survives updates.
- [x] **Responses settings page**: enable toggle, *Edit Responses*, *Show Folder*, and *Reload* (applies edits without restarting SAM).
- [x] **Settings redesign**: resizable window, page titles/descriptions, card sections, restyled controls, live-transcription options, a real About page.
- [x] **Stylesheet inheritance fix**: scoped viewport stylesheet directly to the container.

---

## v0.4.5 - Instant responses + zero-LLM command dispatch

> Predefined phrases now answer instantly from a dictionary lookup, recognized commands
> skip the LLM/`THINKING` step entirely, and live captioning got its own lightweight model.

- [x] **Instant responses**: `knowledge/instant_responses.yaml` + `commands/instant.py`, ~130 predefined TR/EN phrases answered with no LLM round-trip.
- [x] **Fast command path**: `AppController._dispatch()` answers straight from `LISTENING` -> `SPEAKING` for instant responses and matched commands.
- [x] **Fast-path transcription skip**: a live partial transcript that already covers the recording and matches a known command/response skips the final Whisper decode.
- [x] **Dedicated live-transcription model**: `stt.partial_model` decodes captions on a small model on half the CPU threads.

---

## v0.4.0 - Always-on orb + installer

- [x] **Orb overlay**: a small circle, always on screen, breathing when idle and reacting to mic level / LLM state.
- [x] **Auto z-order**: sits at the bottom of the window stack until summoned, then jumps to front for the session.
- [x] **Click-through**: only the visible circle is clickable; desktop underneath receives clicks everywhere else.
- [x] **Ctrl+drag to reposition**: position persisted across sessions.
- [x] **Typed input mode**: `Ctrl+Shift+Space` or a click on the orb opens a text input box.
- [x] **Ollama auto-start**: SAM finds and launches `ollama serve` automatically if not running.
- [x] **Safety guard**: terminal shells hard-blocked from speech commands.
- [x] **Single-instance guard**: named mutex prevents duplicate background instances.
- [x] **Setup installer**: Inno Setup script packages a clean per-user installer.

---

## v0.5.0 - Screen awareness

- [ ] `"what's on my screen"`: screenshot + local vision model (`llava` or similar) via Ollama.

## v0.6.0 - Productivity

- [ ] Voice-triggered reminders with a background scheduler and chime.
- [ ] Local `.ics` / Outlook calendar agenda readout.

## v0.7.0 - Local knowledge base (RAG)

- [ ] A lightweight local vector store, bundled.
- [ ] Background indexer for notes and markdown documents.
- [ ] Ollama embedding model for retrieval, injected into the system prompt on match.

## v0.8.0 - Plugins & portability

- [ ] `BasePlugin` + a `/plugins` directory scanned at startup.
- [ ] Port `commands/system.py` OS layer to cross-platform abstractions.
- [ ] Fully offline TTS option (Piper), removing external network calls completely.

## v1.0.0 - Production polish

- [ ] Auto-updater.
- [ ] First-run configuration wizard.
- [ ] Code-signed installer and executable.

---

## Contributing to the roadmap

Have an idea that fits the principles above? Open an issue or start a discussion on GitHub.
