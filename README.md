# Claude-STT

Local voice-to-text dictation tool for Windows. Push-to-talk with walkie-talkie UX — double-tap Left Shift to record, double-tap again to stop. Transcribes speech locally via Whisper and pastes the result into the active window.

**Fully offline. No data leaves the machine.**

## Quick Start

```powershell
# 1. Clone the repo
git clone https://github.com/paguilar1227/Claude-STT.git
cd Claude-STT

# 2. Run setup (creates venv, installs deps, downloads Whisper model)
.\setup.bat

# 3. Launch (auto-elevates to admin for global hotkeys)
.\claude-stt.bat
```

## Usage

1. **Double-tap Left Shift** → ascending beep → recording starts
2. Speak your instruction
3. **Double-tap Left Shift** → descending beep → recording stops
4. Text is transcribed and pasted into the active window

## CLI Options

```powershell
# Use a different Whisper model (default: base.en)
.\claude-stt.bat --model small.en

# Enable debug logging
.\claude-stt.bat --verbose
```

## Configuration

All tunables live in `claude_stt/config.py`:

| Setting | Default | Description |
|---|---|---|
| `DOUBLE_TAP_KEY` | `left shift` | Hotkey to toggle recording |
| `DOUBLE_TAP_WINDOW_MS` | `400` | Max ms between taps to register as double-tap |
| `MODEL_SIZE` | `base.en` | Whisper model (`tiny.en`, `base.en`, `small.en`, `medium.en`) |
| `COMPUTE_TYPE` | `int8` | Quantization type for CPU inference |
| `MAX_RECORDING_SECONDS` | `120` | Auto-stop recording after this duration |
| `SAMPLE_RATE` | `16000` | Microphone sample rate (Whisper expects 16kHz) |

## Requirements

- Windows 10/11
- Python 3.10+
- A microphone
- Administrator privileges (required for global keyboard hooks)

## Dependencies

- `faster-whisper` — Local Whisper inference (CPU, INT8 quantized)
- `sounddevice` — Audio recording and beep playback
- `numpy` — Audio buffer handling
- `keyboard` — Global hotkey detection and paste simulation

No clipboard library needed — clipboard operations use native Windows APIs via ctypes.

## Architecture

```
Double-tap Shift → Audio Recorder → Whisper Transcriber → Clipboard + Ctrl+V
     ↕                                                          ↕
  Sound FX                                               Active Window
```

State machine: `IDLE → RECORDING → TRANSCRIBING → IDLE`

## Edge Cases

- **Normal Shift usage**: Single taps and holds are ignored — only double-tap within 400ms triggers
- **Empty recording**: Recordings under 0.5s are skipped
- **Whisper hallucinations**: Common false positives (e.g., "[BLANK_AUDIO]", "Thank you.") are filtered
- **Long recording**: Auto-stops at 120s with a warning
- **No microphone**: Detected at startup with a clear error message
