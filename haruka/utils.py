"""Stable utility surface for third-party engine modules."""
from __future__ import annotations

import ipaddress
import re
from datetime import datetime, timezone
from urllib.parse import urlparse


def is_url(value: str, *, allow_local: bool = False) -> bool:
    try:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        if not allow_local:
            try:
                ip = ipaddress.ip_address(parsed.hostname)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    return False
            except ValueError:
                if parsed.hostname in {"localhost", "localhost.localdomain"}:
                    return False
        return True
    except (TypeError, ValueError):
        return False


def format_file_size(size: int) -> str:
    value = float(max(size, 0))
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TiB"


def iso_time(timestamp: float | None = None) -> str:
    dt = datetime.fromtimestamp(timestamp, timezone.utc) if timestamp is not None else datetime.now(timezone.utc)
    return dt.isoformat(timespec="seconds")


def safe_getattr(obj, path: str, default=None):
    current = obj
    for part in path.split("."):
        current = getattr(current, part, default)
        if current is default:
            break
    return current


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.casefold()).strip("_")
