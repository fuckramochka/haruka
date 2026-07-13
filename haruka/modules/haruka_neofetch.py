# ©️ Codrago, 2024-2030
# This file is a part of Haruka Userbot
# 🌐 https://github.com/coddrago/Heroku
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import getpass
import logging
import platform as lib_platform
import time

import psutil
import harukatl
from harukatl.tl.types import Message

from .. import loader, utils, version

logger = logging.getLogger(__name__)

LOGO = (
    "    \u2588\u2588\u2557  \u2588\u2588\u2557\n"
    "    \u2588\u2588\u2551  \u2588\u2588\u2551\n"
    "    \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551\n"
    "    \u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2551\n"
    "    \u2588\u2588\u2551  \u2588\u2588\u2551\n"
    "    \u2255\u2550\u255d  \u2255\u2550\u255d\n"
)


@loader.tds
class HarukaNeofetchMod(loader.Module):
    """Neofetch-style system card for Haruka"""

    strings = {
        "name": "HarukaNeofetch",
        "card": (
            "<b>\ud83e\ude90 Haruka Neofetch</b>\n"
            "<code>{logo}</code>\n"
            "<b>{user}</b>@<b>{host}</b>\n"
            "<code>-----------------------------</code>\n"
            "<b>Haruka</b>: <code>{hv}</code> (<i>{branch}</i>)\n"
            "<b>Haruka-TL</b>: <code>{htl}</code>\n"
            "<b>Python</b>: <code>{py}</code>\n"
            "<b>OS</b>: <code>{os}</code>\n"
            "<b>Kernel</b>: <code>{kernel}</code>\n"
            "<b>Uptime</b>: <code>{uptime}</code>\n"
            "<b>CPU</b>: <code>{cores} core(-s), {cpu}%</code>\n"
            "<b>RAM</b>: <code>{ram} MB</code>\n"
            "<b>Disk</b>: <code>{disk}</code>\n"
            "<b>Ping</b>: <code>{ping} ms</code>"
        ),
    }

    strings_ru = {
        "card": (
            "<b>\ud83e\ude90 Haruka Neofetch</b>\n"
            "<code>{logo}</code>\n"
            "<b>{user}</b>@<b>{host}</b>\n"
            "<code>-----------------------------</code>\n"
            "<b>Haruka</b>: <code>{hv}</code> (<i>{branch}</i>)\n"
            "<b>Haruka-TL</b>: <code>{htl}</code>\n"
            "<b>Python</b>: <code>{py}</code>\n"
            "<b>\u041e\u0421</b>: <code>{os}</code>\n"
            "<b>\u042f\u0434\u0440\u043e</b>: <code>{kernel}</code>\n"
            "<b>\u0410\u043f\u0442\u0430\u0439\u043c</b>: <code>{uptime}</code>\n"
            "<b>CPU</b>: <code>{cores} \u044f\u0434\u0440\u0430, {cpu}%</code>\n"
            "<b>RAM</b>: <code>{ram} MB</code>\n"
            "<b>\u0414\u0438\u0441\u043a</b>: <code>{disk}</code>\n"
            "<b>\u041f\u0438\u043d\u0433</b>: <code>{ping} ms</code>"
        ),
    }

    def _get_os_name(self) -> str:
        try:
            with open("/etc/os-release", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME"):
                        return line.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
        return lib_platform.system() or "Unknown"

    def _disk(self) -> str:
        try:
            usage = psutil.disk_usage("/")
            gb = 1024 ** 3
            return (
                f"{round(usage.used / gb, 1)}/{round(usage.total / gb, 1)} GB"
                f" ({usage.percent}%)"
            )
        except Exception:
            return "n/a"

    @loader.command(ru_doc="\u041a\u0440\u0430\u0441\u0438\u0432\u0430\u044f \u043a\u0430\u0440\u0442\u043e\u0447\u043a\u0430 \u0441\u0438\u0441\u0442\u0435\u043c\u044b")
    async def neofetch(self, message: Message):
        """Show a neofetch-style system card"""
        start = time.perf_counter_ns()
        try:
            user = getpass.getuser()
        except Exception:
            user = "user"
        try:
            cores = f"{psutil.cpu_count(logical=False)} ({psutil.cpu_count()})"
        except Exception:
            cores = "?"
        text = self.strings("card").format(
            logo=LOGO,
            user=utils.escape_html(user),
            host=utils.escape_html(lib_platform.node() or "host"),
            hv=".".join(map(str, list(version.__version__))),
            branch=getattr(version, "branch", "-"),
            htl=getattr(harukatl, "__version__", "?"),
            py=lib_platform.python_version(),
            os=utils.escape_html(self._get_os_name()),
            kernel=utils.escape_html(lib_platform.release() or "-"),
            uptime=utils.formatted_uptime(),
            cores=cores,
            cpu=psutil.cpu_percent(),
            ram=utils.get_ram_usage(),
            disk=self._disk(),
            ping=round((time.perf_counter_ns() - start) / 10 ** 6, 3),
        )
        await utils.answer(message, text)
