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

        # Overlay — "orb" (her zaman gorunur daire) varsayilan; "bar" eski
        # alttan kayan cubugu geri getirir. Ikisi de ayni API'yi sunuyor,
        # bu yuzden asagidaki tum cagri yerleri degismiyor.
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
        # Kullanici Ollama'yi elle baslatmak zorunda kalmasin diye SAM
        # acilirken sunucuyu arka planda (gizli) kendisi ayaga kaldirir.
        self._ollama = OllamaService()
        self._ollama.ready.connect(self._llm.refresh_engine)
        self._ollama.unavailable.connect(self._on_ollama_unavailable)
        if config.get("llm", "ollama", "autostart", default=True):
            self._ollama.ensure_running()

        # ─── Command Router ──────────────────────────────────────
        self._cmd_router = CommandRouter()

        # ─── Wire signals ─────────────────────────────────────────

        # Trigger sources → activation
        self.trigger_signal.connect(self._on_trigger)
        self.text_input_signal.connect(self._open_text_input)
        self._wake_word.detected.connect(self._on_trigger)

        # Recorder → STT pipeline
        self._recorder.recording_done.connect(self._on_recording_done)
        self._recorder.level_update.connect(self._on_audio_level)

        # STT → LLM pipeline
        self._stt.partial_transcript.connect(self._on_partial_transcript)
        self._stt.transcript_ready.connect(self._on_transcript_ready)
        # Iki dilli TTS — algilanan dile gore ses/cevap dili secimi
        self._stt.language_detected.connect(self._on_language_detected)

        # LLM → TTS pipeline
        self._llm.token_received.connect(self._on_llm_token)
        self._llm.generation_complete.connect(self._on_llm_complete)
        self._llm.generation_error.connect(self._on_llm_error)

        # TTS → completion
        self._tts.playback_finished.connect(self._on_tts_finished)
        # TTS her cumle parcasini calmaya basladiginda caption'i o noktaya
        # kaydir — "text follow" ozelligi (bkz. _on_tts_chunk_started).
        self._tts.playback_started.connect(self._on_tts_chunk_started)

        # ─── Auto-hide timer ─────────────────────────────────────
        self._auto_hide_delay: int = config.get(
            "ui", "auto_hide", "delay_seconds", default=4
        ) * 1000

        # Iptal edilebilir auto-hide timer — cooldown sirasinda
        # yeni komut geldiginde timer iptal edilebilsin
        self._auto_hide_timer: QTimer | None = None

        # ─── LLM streaming state ─────────────────────────────────
        self._llm_response_text: str = ""
        # Akis sirasinda TTS'e gonderilmis olan on ek
        self._tts_spoken_text: str = ""
        # Yanitta kod blogu (```) gorulunce akisli seslendirme durur;
        # kod TTS'e gitmemeli, tamamlaninca dosyaya kaydedilir.
        self._tts_stream_ok: bool = True
        # Her speak_chunk() cagrisiyla birebir sirali (FIFO) — _llm_response_text
        # icindeki (start, end) karakter araligi. TTS o parcayi calmaya
        # basladiginda (playback_started) sirdaki araligi cikarip caption'a
        # "buraya kaydir" komutunu veriyoruz — bkz. _on_tts_chunk_started.
        self._tts_chunk_ranges: list[tuple[int, int]] = []

        # ─── Last transcript (for context) ────────────────────────
        self._last_transcript: str = ""

        # ─── Bilingual TTS state ───────────────────────────────────
        # STT'nin son algiladigi dil — TTS sesi ve LLM'e verilen dil
        # talimati bundan turer (bkz. _on_language_detected).
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

        # `keyboard` fazladan basili modifier'lari umursamaz. "ctrl+shift+space"
        # "ctrl+space"in ust kumesi oldugu icin metin kisayolu ses kisayolunu da
        # atesler. Farki bir kez hesaplayip _on_hotkey_pressed'de eleyecegiz.
        self._text_hotkey_extra_keys: set[str] = (
            self._combo_keys(text_combo) - self._combo_keys(trigger_combo)
        )

        def _listen_hotkey():
            try:
                import keyboard
            except ImportError:
                logger.error("keyboard module not installed. Run: pip install keyboard")
                return

            # Her kisayot ayri try/except: hatali bir kullanici kombosu
            # digerini de olduremesin.
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
                # Metin kisayolunun fazladan tuslari basiliysa bu tetikleme
                # aslinda metin kisayolu — sesi baslatma.
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

        # Cooldown (SPEAKING) sirasinda yeni komut gelirse:
        # mevcut auto-hide timer'i iptal et ve yeni dinleme oturumu baslat
        if self._state == AppState.SPEAKING:
            logger.info("New trigger during cooldown — starting new session")
            self._cancel_auto_hide_timer()
            self._tts.stop()
            self._wake_word.pause()
            play_activation_sound()
            self._start_listening(pre_audio)
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
        self._start_listening(pre_audio)

    # ─── Typed input ──────────────────────────────────────────────

    def _open_text_input(self) -> None:
        """Open (or close) the typed-input box under the orb."""
        if not hasattr(self._bar, "toggle_text_input"):
            logger.debug("Text input is not available with the legacy bar overlay")
            return

        # Kayit sirasinda yazmaya baslanirsa, yazi kazanir.
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

        # Devam eden her seyi durdur.
        self._cancel_auto_hide_timer()
        self._recorder.stop()
        self._llm.stop()
        self._tts.stop()
        self._wake_word.pause()   # _on_tts_finished / _reset_to_idle geri aciyor

        # ZORUNLU: _on_llm_token yalnizca state tam olarak THINKING ise
        # SPEAKING'e geciyor — bunu _on_transcript_ready'den once ayarla.
        self._set_state(AppState.THINKING)
        self._bar.activate()

        # _on_transcript_ready _last_transcript'i kendisi set ediyor.
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

        # Start real microphone recording
        self._recorder.start(pre_audio)

    def _on_audio_level(self, level: float) -> None:
        """Receive live audio level from recorder and drive the waveform."""
        self._bar.set_level(level)

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

    # ─── Iki dilli TTS ────────────────────────────────────────────

    # Su an sadece bu iki dil icin ses/persona eslesmesi tanimli
    # (bkz. config tts.voices).
    _SUPPORTED_TTS_LANGS = {"tr", "en"}
    # Kisa/belirsiz ifadelerde ("evet", "ok") faster-whisper'in dil tahmini
    # guvenilmez — bu esigin altinda mevcut sesi/dili koru.
    _LANG_CONFIDENCE_MIN = 0.5

    def _on_language_detected(self, language: str, probability: float) -> None:
        """
        STT her transkripsiyondan algiladigi dili bildirir. Guvenilir ve
        desteklenen bir dilse TTS sesini ve LLM'e verilecek dil talimatini
        buna gore guncelle. transcript_ready'den once tetiklenir, boylece
        _generate_response() cagrildiginda deger hazir olur.
        """
        if not config.get("tts", "auto_language", default=True):
            return
        if probability < self._LANG_CONFIDENCE_MIN or language not in self._SUPPORTED_TTS_LANGS:
            return

        self._detected_language = language
        voices = config.get("tts", "voices", default={}) or {}
        voice = voices.get(language) or config.get("tts", "voice", default="en-US-GuyNeural")
        self._tts.set_voice(voice)
        logger.debug("Language detected: %s (%.2f) — voice set to %s",
                      language, probability, voice)

    def _on_transcript_ready(self, transcript: str) -> None:
        """Full transcription complete — send to LLM."""
        if not transcript.strip():
            logger.warning("Empty transcription — returning to idle")
            self._cancel_and_reset()
            return

        logger.info("Transcript: '%s'", transcript)
        self._last_transcript = transcript
        self._bar.set_transcript(transcript)

        # Kullanicinin kendi cumlesinden kalici bilgi cikar (isim, meslek, vb.)
        # — arka planda, yanit hizini hic etkilemeden.
        self._extract_and_store_facts(transcript)

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

        # 2. Sistem komutu degilse, LLM'e yonlendir.
        # Onceden burada 400ms'lik yapay bir gecikme vardi — her sohbet
        # yanitina bedelsiz 400ms ekliyordu, kaldirildi.
        self._generate_response(cmd_result.image_b64)

    def _generate_response(self, image_b64: str | None = None) -> None:
        """Send transcript to LLM and stream the response."""
        self._bar.set_transcript("Thinking...")
        self._llm_response_text = ""
        self._tts_spoken_text = ""
        self._tts_stream_ok = True
        self._tts_chunk_ranges = []
        # Yeni bir yanit basliyor — onceki konusmayi ve kuyrugu temizle
        self._tts.stop()

        # Send to LLM router (auto-detects Ollama or Claude)
        self._llm.generate(
            self._last_transcript,
            image_b64=image_b64,
            language=self._detected_language,
        )

    def _extract_and_store_facts(self, transcript: str) -> None:
        """
        Kullanici transkriptinden kalici bilgi (isim, meslek, okul vb.) cikar
        ve hafizaya yaz. Fire-and-forget arka plan thread — cevap suresini
        hic etkilemez, _generate_response()'dan once baslatilir.
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

    # ─── Akisli TTS ───────────────────────────────────────────────

    # Cumle sonu sayilan noktalama isaretleri
    _SENTENCE_ENDINGS = (".", "!", "?", "\n", "…")
    # Bundan kisa parcalari seslendirmek kopuk duyuluyor
    _MIN_TTS_CHUNK = 12

    def _flush_streaming_tts(self) -> None:
        """
        Tamamlanmis cumleleri, LLM hala yazmaya devam ederken TTS'e gonder.
        Yanitin tamaminin beklenmesi yerine ilk cumle hemen duyulur.
        """
        if not self._tts_stream_ok:
            return

        pending = self._llm_response_text[len(self._tts_spoken_text):]

        # Kod blogu basladi — buradan sonrasi seslendirilmez
        if "```" in pending:
            self._tts_stream_ok = False
            return

        # En son cumle sinirini bul
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
        TTS bir sonraki parcayi calmaya basladi — hangi metin araligina
        karsilik geldigini kuyruktan cikar ve caption'a bildir (text follow).
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

        # Akis sirasinda zaten seslendirilmis kismi tekrar okuma —
        # sadece kalan bolumu kuyruga ekleyip akisi kapat.
        already = self._tts_spoken_text
        if already and spoken_response.startswith(already):
            remainder = spoken_response[len(already):].strip()
            if remainder:
                # Offset'ler sadece kod cikarilmadiysa (spoken == full) gecerli —
                # cikarildiysa metin kisaldigi icin caption'daki gercek pozisyonla
                # uyusmaz, o durumda takip araligi eklemiyoruz (metin zaten tam gorunur).
                if spoken_response == full_response:
                    self._tts_chunk_ranges.append((len(already), len(full_response)))
                self._tts.speak_chunk(remainder)
            self._tts.end_stream()
        elif already:
            # On ek eslesmedi (kod cikarimi metnin basini degistirdi) —
            # bastan okumak tekrara yol acar, sadece akisi kapat.
            logger.debug("Streamed TTS prefix diverged — skipping remainder")
            self._tts.end_stream()
        else:
            # Hic akisli parca gonderilmemis — klasik tek seferlik okuma
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
        # Yine de tespit calissin: Claude anahtari varsa oraya duser.
        self._llm.refresh_engine()

    def apply_settings(self) -> None:
        """
        Live-apply the settings that don't need a restart (orb geometry, colors,
        fps, click-through, auto-hide delay). Everything else keeps the
        "restart SAM" note in the settings window.
        """
        self._auto_hide_delay = config.get(
            "ui", "auto_hide", "delay_seconds", default=4
        ) * 1000
        if hasattr(self._bar, "apply_settings"):
            self._bar.apply_settings()
            # Yeniden kurulan orb mevcut duruma gore boyansin.
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
