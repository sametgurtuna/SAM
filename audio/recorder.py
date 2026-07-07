# SAM — Microphone Recorder with Silence Detection
# Records audio after wake word activation until the user stops speaking.
# Uses energy-based VAD (Voice Activity Detection) for end-of-speech detection.

import logging
import threading

import numpy as np
import sounddevice as sd

from PyQt6.QtCore import QObject, pyqtSignal

from core.config import config

logger = logging.getLogger(__name__)


class Recorder(QObject):
    """
    Microphone recorder with automatic silence detection.
    
    Captures audio at 16kHz mono after activation. Monitors RMS energy
    and stops recording when silence is detected for a configurable duration.
    
    Signals:
        recording_done(numpy.ndarray): Emitted with complete audio data when recording ends.
        level_update(float): Emitted with current RMS level for waveform visualization.
    """

    # Signal: recording complete — carries the full audio as numpy array
    recording_done = pyqtSignal(object)
    # Signal: live audio level for waveform (0.0–1.0 normalized)
    level_update = pyqtSignal(float)

    def __init__(self) -> None:
        super().__init__()

        self._sample_rate: int = config.get("audio", "sample_rate", default=16000)
        self._channels: int = config.get("audio", "channels", default=1)
        self._silence_threshold: int = config.get("audio", "silence_threshold", default=500)
        self._silence_duration_ms: int = config.get("audio", "silence_duration_ms", default=800)
        self._max_record_seconds: int = config.get("audio", "max_record_seconds", default=30)

        # Chunk size — 100ms of audio per read
        self._chunk_duration_ms: int = 100
        self._chunk_size: int = int(self._sample_rate * self._chunk_duration_ms / 1000)

        # How many consecutive silent chunks = end of speech
        self._silence_chunks_needed: int = self._silence_duration_ms // self._chunk_duration_ms
        self._max_chunks: int = self._max_record_seconds * 1000 // self._chunk_duration_ms

        self._recording: bool = False
        self._thread: threading.Thread | None = None

    def start(self, pre_audio: np.ndarray | None = None) -> None:
        """Start recording in a background thread."""
        if self._recording:
            logger.warning("Recorder already active")
            return

        self._recording = True
        self._thread = threading.Thread(target=self._record_loop, args=(pre_audio,), daemon=True, name="RecorderThread")
        self._thread.start()
        logger.info("Recording started (silence threshold=%d, silence duration=%dms)",
                     self._silence_threshold, self._silence_duration_ms)

    def stop(self) -> None:
        """Force stop recording (e.g., user pressed Escape)."""
        self._recording = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        logger.debug("Recorder force-stopped")

    def _record_loop(self, pre_audio: np.ndarray | None = None) -> None:
        """Main recording loop — runs in background thread."""
        audio_chunks: list[np.ndarray] = []
        
        if pre_audio is not None:
            audio_chunks.append(pre_audio)
            
        silent_chunks: int = 0
        total_chunks: int = 0
        has_speech: bool = pre_audio is not None

        try:
            with sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="int16",
                blocksize=self._chunk_size,
            ) as stream:
                logger.debug("Recording stream opened")

                while self._recording and total_chunks < self._max_chunks:
                    # Read a chunk
                    audio_data, overflowed = stream.read(self._chunk_size)
                    if overflowed:
                        logger.debug("Audio buffer overflow during recording")

                    audio_chunks.append(audio_data.copy())
                    total_chunks += 1

                    # Calculate RMS energy
                    rms = self._calculate_rms(audio_data)

                    # Emit normalized level for waveform visualization (0.0–1.0)
                    # Normalize: typical speech RMS is 1000–10000 for int16
                    normalized_level = min(rms / 5000.0, 1.0)
                    self.level_update.emit(normalized_level)

                    # Silence detection
                    if rms < self._silence_threshold:
                        silent_chunks += 1
                    else:
                        silent_chunks = 0
                        has_speech = True

                    # End recording if we've heard speech and then silence
                    if has_speech and silent_chunks >= self._silence_chunks_needed:
                        logger.info(
                            "Silence detected after speech — stopping recording "
                            "(total: %.1fs, speech detected at chunk %d)",
                            total_chunks * self._chunk_duration_ms / 1000,
                            total_chunks - silent_chunks
                        )
                        break

                    # Safety: if no speech detected after 5 seconds, stop
                    no_speech_timeout_chunks = 5000 // self._chunk_duration_ms
                    if not has_speech and total_chunks >= no_speech_timeout_chunks:
                        logger.warning("No speech detected for 5s — stopping recording")
                        break

        except sd.PortAudioError as e:
            logger.error("Microphone error during recording: %s", e)
        except Exception as e:
            logger.error("Recording failed: %s", e)
        finally:
            self._recording = False

        # Combine all chunks into a single array
        if audio_chunks and has_speech:
            full_audio = np.concatenate(audio_chunks, axis=0)
            logger.info("Recording complete: %.1fs of audio captured",
                        len(full_audio) / self._sample_rate)
            self.recording_done.emit(full_audio)
        else:
            logger.warning("No speech captured — emitting empty result")
            self.recording_done.emit(None)

    @staticmethod
    def _calculate_rms(audio_data: np.ndarray) -> float:
        """Calculate Root Mean Square energy of an audio chunk."""
        audio_float = audio_data.astype(np.float64)
        rms = np.sqrt(np.mean(audio_float ** 2))
        return float(rms)
