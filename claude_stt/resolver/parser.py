"""Rule-based parser: converts spoken text into a file reference.

Handles symbol words (dot, slash, dash, underscore), casing commands,
filler removal, and extension detection. Defaults to PascalCase since
most enterprise C# codebases use it.
"""

from __future__ import annotations

import re

# Words that map to literal symbols
SYMBOL_MAP = {
    "dot": ".",
    "slash": "/",
    "forward slash": "/",
    "backslash": "\\",
    "back slash": "\\",
    "dash": "-",
    "hyphen": "-",
    "underscore": "_",
    "under score": "_",
    "hash": "#",
    "at": "@",
    "star": "*",
    "equals": "=",
    "colon": ":",
    "tilde": "~",
}

# Filler words to strip (only when they don't contribute to the file name)
FILLER_WORDS = {
    "the", "a", "an", "open", "go", "to", "navigate", "find",
    "show", "me", "look", "at", "for", "in", "file", "please",
    "can", "you", "i", "want", "need", "let", "us",
}

# Known file extensions (without dot) — used to detect extension boundaries
KNOWN_EXTENSIONS = {
    "cs", "csproj", "ts", "tsx", "js", "jsx", "py", "json", "yaml", "yml",
    "xml", "md", "sql", "sh", "ps1", "psm1", "css", "scss", "html",
    "txt", "csv", "toml", "env", "config", "props", "targets",
    "resx", "ruleset", "sln", "dockerfile",
}

# Casing mode keywords
CASING_COMMANDS = {
    "camel case": "camel",
    "camelcase": "camel",
    "pascal case": "pascal",
    "pascalcase": "pascal",
    "snake case": "snake",
    "snakecase": "snake",
    "kebab case": "kebab",
    "kebabcase": "kebab",
    "lowercase": "lower",
    "lower case": "lower",
    "uppercase": "upper",
    "upper case": "upper",
}

# Spoken number words
NUMBER_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10",
}


def parse(spoken_text: str) -> dict:
    """Parse spoken text into a file reference.

    Returns:
        {
            "detected": bool,
            "raw_name": str,       # normalized file reference
            "confidence": str,     # "high", "medium", "low"
            "had_extension": bool, # whether an extension was explicitly spoken
        }
    """
    if not spoken_text or not spoken_text.strip():
        return {"detected": False, "raw_name": "", "confidence": "low", "had_extension": False}

    text = spoken_text.strip().lower()

    # Intent detection: only treat as a file reference if the input contains
    # at least one explicit signal (symbol word, casing command, or "capital").
    # Without a signal, this is regular speech — pass it through unchanged.
    has_file_intent = False

    # Check for symbol words
    for word in text.split():
        if word in SYMBOL_MAP:
            has_file_intent = True
            break
    # Check for two-word symbols
    for phrase in SYMBOL_MAP:
        if " " in phrase and phrase in text:
            has_file_intent = True
            break
    # Check for casing commands
    for phrase in CASING_COMMANDS:
        if phrase in text:
            has_file_intent = True
            break
    # Check for "capital" command
    if re.search(r'\bcapital\b', text):
        has_file_intent = True

    if not has_file_intent:
        return {"detected": False, "raw_name": "", "confidence": "low", "had_extension": False}

    # Detect and extract casing mode if specified
    casing_mode = "pascal"  # default
    for phrase, mode in sorted(CASING_COMMANDS.items(), key=lambda x: -len(x[0])):
        if phrase in text:
            casing_mode = mode
            text = text.replace(phrase, " ").strip()
            break

    # Handle "capital X" → uppercase next word
    text = _process_capital_commands(text)

    # Tokenize
    tokens = text.split()

    # Remove filler words (but only from start/end, not middle of compound names)
    tokens = _strip_fillers(tokens)

    if not tokens:
        return {"detected": False, "raw_name": "", "confidence": "low", "had_extension": False}

    # Process tokens: resolve symbols, numbers, and build the name
    result_parts = []
    had_extension = False
    i = 0
    while i < len(tokens):
        token = tokens[i]

        # Check for two-word symbol phrases
        if i + 1 < len(tokens):
            two_word = f"{token} {tokens[i + 1]}"
            if two_word in SYMBOL_MAP:
                result_parts.append(("symbol", SYMBOL_MAP[two_word]))
                i += 2
                continue

        # Single-word symbol
        if token in SYMBOL_MAP:
            symbol = SYMBOL_MAP[token]
            # Track if this creates a file extension
            if symbol == "." and i + 1 < len(tokens):
                next_token = tokens[i + 1].lower().rstrip(".,!?")
                if next_token in KNOWN_EXTENSIONS:
                    had_extension = True
            result_parts.append(("symbol", symbol))
            i += 1
            continue

        # Number words
        if token in NUMBER_WORDS:
            result_parts.append(("word", NUMBER_WORDS[token]))
            i += 1
            continue

        # Capitalization markers (already processed by _process_capital_commands)
        if token == "capital" and i + 1 < len(tokens):
            # capitalize next token
            next_tok = tokens[i + 1]
            result_parts.append(("word", next_tok.capitalize()))
            i += 2
            continue

        # Regular word
        result_parts.append(("word", token))
        i += 1

    # Build the final name based on casing mode
    raw_name = _assemble(result_parts, casing_mode)

    if not raw_name:
        return {"detected": False, "raw_name": "", "confidence": "low", "had_extension": False}

    # Determine confidence
    confidence = _assess_confidence(raw_name, had_extension, result_parts)

    return {
        "detected": True,
        "raw_name": raw_name,
        "confidence": confidence,
        "had_extension": had_extension,
    }


