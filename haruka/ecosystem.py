"""Extension manifests, compatibility checks and trusted catalog support."""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from haruka.version import __version__


@dataclass
class ExtensionManifest:
    name: str
    version: str = "0.0.0"
    engine: str = ">=2.0"
    python: str = ">=3.10"
    author: str = "unknown"
    description: str = ""
    permissions: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    sha256: str = ""

    @classmethod
    def load(cls, path: Path) -> "ExtensionManifest":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not data.get("name"):
            raise ValueError("Manifest must contain a name")
        return cls(**data)

    def verify_source(self, source: bytes) -> bool:
        actual = hashlib.sha256(source).hexdigest()
        return not self.sha256 or actual == self.sha256.lower()


def _minimum_major(requirement: str, fallback: int) -> int:
    if not requirement.startswith(">="):
        return fallback
    try:
        return int(requirement[2:].split(".", 1)[0])
    except ValueError:
        return fallback


def compatibility(manifest: ExtensionManifest) -> list[str]:
    issues = []
    if sys.version_info < (3, 10):
        issues.append("Python 3.10+ required")
    current_major = int(__version__.split(".")[0])
    required_major = _minimum_major(manifest.engine, current_major)
    if current_major < required_major:
        issues.append(f"Haruka {manifest.engine} required")
    return issues


class Catalog:
    def __init__(self, entries=None):
        self.entries = entries or {}

    def add(self, name: str, url: str, sha256: str = "", trusted: bool = False) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Catalog URLs must use public HTTPS endpoints")
        self.entries[name.casefold()] = {
            "url": url,
            "sha256": sha256,
            "trusted": trusted,
        }

    def get(self, name: str):
        return self.entries.get(name.casefold())

    def search(self, query: str):
        needle = query.casefold()
        return {key: value for key, value in self.entries.items() if needle in key}
