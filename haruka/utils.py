"""Stable utility surface for third-party engine modules."""
from __future__ import annotations

import getpass
import ipaddress
import platform as _platform
import re
import socket
import subprocess
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
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


# -- host / platform introspection (Heroku .info parity) ---------------------


def formatted_uptime(seconds: float) -> str:
    """Human readable uptime, e.g. ``3d 4h 12m`` / ``5m 3s``."""
    seconds = int(max(seconds, 0))
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m {sec}s"
    if minutes:
        return f"{minutes}m {sec}s"
    return f"{sec}s"


@lru_cache(maxsize=1)
def get_os_name() -> str:
    """Best-effort pretty OS name (reads /etc/os-release on Linux)."""
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if line.startswith("PRETTY_NAME"):
                return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    system = _platform.system()
    release = _platform.release()
    return f"{system} {release}".strip() or "Unknown"


def hostname() -> str:
    try:
        return socket.gethostname() or _platform.node() or "unknown"
    except OSError:
        return _platform.node() or "unknown"


def username() -> str:
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


def cpu_model() -> str:
    """Physical/logical core summary, e.g. ``4 (8) core(-s)``."""
    try:
        import psutil

        physical = psutil.cpu_count(logical=False) or 0
        logical = psutil.cpu_count() or 0
        return f"{physical} ({logical}) core(-s)"
    except Exception:
        return "unknown"


@lru_cache(maxsize=1)
def git_info() -> dict:
    """Return best-effort git metadata: ``branch``, ``commit``, ``dirty``.

    Never raises: returns empty strings when the working tree is not a git
    checkout (e.g. installed from a wheel).
    """
    info = {"branch": "", "commit": "", "dirty": False}

    def _run(*args: str) -> str:
        try:
            out = subprocess.run(
                ["git", *args],
                cwd=str(Path(__file__).resolve().parent.parent),
                capture_output=True,
                text=True,
                timeout=3,
            )
            return out.stdout.strip() if out.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            return ""

    info["branch"] = _run("rev-parse", "--abbrev-ref", "HEAD")
    info["commit"] = _run("rev-parse", "--short", "HEAD")
    info["dirty"] = bool(_run("status", "--porcelain"))
    return info


def git_status() -> str:
    """Short git description like ``master @ a1b2c3d*`` (``*`` = dirty)."""
    info = git_info()
    if not info["commit"]:
        return "release build"
    dirty = "*" if info["dirty"] else ""
    branch = info["branch"] or "detached"
    return f"{branch} @ {info['commit']}{dirty}"
