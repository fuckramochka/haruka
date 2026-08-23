@echo off
REM Haruka Userbot - Windows installer / launcher
REM Usage: install.bat [-- any extra args for the bot]

setlocal
cd /d "%~dp0"

where py >nul 2>nul && (set "PY=py") || (set "PY=python")

if not exist ".venv" (
    echo [Haruka] Creating virtual environment...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [Haruka] Failed to create virtual environment.
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

echo [Haruka] Installing dependencies...
pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo [Haruka] Dependency installation failed.
    exit /b 1
)

echo [Haruka] Starting...
python -m haruka %*

endlocal
