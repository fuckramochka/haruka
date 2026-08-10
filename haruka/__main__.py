"""Entry point: ``python -m haruka`` or the ``haruka`` console script."""

from __future__ import annotations

import asyncio
import logging
import sys


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("pyrogram").setLevel(logging.WARNING)


def run() -> None:
    if sys.version_info < (3, 10):
        raise SystemExit("Haruka requires Python 3.10+")

    _setup_logging()

    # Load .env if present (dev convenience).
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    from haruka.core.app import Application

    app = Application()
    try:
        asyncio.run(app.run_forever())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
