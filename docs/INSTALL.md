# Installation

The installer uses only Python's standard library and avoids global package
changes by default. It supports Windows 10/11, current macOS, mainstream Linux,
WSL and Android/Termux. No installer can guarantee every modified or unsupported
device, but failures are explicit and recoverable.

## Quick install after cloning

### Linux, macOS, WSL, Termux

```bash
git clone YOUR_REPOSITORY_URL Haruka
cd Haruka
chmod +x install.sh
./install.sh
```

### Windows PowerShell

```powershell
git clone YOUR_REPOSITORY_URL Haruka
cd Haruka
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

### Universal fallback

```bash
python install.py
```

## Options

- `--dev`: install pytest, Ruff and mypy.
- `--force`: rebuild `.venv`.
- `--venv PATH`: choose another environment directory.
- `--no-venv`: current-user install for devices where `venv` is unavailable.
- `--no-config`: leave `.env` and data directories untouched.
- `--overwrite-env`: reset `.env` to the template.
- `--skip-doctor`: skip final compile/import verification.

## Requirements

- Python 3.11 or newer.
- Internet access to PyPI during installation.
- Telegram API credentials for runtime, not installation.

## Recovery

### `venv` is missing on Ubuntu/Debian

```bash
sudo apt update
sudo apt install python3-venv python3-pip
./install.sh
```

### Android / Termux

```bash
pkg update
pkg install python git
./install.sh
```

If Android blocks virtual environments:

```bash
python install.py --no-venv
```

### macOS

Install a current Python with `brew install python` or python.org. Do not use the
old system Python.

### Windows execution policy

Use `Set-ExecutionPolicy -Scope Process Bypass`, or run `py -3.11 install.py`.

### Native wheel/build failure

Upgrade pip with `python -m pip install -U pip setuptools wheel`, then rerun with
`--force`. On unusual CPU architectures, system compiler headers may be needed.

## Uninstall

Delete `.venv`. Runtime state is stored in `data/`; back it up before deleting.
For a `--no-venv` installation, run `python -m pip uninstall haruka-engine`.
