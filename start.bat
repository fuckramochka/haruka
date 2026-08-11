@echo off
REM (c) Codrago, 2024-2030 - Haruka Userbot
REM Windows launcher (cmd). First run creates a venv and installs everything
REM through install.py; later runs just start Haruka.
setlocal EnableExtensions
title Haruka 2.0
cd /d "%~dp0"

set "VENV=.venv"
set "GIT_PYTHON_REFRESH=quiet"

rem === locate a Python 3.10+ interpreter ===
call :find_python
if not defined PY_CMD (
    echo [haruka] Python 3.10+ not found.
    echo Run "Install Haruka.cmd" first - it installs Python and all libraries automatically.
    pause
    exit /b 1
)

rem === create the virtual environment on first run ===
if exist "%VENV%\Scripts\python.exe" goto venv_ready
echo [haruka] First run detected - setting everything up. This can take a few minutes.
%PY_CMD% -m venv "%VENV%"
if errorlevel 1 (
    echo [haruka] Failed to create virtual environment.
    pause
    exit /b 1
)

:venv_ready
rem install.py is idempotent: it skips instantly once everything is installed.
"%VENV%\Scripts\python.exe" install.py
if errorlevel 1 (
    echo [haruka] Dependency installation failed. See the log above.
    pause
    exit /b 1
)

echo [haruka] Starting Haruka...
"%VENV%\Scripts\python.exe" -m haruka %*
exit /b %errorlevel%

rem ----------------------------------------------------------
:find_python
set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 (
    for %%V in (3.13 3.12 3.11 3.10) do (
        if not defined PY_CMD (
            py -%%V -c "import sys" >nul 2>nul
            if not errorlevel 1 set "PY_CMD=py -%%V"
        )
    )
)
if not defined PY_CMD (
    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "import sys; print('PYOK' if sys.version_info >= (3, 10) else 'PYBAD')" 2>nul | findstr /b PYOK >nul
        if not errorlevel 1 set "PY_CMD=python"
    )
)
exit /b 0
