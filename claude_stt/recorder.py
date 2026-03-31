"""Audio capture from default microphone."""

import logging
import threading
import time

import numpy as np
import sounddevice as sd

from . import config

logger = logging.getLogger(__name__)


class Recorder:
    """Records audio from the default microphone into an in-memory buffer."""

    def __init__(self):
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._recording = False
        self._start_time: float = 0.0
        self._lock = threading.Lock()
        self._auto_stop_timer: threading.Timer | None = None
        self._on_auto_stop: callable | None = None

    def start(self, on_auto_stop: callable | None = None):
        """Begin recording from the default microphone.

        Args:
            on_auto_stop: Callback invoked if recording exceeds MAX_RECORDING_SECONDS.
        """
        with self._lock:
            self._frames = []
            self._recording = True
            self._start_time = time.monotonic()
            self._on_auto_stop = on_auto_stop

        self._stream = sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=config.CHANNELS,
            dtype="float32",
            callback=self._audio_callback,
        )
        self._stream.start()

        # Safety valve — auto-stop after max duration
        self._auto_stop_timer = threading.Timer(
            config.MAX_RECORDING_SECONDS, self._handle_auto_stop
        )
        self._auto_stop_timer.daemon = True
        self._auto_stop_timer.start()

        logger.debug("Recording started")

    def stop(self) -> np.ndarray | None:
        """Stop recording and return the captured audio as a numpy array.

        Returns None if the recording was too short.
        """
        with self._lock:
            self._recording = False

        if self._auto_stop_timer:
            self._auto_stop_timer.cancel()
            self._auto_stop_timer = None

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        duration = time.monotonic() - self._start_time
        logger.debug(f"Recording stopped — {duration:.1f}s captured")

        if duration < config.MIN_RECORDING_SECONDS:
            logger.info("Recording too short, skipping transcription")
            return None

        if not self._frames:
            return None

        audio = np.concatenate(self._frames, axis=0).flatten()
        self._frames = []
        return audio

    @property
    def duration(self) -> float:
        """Current recording duration in seconds."""
        if not self._recording:
            return 0.0
        return time.monotonic() - self._start_time

    def _audio_callback(self, indata, frames, time_info, status):
        """Sounddevice callback — appends audio frames to buffer."""
        if status:
            logger.warning(f"Audio callback status: {status}")
        if self._recording:
            self._frames.append(indata.copy())

    def _handle_auto_stop(self):
        """Called when recording exceeds the maximum duration."""
        logger.warning(
            f"Auto-stopping recording after {config.MAX_RECORDING_SECONDS}s"
        )
        if self._on_auto_stop:
            self._on_auto_stop()


def check_microphone() -> bool:
    """Check if a default microphone is available. Returns True if OK."""
    try:
        device = sd.query_devices(kind="input")
        logger.debug(f"Default input device: {device['name']}")
        return True
    except sd.PortAudioError:
        return False
