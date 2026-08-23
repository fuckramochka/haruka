@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo ==========================================
echo   Haruka Userbot - Windows installer
echo ==========================================
echo.

rem Pick a suitable Python interpreter - prefer 3.10-3.12
set "PY="
for %%V in (3.12 3.11 3.10) do (
    if not defined PY (
        py -%%V --version >nul 2>nul && set "PY=py -%%V"
    )
)
if not defined PY ( py --version >nul 2>nul && set "PY=py" )
if not defined PY ( python --version >nul 2>nul && set "PY=python" )
if not defined PY (
    echo [ERROR] Python not found. Install Python 3.10-3.12 from python.org
    goto :fail
)

echo [Haruka] Interpreter:
%PY% --version

set "VPY=.venv\Scripts\python.exe"
set "NEED_CREATE=1"
if exist "!VPY!" (
    if exist ".venv\haruka_marker.txt" (
        set /p MARKER=<".venv\haruka_marker.txt"
        if /i "!MARKER!"=="!PY!" set "NEED_CREATE="
    )
)

if defined NEED_CREATE (
    echo [Haruka] Creating virtual environment...
    if exist ".venv" rmdir /s /q .venv
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        goto :fail
    )
    >".venv\haruka_marker.txt" echo !PY!
) else (
    echo [Haruka] Reusing existing virtual environment.
)

echo [Haruka] Upgrading pip...
"%VPY%" -m pip install --upgrade pip --disable-pip-version-check
echo [Haruka] Installing dependencies - this may take a few minutes...
"%VPY%" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo [Haruka] Retrying installation without pip cache...
    "%VPY%" -m pip install --no-cache-dir --disable-pip-version-check -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed. See messages above.
        goto :fail
    )
)

echo [Haruka] Starting Haruka...
"%VPY%" -m haruka %*

echo.
echo [Haruka] Exited.
goto :end

:fail
echo.
echo *** Something went wrong. Read the messages above. ***
echo Press any key to close this window...
pause >nul
exit /b 1

:end
echo Press any key to close this window...
pause >nul

