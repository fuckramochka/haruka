"""Represents current userbot version"""

# ©️ Dan Gazizullin, 2021-2023
# This file is a part of Hikka Userbot
# 🌐 https://github.com/hikariatama/Hikka
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

# ©️ Haruka contributors, 2024-2026
# This file is a part of Haruka Userbot
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

__version__ = (3, 2, 9)

import os

NO_GIT = os.environ.get("HARUKA_NO_GIT") == "1"
if not NO_GIT:
    import git
else:
    git = None
from ._internal import (
    check_commit_ancestor,
    get_branch_name,
    reset_to_master,
    restart,
    restore_worktree,
)

if NO_GIT:
    branch = "master"
else:
    try:
        branch = git.Repo(
            path=os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        ).active_branch.name
    except Exception:
        branch = "master"


