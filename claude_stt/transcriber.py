"""Whisper wrapper — local speech-to-text transcription."""

import logging
import re
import time

import numpy as np

from . import config

logger = logging.getLogger(__name__)

_model = None


def _is_model_cached(model_name: str) -> bool:
    """Check if the Whisper model is already in the local HuggingFace cache."""
    try:
        from huggingface_hub import try_to_load_from_cache
        result = try_to_load_from_cache(f"Systran/faster-whisper-{model_name}", "model.bin")
        return isinstance(result, str)  # returns a path string if cached, _CACHED_NO_EXIST or None otherwise
    except Exception:
        return False


def load_model():
    """Load the Whisper model into memory. Call once at startup."""
    global _model
    from faster_whisper import WhisperModel

    if config.OFFLINE and not _is_model_cached(config.MODEL_SIZE):
        print(
            f"ERROR: Offline mode is enabled but the '{config.MODEL_SIZE}' model has not been downloaded yet.\n"
            f"Run once without --offline to download the model:\n"
            f"  .\\claude-stt.bat --model {config.MODEL_SIZE}\n"
        )
        raise SystemExit(1)

    logger.info(f"Loading Whisper model '{config.MODEL_SIZE}' (compute={config.COMPUTE_TYPE})...")
    t0 = time.monotonic()
    _model = WhisperModel(
        config.MODEL_SIZE,
        device="cpu",
        compute_type=config.COMPUTE_TYPE,
        local_files_only=config.OFFLINE,
    )
    elapsed = time.monotonic() - t0
    logger.info(f"Model loaded in {elapsed:.1f}s")


def transcribe(audio: np.ndarray) -> str | None:
    """Transcribe an audio numpy array to text.

    Returns None if the result is empty or a known hallucination.
    """
    if _model is None:
        raise RuntimeError("Whisper model not loaded — call load_model() first")

    # Pre-check: skip tiny audio that's too short to contain speech
    if audio.nbytes < config.MIN_AUDIO_BYTES:
        logger.info(f"Audio too small ({audio.nbytes} bytes), skipping transcription")
        return None

    t0 = time.monotonic()
    segments, info = _model.transcribe(
        audio,
        beam_size=config.BEAM_SIZE,
        language="en",
        vad_filter=True,  # Filter out non-speech segments
    )

    text_parts = []
    for segment in segments:
        text_parts.append(segment.text)

    raw_text = "".join(text_parts).strip()
    elapsed = time.monotonic() - t0

    logger.info(
        f"Transcription: {elapsed:.1f}s, "
        f"audio={info.duration:.1f}s, "
        f"text={len(raw_text)} chars"
    )
    logger.debug(f"Raw transcription: {raw_text!r}")

    if not raw_text:
        logger.info("Empty transcription, skipping")
        return None

    if _is_hallucination(raw_text):
        logger.info(f"Hallucination detected, skipping: {raw_text!r}")
        return None

    corrected = _apply_word_corrections(raw_text)
    if corrected != raw_text:
        logger.info(f"Word corrections applied: {raw_text!r} -> {corrected!r}")

    return corrected


def _apply_word_corrections(text: str) -> str:
    """Apply configured word corrections to transcribed text.

    Matches are case-insensitive. Word-boundary matching is used for
    simple words; patterns containing punctuation use lookahead/lookbehind
    for whitespace or string boundaries instead.
    """
    result = text
    for wrong, correct in config.WORD_CORRECTIONS.items():
        # If the pattern has non-word chars (dots, spaces), use whitespace boundaries
        if re.search(r'[^\w]', wrong):
            pattern = re.compile(
                r'(?<!\w)' + re.escape(wrong) + r'(?!\w)',
                re.IGNORECASE,
            )
        else:
            pattern = re.compile(r'\b' + re.escape(wrong) + r'\b', re.IGNORECASE)
        result = pattern.sub(correct, result)
    return result


def _is_hallucination(text: str) -> bool:
    """Multi-layer hallucination filter (borrowed from claude-code-voice).

    Layers:
    1. Empty/too-short check
    2. Regex patterns for known Whisper garbage
    3. Non-Latin script detection (Whisper hallucinates Korean/Chinese/Arabic on silence)
    4. Single-word filter with allowlist
    """
    if not text or len(text.strip()) < 2:
        return True

    # Known patterns (regex)
    for pattern in config.HALLUCINATION_PATTERNS:
        if re.search(pattern, text):
            logger.debug(f"Matched hallucination pattern {pattern!r}: {text!r}")
            return True

    # Non-Latin script detection
    non_latin = sum(1 for ch in text if ch.isalpha() and ord(ch) > 127)
    if non_latin > len(text) * config.NON_LATIN_THRESHOLD:
        logger.debug(f"Non-Latin script ({non_latin}/{len(text)} chars): {text!r}")
        return True

    # Single-word filter — block unless in allowlist
    words = text.split()
    if len(words) <= 1:
        if text.lower().strip(".!?,") in config.ALLOWED_SINGLE_WORDS:
            return False
        logger.debug(f"Single word not in allowlist: {text!r}")
        return True

    return False
