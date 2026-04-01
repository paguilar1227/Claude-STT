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
OFFLINE = False  # If True, skip network calls (model must already be cached)

# Sounds
ENGAGE_FREQS = (440, 880)      # ascending — recording starts
DISENGAGE_FREQS = (880, 440)   # descending — recording stops
TONE_DURATION_MS = 100
TONE_SAMPLE_RATE = 44100       # playback rate for beeps
TONE_VOLUME = 0.2              # 0.0–1.0 amplitude scale for beeps

# TTS (Piper)
TTS_TOGGLE_KEY = "alt"
TTS_MAX_CHARS = 2000           # Max characters to speak per response
TTS_VOICE = "en_US-ryan-medium"
TTS_LENGTH_SCALE = 0.9         # Speed: lower = faster (default 1.0)
TTS_NOISE_SCALE = 1.0          # Expressiveness: higher = more expressive (default 0.667)
TTS_NOISE_W = 1.0              # Rhythm variation: higher = more varied (default 0.8)
TTS_ON_FREQ = 660              # Single beep — TTS enabled
TTS_OFF_FREQ = 330             # Single beep — TTS disabled

# File resolver
RESOLVE_THRESHOLD = 90  # Minimum score to auto-resolve (90+ = high confidence)

# Injector
PASTE_DELAY_MS = 100

# Hallucination filter — regex patterns for common Whisper outputs on silence/noise
HALLUCINATION_PATTERNS = [
    r"^\.+$",                          # just dots
    r"^[\s\.\,\!\?]+$",               # just punctuation/whitespace
    r"^[\W\s]*$",                      # no actual words
    r"(?i)bf.?watch",                  # common Whisper garbage
    r"^©",                             # copyright symbol
    r"(?i)^thanks?\.?$",                # bare "Thank" / "Thanks" / "Thanks."
    r"(?i)^thank you\.?$",              # bare "Thank you."
    r"(?i)^thanks for watching",        # common Whisper hallucination
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

# Word corrections — applied to Whisper output before parsing/pasting.
# Keys are case-insensitive patterns, values are the corrected text.
# Checked as whole words (word boundaries) to avoid false replacements.
WORD_CORRECTIONS = {
    # "cloud" is intentionally NOT here — it's a real word.
    # Whisper sometimes produces these misspellings for "Claude":
    "clawed": "Claude",
    "clod": "Claude",
    "claud": "Claude",
    "clowd": "Claude",
    "klaude": "Claude",
    "klod": "Claude",
    # AI should always be uppercase letters
    "a.i.": "AI",
    "a i": "AI",
    "ay eye": "AI",
}
