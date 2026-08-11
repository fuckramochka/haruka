#!/usr/bin/env python3
# ©️ Codrago, 2024-2030 — Haruka Userbot
# Cross-platform dependency installer (hardened).
#
# Run this INSIDE the target interpreter (normally the venv created by the
# start.* launcher). It installs every required and optional Python package.
# Idempotent: writes a sentinel file and skips on later runs unless --force.
#
# Reliability strategy:
#   1. Upgrade pip/setuptools/wheel (best-effort).
#   2. Bulk-install requirements.txt with retries.
#   3. If the bulk install fails, fall back to installing each package
#      individually with retries, so one flaky package can't kill the rest.
#   4. Verify that every critical module actually imports; fail loudly listing
#      exactly what is missing.
#   5. Optional packages are best-effort and never abort the install.

import hashlib
import os
import platform
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
SENTINEL = os.path.join(ROOT, ".haruka_installed")
MIN_PY = (3, 10)
ATTEMPTS = 3

# Critical import probes: module name -> pip-independent import statement.
CRITICAL_IMPORTS = [
    ("pyrogram (kurigram)", "import pyrogram"),
    ("herokutl (heroku-tl-new)", "import herokutl"),
    ("harukatl alias", "import haruka; import harukatl"),
    ("aiogram", "import aiogram"),
    ("aiohttp", "import aiohttp"),
    ("aiohttp_jinja2", "import aiohttp_jinja2"),
    ("aiosqlite", "import aiosqlite"),
    ("cryptography", "import cryptography"),
    ("python-dotenv", "import dotenv"),
    ("emoji", "import emoji"),
    ("GitPython", "import git"),
    ("grapheme", "import grapheme"),
    ("Jinja2", "import jinja2"),
    ("meval", "import meval"),
    ("orjson", "import orjson"),
    ("psutil", "import psutil"),
    ("pydantic", "import pydantic"),
    ("qrcode", "import qrcode"),
    ("requests", "import requests"),
    ("Pillow", "import PIL"),
    ("aiofile", "import aiofile"),
    ("aiofiles", "import aiofiles"),
    ("pyaes", "import pyaes"),
    ("rsa", "import rsa"),
    ("werkzeug", "import werkzeug"),
    ("bs4", "import bs4"),
    ("ruamel.yaml", "from ruamel.yaml import YAML"),
]


def log(msg: str) -> None:
    print(f"\033[36m[haruka-install]\033[0m {msg}", flush=True)


def err(msg: str) -> None:
    print(f"\033[31m[haruka-install]\033[0m {msg}", file=sys.stderr, flush=True)


def pip(*args: str) -> int:
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "pip",
            "--disable-pip-version-check",
            "--retries",
            "5",
            "--timeout",
            "60",
            *args,
        ]
    )


def pip_install(*args: str) -> int:
    # --prefer-binary: never try to build from source when a wheel exists
    # (critical on Windows where most users have no C compiler).
    return pip("install", "--prefer-binary", *args)


def with_retries(fn, attempts: int = ATTEMPTS) -> bool:
    for attempt in range(1, attempts + 1):
        if fn() == 0:
            return True
        if attempt < attempts:
            delay = attempt * 2
            log(f"Attempt {attempt} failed; retrying in {delay}s...")
            time.sleep(delay)
    return False


def fingerprint() -> str:
    """Hash of the dependency definitions + interpreter version.

    The sentinel only skips installation when this fingerprint matches, so
    editing requirements.txt or switching Python versions triggers a reinstall
    instead of silently running with stale packages."""
    digest = hashlib.sha256()
    digest.update(platform.python_version().encode())
    for name in ("requirements.txt", "optional_requirements.txt"):
        path = os.path.join(ROOT, name)
        if os.path.isfile(path):
            digest.update(name.encode())
            with open(path, "rb") as f:
                digest.update(f.read())
    return digest.hexdigest()


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


def verify_imports() -> list:
    """Return a list of (label, statement) tuples that failed to import."""
    failed = []
    for label, statement in CRITICAL_IMPORTS:
        rc = subprocess.call(
            [sys.executable, "-c", statement],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if rc != 0:
            failed.append(label)
    return failed


def main() -> int:
    force = "--force" in sys.argv or os.environ.get("HARUKA_FORCE_INSTALL") == "1"

    if sys.version_info < MIN_PY:
        err(
            f"Python {MIN_PY[0]}.{MIN_PY[1]}+ required, found "
            f"{platform.python_version()}"
        )
        return 1

    if os.path.exists(SENTINEL) and not force:
        try:
            with open(SENTINEL, encoding="utf-8") as f:
                if f.read().strip() == fingerprint():
                    log("Dependencies already installed and up to date (use --force to reinstall).")
                    return 0
        except OSError:
            pass
        log("Dependency definitions changed - reinstalling...")

    log(
        f"Python {platform.python_version()} on {platform.system()} "
        f"({platform.machine()}) — downloading and installing all libraries..."
    )

    # 1) modern build tooling first (best-effort: an old pip still works)
    if not with_retries(
        lambda: pip_install("--upgrade", "pip", "setuptools", "wheel"), attempts=2
    ):
        log("pip self-upgrade failed; continuing with the bundled pip.")

    # 2) required packages — bulk first, then per-package fallback.
    req_file = os.path.join(ROOT, "requirements.txt")
    reqs = read_reqs("requirements.txt")
    if not reqs:
        err("requirements.txt not found or empty next to install.py")
        return 1

    log(f"Installing {len(reqs)} required packages...")
    if not with_retries(lambda: pip_install("-U", "-r", req_file), attempts=2):
        log("Bulk install failed — switching to per-package installation.")
        failed = []
        for req in reqs:
            log(f"Installing {req} ...")
            if not with_retries(lambda r=req: pip_install("-U", r)):
                failed.append(req)
                err(f"FAILED to install: {req}")
        if failed:
            err("These required packages could not be installed:")
            for item in failed:
                err(f"  - {item}")
            err("Check your internet connection and re-run this installer.")
            return 1

    # 3) verify that everything critical actually imports.
    log("Verifying that every library imports cleanly...")
    missing = verify_imports()
    if missing:
        err("The following libraries did not import after installation:")
        for label in missing:
            err(f"  - {label}")
        err("Re-run this installer; if it persists, install the packages above manually.")
        return 1

    # 4) optional packages — best-effort, one by one so a single failure
    #    (e.g. uvloop on Windows) does not abort the install.
    is_windows = platform.system() == "Windows"
    optional = read_reqs("optional_requirements.txt")
    if optional:
        log("Installing optional packages (best-effort)...")
        for req in optional:
            low = req.lower()
            if low.startswith("uvloop") and is_windows:
                log("Skipping uvloop (not supported on Windows).")
                continue
            if pip_install("-U", req) != 0:
                log(f"Optional package '{req}' failed — skipped (not required).")

    with open(SENTINEL, "w", encoding="utf-8") as f:
        f.write(fingerprint() + "\n")

    log("All dependencies installed and verified ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
