# SAM — Application Controller
# Manages the full lifecycle: wake word → record → STT → LLM → TTS → dismiss.
# Phase 3: Real LLM integration via Ollama (local) or Claude (cloud fallback).

import logging
import threading

import numpy as np
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

from core.config import config
from audio.wake_word import WakeWordEngine
from audio.recorder import Recorder
from audio.stt import STTEngine
from audio.tts import TTSEngine
from audio.sounds import play_activation_sound
from llm.router import LLMRouter
from llm.ollama_service import OllamaService
from commands.router import CommandRouter
from commands.instant import InstantResponder

logger = logging.getLogger(__name__)


class AppState:
    """State constants for SAM's interaction lifecycle."""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


class AppController(QObject):
    """
    Central controller for SAM.
    
    Orchestrates the complete pipeline:
        1. Wake word detection (continuous background listener)
        2. Audio recording with silence detection
        3. Speech-to-text transcription (faster-whisper)
        4. LLM response generation (Ollama local or Claude cloud)
        5. Text-to-speech output (edge-tts)
        6. Floating bar UI state management
    """

    # Signal emitted from hotkey thread → main Qt thread
    trigger_signal = pyqtSignal(object)
    # Text-input hotkey → main Qt thread
    text_input_signal = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        self._state: str = AppState.IDLE

        # Overlay — "orb" is the default always-visible circular overlay;
        # "bar" brings back the legacy bottom sliding bar.
        # Both expose the identical API.
        overlay_style = config.get("ui", "overlay", "style", default="orb")
        if overlay_style == "bar":
            from ui.floating_bar import FloatingBar
            self._bar = FloatingBar()
        else:
            from ui.overlay import SamOverlay
            self._bar = SamOverlay()
            self._bar.text_submitted.connect(self.submit_text)

        # ─── Audio engines ────────────────────────────────────────
        self._wake_word = WakeWordEngine()
        self._recorder = Recorder()
        self._stt = STTEngine()
        self._tts = TTSEngine()

        # ─── LLM engine ──────────────────────────────────────────
        self._llm = LLMRouter()

        # ─── Ollama server lifecycle ─────────────────────────────
        # Automatically start the local Ollama server in the background
        # if not already running.
        self._ollama = OllamaService()
        self._ollama.ready.connect(self._llm.refresh_engine)
        self._ollama.unavailable.connect(self._on_ollama_unavailable)
        if config.get("llm", "ollama", "autostart", default=True):
            self._ollama.ensure_running()

        # ─── Command Router ──────────────────────────────────────
        self._cmd_router = CommandRouter()

        # ─── Instant responses ───────────────────────────────────
        # Predefined phrases answered instantly without calling the LLM.
        self._instant: InstantResponder | None = None
        if config.get("instant", "enabled", default=True):
            self._instant = InstantResponder(
                config.get("instant", "file", default=None)
            )

        # ─── Wire signals ─────────────────────────────────────────

        # Trigger sources → activation
        self.trigger_signal.connect(self._on_trigger)
        self.text_input_signal.connect(self._open_text_input)
        self._wake_word.detected.connect(self._on_trigger)

        # Recorder → STT pipeline
        self._recorder.recording_done.connect(self._on_recording_done)
        self._recorder.level_update.connect(self._on_audio_level)
        self._recorder.partial_audio.connect(self._on_partial_audio)

        # STT → LLM pipeline
        self._stt.partial_transcript.connect(self._on_partial_transcript)
        self._stt.transcript_ready.connect(self._on_transcript_ready)
        # Bilingual TTS — select voice/language instruction based on detected speech
        self._stt.language_detected.connect(self._on_language_detected)

        # LLM → TTS pipeline
        self._llm.token_received.connect(self._on_llm_token)
        self._llm.generation_complete.connect(self._on_llm_complete)
        self._llm.generation_error.connect(self._on_llm_error)

        # TTS → completion
        self._tts.playback_finished.connect(self._on_tts_finished)
        # Follow text in caption window as TTS begins playing each sentence chunk
        self._tts.playback_started.connect(self._on_tts_chunk_started)

        # ─── Auto-hide timer ─────────────────────────────────────
        self._auto_hide_delay: int = config.get(
            "ui", "auto_hide", "delay_seconds", default=4
        ) * 1000

        # Cancellable auto-hide timer for new triggers during cooldown
        self._auto_hide_timer: QTimer | None = None

        # ─── LLM streaming state ─────────────────────────────────
        self._llm_response_text: str = ""
        # Prefix already sent to TTS during streaming
        self._tts_spoken_text: str = ""
        # If code block (```) appears in response, stop TTS streaming
        self._tts_stream_ok: bool = True
        # FIFO queue of (start, end) ranges corresponding to speak_chunk calls
        self._tts_chunk_ranges: list[tuple[int, int]] = []

        # ─── Last transcript (for context) ────────────────────────
        self._last_transcript: str = ""

        # ─── Bilingual TTS state ───────────────────────────────────
        # Last detected language from STT
        self._detected_language: str | None = None

        # ─── Start wake word and hotkey ───────────────────────────
        self._register_hotkey()
        self._wake_word.start()

        # Pre-load Whisper model in background (avoids delay on first use)
        self._preload_stt_model()
        # Pre-warm RAG (embedding model + index) so the first Fenerbahce
        # question doesn't pay the load cost inline.
        self._preload_rag()

        logger.info("AppController initialized — state: %s, LLM: %s",
                     self._state, self._llm.active_engine_name)

    def _preload_stt_model(self) -> None:
        """Pre-load the Whisper model in a background thread."""
        def _load():
            logger.info("Pre-loading Whisper model in background...")
            self._stt.load_model()
        thread = threading.Thread(target=_load, daemon=True, name="STTPreload")
        thread.start()

    def _preload_rag(self) -> None:
        """Pre-warm the RAG engine (embedding model + index) in the background."""
        if not config.get("llm", "rag", "enabled", default=True):
            return

        def _load():
            logger.info("Pre-warming RAG engine in background...")
            self._llm.warm_rag()
        thread = threading.Thread(target=_load, daemon=True, name="RAGPreload")
        thread.start()

    @staticmethod
    def _combo_keys(combo: str) -> set[str]:
        return {part.strip().lower() for part in combo.split("+") if part.strip()}

    def _register_hotkey(self) -> None:
        """Register global hotkeys in a background thread (keyboard library blocks)."""
        trigger_combo: str = config.get("hotkey", "trigger", default="ctrl+space")
        text_combo: str = config.get("hotkey", "text_input", default="ctrl+shift+space")

        # `keyboard` does not distinguish superset modifiers; calculate difference
        self._text_hotkey_extra_keys: set[str] = (
            self._combo_keys(text_combo) - self._combo_keys(trigger_combo)
        )

        def _listen_hotkey():
            try:
                import keyboard
            except ImportError:
                logger.error("keyboard module not installed. Run: pip install keyboard")
                return

            # Register each hotkey independently
            try:
                keyboard.add_hotkey(trigger_combo, self._on_hotkey_pressed)
                logger.info("Voice hotkey registered: %s", trigger_combo)
            except Exception as e:
                logger.error("Failed to register voice hotkey '%s': %s", trigger_combo, e)

            if text_combo:
                try:
                    keyboard.add_hotkey(text_combo, self._on_text_hotkey_pressed)
                    logger.info("Text input hotkey registered: %s", text_combo)
                except Exception as e:
                    logger.error("Failed to register text hotkey '%s': %s", text_combo, e)

            try:
                keyboard.wait()
            except Exception as e:
                logger.error("Hotkey listener stopped: %s", e)

        hotkey_thread = threading.Thread(target=_listen_hotkey, daemon=True)
        hotkey_thread.start()

    def _on_hotkey_pressed(self) -> None:
        """Called from hotkey thread — emits signal to Qt main thread."""
        if self._text_hotkey_extra_keys:
            try:
                import keyboard
                # If extra modifiers of the text shortcut are pressed, ignore voice trigger
                if any(keyboard.is_pressed(k) for k in self._text_hotkey_extra_keys):
                    return
            except Exception:
                pass
        logger.debug("Hotkey pressed")
        self.trigger_signal.emit(None)

    def _on_text_hotkey_pressed(self) -> None:
        """Called from hotkey thread — emits signal to Qt main thread."""
        logger.debug("Text input hotkey pressed")
        self.text_input_signal.emit()

    # ─── Activation ───────────────────────────────────────────────

    def _on_trigger(self, pre_audio: object = None) -> None:
        """Handle activation trigger (from wake word or hotkey)."""

        # If a new trigger arrives during cooldown (SPEAKING):
        # cancel active auto-hide timer and begin a fresh listening session
        if self._state == AppState.SPEAKING:
            logger.info("New trigger during cooldown — starting new session")
            self._cancel_auto_hide_timer()
            self._tts.stop()
            self._wake_word.pause()
            play_activation_sound()
            self._start_listening(pre_audio)
            return

        if self._state != AppState.IDLE:
            # Triggered during LISTENING or THINKING — cancel and dismiss
            logger.debug("Trigger while active — dismissing")
            self._cancel_and_reset()
            return

        logger.info("SAM activated")

        # Pause wake word to prevent self-trigger from TTS output
        self._wake_word.pause()

        # Play activation sound
        play_activation_sound()

        # Start listening
        self._start_listening(pre_audio)

    # ─── Typed input ──────────────────────────────────────────────

    def _open_text_input(self) -> None:
        """Open (or close) the typed-input box under the orb."""
        if not hasattr(self._bar, "toggle_text_input"):
            logger.debug("Text input is not available with the legacy bar overlay")
            return

        # Typing takes precedence over active recording
        if self._state == AppState.LISTENING:
            self._cancel_and_reset()

        self._bar.toggle_text_input()

    def submit_text(self, text: str) -> None:
        """
        Handle typed input. Reuses the exact transcript pipeline, so command
        router → LLM → TTS all behave identically to a spoken question.
        """
        text = text.strip()
        if not text:
            return

        logger.info("Typed input: '%s'", text)

        # Stop any active tasks
        self._cancel_auto_hide_timer()
        self._recorder.stop()
        self._llm.stop()
        self._tts.stop()
        self._wake_word.pause()

        # Switch state to THINKING
        self._set_state(AppState.THINKING)
        self._bar.activate()

        self._on_transcript_ready(text)

    # ─── State Machine ────────────────────────────────────────────

    def _set_state(self, new_state: str) -> None:
        """Transition to a new state and update the UI."""
        old_state = self._state
        self._state = new_state
        self._bar.set_state(new_state)
        logger.debug("State: %s -> %s", old_state, new_state)

    def _start_listening(self, pre_audio: object = None) -> None:
        """LISTENING — activate bar and start recording from microphone."""
        self._set_state(AppState.LISTENING)
        self._bar.clear_transcript()
        self._bar.activate()
        # Reset live transcript for new session
        self._stt.reset_partial()

        # Start real microphone recording
        self._recorder.start(pre_audio)

    def _on_audio_level(self, level: float) -> None:
        """Receive live audio level from recorder and drive the waveform."""
        self._bar.set_level(level)

    def _on_partial_audio(self, audio_data: object) -> None:
        """Receive live audio buffer while recording and perform fast partial decoding."""
        if self._state == AppState.LISTENING and audio_data is not None:
            self._stt.transcribe_partial(audio_data)

    # Minimum audio coverage required to qualify for the fast path
    _FAST_PATH_COVERAGE = 0.9

    def _on_recording_done(self, audio_data: object) -> None:
        """Recording finished — try the fast path, otherwise run final STT."""
        if audio_data is None:
            logger.warning("No speech captured — returning to idle")
            self._cancel_and_reset()
            return

        # ─── Fast path ────────────────────────────────────────────
        # If the partial transcript covers nearly all of the recording
        # and matches a known instant response or command, answer immediately.
        partial = self._stt.last_partial_text
        covered = self._stt.last_partial_samples
        if partial and covered >= len(audio_data) * self._FAST_PATH_COVERAGE:
            if self._dispatch(partial, allow_llm=False):
                logger.info("Fast path hit — skipped final transcription")
                return

        logger.info("Recording done — starting final transcription")
        self._set_state(AppState.THINKING)

        # Send to STT engine
        self._stt.transcribe(audio_data)

    def _on_partial_transcript(self, text: str) -> None:
        """Live partial transcript from STT — update bar display in real time."""
        if self._state in (AppState.LISTENING, AppState.THINKING):
            self._bar.set_transcript(text)

    # ─── Bilingual TTS ────────────────────────────────────────────

    # Currently supported TTS languages (see config tts.voices)
    _SUPPORTED_TTS_LANGS = {"tr", "en"}
    # Minimum confidence threshold to switch language dynamically
    _LANG_CONFIDENCE_MIN = 0.5

    def _on_language_detected(self, language: str, probability: float) -> None:
        """
        STT emits detected language for each transcription.
        Update TTS voice and LLM instructions accordingly if confidence is high.
        """
        if not config.get("tts", "auto_language", default=True):
            return
        if probability < self._LANG_CONFIDENCE_MIN or language not in self._SUPPORTED_TTS_LANGS:
            return

        self._apply_tts_language(language)
        logger.debug("Language detected: %s (%.2f)", language, probability)

    def _apply_tts_language(self, language: str) -> None:
        """Set spoken language and select corresponding TTS voice."""
        if not config.get("tts", "auto_language", default=True):
            return
        if language not in self._SUPPORTED_TTS_LANGS:
            return

        self._detected_language = language
        voices = config.get("tts", "voices", default={}) or {}
        voice = voices.get(language) or config.get("tts", "voice", default="en-US-GuyNeural")
        self._tts.set_voice(voice)

    def _on_transcript_ready(self, transcript: str) -> None:
        """Full transcription complete — send to LLM."""
        if not transcript.strip():
            logger.warning("Empty transcription — returning to idle")
            self._cancel_and_reset()
            return

        logger.info("Transcript: '%s'", transcript)
        self._dispatch(transcript, allow_llm=True)

    def _dispatch(self, transcript: str, *, allow_llm: bool) -> bool:
        """
        Evaluate text sequentially:
            1. Instant response (predefined dictionary lookup)  → speak immediately
            2. System command (regex router)                   → execute and confirm
            3. Conversational query                            → route to LLM (if allow_llm=True)

        The first two paths never touch the LLM or enter THINKING state.
        When allow_llm=False (fast path), returns False if no instant hit/command matched.
        """
        self._last_transcript = transcript

        # 1. Instant response — fast dictionary lookup
        if self._instant is not None:
            hit = self._instant.match(transcript)
            if hit:
                reply, lang = hit
                logger.info("Instant response: '%s' → '%s'", transcript, reply)
                self._apply_tts_language(lang)
                self._speak_now(reply)
                return True

        # 2. System command (without LLM)
        cmd_result = self._cmd_router.try_handle(transcript, vision=allow_llm)
        if cmd_result.handled:
            if cmd_result.response:
                self._speak_now(cmd_result.response)
            else:
                self._cancel_and_reset()
            return True

        if not allow_llm:
            return False

        # 3. Conversational query — forward to LLM
        self._bar.set_transcript(transcript)

        # Extract persistent facts in background (name, profession, etc.)
        self._extract_and_store_facts(transcript)

        if self._state != AppState.THINKING:
            self._set_state(AppState.THINKING)

        self._generate_response(cmd_result.image_b64)
        return True

    def _speak_now(self, text: str) -> None:
        """Speak pre-formatted text immediately — skips LLM and THINKING state."""
        self._set_state(AppState.SPEAKING)
        self._bar.set_transcript(text)
        self._tts.speak(text)

    def _generate_response(self, image_b64: str | None = None) -> None:
        """Send transcript to LLM and stream the response."""
        self._bar.set_transcript("Thinking...")
        self._llm_response_text = ""
        self._tts_spoken_text = ""
        self._tts_stream_ok = True
        self._tts_chunk_ranges = []
        # Clear previous utterance queue before new generation
        self._tts.stop()

        # Send to LLM router (auto-detects Ollama or Claude)
        self._llm.generate(
            self._last_transcript,
            image_b64=image_b64,
            language=self._detected_language,
        )

    def _extract_and_store_facts(self, transcript: str) -> None:
        """
        Extract personal facts (name, profession, field, etc.) from transcript
        and store in persistent memory. Runs asynchronously in a background thread.
        """
        if not config.get("llm", "memory", "enabled", default=True):
            return

        def _run():
            from llm.fact_extractor import extract_facts
            for category, key, value in extract_facts(transcript):
                self._llm.remember(category, key, value)

        thread = threading.Thread(target=_run, daemon=True, name="FactExtract")
        thread.start()

    # ─── LLM Streaming ────────────────────────────────────────────

    def _on_llm_token(self, token: str) -> None:
        """Receive a streaming token from the LLM — update bar in real time."""
        if self._state == AppState.THINKING:
            # First token received — switch to speaking state
            self._set_state(AppState.SPEAKING)
            self._bar.clear_transcript()

        self._llm_response_text += token
        self._bar.set_transcript(self._llm_response_text)
        self._flush_streaming_tts()

    # ─── Streaming TTS ────────────────────────────────────────────

    # Sentence boundary punctuation marks
    _SENTENCE_ENDINGS = (".", "!", "?", "\n", "…")
    # Minimum length for a speech chunk to avoid fragmented audio
    _MIN_TTS_CHUNK = 12

    def _flush_streaming_tts(self) -> None:
        """
        Forward completed sentences to TTS while the LLM is still generating tokens.
        """
        if not self._tts_stream_ok:
            return

        pending = self._llm_response_text[len(self._tts_spoken_text):]

        # Stop streaming TTS if code block starts
        if "```" in pending:
            self._tts_stream_ok = False
            return

        # Find latest sentence boundary
        cut = -1
        for i, ch in enumerate(pending):
            if ch in self._SENTENCE_ENDINGS:
                cut = i
        if cut < 0:
            return

        chunk = pending[: cut + 1]
        if len(chunk.strip()) < self._MIN_TTS_CHUNK:
            return

        start = len(self._tts_spoken_text)
        self._tts_spoken_text += chunk
        self._tts_chunk_ranges.append((start, len(self._tts_spoken_text)))
        self._tts.speak_chunk(chunk.strip())

    def _on_tts_chunk_started(self) -> None:
        """
        TTS began playback of the next chunk — update text-follow range in caption window.
        """
        if not self._tts_chunk_ranges:
            return
        start, end = self._tts_chunk_ranges.pop(0)
        self._bar.follow_to(start, end)

    def _on_llm_complete(self, full_response: str) -> None:
        """LLM generation complete — speak the response aloud."""
        if not full_response.strip():
            logger.warning("Empty LLM response — returning to idle")
            self._cancel_and_reset()
            return

        # Ensure we're in speaking state
        if self._state != AppState.SPEAKING:
            self._set_state(AppState.SPEAKING)

        # Show full response text
        self._bar.set_transcript(full_response)

        logger.info("LLM response: '%s'", full_response[:80])

        # Extract code blocks to desktop and strip them from TTS
        from core.code_parser import extract_and_save_code
        spoken_response = extract_and_save_code(full_response)

        # Avoid re-speaking parts already streamed
        already = self._tts_spoken_text
        if already and spoken_response.startswith(already):
            remainder = spoken_response[len(already):].strip()
            if remainder:
                if spoken_response == full_response:
                    self._tts_chunk_ranges.append((len(already), len(full_response)))
                self._tts.speak_chunk(remainder)
            self._tts.end_stream()
        elif already:
            logger.debug("Streamed TTS prefix diverged — skipping remainder")
            self._tts.end_stream()
        else:
            if spoken_response == full_response:
                self._tts_chunk_ranges.append((0, len(full_response)))
            self._tts.speak(spoken_response)

    def _on_llm_error(self, error: str) -> None:
        """LLM generation failed — show error and dismiss."""
        logger.error("LLM error: %s", error)
        self._bar.set_transcript(error[:100])

        # Auto-dismiss after showing error
        QTimer.singleShot(3000, self._cancel_and_reset)

    # ─── TTS Completion ───────────────────────────────────────────

    def _on_tts_finished(self) -> None:
        """
        TTS playback complete — immediately resume wake word detection,
        and start a cancellable auto-hide timer.
        """
        logger.debug("TTS finished — resuming wake word, auto-hide in %dms",
                      self._auto_hide_delay)

        # Resume wake word detection
        self._wake_word.resume()

        # Start cancellable auto-hide timer
        self._cancel_auto_hide_timer()
        self._auto_hide_timer = QTimer()
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.setInterval(self._auto_hide_delay)
        self._auto_hide_timer.timeout.connect(self._reset_to_idle)
        self._auto_hide_timer.start()

    # ─── Auto-hide Timer Management ───────────────────────────────

    def _cancel_auto_hide_timer(self) -> None:
        """Cancel active auto-hide timer."""
        if self._auto_hide_timer is not None:
            self._auto_hide_timer.stop()
            self._auto_hide_timer.deleteLater()
            self._auto_hide_timer = None

    # ─── Reset ────────────────────────────────────────────────────

    def _cancel_and_reset(self) -> None:
        """Cancel any active operation and return to idle."""
        self._cancel_auto_hide_timer()
        self._recorder.stop()
        self._llm.stop()
        self._tts.stop()
        self._tts_chunk_ranges = []
        self._reset_to_idle()

    def _reset_to_idle(self) -> None:
        """Return to idle state and dismiss the bar."""
        if self._state == AppState.IDLE:
            return  # Already idle, avoid double-dismiss

        self._cancel_auto_hide_timer()
        self._set_state(AppState.IDLE)
        self._bar.dismiss()

        # Resume wake word detection
        self._wake_word.resume()

        logger.info("SAM dismissed — back to idle")

    # ─── Cleanup ──────────────────────────────────────────────────

    def _on_ollama_unavailable(self, reason: str) -> None:
        """Ollama could not be reached — log it; Claude fallback may still work."""
        if reason == "not-installed":
            logger.warning(
                "Ollama is not installed — local LLM unavailable. "
                "Install from https://ollama.com/download, then restart SAM."
            )
        else:
            logger.warning("Ollama server unavailable (%s)", reason)
        # Attempt detection anyway in case Claude API key is configured
        self._llm.refresh_engine()

    def apply_settings(self) -> None:
        """
        Live-apply settings that do not require a restart (orb geometry, colors,
        fps, click-through, auto-hide delay).
        """
        self._auto_hide_delay = config.get(
            "ui", "auto_hide", "delay_seconds", default=4
        ) * 1000
        if hasattr(self._bar, "apply_settings"):
            self._bar.apply_settings()
            self._bar.set_state(self._state)
        logger.info("Settings applied live")

    def shutdown(self) -> None:
        """Clean up all resources on application exit."""
        self._cancel_auto_hide_timer()
        self._wake_word.stop()
        self._recorder.stop()
        self._llm.stop()
        self._ollama.shutdown()
        self._tts.cleanup()
        try:
            import keyboard
            keyboard.unhook_all()
        except Exception:
            pass
        logger.info("AppController shutdown complete")
