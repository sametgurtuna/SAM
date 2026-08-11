<div align="center">

# 🏗️ SAM — Architecture

**Internal technical reference.** Trust this and the source over anything else if they
disagree — this file is kept close to the code, but the code always wins.

<p>
  <img src="https://img.shields.io/badge/state_machine-4_states-38F2D8?style=flat-square">
  <img src="https://img.shields.io/badge/threading-signals_only-00BFFF?style=flat-square">
  <img src="https://img.shields.io/badge/overlay-4_windows-00D4AA?style=flat-square">
</p>

</div>

---

## Contents

1. [Orchestration model](#1-orchestration-model)
2. [Pipeline](#2-pipeline)
3. [State machine](#3-state-machine)
4. [Threading](#4-threading)
5. [The overlay](#5-the-overlay)
6. [Ollama lifecycle](#6-ollama-lifecycle)
7. [Paths — dev vs. frozen exe](#7-paths--dev-vs-frozen-exe)
8. [Single-instance guard](#8-single-instance-guard)
9. [Packaging](#9-packaging)
10. [Module reference](#10-module-reference)

---

## 1. Orchestration model

Everything is wired together by **`AppController`** (`core/app.py`), a `QObject` that owns
every engine and connects them purely through PyQt signals/slots.

```mermaid
flowchart TB
    subgraph AC["AppController — core/app.py"]
        direction TB
        STATE["_state: AppState"]
    end

    WW["WakeWordEngine"] -- "detected(audio)" --> AC
    REC["Recorder"] -- "recording_done(np.ndarray)\nlevel_update(float)" --> AC
    STT["STTEngine"] -- "transcript_ready(str)\npartial_transcript(str)" --> AC
    LLM["LLMRouter"] -- "token_received(str)\ngeneration_complete(str)\ngeneration_error(str)" --> AC
    TTS["TTSEngine"] -- "playback_finished()" --> AC
    OV["SamOverlay"] -- "text_submitted(str)" --> AC

    AC -- "direct method calls\n(activate/set_state/…)" --> OV
    AC -- "start() / speak() / generate()" --> WW & REC & STT & LLM & TTS

    style AC fill:#12121a,stroke:#00D4AA,stroke-width:2px,color:#e8e8e8
```

**No engine calls another engine directly** — `WakeWordEngine` doesn't know `Recorder`
exists; `STTEngine` doesn't know about `LLMRouter`. `AppController` is the only component
that knows the whole pipeline, and `AppController._set_state()` is the only place UI state
changes. This is the file to read first when tracing any feature end to end.

---

## 2. Pipeline

```mermaid
flowchart LR
    A["🎙️ Wake word"] --> D{{"AppController\n._on_trigger"}}
    B["⌨️ Ctrl+Space"] --> D
    C["⌨️ Typed input"] --> E["_on_transcript_ready()"]

    D --> R["Recorder\n(VAD)"]
    R --> S["STTEngine\nfaster-whisper"]
    S --> E

    E --> M{"CommandRouter\nmatch?"}
    M -- "yes" --> H["OS action\nspoken confirmation"]
    M -- "no" --> L["LLMRouter\nOllama / Claude, streaming"]

    H --> T["TTSEngine"]
    L --> T
    T --> I["auto-hide timer\n→ IDLE"]

    style E fill:#12121a,stroke:#00D4AA,color:#e8e8e8
    style M fill:#12121a,stroke:#00BFFF,color:#e8e8e8
```

Three entry points converge on the same downstream pipeline. **Typed input**
(`Ctrl+Shift+Space`, or clicking the orb) skips recording/STT entirely:
`AppController.submit_text()` sets state to `THINKING` and calls
`_on_transcript_ready()` directly — the exact method the STT pipeline calls — so command
routing and LLM generation behave identically whether the words came from a microphone or
a keyboard.

> **Streaming TTS.** The LLM response is spoken while it is still generating.
> `_flush_streaming_tts()` watches the accumulating token buffer and hands each completed
> sentence to `TTSEngine.speak_chunk()`; `_on_llm_complete` sends whatever prose is left and
> calls `end_stream()`. `TTSEngine` is a queue plus one persistent worker thread —
> `playback_finished` fires once per utterance, on the `end` marker, not per chunk. A
> ```` ``` ```` fence in the stream stops streaming speech for that turn
> (`core/code_parser.py` writes the code to the Desktop instead; it's never read aloud).

---

## 3. State machine

`AppState` is four plain string constants — not an enum, not six states:

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> LISTENING: wake word / hotkey / typed text
    LISTENING --> THINKING: VAD silence, or empty
    THINKING --> SPEAKING: command matched, spoken
    THINKING --> SPEAKING: first LLM token
    SPEAKING --> IDLE: TTS finished + auto-hide timeout

    note right of THINKING
        Covers BOTH "transcribing"
        and "waiting on the LLM" —
        no separate state for each.
        The caption text communicates
        the sub-phase, not the FSM.
    end note
```

`AppController._set_state()` is the single funnel: it updates `self._state` and calls
`self._bar.set_state(new_state)` — nothing else touches overlay state directly.

---

## 4. Threading

```mermaid
flowchart TB
    subgraph MAIN["Qt main thread"]
        UI["Overlay paint / animation timers"]
        SIG["Signal handlers in AppController"]
    end

    subgraph WORKERS["daemon threading.Thread — one per engine"]
        T1["WakeWordEngine"]
        T2["Recorder"]
        T3["STTEngine"]
        T4["TTSEngine worker"]
        T5["OllamaEngine / ClaudeEngine"]
        T6["OllamaService.ensure_running"]
        T7["LLMRouter.refresh_engine"]
    end

    T1 -. "pyqtSignal only" .-> SIG
    T2 -. "pyqtSignal only" .-> SIG
    T3 -. "pyqtSignal only" .-> SIG
    T4 -. "pyqtSignal only" .-> SIG
    T5 -. "pyqtSignal only" .-> SIG
    T6 -. "pyqtSignal only" .-> SIG
    T7 -. "pyqtSignal only" .-> SIG

    style MAIN fill:#0d1420,stroke:#00BFFF
    style WORKERS fill:#0d1a16,stroke:#00D4AA
```

Every engine that blocks does its work on a daemon thread and reports back to the Qt main
thread **exclusively** via `pyqtSignal`. Never touch a PyQt widget from inside one of
these threads.

`LLMRouter` is worth calling out specifically: engine detection (`is_available()`, a
2-second-timeout HTTP probe) used to run synchronously in `__init__` and again on *every*
`generate()` call — a real, measured 2-second stall on the Qt thread whenever Ollama was
down. It's now `QTimer.singleShot(0, refresh_engine)` at startup and never probes on the
hot path; redetection is driven asynchronously by `OllamaService.ready`, a connection-error
heuristic on `generation_error`, or an optional staleness TTL — all dispatching a
background probe and applying the result later via a queued signal.

---

## 5. The overlay

```mermaid
flowchart TB
    OV["SamOverlay — ui/overlay.py\n(facade: activate / dismiss / set_state / set_level /\nset_transcript / clear_transcript)"]
    OV --> ORB["OrbWindow\nui/orb.py"]
    OV --> CAP["CaptionWindow\nui/caption.py"]
    OV --> INP["TextInputWindow\nui/text_input.py"]

    ORB -. "position_changed" .-> OV
    ORB -. "clicked" .-> OV
    INP -. "submitted(str)" .-> OV
    OV -. "text_submitted(str)" .-> AC["AppController"]

    style OV fill:#12121a,stroke:#00D4AA,stroke-width:2px,color:#e8e8e8
```

Four top-level windows, one facade. `SamOverlay` presents the exact method surface
`FloatingBar` (the legacy bottom bar, `ui.overlay.style: bar`) used to, so
`AppController` only differs by which class it constructs. Semantics shifted, though:
`activate()` no longer shows a window (the orb is always visible) — it energises the ring
and fades the caption in; `dismiss()` fades the caption back out and lets the orb settle
to breathing. The orb itself never hides during a normal session.

### Click-through and the circular hit-test

A window can be `WS_EX_TRANSPARENT` (receives no mouse input at all — used for the
caption, and for the orb when disabled), or it can answer `WM_NCHITTEST` itself. The orb
does the latter:

```mermaid
flowchart LR
    M["WM_NCHITTEST\nscreen x,y"] --> D{"inside the\ncircular hit radius?"}
    D -- yes --> C["HTCLIENT\nclick lands on the orb"]
    D -- no --> T["HTTRANSPARENT\nclick falls through to the desktop"]
```

`OrbWindow.nativeEvent()` intercepts `WM_NCHITTEST` and returns `HTTRANSPARENT` for every
point outside its circular hit radius, `HTCLIENT` inside it — so the square window around
the circle lets clicks fall through everywhere except the visible disc.

> ⚠️ **`super().nativeEvent()` is deliberately never called** in this handler. PyQt6's
> default implementation returns an invalid pointer for this message and crashes the
> process with an access violation if allowed to run.

### Z-order: the `auto` layer

```mermaid
sequenceDiagram
    participant U as User
    participant Orb as OrbWindow
    participant Win as SetWindowPos (win32.py)

    Note over Orb: idle — HWND_BOTTOM<br/>below every normal window
    U->>Orb: wake word / hotkey / click
    Orb->>Orb: set_state(LISTENING)
    Orb->>Win: bring_to_top(hwnd)
    Note over Orb: engaged — HWND_TOPMOST
    U->>Orb: session ends → IDLE
    Orb->>Win: send_to_bottom(hwnd)
    Note over Orb: back to the bottom
```

`ui.orb.layer` (default `auto`) makes the orb sit at the very bottom of the Windows
z-order — below every normal window, above only the wallpaper — until it's actually
summoned. `ui/win32.py` wraps `SetWindowPos` with the `HWND_BOTTOM` / `HWND_TOPMOST`
pseudo-handles for this; `OrbWindow._sync_zorder()` calls it whenever the engaged/idle
state flips (`set_state`) or the typed-input box opens/closes
(`set_foreground_request`) — the two conditions are OR'd, so opening the text box while
idle still brings the orb forward. `topmost` (always on top, the old default) and `normal`
(no special handling) are also available, static, and never touch `SetWindowPos`.

A 2-second `QTimer` watchdog (`_check_fullscreen`) additionally hides the orb while a
genuinely fullscreen window (a game, a video — not just a maximized app; the check requires
no title bar/border, see `win32.foreground_is_fullscreen`) is in the foreground, unless SAM
is actively engaged, in which case it's exempt so the orb still appears when called.

### Typed input and the foreground-lock problem

`TextInputWindow` is the one overlay window that must take keyboard focus, so — unlike the
orb and caption — it does **not** set `WA_ShowWithoutActivating`. That alone isn't enough:
Windows' foreground lock silently refuses `SetForegroundWindow` from a background process
(exactly SAM's situation when a global hotkey fires), so `win32.force_foreground()`
attaches to the current foreground thread's input queue for the duration of the call to
lift the restriction.

The hotkey shares the existing single `keyboard` listener thread
(`AppController._register_hotkey`) rather than spawning a second one. Because `keyboard`
fires a hotkey when its keys are down regardless of *extra* modifiers held,
`ctrl+shift+space` is a superset of `ctrl+space` and would otherwise also fire the voice
trigger; `_on_hotkey_pressed` checks whether the text hotkey's extra keys are currently
held and bails out if so.

---

## 6. Ollama lifecycle

```mermaid
flowchart TD
    Start(["AppController starts\nautostart: true"]) --> Ping{"/api/tags\nresponds?"}
    Ping -- yes --> Already["already running\n_we_started = False"]
    Ping -- no --> Find{"ollama.exe\nfound?"}
    Find -- no --> Unavail1["unavailable('not-installed')"]
    Find -- yes --> Spawn["Popen([exe, 'serve'],\nCREATE_NO_WINDOW | DETACHED_PROCESS)"]
    Spawn --> Poll["poll /api/tags\nevery 500ms"]
    Poll -- "ready within timeout" --> Ready["ready"]
    Poll -- "timeout" --> Unavail2["unavailable('timeout')"]

    Already --> Ready
    style Ready fill:#0d3b32,stroke:#00D4AA,color:#e8e8e8
    style Spawn fill:#0d2a3b,stroke:#00BFFF,color:#e8e8e8
```

`llm/ollama_engine.py` is a pure HTTP client; `llm/ollama_service.py` (`OllamaService`)
owns the *process*, entirely on a daemon thread. Executable lookup order: config override →
`PATH` → the two locations the official Windows installer uses.

On shutdown, the server is terminated **only if** `_we_started` **and**
`llm.ollama.stop_on_exit` is true (default `false`) — SAM never kills a server the user
already had running, and doesn't kill its own by default either, since model load time is
expensive.

---

## 7. Paths — dev vs. frozen exe

```mermaid
flowchart LR
    subgraph Dev["Source checkout"]
        D1["resource_root() = repo root"]
        D2["user_data_dir() = repo root"]
    end
    subgraph Frozen["Installed exe"]
        F1["resource_root() = sys._MEIPASS\n(read-only)"]
        F2["user_data_dir() = %APPDATA%\\SAM\n(writable)"]
    end
```

`core/paths.py` is the single source of truth for "where do files live?" — separating a
read-only bundle from writable per-user state. The dev-mode fallback is deliberate:
`user_data_dir()` returning the repo root in development means `config.yaml`, `logs/`, and
`assets/` resolve exactly where they always did, so this refactor changed nothing for a
source checkout. Only the frozen build relocates.

`Config.load()` seeds a fresh `%APPDATA%\SAM\config.yaml` from the bundled
`config.example.yaml` the first time it finds none — this is what makes the installed
exe's Settings window able to actually save. (The old behavior wrote into the read-only,
temp-extracted PyInstaller payload and silently lost every change.)

`resolve_asset()` is used wherever a *config value* names a file (the wake word model
path, in particular) — it checks the user data dir, then the bundle, so a value that used
to be resolved against the process's current working directory (breaking whenever SAM was
launched from a shortcut) now resolves consistently regardless of launch method.

---

## 8. Single-instance guard

`core/paths.py::single_instance_lock()` claims a `Local\SAM_SingleInstance` named mutex via
`CreateMutexW`; `main.py` calls it before anything else and exits immediately if another
instance already holds it. This became mandatory once the installer can add a Windows
startup entry — without it, a manual launch on top of the auto-started instance would spawn
a second orb, a second wake-word microphone stream, and two processes fighting over the
same global hotkey.

---

## 9. Packaging

```mermaid
flowchart LR
    SRC["Source tree"] --> SPEC["SAM.spec\nPyInstaller (onedir)"]
    SPEC --> DIST["dist/SAM/"]
    DIST --> ISS["installer/SAM.iss\nInno Setup"]
    ISS --> EXE["SAM-Setup-x.y.z.exe"]

    EXE -. "--install-models" .-> STEPS["core/installer_steps.py\n(no Qt)"]
    STEPS -. "ollama pull" .-> M1["language model"]
    STEPS -. "WhisperModel(download_root=...)" .-> M2["speech model"]

    style SPEC fill:#12121a,stroke:#00D4AA,color:#e8e8e8
    style ISS fill:#12121a,stroke:#00BFFF,color:#e8e8e8
```

- **`SAM.spec`** bundles the wake word model, activation chime, `config.example.yaml`, and
  the native libraries PyInstaller doesn't auto-detect (`ctranslate2`, `onnxruntime`). It
  deliberately excludes `torch`/`torchvision` (openwakeword's unused training-only
  backend — SAM always runs it with `inference_framework="onnx"`), which alone cuts the
  build from ~830 MB to ~450 MB. It refuses to build at all if `config.yaml` or any OAuth
  cache file would be bundled — a hard assertion, not just a `.gitignore` entry.
- **`installer/SAM.iss`** is a per-user install (no admin required), with tasks for
  installing Ollama, pre-pulling the model, and pre-downloading the Whisper model. Model
  downloads run through `SAM.exe --install-models` rather than a second helper binary,
  specifically so the installer and the running app can never disagree about model names
  or download paths.

---

## 10. Module reference

<table>
<tr><th>Package</th><th>Contents</th></tr>
<tr><td><code>core/</code></td><td>
<code>app.py</code> (controller/state machine) ·
<code>config.py</code> (defaults + loader/saver) ·
<code>paths.py</code> (dev/frozen path resolution, single-instance lock) ·
<code>code_parser.py</code> (pulls code blocks out of LLM replies) ·
<code>installer_steps.py</code> (installer-only, no Qt)
</td></tr>
<tr><td><code>audio/</code></td><td>
<code>wake_word.py</code> · <code>recorder.py</code> · <code>stt.py</code> ·
<code>tts.py</code> · <code>sounds.py</code>
</td></tr>
<tr><td><code>commands/</code></td><td>
<code>router.py</code> (regex intent matching, chained commands via "and"/"ve") ·
<code>system.py</code> (all OS side effects — app launch/kill, volume, power, Spotify,
and the shell-launch blocklist) ·
<code>vision.py</code> (screen capture for vision-model requests)
</td></tr>
<tr><td><code>llm/</code></td><td>
<code>base.py</code> (abstract <code>LLMEngine</code>) · <code>ollama_engine.py</code> ·
<code>ollama_service.py</code> (process lifecycle, distinct from the HTTP client) ·
<code>claude_engine.py</code> · <code>router.py</code>
</td></tr>
<tr><td><code>ui/</code></td><td>
<code>orb.py</code> / <code>caption.py</code> / <code>text_input.py</code> /
<code>overlay.py</code> (the current overlay) ·
<code>win32.py</code> (click-through / z-order / foreground-focus ctypes helpers) ·
<code>floating_bar.py</code> + <code>waveform.py</code> (legacy bar, still selectable) ·
<code>settings_window.py</code> · <code>tray.py</code> · <code>styles.py</code> ·
<code>icon_generator.py</code>
</td></tr>
<tr><td><code>tools/make_icon.py</code></td><td>
Regenerates <code>assets/icon.ico</code> from the orb design — run by hand after a visual
change, the output is committed.
</td></tr>
<tr><td><code>main.py</code></td><td>
single-instance check → config load → logging setup → <code>QApplication</code> →
<code>AppController</code> → <code>TrayManager</code> → event loop. Also the
<code>--install-models</code> argv branch used by the installer.
</td></tr>
</table>

<div align="center">

For usage, see the **[README](../README.md)**; for a step-by-step install, see the
**[Setup Guide](../setup.md)**.

</div>
