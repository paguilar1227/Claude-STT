# Claude-STT

Local voice interface for Windows. Speech-to-text via Whisper, text-to-speech via Piper, file path resolution via fuzzy matching — all running entirely on-device.

- **STT**: Double-tap Left Shift to record, double-tap again to stop. Transcribes and pastes into the active window.
- **TTS**: Double-tap Alt to toggle. When enabled, Claude Code responses are spoken aloud after voice input.
- **File Resolver**: Automatically converts spoken file references (e.g., "cosmos db settings dot cs") to actual file paths in your repo.

**Fully offline. No audio or text ever leaves your computer.** All processing happens locally. Designed to prevent any company data from leaking to external services.

## Prerequisites

- **Windows 10/11**
- **Python 3.10+** — check with `python --version`. If you have an older version, install 3.10+ from [python.org](https://www.python.org/downloads/) or via `winget install Python.Python.3.12`
- **A microphone**
- **Administrator privileges** — needed for global keyboard hooks and clipboard paste injection

## Quick Start

```powershell
# 1. Clone the repo
git clone https://github.com/paguilar1227/Claude-STT.git
cd Claude-STT

# 2. Run setup (creates venv, installs deps, downloads Whisper + Piper)
#    Setup will also offer to install the Claude Code TTS hook.
.\setup.bat

# 3. Launch — run from your project directory for file path resolution
cd C:\your\project
C:\path\to\Claude-STT\claude-stt.bat
```

> **Tip:** You can launch from anywhere. If you're inside a git repo, file path resolution is enabled automatically. If not, STT still works — you just won't get fuzzy file matching. Symbol conversion ("dot", "slash", "dash") works everywhere.

Setup handles everything automatically:
- Creates a Python virtual environment
- Installs pip dependencies (faster-whisper, sounddevice, numpy, keyboard, rapidfuzz)
- Downloads the Whisper STT model (base.en)
- Downloads the Piper TTS engine and voice model (en_US-ryan-medium)
- Optionally installs the Claude Code TTS hook into `~/.claude/settings.json`

## Usage

### Speech-to-Text (STT)

1. **Double-tap Left Shift** → ascending beep → recording starts
2. Speak your instruction
3. **Double-tap Left Shift** → descending beep → recording stops
4. Text is transcribed and pasted into the active window

### File Path Resolution

When launched from inside a git repo, Claude-STT automatically indexes the codebase in the background. Spoken file references are resolved to actual paths before pasting:

| You say | Gets pasted |
|---|---|
| "cosmos db settings dot cs" | `Abstractions/Analysis/CosmosDBSettings.cs` |
| "host builder extensions" | `Utilities/HostBuilderExtensions.cs` |
| "docker dash compose dot yml" | `docker/docker-compose.yml` |
| "snake case get underscore users" | `get_users` |
| "app settings dot linux dot json" | `ContainerServicesCore/.../appsettings.linux.json` |

Even outside a git repo, the parser still converts spoken symbols and applies casing. So "auth middleware dot cs" always becomes `AuthMiddleware.Cs` — you just don't get the fuzzy match to an actual path on disk.

**How the index works:**
- On startup, detects the git repo from the current directory
- Indexes all source files in a background thread (doesn't block STT)
- Caches the index at `~/.claude-stt/indexes/` (nothing is written to the repo)
- On subsequent launches, loads from cache and applies a git delta for changes
- While the index is building, STT works normally — resolution kicks in once the index is ready

**Spoken symbol reference:**

| Say | Produces |
|---|---|
| "dot" | `.` |
| "slash" | `/` |
| "dash" | `-` |
| "underscore" | `_` |
| "capital X" | uppercase letter |

**Casing modes** (default is PascalCase):

| Prefix your phrase with... | Result |
|---|---|
| (nothing) | `AuthMiddleware` (PascalCase) |
| "camel case ..." | `authMiddleware` |
| "snake case ..." | `auth_middleware` |
| "kebab case ..." | `auth-middleware` |

**Number words:** "v two" becomes `V2`, "net eight" becomes `Net8`.

### Word Corrections

Whisper sometimes misspells common terms. Claude-STT auto-corrects these before pasting:

| Whisper hears | Corrected to |
|---|---|
| "clawed", "clod", "claud" | Claude |
| "a.i.", "a i", "ay eye" | AI |

> **Note:** "cloud" is intentionally *not* corrected — it's a real word. Only the clearly wrong spellings are fixed. You can add your own corrections in `claude_stt/config.py` under `WORD_CORRECTIONS`.

### Text-to-Speech (TTS)

1. **Double-tap Alt** → high beep → TTS enabled
2. Use STT to speak to Claude Code
3. Claude's response is spoken aloud automatically
4. **Double-tap Alt** → low beep → TTS disabled

TTS only activates after voice input (STT). Typed inputs do not trigger spoken responses. This requires the Claude Code hook to be installed (setup.bat offers to do this automatically).

**To stop TTS playback mid-sentence:** double-tap Alt. This kills the audio and disables TTS. Double-tap Alt again to re-enable.

## CLI Options

```powershell
# Use a different Whisper model (default: base.en)
.\claude-stt.bat --model small.en

# Run fully offline — no network calls at all (model must already be cached)
.\claude-stt.bat --offline

# Enable debug logging
.\claude-stt.bat --verbose

# Combine flags
.\claude-stt.bat --offline --model small.en --verbose
```

### Offline Mode

By default, `faster-whisper` makes an HTTP call on startup to check if the cached model is up to date. The `--offline` flag disables all network calls — the model loads entirely from the local cache.

If the model hasn't been downloaded yet, `--offline` will exit with a clear error telling you to run once without the flag first.

## Claude Code Hook

The TTS hook is a Claude Code "Stop" hook that runs after each assistant response. Setup installs it automatically, but you can also configure it manually.

**How it works:**
1. Claude-STT sets a marker file (`~/.claude-stt-spoke`) when you use voice input
2. After Claude responds, the hook checks for that marker
3. If present (voice input), it speaks the response via Piper in a background process
4. If absent (typed input), it exits silently
5. The hook never blocks Claude Code — TTS runs in a detached process

**Manual hook setup** (if you skipped it during setup):

Add to `~/.claude/settings.json` under the `hooks` key:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "C:/Users/YOUR_USERNAME/tools/Claude-STT/.venv/Scripts/python.exe C:/Users/YOUR_USERNAME/tools/Claude-STT/tts_hook.py"
          }
        ]
      }
    ]
  }
}
```

Replace `YOUR_USERNAME` with your Windows username. If you already have Stop hooks, add this as an additional entry in the Stop array.

**Uninstall** removes the hook automatically.

## Hotkey Reference

| Hotkey | Action |
|---|---|
| Double-tap **Left Shift** | Start/stop recording (STT) |
| Double-tap **Alt** | Toggle TTS on/off (also stops playback if speaking) |
| **Ctrl+C** | Exit Claude-STT |

## Configuration

All tunables live in `claude_stt/config.py`:

| Setting | Default | Description |
|---|---|---|
| `DOUBLE_TAP_KEY` | `left shift` | STT hotkey |
| `TTS_TOGGLE_KEY` | `alt` | TTS toggle hotkey |
| `DOUBLE_TAP_WINDOW_MS` | `400` | Max ms between taps to register as double-tap |
| `MODEL_SIZE` | `base.en` | Whisper model (`tiny.en`, `base.en`, `small.en`, `medium.en`) |
| `COMPUTE_TYPE` | `int8` | Quantization type for CPU inference |
| `OFFLINE` | `False` | If True, skip all network calls (model must be cached) |
| `TTS_VOICE` | `en_US-ryan-medium` | Piper voice model |
| `TTS_LENGTH_SCALE` | `0.9` | TTS speed: lower = faster |
| `TTS_NOISE_SCALE` | `1.0` | TTS expressiveness: higher = more expressive |
| `TTS_NOISE_W` | `1.0` | TTS rhythm variation: higher = more varied |
| `TTS_MAX_CHARS` | `2000` | Max characters to speak per response |
| `RESOLVE_THRESHOLD` | `90` | Minimum fuzzy match score to auto-resolve file paths |
| `WORD_CORRECTIONS` | (see config.py) | Map of Whisper misspellings to corrected text |
| `MAX_RECORDING_SECONDS` | `120` | Auto-stop recording after this duration |
| `SAMPLE_RATE` | `16000` | Microphone sample rate (Whisper expects 16kHz) |
| `TONE_VOLUME` | `0.2` | Beep volume for STT cues (0.0-1.0) |

TTS playback volume is configured in `tts_hook.py` (`TTS_VOLUME`, default 0.85).

## Uninstall

```powershell
.\uninstall.bat
```

This removes:
- The virtual environment (`.venv/`)
- The Piper TTS engine and voice models (`piper/`)
- State files (`~/.claude-stt-tts-enabled`, `~/.claude-stt-spoke`, `~/.claude-stt-tts-pid`)
- The file resolver index cache (`~/.claude-stt/indexes/`)
- The Claude Code TTS hook from `~/.claude/settings.json`
- Optionally, cached Whisper models from `~/.cache/huggingface/` (prompts for confirmation since other tools may share the cache)

The source code is not removed — delete the folder manually if desired.

## Dependencies

- `faster-whisper` — Local Whisper inference (CPU, INT8 quantized)
- `Piper` — Local text-to-speech (downloaded during setup, not a pip package)
- `rapidfuzz` — Fuzzy string matching for file path resolution
- `sounddevice` — Audio recording and playback
- `numpy` — Audio buffer handling
- `keyboard` — Global hotkey detection and paste simulation

No clipboard library needed — clipboard operations use native Windows APIs via ctypes.

## Architecture

### Full Pipeline

```
                           STARTUP
                             |
              +--------------+--------------+
              |                             |
      Load Whisper Model            Detect Git Repo
      (base.en, ~2s)               (walk up to .git)
              |                             |
              v                    +--------+--------+
         STT Ready                 |                 |
                             Repo found         No repo
                                  |                 |
                           Load/build index    Parser-only mode
                           (background thread, (symbols + casing
                            ~0.5s cached,       still work, no
                            ~1-3s first run)    fuzzy matching)
                                  |
                              Index ready
                           (cached at ~/.claude-stt/indexes/)
