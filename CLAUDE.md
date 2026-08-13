# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SAM (Smart Assistant Module) is a Windows desktop voice assistant: a PyQt6 background
app that listens for a wake word or hotkey, records speech, transcribes it locally
(faster-whisper), routes it either to a direct OS action (regex command router) or to
an LLM (local Ollama, with optional Claude cloud fallback), then speaks the response
back (edge-tts / pyttsx3). No build step — it's a pure Python app, run directly.

## Commands

```bash
# Setup
python -m venv venv
.\venv\Scripts\Activate.ps1          # Windows PowerShell
pip install -r requirements.txt

# Run
python main.py

# External dependency required at runtime for local LLM
ollama pull qwen2.5:3b               # or another model set in config.yaml
```

There is no test suite, no linter config, and no build/package step in this repo —
don't invent commands for these. Verify behavior manually by running `python main.py`
and checking `logs/sam.log`.

`config.yaml` (gitignored, user-specific — holds Spotify keys etc.) is deep-merged over
the `DEFAULTS` dict in `core/config.py`; `config.example.yaml` is the template committed
to the repo. When adding a new setting, add its default to `DEFAULTS` too so the app
works even if the key is missing from `config.yaml`.

## Architecture

Everything is orchestrated by `AppController` (`core/app.py`), a `QObject` that wires
together independent engines purely through PyQt signals/slots — no engine calls
another engine directly. This is the file to read first when tracing a feature end to
end.

**Pipeline:** wake word / hotkey → `Recorder` (VAD-based mic capture) → `STTEngine`
(faster-whisper) → `InstantResponder` (dictionary lookup) → `CommandRouter` (regex intent
match) → if still unmatched, `LLMRouter`
(intent classify → mode select → RAG retrieve → engine route → streaming) →
`TTSEngine` (edge-tts or pyttsx3) → auto-hide timer → back to idle.

**LLM Router pipeline:** `IntentClassifier` (keyword/regex, no LLM call) classifies
each message as NORMAL / FENERBAHCE / COMPLEX. NORMAL and FENERBAHCE go to Ollama
(local); COMPLEX goes to Claude (cloud). `PromptBuilder` assembles the system prompt
per-turn: persona + behavior rules + mode instructions + RAG knowledge. For FENERBAHCE
intent, `RAGEngine` retrieves relevant chunks from `knowledge/` markdown files via
sentence-transformers embeddings + ChromaDB (lazy-loaded on first FB query). See
`llm/intent.py`, `llm/prompt_builder.py`, `llm/modes.py`, `llm/rag.py`.

