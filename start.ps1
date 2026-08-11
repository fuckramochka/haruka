# (c) Codrago, 2024-2030 - Haruka Userbot
# Windows launcher (PowerShell). First run creates a venv and installs
# everything via install.py; later runs just start Haruka.
# Run with:  powershell -ExecutionPolicy Bypass -File .\start.ps1

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$env:GIT_PYTHON_REFRESH = "quiet"
$VenvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

function Info($m) { Write-Host "[haruka] $m" -ForegroundColor Cyan }
function Fail($m) { Write-Host "[haruka] $m" -ForegroundColor Red; Read-Host "Press Enter to exit"; exit 1 }

function Get-PythonCmd {
    foreach ($c in @("py -3.13", "py -3.12", "py -3.11", "py -3.10", "py -3", "python")) {
        $parts = $c.Split(" ")
        $exe = $parts[0]
        if (Get-Command $exe -ErrorAction SilentlyContinue) {
            try {
                $rest = @()
                if ($parts.Length -gt 1) { $rest = $parts[1..($parts.Length - 1)] }
                $v = & $exe @rest -c "import sys;print(sys.version_info[0]*100+sys.version_info[1])" 2>$null
                if ($v -and [int]$v -ge 310) { return $c }
            } catch {}
        }
    }
    return $null
}

if (-not (Test-Path $VenvPy)) {
    Info "First run detected - setting everything up. This can take a few minutes."
    $py = Get-PythonCmd
    if (-not $py) {
        Fail "Python 3.10+ not found. Run 'Install Haruka.cmd' - it installs Python automatically."
    }
    Info "Using interpreter: $py"
    $parts = $py.Split(" ")
    $exe = $parts[0]
    $rest = @()
    if ($parts.Length -gt 1) { $rest = $parts[1..($parts.Length - 1)] }
    & $exe @rest -m venv (Join-Path $PSScriptRoot ".venv")
    if ($LASTEXITCODE -ne 0) { Fail "Failed to create virtual environment." }
}

# install.py verifies the dependency fingerprint itself and skips quickly
# when everything is already installed and up to date.
Info "Checking dependencies..."
& $VenvPy install.py
if ($LASTEXITCODE -ne 0) { Fail "Dependency installation failed. See the log above." }

Info "Starting Haruka..."
& $VenvPy -m haruka @args