```

### Speech-to-Text Flow

```
  +------------------+      +----------------+      +------------------+
  |   Double-tap     |      |                |      |   Whisper STT    |
  |   Left Shift     +----->+   Microphone   +----->+   (local CPU)    |
  |   (start/stop)   |      |   Recording    |      +--------+---------+
  +------------------+      +----------------+               |
                                                    raw transcription
                                                             |
                                                             v
                                                    +------------------+
                                                    | Word Corrections |
                                                    | "clawed" -> Claude|
                                                    | "a.i." -> AI     |
                                                    +--------+---------+
                                                             |
                                                             v
  +------------------+      +----------------+      +------------------+
  |                  |      |   Fuzzy Match  |      |   Rule-based     |
  |   Active Window  +<-----+ against index  +<-----+   Parser         |
  |   (Ctrl+V paste) |      |   (rapidfuzz)  |      | "dot" -> "."     |
  +------------------+      +-------+--------+      | PascalCase, etc. |
          ^                         |                +------------------+
          |                  score >= 90?
          |                    yes -> resolved path
          |                    no  -> parser output or raw transcription
          |
   "Abstractions/Analysis/CosmosDBSettings.cs"
```

### Text-to-Speech Flow (Claude Code Integration)

```
  +------------------+                          +------------------+
  |  Claude Code     |   Stop hook fires        |                  |
  |  finishes        +------------------------->+   tts_hook.py    |
  |  responding      |   (stdin: response JSON) |                  |
  +------------------+                          +--------+---------+
                                                         |
                                               +----+----+----+
                                               |              |
                                         spoke marker    no marker
                                         exists?         (typed input)
                                               |              |
                                               v              v
                                        +------+------+   exit (silent)
                                        |  Piper TTS  |
                                        |  (Ryan voice|
                                        |   local CPU)|
                                        +------+------+
                                               |
                                               v
                                        +------+------+
                                        |   Speaker   |
                                        |  (playback) |
                                        +-------------+

  To interrupt: double-tap Alt (kills playback + disables TTS)
