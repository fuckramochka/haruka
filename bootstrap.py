#!/usr/bin/env python3
"""Self-healing installer. No configuration files need manual editing."""
from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

MINIMUM = (3, 10)
ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
INSTALL_MARKER = VENV / ".haruka-dependencies"


def log(icon: str, message: str) -> None:
    # Legacy Windows consoles (for example cp1251) cannot encode every
    # Unicode status icon. Logging must never abort the installer.
    text = f"{icon} {message}"
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe, flush=True)


def run(command, *, check: bool = True) -> subprocess.CompletedProcess:
    command = [str(value) for value in command]
    log(">", " ".join(command))
    return subprocess.run(command, cwd=ROOT, check=check)


def python_version(executable: str):
    try:
        output = subprocess.check_output(
            [executable, "-c", "import sys;print(sys.version_info[0],sys.version_info[1])"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).split()
        return tuple(map(int, output))
    except (OSError, subprocess.SubprocessError, ValueError):
        return (0, 0)


def compatible(executable: str) -> bool:
    return python_version(executable) >= MINIMUM


def discover_python():
    seen = set()
    for candidate in (
        sys.executable,
        "python3.13",
        "python3.12",
        "python3.11",
        "python3.10",
        "python3",
        "python",
        "py",
    ):
        path = candidate if Path(candidate).is_absolute() else shutil.which(candidate)
        if path and path not in seen:
            seen.add(path)
            if compatible(path):
                return path
    return None


def elevated(*parts: str) -> list[str]:
    if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() != 0:
        return ["sudo", *parts]
    return list(parts)


def install_python() -> None:
    options = []
    if shutil.which("apt-get"):
        options.append(
            (
                elevated("apt-get", "update"),
                elevated(
                    "apt-get",
                    "install",
                    "-y",
                    "python3",
                    "python3-venv",
                    "python3-pip",
                    "git",
                    "build-essential",
                ),
            )
        )
    if shutil.which("dnf"):
        options.append((None, elevated("dnf", "install", "-y", "python3", "python3-pip", "git", "gcc")))
    if shutil.which("pacman"):
        options.append((None, elevated("pacman", "-S", "--needed", "--noconfirm", "python", "python-pip", "git", "base-devel")))
    if shutil.which("zypper"):
        options.append((None, elevated("zypper", "--non-interactive", "install", "python3", "python3-pip", "git")))
    if shutil.which("brew"):
        options.append((None, ["brew", "install", "python@3.12", "git"]))
    if shutil.which("winget"):
        options.append((None, ["winget", "install", "-e", "--id", "Python.Python.3.12", "--accept-package-agreements", "--accept-source-agreements"]))
    errors = []
    for prepare, install in options:
        try:
            if prepare:
                run(prepare)
            run(install)
            return
        except (OSError, subprocess.CalledProcessError) as exc:
            errors.append(str(exc))
    raise RuntimeError("Automatic Python installation failed: " + "; ".join(errors))


def ensure_python() -> str:
    executable = discover_python()
    if executable:
        return executable
    log("!", "Python 3.10+ was not found. Trying the system package manager.")
    install_python()
    executable = discover_python()
    if not executable:
        raise RuntimeError("Python was installed but a compatible executable was not found")
    return executable


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def ensure_venv(executable: str) -> Path:
    target = venv_python()
    if VENV.exists() and not compatible(str(target)):
        log("!", "The existing virtual environment is broken or outdated; recreating it.")
        shutil.rmtree(VENV)
    if not VENV.exists():
        try:
            run([executable, "-m", "venv", VENV])
        except subprocess.CalledProcessError:
            run([executable, "-m", "pip", "install", "--user", "virtualenv"])
            run([executable, "-m", "virtualenv", VENV])
    if not target.exists():
        raise RuntimeError("Virtual environment did not produce a Python executable")
    return target


def retry(command, attempts: int = 3) -> None:
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            run(command)
            return
        except (OSError, subprocess.CalledProcessError) as exc:
            last_error = exc
            if attempt < attempts:
                delay = attempt * 2
                log("!", f"Attempt {attempt} failed; retrying in {delay}s.")
                time.sleep(delay)
    raise RuntimeError(f"Command failed after {attempts} attempts: {last_error}")


def dependency_fingerprint() -> str:
    digest = hashlib.sha256()
    digest.update(f"{sys.version_info.major}.{sys.version_info.minor}".encode())
    for name in ("pyproject.toml", "requirements.txt", "optional_requirements.txt"):
        path = ROOT / name
        if path.exists():
            digest.update(name.encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def dependencies_ready(executable: Path) -> bool:
    if not INSTALL_MARKER.exists():
        return False
    if INSTALL_MARKER.read_text(encoding="utf-8", errors="ignore").strip() != dependency_fingerprint():
        return False
    probe = (
        "import haruka,pyrogram,aiohttp,aiosqlite,cryptography,psutil,qrcode;"
        "from haruka.core.loader import Loader"
    )
    return subprocess.run(
        [executable, "-c", probe],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def install_dependencies(executable: Path) -> None:
    if dependencies_ready(executable):
        log("OK", "Dependencies are already installed and unchanged; skipping download.")
        return
    log(">", "Dependency definition changed or environment needs repair.")
    retry([executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    retry([executable, "-m", "pip", "install", "-e", ".[full]"])
    INSTALL_MARKER.write_text(dependency_fingerprint(), encoding="utf-8")


def doctor(executable: Path) -> None:
    checks = (
        "import haruka",
        "import pyrogram, aiohttp, aiosqlite, cryptography, psutil, qrcode",
        "from haruka.core.loader import Loader",
        "from haruka.web.onboarding import BrowserOnboarding",
    )
    for code in checks:
        run([executable, "-c", code])
    run([executable, "-m", "compileall", "-q", "haruka"])


def launch(executable: Path) -> None:
    log("OK", "Starting Haruka. The browser opens only when account setup is required.")
    os.execv(str(executable), [str(executable), "-m", "haruka"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Install and open Haruka")
    parser.add_argument("--install-only", action="store_true", help="do not start Haruka")
    parser.add_argument("--doctor", action="store_true", help="verify an existing installation")
    args = parser.parse_args()

    log("*", f"Haruka 2.0 Setup - {platform.system()} {platform.machine()}")
    try:
        system_python = ensure_python()
        executable = ensure_venv(system_python)
        was_ready = dependencies_ready(executable)
        if not args.doctor:
            install_dependencies(executable)
        if args.doctor or not was_ready:
            doctor(executable)
            log("OK", "Installation and diagnostics completed successfully.")
        else:
            log("OK", "Existing installation is healthy; skipped package downloads and full diagnostics.")
        if not args.install_only and not args.doctor:
            launch(executable)
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        log("ERROR", str(exc))
        log("i", "The installer kept existing data intact. Run it again to retry repair.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
