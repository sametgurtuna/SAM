# SAM — Cyberpunk Sound Effects (SFX) Generator & Player
# Generates short, futuristic micro-audio cues with zero external binary assets.
# Uses mathematical sine & envelope synthesis, cached into %LOCALAPPDATA%\SAM\cache\.

import enum
import logging
import math
import os
import struct
import threading
import wave

from core import paths
from core.config import config

logger = logging.getLogger(__name__)

SAMPLE_RATE = 44100


class SoundType(str, enum.Enum):
    """Audio cue identifiers."""
    WAKE = "wake"             # Wake word detected / activation blip
    SUCCESS = "success"       # Zero-LLM command executed / affirmative chime
    WARNING = "warning"       # Error / Ollama offline / empty clipboard alert
    CLICK = "click"           # Speech ended / transition click


def _generate_tone(
    freq: float,
    duration_ms: int,
    sample_rate: int = SAMPLE_RATE,
    amplitude: float = 0.35,
    fade_ms: int = 15,
) -> list[int]:
    """Generate a single sine wave tone with smooth fade in/out envelope."""
    num_samples = int(sample_rate * duration_ms / 1000)
    fade_samples = max(1, int(sample_rate * fade_ms / 1000))
    samples: list[int] = []

    for i in range(num_samples):
        t = i / sample_rate
        value = math.sin(2.0 * math.pi * freq * t)

        # Apply smooth cosine fade envelope to prevent clicks
        if i < fade_samples:
            env = 0.5 * (1.0 - math.cos(math.pi * i / fade_samples))
            value *= env
        elif i > num_samples - fade_samples:
            remaining = num_samples - i
            env = 0.5 * (1.0 - math.cos(math.pi * remaining / fade_samples))
            value *= env

        sample = int(value * amplitude * 32767)
        samples.append(max(-32767, min(32767, sample)))

    return samples


def _write_wav_file(filepath: str, samples: list[int], sample_rate: int = SAMPLE_RATE) -> None:
    """Save raw 16-bit PCM samples to a standard mono WAV file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with wave.open(filepath, "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)
        wav.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def _build_wake_samples() -> list[int]:
    """High-tech dual-note activation blip (620Hz -> 830Hz)."""
    t1 = _generate_tone(620, 110, amplitude=0.28, fade_ms=18)
    gap = [0] * int(SAMPLE_RATE * 0.015)
    t2 = _generate_tone(830, 95, amplitude=0.24, fade_ms=18)
    return t1 + gap + t2


def _build_success_samples() -> list[int]:
    """Futuristic affirmative ascending chime (D5 -> A5 -> D6)."""
    t1 = _generate_tone(587.3, 70, amplitude=0.22, fade_ms=12)
    gap = [0] * int(SAMPLE_RATE * 0.01)
    t2 = _generate_tone(880.0, 75, amplitude=0.24, fade_ms=12)
    t3 = _generate_tone(1174.6, 120, amplitude=0.20, fade_ms=25)
    return t1 + gap + t2 + gap + t3


def _build_warning_samples() -> list[int]:
    """Gentle low-pitch futuristic alert buzz (280Hz + 210Hz sub)."""
    num_samples = int(SAMPLE_RATE * 180 / 1000)
    samples: list[int] = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        val = 0.65 * math.sin(2.0 * math.pi * 280.0 * t) + 0.35 * math.sin(2.0 * math.pi * 210.0 * t)
        # Envelope
        fade_len = int(SAMPLE_RATE * 0.03)
        if i < fade_len:
            val *= i / fade_len
        elif i > num_samples - fade_len:
            val *= (num_samples - i) / fade_len
        samples.append(int(val * 0.28 * 32767))
    return samples


def _build_click_samples() -> list[int]:
    """Micro UI transition click (950Hz 30ms)."""
    return _generate_tone(950, 30, amplitude=0.18, fade_ms=10)


_SOUND_BUILDERS = {
    SoundType.WAKE: _build_wake_samples,
    SoundType.SUCCESS: _build_success_samples,
    SoundType.WARNING: _build_warning_samples,
    SoundType.CLICK: _build_click_samples,
}


def ensure_sound_file(sound_type: str | SoundType) -> str:
    """
    Ensure the synthesized WAV file for the given sound type exists on disk.
    Returns the absolute path to the playable WAV file.
    """
    key = str(sound_type).lower().split(".")[-1]
    bundled_path = paths.resource_path("assets", f"{key}.wav")
    if os.path.exists(bundled_path):
        return bundled_path

    cache_path = os.path.join(paths.cache_dir(), f"sfx_{key}.wav")
    if not os.path.exists(cache_path):
        builder = _SOUND_BUILDERS.get(key) or _build_wake_samples
        samples = builder()
        _write_wav_file(cache_path, samples)
        logger.debug("Generated SFX WAV: %s", cache_path)

    return cache_path


def play_sound(sound_type: str | SoundType = SoundType.WAKE) -> None:
    """
    Play a futuristic sound effect asynchronously in a background thread.
    Honors audio.sfx.enabled and audio.sfx.volume configs.
    """
    if not config.get("audio", "sfx", "enabled", default=True):
        return

    vol = max(0.0, min(1.0, float(config.get("audio", "sfx", "volume", default=0.45))))
    if vol <= 0.0:
        return

    def _play() -> None:
        try:
            sound_path = ensure_sound_file(sound_type)
            import pygame.mixer
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512)
            sound = pygame.mixer.Sound(sound_path)
            sound.set_volume(vol)
            sound.play()
            logger.debug("SFX played: %s (volume=%.2f)", sound_type, vol)
        except Exception as e:
            logger.debug("SFX playback failed for %s: %s", sound_type, e)

    threading.Thread(target=_play, daemon=True, name="SFXPlayThread").start()


# Backward compatibility alias
def play_activation_sound() -> None:
    play_sound(SoundType.WAKE)

