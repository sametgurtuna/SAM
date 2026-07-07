# SAM — Speech-to-Text Engine
# Transcribes audio using faster-whisper (CTranslate2-based Whisper).
# Runs locally, no cloud calls. Model is downloaded on first use.

import logging
import threading
import time

import numpy as np

from PyQt6.QtCore import QObject, pyqtSignal

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
    """

    # Signal: full transcription complete
    transcript_ready = pyqtSignal(str)
    # Signal: partial transcript (segment-by-segment)
    partial_transcript = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()

        self._model_size: str = config.get("stt", "model", default="base")
        self._language: str | None = config.get("stt", "language", default="en")
        self._beam_size: int = config.get("stt", "beam_size", default=2)
        self._device: str = config.get("stt", "device", default="cpu")
        self._compute_type: str = config.get("stt", "compute_type", default="int8")

        self._model = None
        self._model_loaded: bool = False

    def load_model(self) -> None:
        """
        Pre-load the Whisper model. Call during startup for faster first transcription.
        Safe to call from any thread.
        """
        if self._model_loaded:
            return

        try:
            from faster_whisper import WhisperModel

            logger.info("Loading Whisper model '%s' (device=%s, compute=%s)...",
                        self._model_size, self._device, self._compute_type)

            start = time.time()
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
            elapsed = time.time() - start
            self._model_loaded = True
            logger.info("Whisper model loaded in %.1fs", elapsed)

        except ImportError:
            logger.error("faster-whisper not installed. Run: pip install faster-whisper")
        except Exception as e:
            logger.error("Failed to load Whisper model: %s", e)

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
                initial_prompt="open spotify, mute, volume up, turn down, lock screen, shutdown, close chrome, play, pause, next track.",
                vad_filter=True,           # Filter out non-speech segments
                vad_parameters=dict(
                    min_silence_duration_ms=300,
                    speech_pad_ms=400,  # Prevent clipping the start/end of words
                ),
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

            self.transcript_ready.emit(full_text)

        except Exception as e:
            logger.error("Transcription failed: %s", e)
            self.transcript_ready.emit("")
