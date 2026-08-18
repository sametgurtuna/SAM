# SAM — Speech-to-Text Engine
# Transcribes audio using faster-whisper (CTranslate2-based Whisper).
# Runs locally, no cloud calls. Model is downloaded on first use.

import logging
import os
import threading
import time

import numpy as np

from PyQt6.QtCore import QObject, pyqtSignal

from core import paths
from core.config import config

logger = logging.getLogger(__name__)


class STTEngine(QObject):
    """
    Speech-to-Text engine using faster-whisper.
    
    Transcribes audio numpy arrays (16kHz, mono, int16) into text.
    Model is loaded lazily on first use and cached for subsequent calls.
    
    Signals:
        transcript_ready(str): Full transcription text.
        partial_transcript(str): Intermediate segment text (for live display).
        language_detected(str, float): Detected language code and confidence,
            emitted right before transcript_ready (bilingual TTS voice pick).
    """

    # Signal: full transcription complete
    transcript_ready = pyqtSignal(str)
    # Signal: partial transcript (segment-by-segment)
    partial_transcript = pyqtSignal(str)
    # Signal: detected language (code, probability) — emitted before transcript_ready
    language_detected = pyqtSignal(str, float)

    def __init__(self) -> None:
        super().__init__()

        self._model_size: str = config.get("stt", "model", default="small")
        self._language: str | None = config.get("stt", "language", default=None)
        self._beam_size: int = config.get("stt", "beam_size", default=1)
        self._device: str = config.get("stt", "device", default="cpu")
        self._compute_type: str = config.get("stt", "compute_type", default="int8")

        self._initial_prompt: str = (
            "open spotify, mute, volume up, turn down, lock screen, shutdown, close chrome, "
            "play, pause, next track, sonraki parça, sesi aç, sesi kıs, kapat, durdur, sıradaki şarkı."
        )

        # Separate lightweight model for live transcription. "" = use main model,
        # "off" = disable live transcription.
        self._partial_model_size: str = config.get("stt", "partial_model", default="tiny")
        self._partial_interval: float = config.get(
            "stt", "partial_interval_ms", default=400
        ) / 1000.0

        self._model = None
        self._model_loaded: bool = False
        self._partial_model = None
        self._load_lock = threading.Lock()
        self._partial_load_lock = threading.Lock()
        self._partial_lock = threading.Lock()
        self._last_partial_at: float = 0.0

        # Latest live partial transcript and sample count — used by fast path in AppController
        # to match commands before final Whisper decode (see core/app.py _on_recording_done).
        self.last_partial_text: str = ""
        self.last_partial_samples: int = 0

    def _build_model(self, size: str, threads: int):
        """Create a WhisperModel instance. Returns None on failure."""
        from faster_whisper import WhisperModel

        logger.info("Loading Whisper model '%s' (device=%s, compute=%s, threads=%d)...",
                    size, self._device, self._compute_type, threads)
        start = time.time()
        model = WhisperModel(
            size,
            device=self._device,
            compute_type=self._compute_type,
            # CTranslate2 uses a single core by default; assigning all CPU cores
            # significantly reduces decode latency in CPU mode.
            cpu_threads=threads,
            # Fixed, writable model path cached during installation.
            download_root=os.path.join(paths.models_dir(), "whisper"),
        )
        logger.info("Whisper model '%s' loaded in %.1fs", size, time.time() - start)
        return model

    def load_model(self) -> None:
        """
        Pre-load the Whisper models. Call during startup for faster first transcription.
        Safe to call from any thread — concurrent calls block until the first finishes.
        """
        # Load small live model first for fast initial response
        self.load_partial_model()

        if self._model_loaded:
            return

        with self._load_lock:
            # Another thread may have finished loading while waiting for the lock
            if self._model_loaded:
                return
            self._load_model_locked()

    def _load_model_locked(self) -> None:
        try:
            self._model = self._build_model(self._model_size, os.cpu_count() or 4)
            self._model_loaded = True
        except ImportError as e:
            logger.error("faster-whisper unavailable (%s). Run: pip install faster-whisper", e)
        except Exception as e:
            logger.error("Failed to load Whisper model: %s", e)

    def load_partial_model(self) -> None:
        """Load the lightweight model used for live (partial) transcription."""
        if self._partial_model_size == "off" or self._partial_model is not None:
            return
        if not self._partial_model_size or self._partial_model_size == self._model_size:
            return  # Main model will be used

        with self._partial_load_lock:
            if self._partial_model is not None:
                return
            try:
                # Allocate half CPU cores so live decode does not starve final decode
                threads = max(1, (os.cpu_count() or 4) // 2)
                self._partial_model = self._build_model(self._partial_model_size, threads)
            except Exception as e:
                logger.warning("Partial model unavailable (%s) — falling back to main model", e)
                self._partial_model_size = ""

    def _live_model(self):
        """Model used for partial decodes — the small one if available."""
        if self._partial_model is not None:
            return self._partial_model
        return self._model if self._model_loaded else None

    def transcribe_partial(self, audio_data: np.ndarray) -> None:
        """
        Fast non-blocking partial transcription for live display while the user speaks.
        """
        if self._partial_model_size == "off":
            return

        model = self._live_model()
        if model is None:
            return

        if self._partial_lock.locked():
            return  # Skip if a partial transcription is already decoding

        now = time.time()
        if now - self._last_partial_at < self._partial_interval:
            return
        self._last_partial_at = now

        def _worker():
            if not self._partial_lock.acquire(blocking=False):
                return
            try:
                audio_float = audio_data.astype(np.float32).flatten() / 32768.0
                if len(audio_float) < 1600:  # < 0.1s audio
                    return

                segments, _ = model.transcribe(
                    audio_float,
                    language=self._language,
                    beam_size=1,  # Greedy for maximum speed
                    initial_prompt=self._initial_prompt,
                    # VAD disabled in live stream to minimize latency
                    vad_filter=False,
                    condition_on_previous_text=False,
                    without_timestamps=True,
                )

                text_parts = [seg.text.strip() for seg in segments if seg.text.strip()]
                if text_parts:
                    partial_text = " ".join(text_parts)
                    self.last_partial_text = partial_text
                    self.last_partial_samples = len(audio_float)
                    self.partial_transcript.emit(partial_text)
            except Exception as e:
                logger.debug("Partial transcription failed: %s", e)
            finally:
                self._partial_lock.release()

        thread = threading.Thread(target=_worker, daemon=True, name="STTPartialThread")
        thread.start()

    def reset_partial(self) -> None:
        """Clear live-transcript state at the start of a new listening session."""
        self.last_partial_text = ""
        self.last_partial_samples = 0
        self._last_partial_at = 0.0

    def transcribe(self, audio_data: np.ndarray) -> None:
        """
        Transcribe audio data in a background thread.
        
        Args:
            audio_data: numpy array of int16 audio at 16kHz mono.
        
        Emits transcript_ready signal with the full text when done.
        """
        thread = threading.Thread(
            target=self._transcribe_worker,
            args=(audio_data,),
            daemon=True,
            name="STTThread"
        )
        thread.start()

    def _transcribe_worker(self, audio_data: np.ndarray) -> None:
        """Background worker for transcription."""
        # Ensure model is loaded
        if not self._model_loaded:
            self.partial_transcript.emit("Loading speech model...")
            self.load_model()

        if self._model is None:
            logger.error("STT model not available — cannot transcribe")
            self.transcript_ready.emit("")
            return

        try:
            # faster-whisper expects float32 normalized to [-1.0, 1.0]
            audio_float = audio_data.astype(np.float32).flatten() / 32768.0

            logger.debug("Transcribing %.1fs of audio...", len(audio_float) / 16000)
            start = time.time()

            # Run transcription
            segments, info = self._model.transcribe(
                audio_float,
                language=self._language,
                beam_size=self._beam_size,
                initial_prompt=self._initial_prompt,
                vad_filter=True,           # Filter out non-speech segments
                vad_parameters=dict(
                    min_silence_duration_ms=250,
                    speech_pad_ms=150,
                ),
                condition_on_previous_text=False,
                without_timestamps=True,
            )

            # Collect segments — emit partial transcripts as we go
            full_text_parts: list[str] = []
            for segment in segments:
                text = segment.text.strip()
                if text:
                    full_text_parts.append(text)
                    # Emit partial transcript for live display
                    self.partial_transcript.emit(" ".join(full_text_parts))

            full_text = " ".join(full_text_parts)
            elapsed = time.time() - start

            logger.info("Transcription complete in %.2fs: '%s' (language=%s, prob=%.2f)",
                        elapsed, full_text, info.language, info.language_probability)

            self.language_detected.emit(info.language, info.language_probability)
            self.transcript_ready.emit(full_text)

        except Exception as e:
            logger.error("Transcription failed: %s", e)
            self.transcript_ready.emit("")

    def set_language(self, language: str | None) -> None:
        """
        Dynamically update transcription language.
        None = auto-detect, 'tr' = Turkish, 'en' = English.
        """
        self._language = language
        logger.info("STT language set to: %s", language or "auto-detect")

    @property
    def language(self) -> str | None:
        return self._language