**Streaming TTS:** the LLM response is spoken *while it is still generating*.
`AppController._flush_streaming_tts()` watches the accumulating token buffer and hands
each completed sentence to `TTSEngine.speak_chunk()`; `_on_llm_complete` sends whatever
prose is left and calls `end_stream()`. `TTSEngine` is therefore a queue plus one
persistent worker thread — `playback_finished` fires exactly once per utterance, on the
`end` marker, not per chunk. `stop()` bumps an internal generation counter so anything
still queued from a cancelled turn is discarded rather than spoken late. If a ```` ``` ````
fence appears in the stream, streaming speech stops for that turn (code must not be read
aloud; `core/code_parser.py` writes it to the Desktop instead).

**Fast path:** `AppController._dispatch(text, allow_llm=...)` is the single entry point
for both spoken and typed input. It tries the instant responder, then the command router,
and only then the LLM — the first two go straight to `SPEAKING` and never enter
`THINKING`. `_on_recording_done()` calls it with `allow_llm=False` against the *live
partial* transcript first: if that already covers ≥90% of the recording and matches, the
final Whisper decode is skipped entirely. `STTEngine` runs partials on a separate small
model (`stt.partial_model`) so live captioning doesn't starve the final decode.

State machine (`AppState` in `core/app.py`): `IDLE → LISTENING → THINKING → SPEAKING →
IDLE`. `AppController._set_state()` is the only place state should change; UI updates
happen through `FloatingBar.set_state()` in the same call.

**Threading model:** every engine (`WakeWordEngine`, `Recorder`, `STTEngine`,
`TTSEngine`, `OllamaEngine`, `ClaudeEngine`) does its blocking work on a daemon
`threading.Thread` and reports back to the Qt main thread exclusively via
`pyqtSignal`. Never touch a PyQt widget from inside one of these worker threads —
always go back through a signal.

**Module layout:**
- `core/` — `app.py` (controller/state machine), `config.py` (singleton config
  loader/saver), `code_parser.py` (extracts ```code``` blocks from LLM replies, saves
  them to the Desktop, strips them from the TTS text).
- `audio/` — `wake_word.py` (openwakeword/TFLite continuous listener),
  `recorder.py` (RMS-based VAD recording), `stt.py` (faster-whisper transcription),
  `tts.py` (edge-tts / pyttsx3 playback via pygame.mixer), `sounds.py` (chimes).
- `commands/` — `router.py` (regex intent matching, supports chained commands via
  "and"/"ve"/"then"), `system.py` (all actual OS side effects: app launch/kill via
  `subprocess`/`taskkill`, volume via `ctypes`/`pycaw`, power actions via `shutdown`,
  Spotify via `spotipy`), `vision.py` (screen capture → base64 for vision LLM calls).
  Add new voice commands here: a regex pattern in `router.py` + a handler function in
  `system.py` (or a new module) that returns the spoken confirmation string.
  `instant.py` (`InstantResponder`) answers predefined phrases from
  `knowledge/instant_responses.yaml` with a normalized dictionary lookup — no LLM, no
  regex scan. That YAML is seeded into `paths.user_data_dir()` on first launch (like
  `config.yaml`) and read from there, so installed users can edit it; Settings →
  Responses opens and reloads it.
- `llm/` — `base.py` (abstract `LLMEngine`), `ollama_engine.py`, `claude_engine.py`,
  `router.py` (`LLMRouter` — intent-based dual-engine routing, rolling conversation
  `deque`), `intent.py` (keyword/regex intent classifier: NORMAL/FENERBAHCE/COMPLEX),
  `prompt_builder.py` (per-turn system prompt assembly: persona + rules + mode + RAG),
  `modes.py` (dynamic conversation modes, e.g. FENERBAHCE fan mode),
  `rag.py` (sentence-transformers + ChromaDB semantic retrieval, lazy-loaded),
  `memory.py` (long-term user memory interface, currently NullMemory stub).
- `knowledge/` — markdown knowledge base files for RAG retrieval. Currently:
  `football/fenerbahce/` with history, legends, trophies, stadium, rivals, modern era.
- `ui/` — `floating_bar.py` (frameless always-on-top overlay), `waveform.py`
  (mic-level visualizer), `tray.py` (system tray icon/menu), `settings_window.py`
  (GUI editor for `config.yaml`), `styles.py`.
- `main.py` — entry point: loads config, sets up logging, constructs `AppController`
  and `TrayManager`, starts the Qt event loop.

**`docs/ARCHITECTURE.md`** is a deeper (Mermaid-diagrammed) internal design doc, but
some paths/module names in it are stale relative to the current tree (e.g. it
references `core/stt.py` and `llm/ollama_client.py`, which are actually `audio/stt.py`
and `llm/ollama_engine.py`) — trust the actual source layout over that doc.

## Conventions

- In-line code comments are written in Turkish (existing project convention); code
  identifiers, docstrings, log messages, and user-facing strings are English.
- System-command handlers in `commands/system.py` always return a short spoken-style
  confirmation string (or raise), never raise-and-crash the router — `CommandRouter`
  already wraps handler calls in try/except.
- Config access always goes through `config.get("section", "key", default=...)`
  (dot-path style), never by reading `config.yaml` directly.
- **Never pass transcript text to a shell.** Transcripts come from Whisper and are
  attacker-influencable audio. Launch apps with `os.startfile()` (no `cmd.exe`, and
  faster), run tools with list-form `subprocess`, and validate any free-form name with
  `system._is_safe_name()` before it reaches the OS. There should be no `shell=True`
  in this codebase.
- **Destructive commands are two-step.** `shutdown_pc()`/`restart_pc()` only *arm* an
  action; `confirm_power_action()` executes it within a 30 s window. Regexes for
  destructive or single-word intents are anchored (`^...$`) so a phrase like "restart
  chrome" or "play some music" falls through to the LLM instead of firing a system
  action. Keep new destructive patterns anchored and object-qualified.
- Secrets are read from the environment first, `config.yaml` second (see
  `ANTHROPIC_API_KEY`, `SPOTIFY_CLIENT_ID`/`SPOTIFY_CLIENT_SECRET`). Cached OAuth
  tokens belong in `system._user_cache_dir()` (`%LOCALAPPDATA%\SAM\`), never the repo.

## UI performance rules

The overlay is always-running background software, so idle cost matters:

- Animation `QTimer`s must be started in `showEvent` and stopped in `hideEvent`.
  `WaveformWidget` additionally stops its own timer once the animation settles at rest,
  so a hidden or idle SAM paints nothing at all.
- Don't allocate `QPainterPath` / `QGradient` / `QPen` per frame. `FloatingBar` caches
  its background objects on first paint; `WaveformWidget` reuses a single
  `ObjectBoundingMode` gradient across all 35 bars and only rebuilds it when the color
  or a coarse alpha bucket changes.
- `WaveformWidget.set_level()` takes the live mic RMS (routed from
  `Recorder.level_update` → `AppController._on_audio_level` → `FloatingBar.set_level`),
  so the bars track real speech rather than a canned sine loop.
