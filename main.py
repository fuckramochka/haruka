from __future__ import annotations

import asyncio
import logging

from haruka.config.settings import Settings
from haruka.core.runtime import HarukaRuntime


async def async_main() -> None:
    settings = Settings.from_env()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    runtime = await HarukaRuntime.create(settings)
    try:
        await runtime.run_forever()
    finally:
        await runtime.close()


def main() -> None:
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
