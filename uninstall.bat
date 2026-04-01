@echo off
setlocal enabledelayedexpansion
echo ============================================
echo   Claude-STT Uninstall
echo ============================================
echo.

cd /d "%~dp0"

:: Remove virtual environment
if exist ".venv" (
    echo Removing virtual environment...
    rmdir /s /q ".venv"
    echo   Done.
) else (
    echo No virtual environment found, skipping.
)

:: Remove Piper TTS engine
if exist "piper" (
    echo Removing Piper TTS engine...
    rmdir /s /q "piper"
    echo   Done.
) else (
    echo No Piper installation found, skipping.
)

:: Remove state files
if exist "%USERPROFILE%\.claude-stt-tts-enabled" (
    echo Removing TTS toggle state...
    del "%USERPROFILE%\.claude-stt-tts-enabled"
    echo   Done.
)
if exist "%USERPROFILE%\.claude-stt-spoke" (
    echo Removing STT spoke marker...
    del "%USERPROFILE%\.claude-stt-spoke"
    echo   Done.
)
if exist "%USERPROFILE%\.claude-stt-tts-pid" (
    echo Removing TTS PID file...
    del "%USERPROFILE%\.claude-stt-tts-pid"
    echo   Done.
)

:: Remove file resolver index cache
if exist "%USERPROFILE%\.claude-stt\indexes" (
    echo Removing file resolver index cache...
    rmdir /s /q "%USERPROFILE%\.claude-stt\indexes"
    echo   Done.
)
:: Remove .claude-stt dir if empty
if exist "%USERPROFILE%\.claude-stt" (
    rmdir "%USERPROFILE%\.claude-stt" 2>nul
)

:: Remove Claude Code TTS hook
echo.
echo Checking for Claude Code TTS hook...
python -c "
import json, os, sys

settings_path = os.path.join(os.path.expanduser('~'), '.claude', 'settings.json')
if not os.path.exists(settings_path):
    print('No Claude Code settings found, skipping.')
    sys.exit(0)

with open(settings_path, encoding='utf-8') as f:
    settings = json.load(f)

stop_hooks = settings.get('hooks', {}).get('Stop', [])
original_count = len(stop_hooks)

# Remove any hook entries that reference tts_hook.py
filtered = [
    entry for entry in stop_hooks
    if not any(h.get('command', '').endswith('tts_hook.py') for h in entry.get('hooks', []))
]

if len(filtered) < original_count:
    settings['hooks']['Stop'] = filtered
    # Clean up empty hook lists
    if not filtered:
        del settings['hooks']['Stop']
    if not settings['hooks']:
        del settings['hooks']
    with open(settings_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)
    print('TTS hook removed from Claude Code settings.')
else:
    print('No TTS hook found in Claude Code settings, skipping.')
"

:: Remove cached Whisper models
echo.
set "HF_CACHE=%USERPROFILE%\.cache\huggingface\hub"
set "HAS_MODELS=0"

for /d %%D in ("%HF_CACHE%\models--Systran--faster-whisper-*") do (
    set "HAS_MODELS=1"
    echo Found cached model: %%~nxD
)

if "!HAS_MODELS!"=="1" (
    echo.
    echo These cached Whisper models were downloaded by Claude-STT.
    echo Other tools using faster-whisper may share this cache.
    echo.
    set /p "CONFIRM=Delete cached models? (Y/N): "
    if /i "!CONFIRM!"=="Y" (
        for /d %%D in ("%HF_CACHE%\models--Systran--faster-whisper-*") do (
            echo Removing %%~nxD...
            rmdir /s /q "%%D"
        )
        echo   Done.
    ) else (
        echo Skipping model cache removal.
    )
) else (
    echo No cached Whisper models found, skipping.
)

echo.
echo ============================================
echo   Uninstall complete.
echo   The Claude-STT source code was not removed.
echo   To fully remove, delete this folder manually.
echo ============================================
pause
