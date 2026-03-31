@echo off
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

echo.
echo ============================================
echo   Setup complete!
echo   Run: .\claude-stt.bat
echo ============================================
pause
