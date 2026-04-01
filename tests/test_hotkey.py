"""Tests for hotkey module — double-tap detection logic."""

import time
from unittest.mock import MagicMock, patch

from claude_stt import config
from claude_stt.hotkey import DoubleTapDetector


class FakeEvent:
    """Minimal event object for testing."""
    pass


def test_double_tap_fires_callback():
    """Two releases within the time window should trigger the callback."""
    callback = MagicMock()
    detector = DoubleTapDetector(on_double_tap=callback)
    event = FakeEvent()

    # Simulate first tap (press + release)
    detector._on_press(event)
    detector._on_release(event)

    # Simulate second tap quickly
    detector._on_press(event)
    detector._on_release(event)

    callback.assert_called_once()


def test_slow_double_tap_does_not_fire():
    """Two releases outside the time window should NOT trigger."""
    callback = MagicMock()
    detector = DoubleTapDetector(on_double_tap=callback)
    event = FakeEvent()

    detector._on_press(event)
    detector._on_release(event)

    # Wait longer than the double-tap window
    time.sleep((config.DOUBLE_TAP_WINDOW_MS + 100) / 1000)

    detector._on_press(event)
    detector._on_release(event)

    callback.assert_not_called()


def test_single_tap_does_not_fire():
    """A single tap should not trigger the callback."""
    callback = MagicMock()
    detector = DoubleTapDetector(on_double_tap=callback)
    event = FakeEvent()

    detector._on_press(event)
    detector._on_release(event)

    callback.assert_not_called()


def test_triple_tap_fires_only_once():
    """Three rapid taps should only fire once (second tap triggers, third resets)."""
    callback = MagicMock()
    detector = DoubleTapDetector(on_double_tap=callback)
    event = FakeEvent()

    # Tap 1
    detector._on_press(event)
    detector._on_release(event)

    # Tap 2 — triggers
    detector._on_press(event)
    detector._on_release(event)

    # Tap 3 — should NOT trigger again (last_release_time was reset)
    detector._on_press(event)
    detector._on_release(event)

    callback.assert_called_once()


def test_release_without_press_ignored():
    """A release event without a preceding press should be ignored."""
    callback = MagicMock()
    detector = DoubleTapDetector(on_double_tap=callback)
    event = FakeEvent()

    # Release without press
    detector._on_release(event)
    detector._on_release(event)

    callback.assert_not_called()