```

### File Resolver Detail

```
  Spoken text                   Parser                    Matcher
  +-----------------------+     +-------------------+     +-------------------+
  | "open the cosmos db   | --> | Strip fillers     | --> | Exact basename?   |
  |  settings dot cs"     |     | "dot" -> "."      |     |   yes -> score 100|
  |                       |     | PascalCase words  |     | Exact stem?       |
  |                       |     | Detect extension  |     |   yes -> score 95 |
  +-----------------------+     +--------+----------+     | Fuzzy match?      |
                                         |                |   rapidfuzz WRatio|
                                "CosmosDbSettings.Cs"     +--------+----------+
                                                                   |
                                                          Repo File Index
                                                          (cached at ~/.claude-stt/indexes/)
                                                          +-------------------+
                                                          | Abstractions/     |
                                                          |   Analysis/       |
                                                          |     CosmosDB-     |
                                                          |     Settings.cs   |
                                                          | Utilities/        |
                                                          |   HostBuilder-    |
                                                          |   Extensions.cs   |
                                                          | ...5000 files     |
                                                          +-------------------+
```

### State Machine

```
                 double-tap                double-tap
                 LShift                    LShift
  +-------+    (start)     +-----------+  (stop)    +--------------+
  |       +--------------->+           +----------->+              |
  | IDLE  |                | RECORDING |            | TRANSCRIBING |
  |       +<---------------+           +<-----------+              |
  +---+---+   (auto-stop   +-----------+  (done)    +------+-------+
      ^       after 120s)                                   |
      |                                                     |
      +-----------------------------------------------------+
              word corrections + resolve + paste + back to IDLE
