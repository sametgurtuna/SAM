# SAM — Activation Sound Generator
# Generates a short, subtle audio cue played when the wake word is detected.
# Uses numpy to create a sine tone, saves as WAV to assets/ on first run.

import os
import wave
import struct
import math
import logging
import threading

logger = logging.getLogger(__name__)

# Sound parameters — short, subtle notification
FREQUENCY_HZ = 620              # Tone frequency (pleasant mid-range)
DURATION_MS = 150               # Duration in milliseconds
SAMPLE_RATE = 44100             # Standard audio sample rate
AMPLITUDE = 0.3                 # Volume (0.0–1.0) — subtle, not jarring
FADE_MS = 30                    # Fade in/out to avoid clicks

# Second tone for a two-note chime (slightly higher pitch)
FREQUENCY_HZ_2 = 830
DURATION_MS_2 = 120

# File path
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
SOUND_FILE = os.path.join(ASSETS_DIR, "activation.wav")


def _generate_tone(freq: float, duration_ms: int, sample_rate: int,
                   amplitude: float, fade_ms: int) -> list[int]:
    """Generate a single sine wave tone with fade in/out."""
    num_samples = int(sample_rate * duration_ms / 1000)
    fade_samples = int(sample_rate * fade_ms / 1000)
    samples: list[int] = []

    for i in range(num_samples):
        # Sine wave
        t = i / sample_rate
        value = math.sin(2.0 * math.pi * freq * t)

        # Apply fade envelope
        if i < fade_samples:
            # Fade in
            value *= i / fade_samples
        elif i > num_samples - fade_samples:
            # Fade out
            value *= (num_samples - i) / fade_samples

        # Scale to 16-bit integer range
        sample = int(value * amplitude * 32767)
        samples.append(sample)

    return samples


def _generate_activation_sound() -> None:
    """Generate the two-note activation chime and save as WAV."""
    os.makedirs(ASSETS_DIR, exist_ok=True)

    # Generate two tones
    tone1 = _generate_tone(FREQUENCY_HZ, DURATION_MS, SAMPLE_RATE, AMPLITUDE, FADE_MS)
    # Short gap between notes (20ms silence)
    gap = [0] * int(SAMPLE_RATE * 0.02)
    tone2 = _generate_tone(FREQUENCY_HZ_2, DURATION_MS_2, SAMPLE_RATE, AMPLITUDE * 0.8, FADE_MS)

    all_samples = tone1 + gap + tone2

    # Write WAV file
    with wave.open(SOUND_FILE, "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(SAMPLE_RATE)
        for sample in all_samples:
            wav.writeframes(struct.pack("<h", sample))

    logger.info("Activation sound generated: %s", SOUND_FILE)


def ensure_activation_sound() -> str:
    """Ensure the activation sound file exists, generate if missing. Returns file path."""
    if not os.path.exists(SOUND_FILE):
        _generate_activation_sound()
    return SOUND_FILE


def play_activation_sound() -> None:
    """Play the activation sound in a background thread (non-blocking)."""
    def _play():
        try:
            sound_path = ensure_activation_sound()
            # Use pygame.mixer for playback
            import pygame.mixer
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512)
            sound = pygame.mixer.Sound(sound_path)
            sound.play()
            logger.debug("Activation sound played")
        except Exception as e:
            logger.warning("Failed to play activation sound: %s", e)

    thread = threading.Thread(target=_play, daemon=True)
    thread.start()
