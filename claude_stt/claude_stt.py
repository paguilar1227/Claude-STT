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
from .resolver import VoiceFileResolver, find_repo_root
from .resolver.parser import parse as parse_file_ref
from .sounds import init as init_sounds, play_engage, play_disengage, play_tts_on, play_tts_off
from . import tts
from .transcriber import load_model, transcribe

logger = logging.getLogger(__name__)


class State(enum.Enum):
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"


class ClaudeSTT:
    """Main application — coordinates all modules via a state machine."""

    def __init__(self, verbose: bool = False, resolver: VoiceFileResolver | None = None):
        self._state = State.IDLE
        self._lock = threading.Lock()
        self._recorder = Recorder()
        self._detector = DoubleTapDetector(on_double_tap=self._on_double_tap)
        self._tts_detector = DoubleTapDetector(
            on_double_tap=self._on_tts_toggle,
            key=config.TTS_TOGGLE_KEY,
        )
        self._verbose = verbose
        self._resolver = resolver

    def run(self):
        """Start the application. Blocks until interrupted."""
        self._print_status()
        self._detector.start()
        self._tts_detector.start()

        try:
            # Block main thread with short timeouts so Ctrl+C works on Windows
            stop = threading.Event()
            while not stop.is_set():
                stop.wait(timeout=0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self._detector.stop()
            self._tts_detector.stop()
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
            self._print_status("Recording too short, skipped.", newline=True)
            return

        thread = threading.Thread(
            target=self._transcribe_and_inject, args=(audio,), daemon=True
        )
        thread.start()

    def _resolve_file_refs(self, text: str) -> str:
        """Try to resolve spoken file references in the text.

        Three modes:
        1. Resolver ready + high-confidence match -> resolved file path
        2. Resolver not available -> parser-only (symbol/casing conversion)
        3. No file reference detected -> original text
        """
        # If resolver is ready, try full resolution (parse + fuzzy match)
        if self._resolver is not None and self._resolver.is_ready():
            result = self._resolver.resolve(text, threshold=config.RESOLVE_THRESHOLD)
            if result["detected"] and result["resolved_path"] and result["score"] >= config.RESOLVE_THRESHOLD:
                logger.info(
                    f"Resolved '{result['raw_name']}' -> {result['resolved_path']} "
                    f"(score={result['score']})"
                )
                return result["resolved_path"]

        # Fallback: run parser only for symbol/casing conversion
        # (useful even without a repo — "dot", "slash", "dash" etc. still work)
        parsed = parse_file_ref(text)
        if parsed["detected"] and parsed["raw_name"] != text:
            logger.info(f"Parser converted: {text!r} -> {parsed['raw_name']!r}")
            return parsed["raw_name"]

        return text

    def _transcribe_and_inject(self, audio):
        """Transcribe audio and inject the result. Runs in a worker thread."""
        try:
            text = transcribe(audio)
            if text:
                resolved = self._resolve_file_refs(text)
                inject(resolved)
                tts.mark_spoke()
                if resolved != text:
                    self._print_status(
                        f"Resolved: {_truncate(resolved, 60)} (from: {_truncate(text, 40)})",
                        newline=True,
                    )
                else:
                    self._print_status(f"Pasted: {_truncate(text, 80)}", newline=True)
            else:
                self._print_status("No speech detected, skipped.", newline=True)
        except Exception:
            logger.exception("Transcription/injection failed")
            self._print_status("Error during transcription!", newline=True)
        finally:
            with self._lock:
                self._state = State.IDLE

    def _on_tts_toggle(self):
        """Called by the TTS hotkey detector on double-tap Right Shift."""
        enabled = tts.toggle()
        if enabled:
            play_tts_on()
            self._print_status("TTS enabled (Claude responses will be spoken)", newline=True)
        else:
            play_tts_off()
            self._print_status("TTS disabled", newline=True)

    def _handle_auto_stop(self):
        """Called when recording exceeds the max duration."""
        with self._lock:
            if self._state == State.RECORDING:
                self._stop_recording()

    def _print_status(self, detail: str | None = None, newline: bool = False):
        """Update the console status line.

        Args:
            detail: Optional extra text to show alongside the state.
            newline: If True, print on a new line instead of overwriting.
        """
        tts_tag = " [TTS on]" if tts.is_enabled() else ""
        icons = {
            State.IDLE: f"\U0001f3a4 Claude-STT ready{tts_tag} \u2014 double-tap LShift=speak, Alt=TTS",
            State.RECORDING: "\U0001f534 RECORDING... (double-tap LShift to stop)",
            State.TRANSCRIBING: "\u23f3 Transcribing...",
        }
        line = icons[self._state]
        if detail:
            line = f"{line}  |  {detail}"
        if newline:
            # Clear current line, print result on its own line, then reprint status
            print(f"\r{' ':<100}", end="", flush=True)
            print(f"\r{detail}")
            print(f"{icons[self._state]:<100}", end="", flush=True)
        else:
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
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run fully offline — no network calls (model must already be cached)",
    )
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Override config from CLI args
    if args.model:
        config.MODEL_SIZE = args.model
    if args.offline:
        config.OFFLINE = True

    # Admin check (Windows-only)
    if sys.platform == "win32" and not _is_admin():
        print(
            "WARNING: Claude-STT requires administrator privileges for global hotkeys and clipboard access.\n"
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
    print("Privacy: all speech processing happens locally. No audio or text leaves this computer.")
    init_sounds()
    load_model()

    # Auto-detect repo and start background indexing for file resolver
    resolver = None
    repo_root = find_repo_root()
    if repo_root:
        logger.info(f"Detected repo: {repo_root} — indexing in background...")
        resolver = VoiceFileResolver.background(repo_root)
    else:
        logger.info("No git repo detected — file resolver disabled")

    # Run
    app = ClaudeSTT(verbose=args.verbose, resolver=resolver)
    app.run()


if __name__ == "__main__":
    main()
