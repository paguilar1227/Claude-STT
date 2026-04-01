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

# Windows constants
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

# Set proper return/arg types for 64-bit Windows — without this, pointer-sized
# return values (HGLOBAL, LPVOID) get truncated to 32-bit c_int.
kernel32.GlobalAlloc.restype = ctypes.wintypes.HGLOBAL
kernel32.GlobalAlloc.argtypes = [ctypes.wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = ctypes.wintypes.BOOL
kernel32.GlobalUnlock.argtypes = [ctypes.wintypes.HGLOBAL]
kernel32.GlobalFree.restype = ctypes.wintypes.HGLOBAL
kernel32.GlobalFree.argtypes = [ctypes.wintypes.HGLOBAL]
user32.OpenClipboard.restype = ctypes.wintypes.BOOL
user32.OpenClipboard.argtypes = [ctypes.wintypes.HWND]
user32.CloseClipboard.restype = ctypes.wintypes.BOOL
user32.EmptyClipboard.restype = ctypes.wintypes.BOOL
user32.SetClipboardData.restype = ctypes.wintypes.HANDLE
user32.SetClipboardData.argtypes = [ctypes.wintypes.UINT, ctypes.wintypes.HANDLE]

_CLIPBOARD_RETRIES = 5
_CLIPBOARD_RETRY_DELAY = 0.05  # 50ms between retries


def inject(text: str):
    """Copy text to clipboard and simulate Ctrl+V in the active window."""
    _copy_to_clipboard(text)
    time.sleep(config.PASTE_DELAY_MS / 1000)
    keyboard.send("ctrl+v")
    logger.debug(f"Injected {len(text)} chars via clipboard + Ctrl+V")


def _copy_to_clipboard(text: str):
    """Copy text to the Windows clipboard using ctypes.

    Retries OpenClipboard if another application holds the lock.
    """
    data = text.encode("utf-16-le") + b"\x00\x00"

    # OpenClipboard can fail if another app has it locked — retry a few times
    for attempt in range(_CLIPBOARD_RETRIES):
        if user32.OpenClipboard(None):
            break
        logger.debug(f"OpenClipboard failed (attempt {attempt + 1}), retrying...")
        time.sleep(_CLIPBOARD_RETRY_DELAY)
    else:
        raise RuntimeError(
            "Could not open clipboard after retries — another application may be holding it"
        )

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
