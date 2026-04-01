"""Double-tap hotkey detection for push-to-talk."""

from __future__ import annotations

import time
import threading
from typing import Callable

import keyboard

from . import config


class DoubleTapDetector:
    """Detects double-tap of a key within a configurable time window.

    Ignores single taps, holds, and normal Shift usage for typing.
    """

    def __init__(self, on_double_tap: Callable[[], None], key: str | None = None):
        self._on_double_tap = on_double_tap
        self._key = key or config.DOUBLE_TAP_KEY
        self._last_release_time: float = 0.0
        self._key_held = False
        self._lock = threading.Lock()
        self._hooks: list = []

    def start(self):
        """Register global keyboard hooks."""
        self._hooks.append(
            keyboard.on_press_key(self._key, self._on_press, suppress=False)
        )
        self._hooks.append(
            keyboard.on_release_key(self._key, self._on_release, suppress=False)
        )

    def stop(self):
        """Unregister this detector's hooks."""
        for hook in self._hooks:
            try:
                keyboard.unhook(hook)
            except Exception:
                pass
        self._hooks.clear()

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