```

### Data Flow Summary

```
  Nothing leaves your machine. Everything is local:

  Audio:   Microphone -> numpy buffer -> Whisper (CPU) -> text
  Correct: text -> word corrections (regex) -> corrected text
  Files:   os.walk / git diff -> index cache (~/.claude-stt/indexes/)
  Resolve: text -> parser (regex) -> matcher (rapidfuzz) -> path
  Paste:   path -> Windows clipboard (ctypes) -> Ctrl+V
  TTS:     text -> Piper (CPU) -> WAV -> sounddevice playback
```

All processing is local. No data is sent to any external service.

## Edge Cases

- **Normal Shift/Alt usage**: Single taps and holds are ignored — only double-tap within 400ms triggers
- **Empty recording**: Recordings under 0.5s are skipped
- **Whisper hallucinations**: Common false positives (e.g., "[BLANK_AUDIO]", "Thank you.") are filtered
- **Word misspellings**: "clawed", "clod", "a.i." etc. are auto-corrected (configurable in config.py)
- **Long recording**: Auto-stops at 120s with a warning
- **No microphone**: Detected at startup with a clear error message
- **Offline + missing model**: Clear error with instructions to run once without `--offline`
- **TTS without Piper**: Toggle works but speech is skipped with a log warning
- **Long Claude responses**: Truncated to `TTS_MAX_CHARS` (default 2000) before speaking
- **Typed input with TTS on**: No spoken response — TTS only fires after voice input
- **No git repo detected**: Parser still works (symbols, casing), just no fuzzy file matching
- **Index still building**: STT pastes raw transcription until the background index is ready
- **Low-confidence file match**: Below `RESOLVE_THRESHOLD` (90), parser output is pasted instead
