"""Claude-STT configuration — all tunables in one place."""

# Hotkey
DOUBLE_TAP_KEY = "left shift"
DOUBLE_TAP_WINDOW_MS = 400

# Audio
SAMPLE_RATE = 16000
CHANNELS = 1
MAX_RECORDING_SECONDS = 120
MIN_RECORDING_SECONDS = 0.5  # Skip transcription if shorter

# Whisper
MODEL_SIZE = "base.en"
COMPUTE_TYPE = "int8"
BEAM_SIZE = 5

# Sounds
ENGAGE_FREQS = (440, 880)      # ascending — recording starts
DISENGAGE_FREQS = (880, 440)   # descending — recording stops
TONE_DURATION_MS = 100
TONE_SAMPLE_RATE = 44100       # playback rate for beeps

# Injector
PASTE_DELAY_MS = 100

# Hallucination filter — regex patterns for common Whisper outputs on silence/noise
HALLUCINATION_PATTERNS = [
    r"^\.+$",                          # just dots
    r"^[\s\.\,\!\?]+$",               # just punctuation/whitespace
    r"^[\W\s]*$",                      # no actual words
    r"(?i)bf.?watch",                  # common Whisper garbage
    r"^©",                             # copyright symbol
    r"(?i)^thank(s| you)",             # "Thank you", "Thanks for watching", etc.
    r"(?i)^please subscribe",
    r"(?i)^subtitles by",
    r"(?i)^the end\.?$",
    r"^\[BLANK_AUDIO\]$",
]

# Single words to allow through the filter (useful short commands)
ALLOWED_SINGLE_WORDS = {
    "yes", "no", "stop", "quit", "exit", "help",
    "okay", "hey", "hi", "hello", "maybe",
}

# Non-Latin character threshold — if more than this fraction of chars are
# non-Latin, the transcription is likely a hallucination (e.g., Korean, Arabic)
NON_LATIN_THRESHOLD = 0.3

# Minimum audio byte size to bother transcribing (~0.3s at 16kHz float32)
MIN_AUDIO_BYTES = 10000
