"""Text-to-speech via local Piper TTS engine."""

import logging
import os
import subprocess
import tempfile
import wave

import numpy as np
import sounddevice as sd

from . import config

logger = logging.getLogger(__name__)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PIPER_EXE = os.path.join(_PROJECT_ROOT, "piper", "piper.exe")
_VOICE_MODEL = os.path.join(
    _PROJECT_ROOT, "piper", "voices", f"{config.TTS_VOICE}.onnx"
)
_TOGGLE_FILE = os.path.join(os.path.expanduser("~"), ".claude-stt-tts-enabled")
_SPOKE_FILE = os.path.join(os.path.expanduser("~"), ".claude-stt-spoke")
_PID_FILE = os.path.join(os.path.expanduser("~"), ".claude-stt-tts-pid")


def is_enabled() -> bool:
    """Check if TTS is currently enabled."""
    return os.path.exists(_TOGGLE_FILE)


def mark_spoke():
    """Mark that the last input was spoken (STT), so the hook knows to reply with TTS."""
    with open(_SPOKE_FILE, "w") as f:
        f.write("1")


def clear_spoke():
    """Clear the spoke marker."""
    try:
        os.remove(_SPOKE_FILE)
    except FileNotFoundError:
        pass


def was_spoken() -> bool:
    """Check if the last input was via STT."""
    return os.path.exists(_SPOKE_FILE)


def enable():
    """Enable TTS."""
    with open(_TOGGLE_FILE, "w") as f:
        f.write("on")


def disable():
    """Disable TTS."""
    try:
        os.remove(_TOGGLE_FILE)
    except FileNotFoundError:
        pass


def kill_playback():
    """Kill any running TTS background process."""
    try:
        with open(_PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 9)
        logger.info(f"Killed TTS playback process (PID {pid})")
    except (FileNotFoundError, ValueError, ProcessLookupError, OSError):
        pass
    try:
        os.remove(_PID_FILE)
    except FileNotFoundError:
        pass


def toggle() -> bool:
    """Toggle TTS on/off. Returns True if now enabled.

    If TTS is on and playing, toggling off also kills playback.
    """
    if is_enabled():
        kill_playback()
        disable()
        return False
    else:
        enable()
        return True


def is_piper_installed() -> bool:
    """Check if Piper and the voice model are available."""
    return os.path.exists(_PIPER_EXE) and os.path.exists(_VOICE_MODEL)


def speak(text: str):
    """Speak text using Piper TTS. Blocks until playback finishes."""
    if not os.path.exists(_PIPER_EXE):
        logger.error(f"Piper not found at {_PIPER_EXE}. Run setup.bat to install.")
        return

    if not os.path.exists(_VOICE_MODEL):
        logger.error(f"Voice model not found at {_VOICE_MODEL}. Run setup.bat to install.")
        return

    if len(text) > config.TTS_MAX_CHARS:
        text = text[: config.TTS_MAX_CHARS]

    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)

        process = subprocess.run(
            [
                _PIPER_EXE, "--model", _VOICE_MODEL, "--output_file", tmp_path,
                "--length_scale", str(config.TTS_LENGTH_SCALE),
                "--noise_scale", str(config.TTS_NOISE_SCALE),
                "--noise_w", str(config.TTS_NOISE_W),
            ],
            input=text,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if process.returncode != 0:
            logger.error(f"Piper failed: {process.stderr}")
            return

        with wave.open(tmp_path, "rb") as wf:
            rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

        sd.play(audio, samplerate=rate, blocking=True)

    except subprocess.TimeoutExpired:
        logger.error("Piper TTS timed out")
    except Exception:
        logger.exception("TTS playback failed")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