def _process_capital_commands(text: str) -> str:
    """Convert 'capital X' patterns to preserve casing intent."""
    # Handle "capital letter" pattern: "capital P user capital S service"
    result = re.sub(
        r'\bcapital\s+([a-z])\b',
        lambda m: f"CAPMARKER{m.group(1).upper()}",
        text,
    )
    return result


def _strip_fillers(tokens: list[str]) -> list[str]:
    """Remove filler words from the beginning and end of token list."""
    # Strip from the front
    while tokens and tokens[0].lower() in FILLER_WORDS:
        tokens = tokens[1:]
    # Strip from the end
    while tokens and tokens[-1].lower() in FILLER_WORDS:
        tokens = tokens[:-1]
    return tokens


def _assemble(parts: list[tuple[str, str]], casing_mode: str) -> str:
    """Assemble parts into a file name string based on casing mode."""
    result = []
    word_index = 0

    for kind, value in parts:
        if kind == "symbol":
            result.append(value)
            word_index = 0  # reset after symbol
            continue

        # Handle capital markers
        if value.startswith("CAPMARKER"):
            letter = value[len("CAPMARKER"):]
            result.append(letter)
            continue

        # Apply casing
        if casing_mode == "pascal":
            result.append(value.capitalize())
        elif casing_mode == "camel":
            if word_index == 0:
                result.append(value.lower())
            else:
                result.append(value.capitalize())
        elif casing_mode == "snake":
            if word_index > 0:
                result.append("_")
            result.append(value.lower())
        elif casing_mode == "kebab":
            if word_index > 0:
                result.append("-")
            result.append(value.lower())
        elif casing_mode == "lower":
            result.append(value.lower())
        elif casing_mode == "upper":
            result.append(value.upper())
        else:
            result.append(value)

        word_index += 1

    return "".join(result)


def _assess_confidence(raw_name: str, had_extension: bool, parts: list) -> str:
    """Assess confidence of the parse result."""
    word_count = sum(1 for kind, _ in parts if kind == "word")
    has_symbols = any(kind == "symbol" for kind, _ in parts)

    # High confidence: has extension or path separators
    if had_extension or "/" in raw_name or "\\" in raw_name:
        return "high"

    # Medium confidence: multiple words or has symbols
    if word_count >= 2 or has_symbols:
        return "medium"

    # Low confidence: single word, no extension, no symbols
    return "low"
