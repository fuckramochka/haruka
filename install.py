#!/usr/bin/env python3
from __future__ import annotations

"""Cross-platform Haruka Engine installer (standard library only)."""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

MIN_PYTHON = (3, 11)
ROOT = Path(__file__).resolve().parent
IS_WINDOWS = os.name == "nt"


class InstallError(RuntimeError):
    pass


def say(message: str, *, prefix: str = "Haruka") -> None:
    print(f"[{prefix}] {message}", flush=True)


def run(command: list[str], *, retries: int = 0, env: dict[str, str] | None = None) -> None:
    printable = " ".join(command)
    for attempt in range(retries + 1):
        say(printable, prefix="run")
        try:
            subprocess.run(command, cwd=ROOT, check=True, env=env)
            return
        except (OSError, subprocess.CalledProcessError) as exc:
            if attempt >= retries:
                raise InstallError(f"Command failed: {printable}") from exc
            delay = 2**attempt
            say(f"Retrying in {delay}s ({attempt + 1}/{retries})", prefix="warn")
            time.sleep(delay)


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def create_venv(path: Path, *, force: bool) -> Path:
    if force and path.exists():
        say(f"Removing existing environment: {path}")
        shutil.rmtree(path)
    python = venv_python(path)
    if not python.exists():
        say(f"Creating isolated environment in {path}")
        run([sys.executable, "-m", "venv", str(path)])
    return python


def pip_install(python: Path, *, dev: bool, no_venv: bool) -> None:
    env = os.environ.copy()
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    env.setdefault("PIP_DEFAULT_TIMEOUT", "100")
    try:
        run([str(python), "-m", "ensurepip", "--upgrade"], env=env)
    except InstallError:
        say("ensurepip unavailable; using the existing pip", prefix="warn")
    run([str(python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], retries=2, env=env)
    target = f"{ROOT}[dev]" if dev else str(ROOT)
    command = [str(python), "-m", "pip", "install", "-e", target]
    if no_venv and not IS_WINDOWS:
        command.append("--user")
    run(command, retries=2, env=env)


def prepare_config(*, overwrite: bool) -> None:
    source, target = ROOT / ".env.example", ROOT / ".env"
    if target.exists() and not overwrite:
        say("Keeping existing .env")
    else:
        shutil.copyfile(source, target)
        try:
            target.chmod(0o600)
        except OSError:
            pass
        say("Created .env from the safe template")
    for directory in (ROOT / "data", ROOT / "data/snapshots", ROOT / "data/lore"):
        directory.mkdir(parents=True, exist_ok=True)


def doctor(python: Path) -> None:
    run([str(python), "-m", "compileall", "-q", str(ROOT / "haruka")])
    code = "import haruka; print('Haruka Engine', haruka.__version__)"
    run([str(python), "-c", code])


def activation(venv: Path) -> str:
    if IS_WINDOWS:
        return f"{venv}\\Scripts\\Activate.ps1  (PowerShell)\n  or {venv}\\Scripts\\activate.bat  (cmd)"
    return f"source {venv}/bin/activate"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install Haruka Engine on Windows, macOS, Linux or Android/Termux")
    parser.add_argument("--dev", action="store_true", help="install test and lint tools")
    parser.add_argument("--force", action="store_true", help="recreate the virtual environment")
    parser.add_argument("--no-venv", action="store_true", help="install for the current user (fallback for restricted devices)")
    parser.add_argument("--venv", type=Path, default=ROOT / ".venv", help="virtual environment path")
    parser.add_argument("--overwrite-env", action="store_true", help="replace .env with the template")
    parser.add_argument("--no-config", action="store_true", help="do not create .env and data folders")
    parser.add_argument("--skip-doctor", action="store_true", help="skip final import/compile check")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    say(f"Platform: {platform.system()} {platform.machine()} | Python {platform.python_version()}")
    if sys.version_info < MIN_PYTHON:
        raise InstallError(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required; found {platform.python_version()}")
    if not (ROOT / "pyproject.toml").exists():
        raise InstallError("Run install.py from the cloned Haruka repository")

    python = Path(sys.executable)
    if not args.no_venv:
        try:
            python = create_venv(args.venv.resolve(), force=args.force)
        except InstallError:
            say("Virtual environment creation failed. Try: python install.py --no-venv", prefix="hint")
            raise
    pip_install(python, dev=args.dev, no_venv=args.no_venv)
    if not args.no_config:
        prepare_config(overwrite=args.overwrite_env)
    if not args.skip_doctor:
        doctor(python)

    say("Installation completed", prefix="ok")
    if not args.no_venv:
        print(f"\nActivate:\n  {activation(args.venv)}")
    print("\nNext steps:\n  1. Edit .env and add Telegram/API credentials.\n  2. Start with: haruka  (or python main.py)\n  3. Run tests with: python -m pytest")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except InstallError as exc:
        say(str(exc), prefix="error")
        say("See docs/INSTALL.md for platform-specific recovery steps", prefix="hint")
        raise SystemExit(1)
    except KeyboardInterrupt:
        say("Installation cancelled", prefix="warn")
        raise SystemExit(130)
