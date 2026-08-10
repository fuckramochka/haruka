#!/usr/bin/env python3
# ©️ Codrago, 2024-2030 — Haruka Userbot
# Cross-platform dependency installer.
#
# Run this INSIDE the target interpreter (normally the venv created by the
# start.* launcher). It installs every required and optional Python package.
# Idempotent: writes a sentinel file and skips on later runs unless --force.
#
# Works anywhere CPython 3.10+ runs: Linux, macOS, FreeBSD, Termux, UserLAnd,
# Windows. System packages (python, git, ffmpeg, compilers) are handled by the
# start.sh / start.bat / start.ps1 launchers; this script handles pip packages.

import os
import platform
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SENTINEL = os.path.join(ROOT, ".haruka_installed")
MIN_PY = (3, 10)


def log(msg: str) -> None:
    print(f"\033[36m[haruka-install]\033[0m {msg}", flush=True)


def err(msg: str) -> None:
    print(f"\033[31m[haruka-install]\033[0m {msg}", file=sys.stderr, flush=True)


def pip(*args: str) -> int:
    return subprocess.call(
        [sys.executable, "-m", "pip", "--disable-pip-version-check", *args]
    )


def read_reqs(name: str):
    path = os.path.join(ROOT, name)
    reqs = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if line and not line.startswith("#"):
                    reqs.append(line)
    return reqs


def main() -> int:
    force = "--force" in sys.argv or os.environ.get("HARUKA_FORCE_INSTALL") == "1"

    if sys.version_info < MIN_PY:
        err(
            f"Python {MIN_PY[0]}.{MIN_PY[1]}+ required, found "
            f"{platform.python_version()}"
        )
        return 1

    if os.path.exists(SENTINEL) and not force:
        log("Dependencies already installed (pass --force to reinstall).")
        return 0

    log(
        f"Python {platform.python_version()} on {platform.system()} "
        f"({platform.machine()}) — downloading and installing all libraries..."
    )

    # 1) modern build tooling first (needed for source builds on Termux/BSD/etc.)
    pip("install", "--upgrade", "pip", "setuptools", "wheel")

    # 2) required packages — hard failure if these don't install
    req_file = os.path.join(ROOT, "requirements.txt")
    if not os.path.isfile(req_file):
        err("requirements.txt not found next to install.py")
        return 1
    log("Installing required packages...")
    rc = pip("install", "-U", "-r", req_file)
    if rc != 0:
        err("Failed to install required packages. See the pip output above.")
        return rc

    # 3) optional packages — best-effort, one by one so a single failure
    #    (e.g. ffmpeg wheels, uvloop on Windows) does not abort the install.
    is_windows = platform.system() == "Windows"
    optional = read_reqs("optional_requirements.txt")
    if optional:
        log("Installing optional packages (best-effort)...")
        for req in optional:
            low = req.lower()
            if low.startswith("uvloop") and is_windows:
                log("Skipping uvloop (not supported on Windows).")
                continue
            if pip("install", "-U", req) != 0:
                log(f"Optional package '{req}' failed — skipped.")

    with open(SENTINEL, "w", encoding="utf-8") as f:
        f.write(f"{platform.python_version()} {platform.system()}\n")

    log("All dependencies installed ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
