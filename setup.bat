@echo off
setlocal enabledelayedexpansion
echo ============================================
echo   Claude-STT Setup
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found. Install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

:: Create virtual environment
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
) else (
    echo Virtual environment already exists.
)

:: Activate and install dependencies
echo Installing dependencies...
call .venv\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt

:: Pre-download the Whisper model
echo.
echo Downloading Whisper model (base.en)...
python -c "from faster_whisper import WhisperModel; WhisperModel('base.en', device='cpu', compute_type='int8')"

:: Download Piper TTS engine + voice model
echo.
echo Setting up Piper TTS engine...
python setup_piper.py

:: Install Claude Code TTS hook
echo.
echo ============================================
echo   Claude Code TTS Hook Setup
echo ============================================
echo.
echo The TTS hook lets Claude Code speak responses aloud
echo when you use voice input (STT). It will be added to
echo your Claude Code settings at:
echo   %USERPROFILE%\.claude\settings.json
echo.
set /p "INSTALL_HOOK=Install the Claude Code TTS hook? (Y/N): "
if /i "!INSTALL_HOOK!"=="Y" (
    python -c "
import json, os, sys

settings_path = os.path.join(os.path.expanduser('~'), '.claude', 'settings.json')
project_dir = os.path.dirname(os.path.abspath('setup.bat')).replace('\\', '/')
venv_python = os.path.join(project_dir, '.venv/Scripts/python.exe')
hook_script = os.path.join(project_dir, 'tts_hook.py')
hook_command = f'{venv_python} {hook_script}'

new_hook = {
    'matcher': '',
    'hooks': [{'type': 'command', 'command': hook_command}]
}

# Load existing settings or create new
if os.path.exists(settings_path):
    with open(settings_path, encoding='utf-8') as f:
        settings = json.load(f)
else:
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    settings = {}

# Check if hook already exists
hooks = settings.setdefault('hooks', {})
stop_hooks = hooks.setdefault('Stop', [])

already_installed = any(
    any(h.get('command', '').endswith('tts_hook.py') for h in entry.get('hooks', []))
    for entry in stop_hooks
)

if already_installed:
    print('TTS hook is already installed.')
else:
    stop_hooks.append(new_hook)
    with open(settings_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)
    print('TTS hook installed successfully.')
"
) else (
    echo Skipping hook installation.
    echo You can install it later by re-running setup.bat.
)

echo.
echo ============================================
echo   Setup complete!
echo.
echo   Run: .\claude-stt.bat
echo   Tip: use --offline to prevent any network calls
echo.
echo   Hotkeys (while claude-stt.bat is running):
echo     Double-tap Left Shift = speak (STT)
echo     Double-tap Alt = toggle TTS on/off
echo.
echo   TTS only responds to voice input, not typed input.
echo.
echo   File Resolver: launch from inside a git repo to
echo   auto-resolve spoken file references to actual paths.
echo   Index is cached at %%USERPROFILE%%\.claude-stt\indexes\
echo ============================================
pause
