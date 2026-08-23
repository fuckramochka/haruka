# ©️ Haruka contributors, 2024-2026
# This file is a part of Haruka Userbot
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

"""
Haruka module scaffolder.

Generates a ready-to-edit core or external module template.

Usage:
    python tools/newmodule.py MyFeature
    python tools/newmodule.py MyFeature --dir loaded_modules
"""

import argparse
import sys
from pathlib import Path

TEMPLATE = '''# ©️ Haruka contributors, 2024-2026
# This file is a part of Haruka Userbot
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

"""{doc}"""

import logging

from telethon.tl.types import Message

from .. import loader, utils  # for external modules use: from haruka import loader, utils

logger = logging.getLogger(__name__)


class {cls}(loader.Module):
    """{doc}"""

    strings = {{"name": "{cls}"}}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "example_option",
                "default",
                lambda: "Example option documented in .config {cls_lower}",
            ),
        )

    async def client_ready(self):
        logger.debug("%s loaded", self.strings["name"])

    @loader.command()
    async def example(self, message: Message):
        """Example command — edit me"""
        await utils.answer(
            message,
            f"🌸 <b>{{self.strings['name']}}</b> works!"
            f" Option: <code>{{self.config['example_option']}}</code>",
        )
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Haruka module template")
    parser.add_argument("name", help="Module name, e.g. MyFeature")
    parser.add_argument(
        "--dir",
        default="haruka/modules",
        help="Target directory (default: haruka/modules)",
    )
    args = parser.parse_args()

    cls = "".join(part.capitalize() for part in args.name.split("-"))
    if not cls.endswith("Mod"):
        cls += "Mod"

    target = Path(args.dir) / f"{args.name.lower().replace('-', '_')}.py"
    if target.exists():
        print(f"[FAIL] {target} already exists")
        return 1

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        TEMPLATE.format(cls=cls, cls_lower=cls.lower(), doc=args.name),
        encoding="utf-8",
    )
    print(f"[OK]   Created {target}")
    print("       Next steps:")
    print("       - edit commands/watchers")
    print("       - restart the bot (.restart) or load externally via .loadmod")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
