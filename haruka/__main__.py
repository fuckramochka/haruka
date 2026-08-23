"""Entry point. Checks for user and starts main script"""

# ©️ Dan Gazizullin, 2021-2023
# This file is a part of Hikka Userbot
# 🌐 https://github.com/hikariatama/Hikka
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

# ©️ Haruka contributors, 2024-2026
# This file is a part of Haruka Userbot
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import getpass
import hashlib
import os
import subprocess
import sys

from ._internal import restart

# Windows consoles often default to legacy codepages (cp1251/cp866),
# which crash on emoji output — force UTF-8 early.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

_DRY_RUN = "--dry-run" in sys.argv

if "--no-git" in sys.argv:
    os.environ["HARUKA_NO_GIT"] = "1"

# Faster event loop on Linux/macOS when uvloop is available
if sys.platform != "win32":
    try:
        import uvloop

        uvloop.install()
    except ImportError:
        pass


def get_file_hash(filename):
    hasher = hashlib.sha256()
    try:
        with open(filename, "rb") as f:
            hasher.update(f.read())
        return hasher.hexdigest()
    except FileNotFoundError:
        return None


def deps():
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "-q",
            "--disable-pip-version-check",
            "--no-warn-script-location",
            "-r",
            "requirements.txt",
        ],
        check=True,
        timeout=600,
        capture_output=True,
    )
    with open(".requirements_hash", "w") as f:
        f.write(get_file_hash("requirements.txt"))


if (
    getpass.getuser() == "root"
    and "--root" not in " ".join(sys.argv)
    and all(trigger not in os.environ for trigger in {"DOCKER", "NO_SUDO"})
):
    print("\U0001f6ab" * 15)
    print("You attempted to run Haruka on behalf of root user")
    print("Please, create a new user and restart script")
    print("If this action was intentional, pass --root argument instead")
    print("\U0001f6ab" * 15)
    print()
    print("Type force_insecure to ignore this warning")
    print("Type no_sudo if your system has no sudo (Debian vibes)")
    inp = input("> ").lower()
    if inp != "force_insecure":
        sys.exit(1)
    elif inp == "no_sudo":
        os.environ["NO_SUDO"] = "1"
        print("Added NO_SUDO in your environment variables")
        restart()

if sys.version_info < (3, 10, 0):
    print("\U0001f6ab Error: you must use at least Python version 3.10.0")
elif __package__ != "haruka":
    print(
        "\U0001f6ab Error: you cannot run this as a script; you must execute as a package"
    )
else:
    try:
        import telethon
    except Exception:
        pass
    else:
        try:
            import telethon  # noqa: F811

            version_parts = telethon.__version__.split(".")[:2]
            if tuple(map(int, version_parts)) < (1, 44):
                raise ImportError
        except (ImportError, ValueError):
            print("\U0001f504 Installing dependencies...")
            deps()
            restart()

    try:
        from . import log

        log.init()
        from . import main
    except ImportError as e:
        print(
            f"{str(e)}\n\U0001f504 Attempting dependencies installation... Just wait ⏱"
        )
        deps()
        restart()

    if "HARUKA_DO_NOT_RESTART" in os.environ:
        del os.environ["HARUKA_DO_NOT_RESTART"]
    if "HARUKA_DO_NOT_RESTART2" in os.environ:
        del os.environ["HARUKA_DO_NOT_RESTART2"]

    prev_hash = None
    if os.path.exists(".requirements_hash"):
        with open(".requirements_hash", "r") as f:
            prev_hash = f.read().strip()

    if prev_hash != get_file_hash("requirements.txt"):
        if _DRY_RUN:
            print(
                "\U0001f504 requirements.txt changed, but skipping install in dry-run"
            )
        else:
            print(
                "\U0001f504 Detected changes in requirements.txt, updating dependencies..."
            )
            deps()
            restart()

    main.haruka.main()
