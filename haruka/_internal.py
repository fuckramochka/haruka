# ©️ Dan Gazizullin, 2021-2023
# This file is a part of Hikka Userbot
# 🌐 https://github.com/hikariatama/Hikka
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

# ©️ Haruka contributors, 2024-2026
# This file is a part of Haruka Userbot
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import asyncio
import atexit
import json
import logging
import os
import random
import signal
import sys
import subprocess
import re

# Runtime feature flags, shared across the whole package.
# Read dynamically as `_internal.CUSTOM_EMOJIS` so that runtime
# updates are visible to every consumer.
CUSTOM_EMOJIS = True


def update_feature_flags(config_path):
    """Sync runtime feature flags with values from config file"""
    global CUSTOM_EMOJIS
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        CUSTOM_EMOJIS = not bool(config.get("disable_custom_emojis", False))
    except Exception:
        pass


async def fw_protect():
    await asyncio.sleep(random.randint(1000, 2000) / 1000)


def get_startup_callback() -> callable:
    return lambda *_: os.execl(
        sys.executable,
        sys.executable,
        "-m",
        os.path.relpath(os.path.abspath(os.path.dirname(os.path.abspath(__file__)))),
        *sys.argv[1:],
    )


def die():
    """Platform-dependent way to kill the current process group"""
    match True:
        case _ if "DOCKER" in os.environ:
            sys.exit(0)
        case _ if sys.platform == "win32":
            sys.exit(0)
        case _:
            os.killpg(os.getpgid(os.getpid()), signal.SIGTERM)


def restart():
    if "--sandbox" in " ".join(sys.argv):
        exit(0)

    if "HARUKA_DO_NOT_RESTART2" in os.environ:
        print(
            "Telethon version 1.44 or higher is required, use `pip install -U telethon` for update."
        )
        sys.exit(0)

    logging.getLogger().setLevel(logging.CRITICAL)

    print("🔄 Restarting...")

    match True:
        case _ if "LAVHOST" in os.environ:
            os.system("lavhost restart")
            return
        case _:
            if "HARUKA_DO_NOT_RESTART" not in os.environ:
                os.environ["HARUKA_DO_NOT_RESTART"] = "1"
            else:
                os.environ["HARUKA_DO_NOT_RESTART2"] = "1"

            if "DOCKER" in os.environ or sys.platform == "win32":
                atexit.register(get_startup_callback())
            else:
                signal.signal(signal.SIGTERM, get_startup_callback())
            die()


def print_banner(banner: str):
    print("\033[2J\033[3;1f")
    with open(
        os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "assets",
                banner,
            )
        ),
        "r",
    ) as f:
        print(f.read())


def check_commit_ancestor(commit, repo_path):
    """Check if commit is ancestor of origin/master"""
    try:
        proc = subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                commit,
                "refs/remotes/origin/master",
            ],
            cwd=repo_path,
            capture_output=True,
            timeout=5,
        )
        return proc.returncode == 0
    except (subprocess.TimeoutExpired, Exception):
        return False


def get_branch_name(repo_path):
    """Get the current branch name using multiple methods (gitpython, HEAD, git cmd)"""
    branch_name = None

    try:
        import git

        repo = git.Repo(path=repo_path)
        branch_name = repo.active_branch.name
    except Exception:
        pass

    if not branch_name:
        try:
            head_path = os.path.join(repo_path, ".git", "HEAD")
            with open(head_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content.startswith("ref:"):
                branch_name = content.split("/")[-1]
        except Exception:
            pass

    if not branch_name:
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                candidate = proc.stdout.strip()
                if candidate:
                    branch_name = candidate
        except (subprocess.TimeoutExpired, Exception):
            pass

    if isinstance(branch_name, str):
        branch_name = branch_name.strip().lstrip("refs/heads/")

    return branch_name


def reset_to_master(repo_path):
    """Reset repository to master branch using gitpython or subprocess fallback"""
    try:
        import git

        repo = git.Repo(path=repo_path)
        repo.head.reset(index=True, working_tree=True)
        repo.heads.master.checkout(force=True)
    except Exception:
        try:
            subprocess.run(
                ["git", "reset", "--hard", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                timeout=5,
            )
            subprocess.run(
                ["git", "checkout", "master", "-f"],
                cwd=repo_path,
                capture_output=True,
                timeout=5,
            )
        except (subprocess.TimeoutExpired, Exception):
            pass


def restore_worktree(repo_path):
    """Restore working tree for allowed users. Try `git restore .`, fallback to `git reset --hard`.

    Returns True if an operation succeeded, False otherwise.
    """

    try:
        proc = subprocess.run(
            ["git", "restore", "."], cwd=repo_path, capture_output=True, timeout=5
        )
        if proc.returncode == 0:
            return True
    except (subprocess.TimeoutExpired, Exception):
        pass

    try:
        proc = subprocess.run(
            ["git", "reset", "--hard"], cwd=repo_path, capture_output=True, timeout=5
        )
        return proc.returncode == 0
    except (subprocess.TimeoutExpired, Exception):
        return False
