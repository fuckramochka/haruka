"""Just a placeholder to do relative imports"""

# ©️ Dan Gazizullin, 2021-2023
# This file is a part of Hikka Userbot
# 🌐 https://github.com/hikariatama/Hikka
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

# ©️ Haruka contributors, 2024-2026
# This file is a part of Haruka Userbot
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

# Do not delete this file, it will cause errors.

# Install legacy import aliases (hikka.*, heroku.*, hikkatl, herokutl, ...)
# as early as possible, so every subsequent import benefits from them.
from .compat import install as _install_compat

_install_compat()

__author__ = "Dan Gazizullin"
__ForkAuthor__ = "Haruka contributors"
__contact__ = "me@hikariatama.ru"
__copyright__ = "Copyright 2022, Dan Gazizullin"
__credits__ = ["LonamiWebs", "penn5"]
__license__ = "AGPLv3"
__maintainer__ = "developer"
__status__ = "Production"
