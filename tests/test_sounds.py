"""Tests for sounds module — verify waveform properties."""

import numpy as np

from claude_stt import config
from claude_stt.sounds import _generate_tone, _generate_two_tone


def test_generate_tone_correct_length():
    tone = _generate_tone(440, 100)
    expected_samples = int(config.TONE_SAMPLE_RATE * 100 / 1000)
    assert len(tone) == expected_samples


def test_generate_tone_is_float32():
    tone = _generate_tone(440, 100)
    assert tone.dtype == np.float32


def test_generate_tone_amplitude_within_bounds():
    tone = _generate_tone(440, 100)
    assert np.max(np.abs(tone)) <= 1.0


def test_generate_tone_not_silent():
    tone = _generate_tone(440, 100)
    assert np.max(np.abs(tone)) > 0.5


def test_generate_two_tone_double_length():
    single_len = int(config.TONE_SAMPLE_RATE * config.TONE_DURATION_MS / 1000)
    two_tone = _generate_two_tone((440, 880))
    assert len(two_tone) == single_len * 2


def test_engage_and_disengage_different():
    engage = _generate_two_tone(config.ENGAGE_FREQS)
    disengage = _generate_two_tone(config.DISENGAGE_FREQS)
    # They should be different waveforms (reversed frequency order)
    assert not np.array_equal(engage, disengage)


def test_fade_applied():
    """First and last samples should be near zero due to fade."""
    tone = _generate_tone(440, 100)
    assert abs(tone[0]) < 0.01
    assert abs(tone[-1]) < 0.01
