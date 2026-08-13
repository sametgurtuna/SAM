<div align="center">

# 📜 Changelog

All notable changes to **SAM** are documented in this file.

<img src="https://img.shields.io/badge/Keep%20a%20Changelog-1.1.0-e05735?style=flat-square" alt="Keep a Changelog">
<img src="https://img.shields.io/badge/SemVer-2.0.0-3776AB?style=flat-square" alt="Semantic Versioning">
<img src="https://img.shields.io/badge/Current-v0.4.4-22c55e?style=flat-square" alt="Current version">

</div>

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and SAM
follows [Semantic Versioning](https://semver.org/) once it reaches 1.0. Until then,
minor versions (`0.x.0`) may include breaking config or behavior changes — see
[ROADMAP.md](ROADMAP.md) for what's planned next.

---

## At a glance

| Version | Date | Highlight |
|:---|:---|:---|
| [Unreleased](#unreleased) | — | Screen/clipboard awareness, plugin system |
| [0.4.4](#044---2026-08-13) | 2026-08-13 | ⚡ Real-time speech transcription & bilingual command routing fixes |
| [0.4.3](#043---2026-08-12) | 2026-08-12 | 🎯 Fenerbahçe RAG accuracy fixes (multilingual embeddings, strict grounding) |
| [0.4.2](#042---2026-08-11) | 2026-08-11 | 🧠 Intent classification, RAG, conversation modes |
| [0.4.1](#041---2026-08-11) | 2026-08-11 | 🟢 The always-on orb, typed input, installer |
| [0.3.6](#036---2026-07-09) | 2026-07-09 | 🎙️ Custom "Hey Sam" wake word |
| [0.3.5](#035---2026-07-07) | 2026-07-07 | ⚡ Router & VAD performance pass |
| [0.3.0](#030---2026-07-07) | 2026-07-07 | 🚀 Initial public release |

---

## [Unreleased]

Tracked in [ROADMAP.md](ROADMAP.md) — screen/clipboard awareness, productivity
features (reminders, scheduling), a plugin system, and a cross-platform command layer
are next up.

---

## [0.4.4] - 2026-08-13

> ⚡ **Real-time live speech transcription & robust bilingual command routing.**

### Added
- **Live Partial Captioning**: Audio captured while speaking is decoded every ~300ms using fast greedy Whisper (`beam_size=1`) and streamed live to the UI overlay/orb in real-time.
- **Turkish Command Support**: Complete Turkish intent coverage for media (`sonraki parça`, `şarkıyı geç`, `sıradaki`, `pas geç`), volume control (`sesi aç`, `sesi kıs`, `sessize al`), system actions (`ekranı kilitle`, `ekran görüntüsü al`), and application management (`chrome aç`, `spotify kapat`).

### Fixed
- **Command Router Matching**: Stripped conversational fluff (`hey sam`, `please`, `lütfen`) and flexible phrase matching to prevent system commands like `"next track please"` or `"sonraki parçaya geç"` from falling through to the LLM.
- **Latency & Turnaround**: Tuned default silence detection duration from 900ms to 600ms for faster post-speech response.

---

## [0.4.3] - 2026-08-12

> 🎯 **Fenerbahçe RAG accuracy pass** — less hallucination, more grounded answers.

#### 🐛 Fixed

- Retrieval broke for Turkish questions against English knowledge files. Swapped the
  embedding model from `all-MiniLM-L6-v2` (English-only) to
  `paraphrase-multilingual-MiniLM-L12-v2` (~same size, cross-lingual TR/EN), so a
  Turkish query now actually matches the relevant chunk instead of returning noise.
- `legends.md` claimed Alex de Souza won "four Süper Lig titles (2004-05, 2006-07,
  2010-11, and one more)" — the trailing "and one more" was effectively an instruction
  to fabricate. Corrected to the actual three titles.

#### 🔧 Changed

- `FENERBAHCE` mode instructions rebalanced — the previous "fanaticism 9/10" tone
  fought with the accuracy rules on a 3B local model. Now accuracy is the explicit
  priority; tone stays warm but not shouted, with an explicit "Bunu net bilmiyorum"
  fallback taught to the model.
- Prompt builder now wraps retrieved knowledge in a hard `GROUNDED FACTS` block that
  forbids invention and requires the model to say it doesn't know when the answer
  isn't in the facts.
- `rag.top_k`: 3 → 5. The KB is small; the extra chunks cost nothing and reduce the
  chance the right chunk falls outside the top-3 window.

---

## [0.4.2] - 2026-08-11

> 🧠 **Conversation intelligence** — SAM stopped treating every message the same way.

#### ✨ Added

- Intent classification (`llm/intent.py`) — a keyword/regex layer, no LLM call, tags
  every message as `NORMAL`, `FENERBAHCE`, or `COMPLEX` before it's routed, so simple
  chat never pays for a heavier round-trip it doesn't need.
- Dynamic conversation modes (`llm/modes.py`) — the system prompt now adapts per-turn
  instead of staying static for the whole session.
- RAG knowledge retrieval (`llm/rag.py`) — sentence-transformers embeddings +
  ChromaDB, lazy-loaded on first query. Ships with a first knowledge domain:
  Fenerbahçe history, legends, trophies, stadium, rivals, and modern era
  (`knowledge/football/fenerbahce/`).
- Prompt assembly pipeline (`llm/prompt_builder.py`) — persona, behavior rules, mode
  instructions, and RAG context are now composed per-turn instead of concatenated
  ad hoc inside the router.
- Long-term memory interface (`llm/memory.py`) — currently a `NullMemory` stub, laying
  the groundwork for persistent user memory in a future release.

#### 🔧 Changed

- `llm/router.py` reworked to wire intent classification, mode selection, RAG
  retrieval, and prompt building into the existing engine routing flow.
- `ui/caption.py` reworked for the longer, RAG-backed replies this release introduced.
- `core/config.py` and `config.example.yaml` gained new keys for RAG, modes, and
  intent thresholds — all with safe defaults, so existing `config.yaml` files keep
  working unmodified.

#### 🗑️ Removed

- `BUILDING.md` — consolidated into the contribution guide and [setup.md](setup.md).

---

## [0.4.1] - 2026-08-11

> 🟢 **The orb** — the biggest visual and structural change since v0.1.0.

#### ✨ Added

- The orb overlay (`ui/orb.py`) — replaces the trigger-only floating bar with an
  always-on circle that breathes gently when idle and reacts live to mic input while
  engaged.
- Z-order presence control — the orb sits at the bottom of the window stack by
  default (`ui.orb.layer: auto`), below every other window and above only the
  wallpaper, until a wake word, hotkey, or click brings it to the front
  (`ui/win32.py` — click-through and foreground-focus ctypes helpers).
- Click-through hit-testing — only the visible circle is clickable; everything else
  in its bounding box passes mouse events straight to the desktop underneath. `Ctrl`
  + drag repositions it, and the position is remembered.
- Typed input mode (`ui/text_input.py`) — `Ctrl+Shift+Space`, or a click on the orb,
  opens a text box that runs through the same router → LLM → TTS pipeline as speech.
- Ollama auto-start (`llm/ollama_service.py`) — SAM finds and starts the Ollama
  server itself, hidden, with no console flash, and never touches a server that was
  already running (`stop_on_exit: false` by default).
- A real installer — Inno Setup script (`installer/SAM.iss`), a PyInstaller build
  spec (`SAM.spec`), and `core/installer_steps.py` (`SAM.exe --install-models`)
  produce a per-user `SAM-Setup-x.y.z.exe` with no admin requirement.
- Frozen-exe path resolution (`core/paths.py`) — dev vs. installed-build paths, plus
  a named-mutex single-instance lock so SAM can't run twice.
- Codebase conventions formalized into a single contribution guide.
- New icon and preview assets (`assets/icon.ico`, `assets/icon.png`,
  `assets/preview-orb-states.png`) and the generator behind them
  (`tools/make_icon.py`).

#### 🔧 Changed

- `docs/ARCHITECTURE.md` rewritten to describe the orb-based overlay and the new
  threading/z-order model.
- `audio/tts.py` reworked for smoother streaming playback alongside the new overlay.
- `ui/settings_window.py`, `ui/waveform.py`, and `ui/floating_bar.py` updated for the
  orb-first UI (the floating bar remains available via `ui.overlay.style: bar`).
- `main.py`, `core/app.py`, and `core/config.py` extended to support the new
  overlay, installer flags, and Ollama service lifecycle.

#### 🛡️ Security

- Shells can no longer be opened by voice or text, under any circumstance. `cmd`,
  `powershell`, `wt`, `bash`, and similar are hard-blocked in `commands/system.py`
  regardless of how the request arrives — closing a real gap where a Whisper
  hallucination on background noise could previously have opened a terminal window
  unprompted.

---

## [0.3.6] - 2026-07-09

> 🎙️ **"Hey Sam"** — SAM's own name became its wake word.

#### ✨ Added

- Custom-trained wake word model, `assets/models/hey_sam.onnx`, set as the new
  default — replacing the generic wake word used since v0.2.0.
- A file browser dialog in the Settings UI for choosing custom wake word models
  (`.onnx` / `.tflite`), instead of hand-editing `config.yaml`.
- Dynamic rendering of the active wake word and app version in the CLI banner and
  the about screen, instead of hardcoded strings.

#### 🔧 Changed

- Default app version bumped to v0.3.6 consistently across configs, scripts, and
  docs (`README.md`, `ROADMAP.md`, `setup.md`).

---

## [0.3.5] - 2026-07-07

> ⚡ **Performance & fluidity** — a same-day follow-up to the initial release.

#### 🔧 Changed

- `commands/router.py` expanded significantly — broader command pattern coverage
  and improved chained-command handling (`"and"` / `"ve"` / `"then"`).
- `audio/recorder.py` and `audio/wake_word.py` tuned for more responsive voice
  activity detection and wake word sensitivity.
- `core/app.py` state transitions tightened for a smoother idle → listening →
  thinking → speaking cycle.
- `audio/stt.py` simplified — trimmed dead configuration paths left over from the
  initial implementation.

---

## [0.3.0] - 2026-07-07

> 🚀 **Initial public release.**

#### ✨ Added

- PyQt6 floating overlay UI with a live mic-level waveform visualizer.
- Wake word detection via `openwakeword` (ONNX/TFLite), continuous and low-CPU.
- Local speech-to-text via `faster-whisper` (CTranslate2, int8 quantized).
- Local LLM conversation via Ollama (`qwen2.5:3b` default model).
- Instant OS command routing (regex-matched, <10ms) for volume, media playback,
  app launch/close, and power actions.
- Spotify API integration for direct track playback by voice.
- System tray icon with a dark-themed settings dashboard.
- Speech synthesis via `edge-tts` (online voices) or `pyttsx3` (fully offline).
- Full initial documentation set: README, setup guide, roadmap, and architecture doc.

---

<div align="center">

*For where SAM is headed next, see* [*ROADMAP.md*](ROADMAP.md)*.*

</div>

[Unreleased]: https://github.com/sametgurtuna/SAM/compare/v0.4.3...HEAD
[0.4.3]: https://github.com/sametgurtuna/SAM/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/sametgurtuna/SAM/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/sametgurtuna/SAM/compare/v0.3.6...v0.4.1
[0.3.6]: https://github.com/sametgurtuna/SAM/compare/v0.3.5...v0.3.6
[0.3.5]: https://github.com/sametgurtuna/SAM/compare/v0.3.0...v0.3.5
[0.3.0]: https://github.com/sametgurtuna/SAM/releases/tag/v0.3.0
