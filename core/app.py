# SAM — Application Controller
# Manages the full lifecycle: wake word → record → STT → LLM → TTS → dismiss.
# Phase 3: Real LLM integration via Ollama (local) or Claude (cloud fallback).

import logging
import threading

import numpy as np
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

from core.config import config
from ui.floating_bar import FloatingBar
from audio.wake_word import WakeWordEngine
from audio.recorder import Recorder
from audio.stt import STTEngine
from audio.tts import TTSEngine
from audio.sounds import play_activation_sound
from llm.router import LLMRouter
from commands.router import CommandRouter

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
    trigger_signal = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        self._state: str = AppState.IDLE
        self._bar = FloatingBar()

        # ─── Audio engines ────────────────────────────────────────
        self._wake_word = WakeWordEngine()
        self._recorder = Recorder()
        self._stt = STTEngine()
        self._tts = TTSEngine()

        # ─── LLM engine ──────────────────────────────────────────
        self._llm = LLMRouter()

        # ─── Command Router ──────────────────────────────────────
        self._cmd_router = CommandRouter()

        # ─── Wire signals ─────────────────────────────────────────

        # Trigger sources → activation
        self.trigger_signal.connect(self._on_trigger)
        self._wake_word.detected.connect(self._on_trigger)

        # Recorder → STT pipeline
        self._recorder.recording_done.connect(self._on_recording_done)
        self._recorder.level_update.connect(self._on_audio_level)

        # STT → LLM pipeline
        self._stt.partial_transcript.connect(self._on_partial_transcript)
        self._stt.transcript_ready.connect(self._on_transcript_ready)

        # LLM → TTS pipeline
        self._llm.token_received.connect(self._on_llm_token)
        self._llm.generation_complete.connect(self._on_llm_complete)
        self._llm.generation_error.connect(self._on_llm_error)

        # TTS → completion
        self._tts.playback_finished.connect(self._on_tts_finished)

        # ─── Auto-hide timer ─────────────────────────────────────
        self._auto_hide_delay: int = config.get(
            "ui", "auto_hide", "delay_seconds", default=4
        ) * 1000

        # Iptal edilebilir auto-hide timer — cooldown sirasinda
        # yeni komut geldiginde timer iptal edilebilsin
        self._auto_hide_timer: QTimer | None = None

        # ─── LLM streaming state ─────────────────────────────────
        self._llm_response_text: str = ""

        # ─── Last transcript (for context) ────────────────────────
        self._last_transcript: str = ""

        # ─── Start wake word and hotkey ───────────────────────────
        self._register_hotkey()
        self._wake_word.start()

        # Pre-load Whisper model in background (avoids delay on first use)
        self._preload_stt_model()

        logger.info("AppController initialized — state: %s, LLM: %s",
                     self._state, self._llm.active_engine_name)

    def _preload_stt_model(self) -> None:
        """Pre-load the Whisper model in a background thread."""
        def _load():
            logger.info("Pre-loading Whisper model in background...")
            self._stt.load_model()
        thread = threading.Thread(target=_load, daemon=True, name="STTPreload")
        thread.start()

    def _register_hotkey(self) -> None:
        """Register global hotkey in a background thread (keyboard library blocks)."""
        hotkey_combo: str = config.get("hotkey", "trigger", default="ctrl+space")

        def _listen_hotkey():
            try:
                import keyboard
                keyboard.add_hotkey(hotkey_combo, self._on_hotkey_pressed)
                logger.info("Global hotkey registered: %s", hotkey_combo)
                keyboard.wait()
            except ImportError:
                logger.error(
                    "keyboard module not installed. Run: pip install keyboard"
                )
            except Exception as e:
                logger.error("Failed to register hotkey: %s", e)

        hotkey_thread = threading.Thread(target=_listen_hotkey, daemon=True)
        hotkey_thread.start()

    def _on_hotkey_pressed(self) -> None:
        """Called from hotkey thread — emits signal to Qt main thread."""
        logger.debug("Hotkey pressed")
        self.trigger_signal.emit()

    # ─── Activation ───────────────────────────────────────────────

    def _on_trigger(self) -> None:
        """Handle activation trigger (from wake word or hotkey)."""

        # Cooldown (SPEAKING) sirasinda yeni komut gelirse:
        # mevcut auto-hide timer'i iptal et ve yeni dinleme oturumu baslat
        if self._state == AppState.SPEAKING:
            logger.info("New trigger during cooldown — starting new session")
            self._cancel_auto_hide_timer()
            self._tts.stop()
            self._wake_word.pause()
            play_activation_sound()
            self._start_listening()
            return

        if self._state != AppState.IDLE:
            # LISTENING veya THINKING sirasinda tetiklendi — iptal et
            logger.debug("Trigger while active — dismissing")
            self._cancel_and_reset()
            return

        logger.info("SAM activated")

        # Pause wake word to prevent self-trigger from TTS output
        self._wake_word.pause()

        # Play activation sound
        play_activation_sound()

        # Start listening
        self._start_listening()

    # ─── State Machine ────────────────────────────────────────────

    def _set_state(self, new_state: str) -> None:
        """Transition to a new state and update the UI."""
        old_state = self._state
        self._state = new_state
        self._bar.set_state(new_state)
        logger.debug("State: %s -> %s", old_state, new_state)

    def _start_listening(self) -> None:
        """LISTENING — activate bar and start recording from microphone."""
        self._set_state(AppState.LISTENING)
        self._bar.clear_transcript()
        self._bar.activate()

        # Start real microphone recording
        self._recorder.start()

    def _on_audio_level(self, level: float) -> None:
        """Receive live audio level from recorder for waveform visualization."""
        pass

    def _on_recording_done(self, audio_data: object) -> None:
        """Recording finished — send audio to STT."""
        if audio_data is None:
            logger.warning("No speech captured — returning to idle")
            self._cancel_and_reset()
            return

        logger.info("Recording done — starting transcription")
        self._set_state(AppState.THINKING)
        self._bar.set_transcript("Transcribing...")

        # Send to STT engine
        self._stt.transcribe(audio_data)

    def _on_partial_transcript(self, text: str) -> None:
        """Live partial transcript from STT — update bar display."""
        if self._state == AppState.THINKING:
            self._bar.set_transcript(text)

    def _on_transcript_ready(self, transcript: str) -> None:
        """Full transcription complete — send to LLM."""
        if not transcript.strip():
            logger.warning("Empty transcription — returning to idle")
            self._cancel_and_reset()
            return

        logger.info("Transcript: '%s'", transcript)
        self._last_transcript = transcript
        self._bar.set_transcript(transcript)

        # 1. Once system komutu mu diye kontrol et (LLM'e gitmeden)
        cmd_result = self._cmd_router.try_handle(transcript)
        if cmd_result.handled:
            if cmd_result.response:
                # Komut calisti, yaniti sesli oku
                self._set_state(AppState.SPEAKING)
                self._bar.set_transcript(cmd_result.response)
                self._tts.speak(cmd_result.response)
            else:
                # Yanit yoksa direkt kapat
                self._cancel_and_reset()
            return

        # 2. Sistem komutu degilse, LLM'e yonlendir
        # Brief pause to show the transcript before generating response
        QTimer.singleShot(400, self._generate_response)

    def _generate_response(self) -> None:
        """Send transcript to LLM and stream the response."""
        self._bar.set_transcript("Thinking...")
        self._llm_response_text = ""

        # Send to LLM router (auto-detects Ollama or Claude)
        self._llm.generate(self._last_transcript)

    # ─── LLM Streaming ────────────────────────────────────────────

    def _on_llm_token(self, token: str) -> None:
        """Receive a streaming token from the LLM — update bar in real time."""
        if self._state == AppState.THINKING:
            # First token received — switch to speaking state
            self._set_state(AppState.SPEAKING)
            self._bar.clear_transcript()

        self._llm_response_text += token
        self._bar.set_transcript(self._llm_response_text)

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

        # Speak aloud via TTS
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
        TTS playback complete — wake word'u hemen resume et,
        boylece cooldown sirasinda kullanici yeni komut verebilsin.
        Auto-hide timer baslat ama yeni trigger gelirse iptal edilebilsin.
        """
        logger.debug("TTS finished — resuming wake word, auto-hide in %dms",
                      self._auto_hide_delay)

        # Wake word'u hemen resume et — cooldown sirasinda da dinle
        self._wake_word.resume()

        # Iptal edilebilir auto-hide timer baslat
        self._cancel_auto_hide_timer()
        self._auto_hide_timer = QTimer()
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.setInterval(self._auto_hide_delay)
        self._auto_hide_timer.timeout.connect(self._reset_to_idle)
        self._auto_hide_timer.start()

    # ─── Auto-hide Timer Yonetimi ─────────────────────────────────

    def _cancel_auto_hide_timer(self) -> None:
        """Aktif auto-hide timer'i iptal et."""
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

    def shutdown(self) -> None:
        """Clean up all resources on application exit."""
        self._cancel_auto_hide_timer()
        self._wake_word.stop()
        self._recorder.stop()
        self._llm.stop()
        self._tts.cleanup()
        try:
            import keyboard
            keyboard.unhook_all()
        except Exception:
            pass
        logger.info("AppController shutdown complete")
