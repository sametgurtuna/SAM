<div align="center">

# 🗺️ SAM — Roadmap

[![Current Version](https://img.shields.io/badge/Current-v0.4.6-22c55e?style=flat-square)](#v046--editable-instant-responses--rebuilt-settings-current-release)

</div>

---

## Principles

| Pillar | Meaning |
|:---|:---|
| 🛡️ **Local-first** | Voice capture, transcription, and (with Ollama) the language model itself run on your machine. No telemetry, ever. |
| ⚡ **Instant where it can be** | Anything that doesn't need a language model (opening an app, volume, power) is a regex match away, not an LLM round-trip. |
| 🙈 **Out of your way** | An always-on assistant has to earn its place on your screen. It shouldn't sit on top of your work, and it shouldn't do anything alarming (like popping open a terminal) on its own. |

---

## Milestones

| Version | Status | Focus |
|:---|:---|:---|
| v0.1.0 | ✅ Done | Floating-bar UI, state machine, mock engines |
| v0.2.0 | ✅ Done | Real audio pipeline — wake word, VAD, faster-whisper, edge-tts |
| v0.3.0 | ✅ Done | Ollama integration, OS command router, system tray |
| v0.3.6 | ✅ Done | Custom "Hey Sam" wake word model, wake-word file browser |
| v0.4.0 | ✅ Done | Always-on orb overlay, typed input, Ollama auto-start, installer |
| v0.4.1 – v0.4.4 | ✅ Done | Intent classification, RAG, conversation modes, real-time live captioning |
| v0.4.5 | ✅ Done | Instant predefined responses, zero-LLM command dispatch, dedicated live-transcription model |
| **v0.4.6** | ✅ **Current** | Editable instant responses (seeded to user data dir), rebuilt settings window |
| v0.5.0 | 📅 Planned | Screen & clipboard awareness |
| v0.6.0 | 📅 Planned | Productivity — reminders, scheduling |
| v0.7.0 | 📅 Planned | Local knowledge base (RAG) |
| v0.8.0 | 📅 Planned | Plugin system, cross-platform command layer |
| v1.0.0 | 📅 Planned | Auto-updater, first-run wizard, signed builds |

---

## v0.4.6 — Editable instant responses + rebuilt settings *(current release)*

> The phrase list is now a file installed users own and can edit, and the settings window
> was rebuilt around it. Full details in [CHANGELOG.md](CHANGELOG.md#046---2026-08-13).

- [x] **Seeded, editable response file** — copied to the writable data dir on first launch
  (`%APPDATA%\SAM\knowledge\`), read from there, survives updates
- [x] **Responses settings page** — enable toggle, *Edit Responses…*, *Show Folder*, and
  *Reload* (applies edits without restarting SAM)
- [x] **Settings redesign** — resizable window, page titles/descriptions, card sections,
  restyled controls, live-transcription options, a real About page
- [x] **Stylesheet inheritance fix** — a selector-less viewport stylesheet was blanking the
  background of every widget nested inside a settings page

---

## v0.4.5 — Instant responses + zero-LLM command dispatch

> Predefined phrases now answer instantly from a dictionary lookup, recognized commands
> skip the LLM/`THINKING` step entirely, and live captioning got its own lightweight model
> so it stops competing with the final transcription. Full details in
> [CHANGELOG.md](CHANGELOG.md#045---2026-08-13).

- [x] **Instant responses** — `knowledge/instant_responses.yaml` + `commands/instant.py`,
  ~130 predefined TR/EN phrases answered with no LLM round-trip
- [x] **Fast command path** — `AppController._dispatch()` goes `LISTENING` → `SPEAKING`
  directly for instant responses and matched commands, never entering `THINKING`
- [x] **Fast-path transcription skip** — a live partial transcript that already covers the
  recording and matches a known command/response skips the final Whisper decode
- [x] **Dedicated live-transcription model** — `stt.partial_model` decodes captions on a
  small model on half the CPU threads, instead of re-running the full-size model every
  ~300ms

---

## v0.4.0 — Always-on orb + installer

> Replaced the trigger-only floating bar with a permanent desktop presence, added a typed
> input mode, and shipped SAM's first real installer.

- [x] **Orb overlay** — a small circle, always on screen, breathing when idle and
  reacting to mic level / LLM state (`ui/orb.py`, `ui/caption.py`, `ui/overlay.py`)
- [x] **Auto z-order** — sits at the bottom of the window stack until summoned (wake word,
  hotkey, click), then jumps to the front for the session and sinks back down afterward
- [x] **Click-through** — only the visible circle is clickable; everything else in its
  bounding box passes clicks to the desktop underneath
- [x] **Ctrl+drag to reposition**, position persisted and validated against the current
  monitor layout on restart
- [x] **Typed input mode** — `Ctrl+Shift+Space` or a click on the orb opens a text box that
  feeds the exact same command-router → LLM → TTS pipeline as speech
- [x] **Ollama auto-start** — SAM finds and launches `ollama serve` itself, hidden, without
  ever touching a server the user already had running
- [x] **Async engine detection** — removed a real, measured 2-second Qt-thread stall that
  used to happen on every LLM request when Ollama's HTTP check was run synchronously
- [x] **Safety: voice/text can no longer open a shell** — `cmd`, `powershell`, `wt`, `bash`
  and similar are hard-blocked in `commands/system.py`, closing a real gap where a Whisper
  hallucination on background noise could have opened a visible terminal window
- [x] **Freeze-ready paths** — `core/paths.py` separates the read-only bundle from
  `%APPDATA%\SAM`, so the installed app's Settings window can actually persist changes
- [x] **Single-instance guard** — required once SAM can add itself to Windows startup
- [x] **`SAM-Setup-x.y.z.exe`** — PyInstaller (onedir) + Inno Setup, with opt-in steps for
  installing Ollama, pre-pulling the model, pre-downloading the speech model, and starting
  with Windows

---

## v0.5.0 — Screen & clipboard awareness

- [ ] `"what's on my screen"` — screenshot + local vision model (`llava` or similar) via
  Ollama
- [ ] Clipboard-aware quick actions ("explain this", "translate this") on the copied text
- [ ] Multi-language STT — a tray toggle instead of editing `stt.language` by hand

## v0.6.0 — Productivity

- [ ] Voice-triggered reminders with a background scheduler and a chime
- [ ] Local `.ics` / Outlook calendar agenda readout

## v0.7.0 — Local knowledge base (RAG)

- [ ] A lightweight local vector store (Chroma or LanceDB), bundled
- [ ] Background indexer for a configured folder of notes/markdown/PDFs
- [ ] Ollama embedding model for retrieval, injected into the system prompt on match

## v0.8.0 — Plugins & portability

- [ ] `BasePlugin` + a `/plugins` directory scanned at startup — no core file edits needed
  to add a command
- [ ] Port `commands/system.py`'s OS layer to Linux (DBus/`amixer`) and macOS (AppleScript) —
  today it is Windows-only by design (`ctypes.windll`, `pycaw`, `SetWindowPos`)
- [ ] Fully offline TTS option (Piper or similar), removing the `edge-tts` network
  dependency entirely for people who don't want even that outbound call

## v1.0.0 — Production polish

- [ ] Auto-updater
- [ ] First-run wizard (mic test, wake-word calibration, model picker) instead of the
  installer's static checkboxes
- [ ] Code-signed installer and executable

---

## Contributing to the roadmap

Open an issue describing the feature, why it fits SAM's local-first / out-of-your-way
philosophy, and — for anything touching `commands/system.py` — how it stays safe against
misheard or hallucinated transcripts (see `CLAUDE.md`'s conventions on anchored,
object-qualified patterns for anything destructive or surprising).

<div align="center">

*Keep your data local.*

</div>
