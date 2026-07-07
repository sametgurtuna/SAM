# SAM — Text-to-Speech Engine
# Converts text to speech using edge-tts and plays it via pygame.
# edge-tts uses Microsoft Edge's TTS voices — free, no API key needed.

import asyncio
import logging
import os
import tempfile
import threading
import time

from PyQt6.QtCore import QObject, pyqtSignal

from core.config import config

logger = logging.getLogger(__name__)


class TTSEngine(QObject):
    """
    Text-to-Speech engine using edge-tts.
    
    Generates speech audio from text using Microsoft Edge TTS voices,
    saves to a temporary MP3 file, and plays it via pygame.mixer.
    
    Signals:
        playback_started(): TTS audio playback has begun.
        playback_finished(): TTS audio playback has ended.
    """

    playback_started = pyqtSignal()
    playback_finished = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        self._voice: str = config.get("tts", "voice", default="en-US-GuyNeural")
        self._rate: str = config.get("tts", "rate", default="+0%")
        self._volume: str = config.get("tts", "volume", default="+0%")
        self._engine_type: str = config.get("tts", "engine", default="edge-tts")

        # Temp directory for TTS audio files
        self._temp_dir: str = tempfile.mkdtemp(prefix="sam_tts_")
        self._playing: bool = False

        # Cift konusmayi engellemek icin threading lock
        self._speak_lock = threading.Lock()

        # Initialize pygame mixer
        self._mixer_ready: bool = False
        self._init_mixer()

    def _init_mixer(self) -> None:
        """Initialize pygame mixer for audio playback."""
        try:
            import pygame.mixer
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=2048)
            self._mixer_ready = True
            logger.debug("pygame.mixer initialized for TTS playback")
        except Exception as e:
            logger.warning("Failed to initialize pygame.mixer: %s", e)
            self._mixer_ready = False

    def speak(self, text: str) -> None:
        """
        Convert text to speech and play it. Runs in a background thread.
        
        Args:
            text: The text to speak aloud.
        """
        if not text.strip():
            logger.debug("Empty text — skipping TTS")
            self.playback_finished.emit()
            return

        # Mevcut konusmayi durdur — cift konusmayi onle
        self.stop()

        thread = threading.Thread(
            target=self._speak_worker,
            args=(text,),
            daemon=True,
            name="TTSThread"
        )
        thread.start()

    def stop(self) -> None:
        """Stop any currently playing audio."""
        self._playing = False
        try:
            import pygame.mixer
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass

    def _speak_worker(self, text: str) -> None:
        """Background worker: generate TTS audio and play it."""
        # Lock ile ayni anda sadece bir konusma yapilmasini sagla
        if not self._speak_lock.acquire(blocking=False):
            logger.debug("TTS already speaking — skipping duplicate call")
            return

        try:
            # Refresh engine setting in case it was changed in GUI
            self._engine_type = config.get("tts", "engine", default="edge-tts")
            
            if self._engine_type == "local":
                self._speak_local(text)
                return

            # Edge-TTS: Generate audio file and play
            audio_path = self._generate_audio(text)
            if audio_path is None:
                self.playback_finished.emit()
                return

            # Play audio
            self._play_audio(audio_path)

        except Exception as e:
            logger.error("TTS failed: %s", e)
            self.playback_finished.emit()
        finally:
            self._speak_lock.release()

    def _generate_audio(self, text: str) -> str | None:
        """Generate TTS audio using edge-tts (async). Returns path to MP3 file."""
        try:
            import edge_tts

            # Create unique temp file
            audio_path = os.path.join(
                self._temp_dir,
                f"tts_{int(time.time() * 1000)}.mp3"
            )

            logger.debug("Generating TTS: voice=%s, text='%s'", self._voice, text[:50])
            start = time.time()

            # Run async edge-tts in a new event loop (we're in a thread)
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    self._async_generate(text, audio_path)
                )
            finally:
                loop.close()

            elapsed = time.time() - start
            file_size = os.path.getsize(audio_path) if os.path.exists(audio_path) else 0
            logger.info("TTS audio generated in %.2fs (%d bytes): %s",
                        elapsed, file_size, audio_path)

            return audio_path if os.path.exists(audio_path) and file_size > 0 else None

        except ImportError:
            logger.error("edge-tts not installed. Run: pip install edge-tts")
            return None
        except Exception as e:
            logger.error("TTS generation failed: %s", e)
            return None

    def _speak_local(self, text: str) -> None:
        """Speak text using offline pyttsx3."""
        try:
            import pyttsx3
            
            self._playing = True
            self.playback_started.emit()
            
            engine = pyttsx3.init()
            # If pyttsx3 is already in a loop in another thread this can fail,
            # but since we run this in a new worker thread each time, 
            # initializing per-call is usually safe on Windows.
            engine.say(text)
            engine.runAndWait()
            
            logger.debug("Local TTS playback finished")
        except ImportError:
            logger.error("pyttsx3 not installed. Run: pip install pyttsx3")
        except Exception as e:
            logger.error("Local TTS failed: %s", e)
        finally:
            self._playing = False
            self.playback_finished.emit()

    async def _async_generate(self, text: str, output_path: str) -> None:
        """Async edge-tts generation."""
        import edge_tts

        communicate = edge_tts.Communicate(
            text=text,
            voice=self._voice,
            rate=self._rate,
            volume=self._volume,
        )
        await communicate.save(output_path)

    def _play_audio(self, audio_path: str) -> None:
        """Play an MP3 file via pygame.mixer and wait for it to finish."""
        if not self._mixer_ready:
            logger.warning("Mixer not ready — cannot play TTS audio")
            self.playback_finished.emit()
            return

        try:
            import pygame.mixer

            self._playing = True
            self.playback_started.emit()

            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()

            logger.debug("TTS playback started")

            # Wait for playback to finish
            while pygame.mixer.music.get_busy() and self._playing:
                time.sleep(0.1)

            pygame.mixer.music.unload()
            logger.debug("TTS playback finished")

        except Exception as e:
            logger.error("TTS playback failed: %s", e)
        finally:
            self._playing = False
            self.playback_finished.emit()

            # Clean up temp file
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except OSError:
                pass

    def cleanup(self) -> None:
        """Clean up temp files and mixer resources."""
        self.stop()
        try:
            import shutil
            if os.path.exists(self._temp_dir):
                shutil.rmtree(self._temp_dir, ignore_errors=True)
        except Exception:
            pass
        logger.debug("TTS engine cleaned up")
