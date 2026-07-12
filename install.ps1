$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$candidates = @(
    @{ Command = "py"; Args = @("-3.13") },
    @{ Command = "py"; Args = @("-3.12") },
    @{ Command = "py"; Args = @("-3.11") },
    @{ Command = "python"; Args = @() },
    @{ Command = "python3"; Args = @() }
)

foreach ($candidate in $candidates) {
    if (Get-Command $candidate.Command -ErrorAction SilentlyContinue) {
        & $candidate.Command @($candidate.Args) -c "import sys; raise SystemExit(sys.version_info < (3, 11))" 2>$null
        if ($LASTEXITCODE -eq 0) {
            & $candidate.Command @($candidate.Args) install.py @args
            exit $LASTEXITCODE
        }
    }
}

Write-Error "Python 3.11+ not found. Install it from https://python.org/downloads/ and enable 'Add Python to PATH'."
