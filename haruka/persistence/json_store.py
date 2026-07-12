from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonSnapshotStore:
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    async def write(self, name: str, data: dict[str, Any]) -> Path:
        path = self.directory / f"{name}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

