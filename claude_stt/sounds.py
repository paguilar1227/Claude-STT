"""Beep generation and playback — no external audio files needed."""

import numpy as np
import sounddevice as sd

from . import config


def _generate_tone(frequency: float, duration_ms: int) -> np.ndarray:
    """Generate a sine wave tone at the given frequency and duration."""
    t = np.linspace(
        0,
        duration_ms / 1000,
        int(config.TONE_SAMPLE_RATE * duration_ms / 1000),
        endpoint=False,
    )
    # Apply a short fade-in/fade-out to avoid click artifacts
    tone = np.sin(2 * np.pi * frequency * t).astype(np.float32)
    fade_samples = min(len(tone) // 4, int(config.TONE_SAMPLE_RATE * 0.01))
    if fade_samples > 0:
        fade_in = np.linspace(0, 1, fade_samples, dtype=np.float32)
        fade_out = np.linspace(1, 0, fade_samples, dtype=np.float32)
        tone[:fade_samples] *= fade_in
        tone[-fade_samples:] *= fade_out
    return tone


def _generate_two_tone(freqs: tuple[float, float]) -> np.ndarray:
    """Generate a two-tone beep (e.g., ascending or descending)."""
    tone1 = _generate_tone(freqs[0], config.TONE_DURATION_MS)
    tone2 = _generate_tone(freqs[1], config.TONE_DURATION_MS)
    return np.concatenate([tone1, tone2])


# Pre-generate at import time so playback is instant
_engage_beep: np.ndarray | None = None
_disengage_beep: np.ndarray | None = None


def init():
    """Pre-generate beep sounds. Call once at startup."""
    global _engage_beep, _disengage_beep
    _engage_beep = _generate_two_tone(config.ENGAGE_FREQS)
    _disengage_beep = _generate_two_tone(config.DISENGAGE_FREQS)


def play_engage():
    """Play the ascending two-tone beep (recording starts)."""
    if _engage_beep is not None:
        sd.play(_engage_beep, samplerate=config.TONE_SAMPLE_RATE, blocking=False)


def play_disengage():
    """Play the descending two-tone beep (recording stops)."""
    if _disengage_beep is not None:
        sd.play(_disengage_beep, samplerate=config.TONE_SAMPLE_RATE, blocking=False)
