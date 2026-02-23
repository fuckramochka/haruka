"""Entry point. Checks for user and starts main script"""

# ©️ Dan Gazizullin, 2021-2023
# This file is a part of Hikka Userbot
# 🌐 https://github.com/hikariatama/Hikka
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

# ©️ Codrago, 2024-2025
# This file is a part of Haruka Userbot
# 🌐 https://github.com/fuckramochka/haruka
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import getpass
import os
import subprocess
import sys
import hashlib

from ._internal import restart

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REQUIREMENTS_FILE = os.path.join(BASE_DIR, "requirements.txt")
REQUIREMENTS_HASH_FILE = os.path.join(BASE_DIR, ".requirements_hash")
VENV_DIR = os.path.join(BASE_DIR, ".venv")
VENV_PYTHON = os.path.join(
    VENV_DIR,
    "Scripts" if sys.platform == "win32" else "bin",
    "python.exe" if sys.platform == "win32" else "python",
)


def in_venv() -> bool:
    return bool(os.environ.get("VIRTUAL_ENV")) or (
        hasattr(sys, "base_prefix") and sys.prefix != sys.base_prefix
    )


def get_file_hash(filename):
    hasher = hashlib.sha256()
    try:
        with open(filename, "rb") as f:
            hasher.update(f.read())
        return hasher.hexdigest()
    except FileNotFoundError:
        return None


def reexec_with(python_executable: str):
    os.execv(
        python_executable,
        [
            python_executable,
            "-m",
            "haruka",
            *sys.argv[1:],
        ],
    )


def bootstrap_existing_venv():
    if in_venv():
        return

    if os.path.isfile(VENV_PYTHON):
        print("🐍 Using local virtual environment: .venv")
        reexec_with(VENV_PYTHON)


def run_pip_install(python_executable: str):
    subprocess.run(
        [
            python_executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "-q",
            "--disable-pip-version-check",
            "--no-warn-script-location",
            "-r",
            REQUIREMENTS_FILE,
        ],
        check=True,
        cwd=BASE_DIR,
    )


def write_requirements_hash():
    with open(REQUIREMENTS_HASH_FILE, "w") as f:
        f.write(get_file_hash(REQUIREMENTS_FILE))


def ensure_local_venv():
    if not os.path.isfile(VENV_PYTHON):
        print("🛠 Creating local virtual environment (.venv)...")
        subprocess.run(
            [sys.executable, "-m", "venv", VENV_DIR],
            check=True,
            cwd=BASE_DIR,
        )


def deps():
    try:
        run_pip_install(sys.executable)
        write_requirements_hash()
        return
    except subprocess.CalledProcessError:
        if in_venv():
            raise

    print("⚙️ System Python is externally managed. Installing dependencies in local .venv...")
    ensure_local_venv()
    run_pip_install(VENV_PYTHON)
    write_requirements_hash()
    print("✅ Dependencies installed in .venv. Restarting with venv Python...")
    reexec_with(VENV_PYTHON)


if (
    getpass.getuser() == "root"
    and "--root" not in " ".join(sys.argv)
    and all(trigger not in os.environ for trigger in {"DOCKER", "NO_SUDO"})
):
    print("\U0001F6AB" * 15)
    print("You attempted to run Haruka on behalf of root user")
    print("Please, create a new user and restart script")
    print("If this action was intentional, pass --root argument instead")
    print("\U0001F6AB" * 15)
    print()
    print("Type force_insecure to ignore this warning")
    print("Type no_sudo if your system has no sudo (Debian vibes)")
    inp = input('> ').lower()
    if inp != "force_insecure":
        sys.exit(1)
    elif inp == "no_sudo":
        os.environ["NO_SUDO"] = "1"
        print("Added NO_SUDO in your environment variables")
        restart()

if sys.version_info < (3, 9, 0):
    print("\U0001F6AB Error: you must use at least Python version 3.9.0")
elif __package__ != "haruka":
    print("\U0001F6AB Error: you cannot run this as a script; you must execute as a package")
else:
    bootstrap_existing_venv()

    try:
        import harukatl
    except Exception:
        pass
    else:
        try:
            import harukatl  # noqa: F811
            if tuple(map(int, harukatl.__version__.split("."))) < (1, 1, 0):
                raise ImportError
        except ImportError:
            print("\U0001F504 Installing dependencies...")
            deps()
            restart()

    try:
        from . import log
        log.init()
        from . import main
    except ImportError as e:
        print(f"{str(e)}\n\U0001F504 Attempting dependencies installation... Just wait ⏱")
        deps()
        restart()

    if "HARUKA_DO_NOT_RESTART" in os.environ:
        del os.environ["HARUKA_DO_NOT_RESTART"]
    if "HARUKA_DO_NOT_RESTART2" in os.environ:
        del os.environ["HARUKA_DO_NOT_RESTART2"]

    prev_hash = None
    if os.path.exists(REQUIREMENTS_HASH_FILE):
        with open(REQUIREMENTS_HASH_FILE, "r") as f:
            prev_hash = f.read().strip()

    if prev_hash != get_file_hash(REQUIREMENTS_FILE):
        print("\U0001F504 Detected changes in requirements.txt, updating dependencies...")
        deps()
        restart()
    
    main.haruka.main()
