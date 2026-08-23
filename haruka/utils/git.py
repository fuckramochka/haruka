# ©️ Haruka contributors, 2024-2026
# This file is a part of Haruka Userbot
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import asyncio
import logging
import os
import subprocess
import typing

import git
import telethon

from .. import version

parser = telethon.utils.sanitize_parse_mode("html")
logger = logging.getLogger(__name__)


def _is_no_git() -> bool:
    return os.environ.get("HARUKA_NO_GIT") == "1"


DEFAULT_REPO_URL = "https://github.com/fuckramochka/haruka"


def get_repo_url() -> str:
    """
    URL of the repository this Haruka distribution tracks.
    Overridable via `HARUKA_REPO_URL` environment variable.
    """
    return (
        os.environ.get("HARUKA_REPO_URL")
        or os.environ.get("HARUKA_ORIGIN_URL")
        or DEFAULT_REPO_URL
    ).rstrip("/")


# GeekTG Compatibility
def get_git_info() -> typing.Tuple[str, str]:
    """
    Get git info
    :return: Git info
    """
    if _is_no_git():
        return ("", "")
    hash_ = get_git_hash()
    return (
        hash_,
        f"{get_repo_url()}/commit/{hash_}" if hash_ else "",
    )


def get_git_hash() -> typing.Union[str, bool]:
    """
    Get current Haruka git hash
    :return: Git commit hash
    """
    if _is_no_git():
        return False
    try:
        return git.Repo().head.commit.hexsha
    except Exception:
        return False


def get_commit_url() -> str:
    """
    Get current Haruka git commit url
    :return: Git commit url
    """
    if _is_no_git():
        return "Unknown"
    try:
        hash_ = get_git_hash()
        return f'<a href="{get_repo_url()}/commit/{hash_}">#{hash_[:7]}</a>'
    except Exception:
        return "Unknown"


def get_git_status() -> str:
    """
    :return: 'Clean' or 'X files modified'.
    """
    if _is_no_git():
        return "Git disabled"
    try:
        process = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if process.returncode != 0:
            return "Not a Git repo"

        output = process.stdout.strip()

        if not output:
            return "Clean"

        count = len(output.splitlines())
        word = "file" if count == 1 else "files"
        return f"{count} {word} modified"

    except subprocess.TimeoutExpired:
        return "Unknown"
    except Exception:
        return "Unknown"


def get_last_commit_message() -> str:
    """
    Get the message of the last commit
    :return: Last commit message
    """
    if _is_no_git():
        return "Unknown"
    try:
        repo = git.Repo()
        return repo.head.commit.message.strip()
    except Exception:
        return "Unknown"


def get_commit_count() -> int:
    """
    Get the total number of commits in the repository
    :return: Number of commits
    """
    if _is_no_git():
        return 0
    try:
        repo = git.Repo()
        return len(list(repo.iter_commits()))
    except Exception:
        return 0


def is_up_to_date():
    repo = git.Repo(search_parent_directories=True)
    diff = any(repo.iter_commits(f"HEAD..origin/{version.branch}", max_count=1))
    return not diff
