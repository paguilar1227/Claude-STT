"""Claude-STT — main entry point and state machine orchestrator."""

import argparse
import ctypes
import enum
import logging
import sys
import threading

from . import config
from .hotkey import DoubleTapDetector
from .injector import inject
from .recorder import Recorder, check_microphone
from .sounds import init as init_sounds, play_engage, play_disengage
from .transcriber import load_model, transcribe

logger = logging.getLogger(__name__)


class State(enum.Enum):
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"


class ClaudeSTT:
    """Main application — coordinates all modules via a state machine."""

    def __init__(self, verbose: bool = False):
        self._state = State.IDLE
        self._lock = threading.Lock()
        self._recorder = Recorder()
        self._detector = DoubleTapDetector(on_double_tap=self._on_double_tap)
        self._verbose = verbose

    def run(self):
        """Start the application. Blocks until interrupted."""
        self._print_status()
        self._detector.start()

        try:
            # Block the main thread — keyboard hooks run in background threads
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            self._detector.stop()
            print("\nClaude-STT stopped.")

    def _on_double_tap(self):
        """Called by the hotkey detector on double-tap. Drives the state machine."""
        with self._lock:
            if self._state == State.IDLE:
                self._start_recording()
            elif self._state == State.RECORDING:
                self._stop_recording()
            # Ignore double-taps during TRANSCRIBING

    def _start_recording(self):
        """Transition: IDLE → RECORDING."""
        self._state = State.RECORDING
        play_engage()
        self._recorder.start(on_auto_stop=self._handle_auto_stop)
        self._print_status()

    def _stop_recording(self):
        """Transition: RECORDING → TRANSCRIBING → IDLE."""
        self._state = State.TRANSCRIBING
        play_disengage()
        self._print_status()

        # Run transcription in a thread to avoid blocking the hotkey listener
        audio = self._recorder.stop()
        if audio is None:
            self._state = State.IDLE
            self._print_status("Recording too short, skipped.")
            return

        thread = threading.Thread(
            target=self._transcribe_and_inject, args=(audio,), daemon=True
        )
        thread.start()

    def _transcribe_and_inject(self, audio):
        """Transcribe audio and inject the result. Runs in a worker thread."""
        try:
            text = transcribe(audio)
            if text:
                inject(text)
                self._print_status(f"Pasted: {_truncate(text, 80)}")
            else:
                self._print_status("No speech detected, skipped.")
        except Exception:
            logger.exception("Transcription/injection failed")
            self._print_status("Error during transcription!")
        finally:
            with self._lock:
                self._state = State.IDLE

    def _handle_auto_stop(self):
        """Called when recording exceeds the max duration."""
        with self._lock:
            if self._state == State.RECORDING:
                self._stop_recording()

    def _print_status(self, detail: str | None = None):
        """Update the console status line."""
        icons = {
            State.IDLE: "\U0001f3a4 Claude-STT ready \u2014 double-tap Shift to speak",
            State.RECORDING: "\U0001f534 RECORDING... (double-tap Shift to stop)",
            State.TRANSCRIBING: "\u23f3 Transcribing...",
        }
        line = icons[self._state]
        if detail:
            line = f"{line}  |  {detail}"
        # Pad to overwrite previous longer lines
        print(f"\r{line:<100}", end="", flush=True)


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _is_admin() -> bool:
    """Check if the process is running with admin privileges (Windows)."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except (AttributeError, OSError):
        # Not on Windows — assume OK
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Claude-STT — Local voice-to-text dictation tool"
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"Whisper model size (default: {config.MODEL_SIZE})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Override model if specified
    if args.model:
        config.MODEL_SIZE = args.model

    # Admin check (Windows-only)
    if sys.platform == "win32" and not _is_admin():
        print(
            "WARNING: Claude-STT requires administrator privileges for global hotkeys.\n"
            "Please re-run as Administrator:\n"
            "  Right-click PowerShell > Run as Administrator > .\\claude-stt.bat\n"
        )
        sys.exit(1)

    # Microphone check
    if not check_microphone():
        print("ERROR: No microphone detected. Please connect a microphone and try again.")
        sys.exit(1)

    # Initialize components
    print("Starting Claude-STT...")
    init_sounds()
    load_model()

    # Run
    app = ClaudeSTT(verbose=args.verbose)
    app.run()


if __name__ == "__main__":
    main()
