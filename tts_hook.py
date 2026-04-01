"""Claude Code Stop hook — speaks the assistant's response via Piper TTS.

This script is called by Claude Code after each response. It checks if TTS is
enabled AND the last input was via STT (spoken, not typed). If both conditions
are met, it speaks the response in a background process.

All processing is local. No text leaves the machine.
"""

import json
import os
import subprocess
import sys
import tempfile
import wave

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOGGLE_FILE = os.path.join(os.path.expanduser("~"), ".claude-stt-tts-enabled")
SPOKE_FILE = os.path.join(os.path.expanduser("~"), ".claude-stt-spoke")
PID_FILE = os.path.join(os.path.expanduser("~"), ".claude-stt-tts-pid")
PIPER_EXE = os.path.join(SCRIPT_DIR, "piper", "piper.exe")
VOICE_MODEL = os.path.join(SCRIPT_DIR, "piper", "voices", "en_US-ryan-medium.onnx")
MAX_CHARS = 2000
TTS_VOLUME = 0.85  # 0.0–1.0 scale applied to playback

# Piper voice parameters
LENGTH_SCALE = 0.9
NOISE_SCALE = 1.0
NOISE_W = 1.0


def _speak(text_file: str):
    """Background worker: read text from file, generate speech, play it."""
    # Write our PID so the main app can kill us
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    try:
        with open(text_file, encoding="utf-8") as f:
            text = f.read()
    finally:
        try:
            os.unlink(text_file)
        except OSError:
            pass

    if not text or not os.path.exists(PIPER_EXE) or not os.path.exists(VOICE_MODEL):
        return

    tmp_wav = None
    try:
        import numpy as np
        import sounddevice as sd

        fd, tmp_wav = tempfile.mkstemp(suffix=".wav")
        os.close(fd)

        result = subprocess.run(
            [
                PIPER_EXE, "--model", VOICE_MODEL, "--output_file", tmp_wav,
                "--length_scale", str(LENGTH_SCALE),
                "--noise_scale", str(NOISE_SCALE),
                "--noise_w", str(NOISE_W),
            ],
            input=text,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            return

        with wave.open(tmp_wav, "rb") as wf:
            rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

        audio *= TTS_VOLUME
        sd.play(audio, samplerate=rate, blocking=True)

    except Exception:
        pass
    finally:
        if tmp_wav:
            try:
                os.unlink(tmp_wav)
            except OSError:
                pass
        try:
            os.unlink(PID_FILE)
        except OSError:
            pass


def main():
    # If called with --speak, we're the background worker
    if len(sys.argv) > 1 and sys.argv[1] == "--speak":
        _speak(sys.argv[2])
        return

    # Hook mode: check toggle + spoke marker
    if not os.path.exists(TOGGLE_FILE):
        sys.exit(0)

    if not os.path.exists(SPOKE_FILE):
        sys.exit(0)

    # Clear the spoke marker so typed inputs don't trigger TTS
    try:
        os.remove(SPOKE_FILE)
    except OSError:
        pass

    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError, KeyboardInterrupt):
        sys.exit(0)

    text = data.get("last_assistant_message", "")
    if not text:
        sys.exit(0)

    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]

    # Write text to temp file for the background worker
    fd, tmp = tempfile.mkstemp(suffix=".txt", prefix="claude-tts-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)

    # Spawn background process so the hook returns immediately
    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "--speak", tmp],
        creationflags=CREATE_NO_WINDOW,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
