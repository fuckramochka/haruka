@echo off
setlocal EnableExtensions
title Haruka 2.0 Setup
cd /d "%~dp0"

rem === 1. Locate a compatible Python interpreter (3.10+) ===
call :find_python
if defined PY_CMD goto have_python

rem === 2. Install Python 3.12 automatically ===
echo [haruka] Python 3.10+ not found. Installing Python automatically...
where winget >nul 2>nul
if errorlevel 1 goto no_winget
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto winget_failed
call :refresh_path
call :find_python
if defined PY_CMD goto have_python
rem winget installs per-user; PATH of this console is stale, so probe known locations:
for %%D in (313 312 311 310) do (
    if not defined PY_CMD if exist "%LocalAppData%\Programs\Python\Python%%D\python.exe" set "PY_CMD="%LocalAppData%\Programs\Python\Python%%D\python.exe""
    if not defined PY_CMD if exist "%ProgramFiles%\Python%%D\python.exe" set "PY_CMD="%ProgramFiles%\Python%%D\python.exe""
)
if defined PY_CMD goto have_python
goto manual_python

:manual_python
echo.
echo [haruka] Could not install Python automatically.
echo Install Python 3.10+ from https://www.python.org/downloads/
echo IMPORTANT: tick the "Add python.exe to PATH" checkbox during installation,
echo then run this file again.
pause
exit /b 1

:no_winget
echo [haruka] winget is unavailable on this Windows.
goto manual_python

:winget_failed
echo [haruka] winget could not install Python.
goto manual_python

:have_python
echo [haruka] Found Python: %PY_CMD%
echo [haruka] Running setup - all libraries will be downloaded automatically.
echo.
%PY_CMD% bootstrap.py
if errorlevel 1 (
    echo.
    echo [haruka] Setup failed - read the messages above.
    pause
    exit /b 1
)
exit /b 0

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

rem ----------------------------------------------------------
:refresh_path
set "SYS_PATH="
set "USR_PATH="
for /f "tokens=2,*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul ^| findstr /i "REG_SZ REG_EXPAND_SZ"') do set "SYS_PATH=%%B"
for /f "tokens=2,*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul ^| findstr /i "REG_SZ REG_EXPAND_SZ"') do set "USR_PATH=%%B"
if defined SYS_PATH if defined USR_PATH set "PATH=%SYS_PATH%;%USR_PATH%"
if defined SYS_PATH if not defined USR_PATH set "PATH=%SYS_PATH%"
exit /b 0
