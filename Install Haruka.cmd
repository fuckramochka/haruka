@echo off
setlocal
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw launcher.pyw & exit /b 0)
where pythonw >nul 2>nul && (start "" pythonw launcher.pyw & exit /b 0)
where py >nul 2>nul && (py bootstrap.py & pause & exit /b %errorlevel%)
where python >nul 2>nul && (python bootstrap.py & pause & exit /b %errorlevel%)
echo Installing Python automatically...
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
if errorlevel 1 (echo Python installation failed. & pause & exit /b 1)
start "" pyw launcher.pyw
