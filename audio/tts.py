# SAM — Text-to-Speech Engine
# Converts text to speech using edge-tts and plays it via pygame.
# edge-tts uses Microsoft Edge's TTS voices — free, no API key needed.

import asyncio
import logging
import os
import queue
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

        # ─── Konusma kuyrugu ─────────────────────────────────────
        # LLM yanitinin tamamlanmasini beklemek yerine cumle cumle
        # seslendirebilmek icin kalici bir worker + kuyruk kullanilir.
        # `_generation` sayaci stop() cagrildiginda artar; kuyrukta
        # bekleyen eski parcalar boylece sessizce atilir.
        self._queue: "queue.Queue[tuple[int, str, str, int]]" = queue.Queue()
        self._generation: int = 0
        self._gen_lock = threading.Lock()

        # ─── Prefetch (chunk overlap) ────────────────────────────
        # Bir cumle calarken bir sonraki cumlenin sentezi arka planda
        # baslar, boylece cumleler arasi sessiz bosluk (network round-trip)
        # kalmaz. `_seq_counter` her enqueue'da artar; cache seq -> mp3 yolu.
        self._seq_counter: int = 0
        self._prefetch_cache: dict[int, str] = {}
        self._prefetch_lock = threading.Lock()

        # Initialize pygame mixer
        self._mixer_ready: bool = False
        self._init_mixer()

        self._worker = threading.Thread(
            target=self._worker_loop, daemon=True, name="TTSWorker"
        )
        self._worker.start()

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

    def set_voice(self, voice: str) -> None:
        """
        Runtime'da konusma sesini degistir (ör. algilanan dile gore).

        `_engine_type`'in `_speak_one` icinde her cagrida tazelenmesiyle ayni
        desen — bir sonraki sentezden itibaren gecerli olur, kuyrukta zaten
        bekleyen parcalar (varsa) eski sesle sentezlenmis olabilir.
        """
        self._voice = voice

    def speak(self, text: str) -> None:
        """
        Convert text to speech and play it. Non-blocking.

        Replaces anything currently queued or playing — use this for
        one-shot utterances (command confirmations, errors).
        """
        self.stop()
        if not text.strip():
            logger.debug("Empty text — skipping TTS")
            self.playback_finished.emit()
            return

        self._enqueue("say", text)
        self._enqueue("end", "")

    def speak_chunk(self, text: str) -> None:
        """
        Queue one more piece of an in-progress utterance without cancelling
        what is already playing. Used to speak an LLM response sentence by
        sentence while it is still streaming in.
        """
        if not text.strip():
            return
        self._enqueue("say", text)

    def end_stream(self) -> None:
        """Mark the end of a streamed utterance — fires playback_finished."""
        self._enqueue("end", "")

    def _enqueue(self, kind: str, text: str) -> int:
        with self._gen_lock:
            generation = self._generation
            seq = self._seq_counter
            self._seq_counter += 1
        self._queue.put((generation, kind, text, seq))
        return seq

    def stop(self) -> None:
        """Cancel queued speech and stop any currently playing audio."""
        with self._gen_lock:
            # Kuyrukta bekleyen her sey artik eski nesle ait — worker atacak
            self._generation += 1

        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        self._playing = False
        try:
            import pygame.mixer
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass

        self._clear_prefetch_cache()

    def _is_current(self, generation: int) -> bool:
        with self._gen_lock:
            return generation == self._generation

    def _clear_prefetch_cache(self) -> None:
        """Iptal edilen/kullanilmayan onceden-sentezlenmis ses dosyalarini sil."""
        with self._prefetch_lock:
            paths = list(self._prefetch_cache.values())
            self._prefetch_cache.clear()
        for p in paths:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass

    def _worker_loop(self) -> None:
        """Persistent worker: drains the speech queue in order."""
        while True:
            generation, kind, text, seq = self._queue.get()

            # stop() sonrasi kuyrukta kalan eski parcalari atla
            if not self._is_current(generation):
                continue

            if kind == "end":
                self.playback_finished.emit()
                continue

            try:
                self._speak_one(text, generation, seq)
            except Exception as e:
                logger.error("TTS failed: %s", e)

    def _speak_one(self, text: str, generation: int, seq: int) -> None:
        """Synthesize and play a single chunk (blocking, on the worker)."""
        # Refresh engine setting in case it was changed in GUI
        self._engine_type = config.get("tts", "engine", default="edge-tts")

        if self._engine_type == "local":
            self._speak_local(text)
            return

        # Onceki cumle calarken arka planda hazirlanmis olabilir — varsa
        # kullan, yoksa simdi senkron sentezle (ilk cumlede her zaman boyle).
        audio_path = self._take_prefetched(seq)
        if audio_path is None:
            audio_path = self._generate_audio(text)
        if audio_path is None or not self._is_current(generation):
            return

        # Bu parca calmaya baslamadan once, kuyruktaki bir sonraki parcanin
        # sentezini arka planda baslat — boylece cumleler arasinda network
        # round-trip'i beklenmez.
        self._prefetch_next(generation)

        self._play_audio(audio_path)

    def _take_prefetched(self, seq: int) -> str | None:
        with self._prefetch_lock:
            return self._prefetch_cache.pop(seq, None)

    def _prefetch_next(self, current_generation: int) -> None:
        """Kuyruktaki bir sonraki 'say' parcasini arka planda onceden sentezle."""
        with self._queue.mutex:
            peeked = self._queue.queue[0] if self._queue.queue else None
        if peeked is None:
            return

        gen, kind, text, seq = peeked
        if kind != "say" or gen != current_generation:
            return
        with self._prefetch_lock:
            if seq in self._prefetch_cache:
                return

        def _run() -> None:
            if not self._is_current(gen):
                return
            path = self._generate_audio(text)
            if path is None:
                return
            if not self._is_current(gen):
                # Bu arada iptal edildi (stop()) — dosyayi tut, bir sonraki
                # cleanup()/stop() genel temizlikte silinir.
                return
            with self._prefetch_lock:
                self._prefetch_cache[seq] = path

        threading.Thread(target=_run, daemon=True, name="TTSPrefetch").start()

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
            self._apply_local_voice(engine)
            engine.say(text)
            engine.runAndWait()

            logger.debug("Local TTS playback finished")
        except ImportError:
            logger.error("pyttsx3 not installed. Run: pip install pyttsx3")
        except Exception as e:
            logger.error("Local TTS failed: %s", e)
        finally:
            self._playing = False

    def _apply_local_voice(self, engine) -> None:
        """
        pyttsx3 (Windows SAPI5) edge-tts ses adlarini ("tr-TR-EmelNeural" gibi)
        taniyamaz — bunun yerine sistemde KURULU SAPI seslerinden birini secmek
        gerekir. `_voice`'in bastaki locale onekini ("tr-TR", "en-US") kurulu
        seslerin id/name alaninda arayip eslesen ilkini seciyoruz. Eslesme
        yoksa (ör. Turkce SAPI sesi kurulu degilse) sistem varsayilani kalir.
        """
        locale_prefix = "-".join(self._voice.split("-")[:2]).lower()
        if not locale_prefix:
            return
        try:
            voices = engine.getProperty("voices") or []
        except Exception:
            return

        for v in voices:
            haystack = f"{getattr(v, 'id', '')} {getattr(v, 'name', '')}".lower().replace("_", "-")
            if locale_prefix in haystack:
                engine.setProperty("voice", v.id)
                return

        logger.debug(
            "No installed local (SAPI) voice matches '%s' — using system default. "
            "Install the language's Windows speech pack, or switch tts.engine to "
            "'edge-tts' for full bilingual voice support.",
            locale_prefix,
        )

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
            return

        try:
            import pygame.mixer

            self._playing = True
            self.playback_started.emit()

            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()

            logger.debug("TTS playback started")

            # Wait for playback to finish
            # Kisa poll araligi — zincirlenmis cumleler arasinda
            # duyulur bir bosluk kalmasini onler.
            while pygame.mixer.music.get_busy() and self._playing:
                time.sleep(0.02)

            pygame.mixer.music.unload()
            logger.debug("TTS playback finished")

        except Exception as e:
            logger.error("TTS playback failed: %s", e)
        finally:
            self._playing = False

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
