# SAM — Wake Word Detection Engine
# Continuously listens for the wake word using openwakeword.
# Runs in a daemon thread with minimal CPU usage.
# Signals the app controller when the wake word is detected.

import logging
import threading
import time

import numpy as np
import sounddevice as sd

from PyQt6.QtCore import QObject, pyqtSignal

from core.config import config

logger = logging.getLogger(__name__)


class WakeWordEngine(QObject):
    """
    Continuous wake word listener using openwakeword.
    
    Runs microphone capture in a background thread and checks each audio
    chunk against the wake word model. Emits `detected` signal when triggered.
    
    Usage:
        engine = WakeWordEngine()
        engine.detected.connect(on_wake_word)
        engine.start()
        ...
        engine.stop()
    """

    # Signal emitted when wake word is detected (thread-safe → Qt main thread)
    detected = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        self._model_name: str = config.get("wake_word", "model", default="hey_jarvis")
        self._threshold: float = config.get("wake_word", "threshold", default=0.5)
        self._chunk_size: int = config.get("wake_word", "chunk_size", default=1280)
        self._sample_rate: int = config.get("audio", "sample_rate", default=16000)

        self._running: bool = False
        self._thread: threading.Thread | None = None
        self._model = None

        # Cooldown — prevent rapid re-triggers
        self._last_detection_time: float = 0.0
        self._cooldown_seconds: float = 3.0

    def start(self) -> None:
        """Start the wake word listener in a background thread."""
        if self._running:
            logger.warning("Wake word engine already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="WakeWordThread")
        self._thread.start()
        logger.info("Wake word engine started — listening for '%s'", self._model_name)

    def stop(self) -> None:
        """Stop the wake word listener."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        logger.info("Wake word engine stopped")

    def pause(self) -> None:
        """Temporarily pause detection (e.g., while SAM is active to avoid self-trigger)."""
        self._paused = True

    def resume(self) -> None:
        """Resume detection after pause."""
        self._paused = False

    def _listen_loop(self) -> None:
        """Main listening loop — runs in background thread."""
        self._paused = False

        # Load model
        try:
            import openwakeword
            from openwakeword.model import Model

            # Download pre-trained models if needed
            openwakeword.utils.download_models()

            self._model = Model(
                wakeword_models=[self._model_name],
                inference_framework="onnx"
            )
            logger.info("Wake word model loaded: %s", self._model_name)
        except Exception as e:
            logger.error("Failed to load wake word model: %s", e)
            logger.error("Wake word detection disabled. Use Ctrl+Space to activate SAM.")
            self._running = False
            return

        # Open microphone stream
        try:
            with sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self._chunk_size,
            ) as stream:
                logger.debug("Microphone stream opened for wake word detection")

                while self._running:
                    if self._paused:
                        time.sleep(0.1)
                        continue

                    # Read audio chunk
                    audio_data, overflowed = stream.read(self._chunk_size)
                    if overflowed:
                        logger.debug("Audio buffer overflow in wake word stream")

                    # Feed to model — expects int16 numpy array
                    audio_flat = audio_data.flatten()
                    self._model.predict(audio_flat)

                    # Check detection scores
                    for model_name, score in self._model.prediction_buffer.items():
                        # score is a list of recent predictions
                        latest_score = score[-1] if score else 0.0

                        if latest_score >= self._threshold:
                            now = time.time()
                            if now - self._last_detection_time > self._cooldown_seconds:
                                self._last_detection_time = now
                                logger.info(
                                    "Wake word detected: '%s' (score: %.3f)",
                                    model_name, latest_score
                                )
                                # Reset model to avoid re-triggers
                                self._model.reset()
                                self.detected.emit()

        except sd.PortAudioError as e:
            logger.error("Microphone error: %s", e)
            logger.error("No microphone found. Use Ctrl+Space to activate SAM.")
        except Exception as e:
            logger.error("Wake word listener crashed: %s", e)
        finally:
            self._running = False
            logger.debug("Wake word listen loop exited")
