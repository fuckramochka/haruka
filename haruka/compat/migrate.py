"""One-shot migration from the legacy JSON database.

Old Haruka/Hikka stored everything in a single ``db.json`` (or
``config-<phone>.json``). If such a file is found next to the data directory
on first start, its contents are imported into the new SQLite store under the
same owner/key layout, then the file is renamed to ``*.migrated`` so the
import never runs twice.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from haruka.core.database import Database

logger = logging.getLogger(__name__)

_LEGACY_NAMES = ("db.json", "database.json")


def find_legacy_db(data_dir: Path) -> Path | None:
    candidates = [
        *(data_dir / name for name in _LEGACY_NAMES),
        *(data_dir.parent / name for name in _LEGACY_NAMES),
        *data_dir.parent.glob("config-*.json"),
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


async def migrate_legacy_db(db: "Database", data_dir: Path) -> int:
    """Import a legacy JSON DB if present. Returns number of keys imported."""
    legacy = find_legacy_db(data_dir)
    if legacy is None:
        return 0

    try:
        raw = json.loads(legacy.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Legacy DB at %s is unreadable — skipping migration", legacy)
        return 0

    if not isinstance(raw, dict):
        return 0

    count = 0
    for owner, entries in raw.items():
        if not isinstance(entries, dict):
            continue
        for key, value in entries.items():
            await db.set(str(owner), str(key), value)
            count += 1

    legacy.rename(legacy.with_suffix(legacy.suffix + ".migrated"))
    await db.audit("compat.migrate", f"imported {count} keys from {legacy.name}")
    logger.info("Migrated %d keys from legacy database %s", count, legacy.name)
    return count
