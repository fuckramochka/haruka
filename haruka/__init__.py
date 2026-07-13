"""Just a placeholder to do relative imports"""

# ©️ Dan Gazizullin, 2021-2023
# This file is a part of Hikka Userbot
# 🌐 https://github.com/hikariatama/Hikka
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

# ©️ Codrago, 2024-2030
# This file is a part of Haruka Userbot
# 🌐 https://github.com/coddrago/Heroku
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

# Do not delete this file, it will cause errors.

# Install the harukatl -> herokutl import redirect before anything else imports
# the Telegram library. This must run first so both core and plugins resolve.
from . import _harukatl as _harukatl_compat

_harukatl_compat.install()

# Backward compatibility: Haruka renamed all HEROKU_* environment variables to
# HARUKA_*. Mirror any legacy HEROKU_* var onto its HARUKA_* counterpart so
# existing deployments/hosting configs keep working without edits.
import os as _os

for _legacy_key in [k for k in _os.environ if k.startswith("HEROKU_")]:
    _new_key = "HARUKA_" + _legacy_key[len("HEROKU_"):]
    _os.environ.setdefault(_new_key, _os.environ[_legacy_key])
del _os

__author__ = "Dan Gazizullin"
__ForkAuthor__ = "Codrago"
__contact__ = "me@hikariatama.ru"
__copyright__ = "Copyright 2022, Dan Gazizullin"
__credits__ = ["LonamiWebs", "penn5"]
__license__ = "AGPLv3"
__maintainer__ = "developer"
__status__ = "Production"
