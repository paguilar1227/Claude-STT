"""Text injection — clipboard copy + Ctrl+V paste into active window.

Uses ctypes for clipboard (no pyperclip dependency) and keyboard for paste simulation.
"""

import ctypes
import ctypes.wintypes
import logging
import time

import keyboard

from . import config

logger = logging.getLogger(__name__)


def inject(text: str):
    """Copy text to clipboard and simulate Ctrl+V in the active window."""
    _copy_to_clipboard(text)
    time.sleep(config.PASTE_DELAY_MS / 1000)
    keyboard.send("ctrl+v")
    logger.debug(f"Injected {len(text)} chars via clipboard + Ctrl+V")


def _copy_to_clipboard(text: str):
    """Copy text to the Windows clipboard using ctypes."""
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32

    # Encode as UTF-16 LE with null terminator
    data = text.encode("utf-16-le") + b"\x00\x00"

    user32.OpenClipboard(0)
    try:
        user32.EmptyClipboard()
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not h_mem:
            raise RuntimeError("GlobalAlloc failed")
        p_mem = kernel32.GlobalLock(h_mem)
        if not p_mem:
            kernel32.GlobalFree(h_mem)
            raise RuntimeError("GlobalLock failed")
        ctypes.memmove(p_mem, data, len(data))
        kernel32.GlobalUnlock(h_mem)
        user32.SetClipboardData(CF_UNICODETEXT, h_mem)
    finally:
        user32.CloseClipboard()
