"""Tests for transcriber module — multi-layer hallucination filtering."""

from claude_stt.transcriber import _is_hallucination


# --- Layer 1: Empty / too short ---

def test_empty_string_is_hallucination():
    assert _is_hallucination("")


def test_whitespace_only_is_hallucination():
    assert _is_hallucination("   ")


def test_single_char_is_hallucination():
    assert _is_hallucination("a")


# --- Layer 2: Regex pattern matching ---

def test_blank_audio_is_hallucination():
    assert _is_hallucination("[BLANK_AUDIO]")


def test_dots_only_is_hallucination():
    assert _is_hallucination("...")


def test_punctuation_only_is_hallucination():
    assert _is_hallucination("...,!?")


def test_thank_you_is_hallucination():
    assert _is_hallucination("Thank you.")


def test_thank_you_no_period():
    assert _is_hallucination("Thank you")


def test_thanks_for_watching():
    assert _is_hallucination("Thanks for watching.")


def test_please_subscribe():
    assert _is_hallucination("Please subscribe.")


def test_subtitles_by():
    assert _is_hallucination("Subtitles by the Amara.org community")


def test_the_end():
    assert _is_hallucination("The End")


def test_the_end_lowercase():
    assert _is_hallucination("the end")


def test_copyright_symbol():
    assert _is_hallucination("© 2024")


def test_bf_watch_garbage():
    assert _is_hallucination("bfwatch something")


# --- Layer 3: Non-Latin script detection ---

def test_korean_hallucination():
    assert _is_hallucination("시청해 주셔서 감사합니다")


def test_chinese_hallucination():
    assert _is_hallucination("谢谢观看")


def test_arabic_hallucination():
    assert _is_hallucination("شكرا للمشاهدة")


def test_mixed_mostly_latin_is_ok():
    # Some non-Latin chars below threshold is fine
    assert not _is_hallucination("Deploy the café backend server today")


# --- Layer 4: Single-word filter with allowlist ---

def test_single_word_not_in_allowlist():
    assert _is_hallucination("you")


def test_single_word_yes_allowed():
    assert not _is_hallucination("yes")


def test_single_word_no_allowed():
    assert not _is_hallucination("no")


def test_single_word_stop_allowed():
    assert not _is_hallucination("stop")


def test_single_word_help_allowed():
    assert not _is_hallucination("help")


def test_single_word_hello_allowed():
    assert not _is_hallucination("hello")


def test_single_word_exit_allowed():
    assert not _is_hallucination("exit")


def test_single_word_with_punctuation_allowed():
    assert not _is_hallucination("yes.")


# --- Normal dictation should pass ---

def test_normal_text_is_not_hallucination():
    assert not _is_hallucination("Refactor the auth middleware to use JWT")


def test_real_dictation_not_hallucination():
    assert not _is_hallucination(
        "Add a new endpoint for user registration that validates email format"
    )


def test_short_sentence_ok():
    assert not _is_hallucination("Fix the bug")


def test_two_words_ok():
    assert not _is_hallucination("do it")
