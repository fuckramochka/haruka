"""Fast, side-effect-free health snapshot for the engine shell."""
from __future__ import annotations

import asyncio
import os
import platform
from dataclasses import asdict, dataclass
from pathlib import Path

import psutil


@dataclass(frozen=True)
class HealthSnapshot:
    status: str
    memory_mb: float
    cpu_percent: float
    disk_free_gb: float
    tasks: int
    database_kb: float
    python: str
    platform: str

    def as_dict(self):
        return asdict(self)


def collect_health(db_path: Path) -> HealthSnapshot:
    proc = psutil.Process(os.getpid())
    memory = proc.memory_info().rss / 1024 / 1024
    cpu = proc.cpu_percent(interval=None)
    disk = psutil.disk_usage(str(db_path.parent if db_path.parent.exists() else Path.cwd()))
    db_size = db_path.stat().st_size / 1024 if db_path.exists() else 0.0
    try:
        tasks = len(asyncio.all_tasks())
    except RuntimeError:
        tasks = 0
    status = "healthy" if memory < 1024 and disk.free > 256 * 1024 * 1024 else "attention"
    return HealthSnapshot(
        status=status,
        memory_mb=memory,
        cpu_percent=cpu,
        disk_free_gb=disk.free / 1024 / 1024 / 1024,
        tasks=tasks,
        database_kb=db_size,
        python=platform.python_version(),
        platform=platform.system(),
    )
