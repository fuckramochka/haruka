@echo off
REM (c) Codrago, 2024-2030 - Haruka Userbot
REM Windows launcher (cmd). First run creates a venv and installs everything
REM through install.py; later runs just start Haruka.
setlocal enableextensions
cd /d "%~dp0"

set "VENV=.venv"
set "SENTINEL=.haruka_installed"
set "GIT_PYTHON_REFRESH=quiet"

REM --- locate a Python launcher ---
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo [haruka] Python 3.10+ not found. Install it from https://www.python.org/downloads/ ^(check "Add to PATH"^) and re-run.
    pause
    exit /b 1
)

if not exist "%SENTINEL%" goto install
if not exist "%VENV%" goto install
goto run

:install
echo [haruka] First run detected - setting everything up. This can take a few minutes.
%PY% -m venv "%VENV%"
if errorlevel 1 (
    echo [haruka] Failed to create virtual environment.
    pause
    exit /b 1
)
call "%VENV%\Scripts\activate.bat"
python install.py --force
if errorlevel 1 (
    echo [haruka] Dependency installation failed. See the log above.
    pause
    exit /b 1
)
goto run

:run
call "%VENV%\Scripts\activate.bat"
echo [haruka] Starting Haruka...
python -m haruka %*
