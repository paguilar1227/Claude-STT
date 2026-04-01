@echo off
:: Claude-STT launcher — run as Administrator for global hotkeys

:: Check admin
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Activate venv and run
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m claude_stt %*
