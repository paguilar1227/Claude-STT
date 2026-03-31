"""Double-tap hotkey detection for push-to-talk."""

import time
import threading
from typing import Callable

import keyboard

from . import config


class DoubleTapDetector:
    """Detects double-tap of a key within a configurable time window.

    Ignores single taps, holds, and normal Shift usage for typing.
    """

    def __init__(self, on_double_tap: Callable[[], None]):
        self._on_double_tap = on_double_tap
        self._last_release_time: float = 0.0
        self._key_held = False
        self._lock = threading.Lock()

    def start(self):
        """Register global keyboard hooks."""
        keyboard.on_press_key(
            config.DOUBLE_TAP_KEY, self._on_press, suppress=False
        )
        keyboard.on_release_key(
            config.DOUBLE_TAP_KEY, self._on_release, suppress=False
        )

    def stop(self):
        """Unregister all hooks."""
        keyboard.unhook_all()

    def _on_press(self, event):
        """Track that the key is being held down."""
        self._key_held = True

    def _on_release(self, event):
        """On release, check if this is the second tap in the window."""
        with self._lock:
            if not self._key_held:
                return
            self._key_held = False

            now = time.monotonic()
            elapsed_ms = (now - self._last_release_time) * 1000

            if elapsed_ms <= config.DOUBLE_TAP_WINDOW_MS:
                # Double-tap detected — reset so triple-tap doesn't re-fire
                self._last_release_time = 0.0
                self._on_double_tap()
            else:
                self._last_release_time = now
