"""Tests for config module — verify defaults and consistency."""

from claude_stt import config


def test_double_tap_window_is_positive():
    assert config.DOUBLE_TAP_WINDOW_MS > 0


def test_sample_rate_is_whisper_compatible():
    assert config.SAMPLE_RATE == 16000


def test_channels_is_mono():
    assert config.CHANNELS == 1


def test_max_recording_greater_than_min():
    assert config.MAX_RECORDING_SECONDS > config.MIN_RECORDING_SECONDS


def test_engage_and_disengage_freqs_are_different():
    assert config.ENGAGE_FREQS != config.DISENGAGE_FREQS


def test_engage_freqs_are_ascending():
    assert config.ENGAGE_FREQS[0] < config.ENGAGE_FREQS[1]


def test_disengage_freqs_are_descending():
    assert config.DISENGAGE_FREQS[0] > config.DISENGAGE_FREQS[1]


def test_hallucination_patterns_not_empty():
    assert len(config.HALLUCINATION_PATTERNS) > 0


def test_paste_delay_is_reasonable():
    assert 0 < config.PASTE_DELAY_MS < 1000
