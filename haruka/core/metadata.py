"""Module manifest parsing and dependency provisioning.

Heroku (and the wider FTG/Hikka lineage) let a module declare metadata and its
Python requirements directly in the source header::

    # meta developer: @author
    # meta pic: https://...
    # requires: httpx beautifulsoup4
    # min_engine: 2.0.0
    # scope: heroku_only

Haruka keeps the ergonomics but makes provisioning explicit and safe: parsing
is pure, and installation is a bounded, opt-outable best-effort step that never
corrupts the loader if it fails.
"""
from __future__ import annotations

import importlib
import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_META_RE = re.compile(r"^#\s*meta\s+([\w.-]+)\s*:\s*(.+?)\s*$", re.MULTILINE)
_REQUIRES_RE = re.compile(r"^#\s*requires\s*:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
_MIN_ENGINE_RE = re.compile(r"^#\s*min_engine\s*:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
_SCOPE_RE = re.compile(r"^#\s*scope\s*:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)

# pip name -> importable module name, for the common mismatches.
_IMPORT_ALIASES = {
    "beautifulsoup4": "bs4",
    "pillow": "PIL",
    "pyyaml": "yaml",
    "python-dateutil": "dateutil",
    "opencv-python": "cv2",
    "scikit-learn": "sklearn",
}


@dataclass
class ModuleManifest:
    meta: dict[str, str] = field(default_factory=dict)
    requires: list[str] = field(default_factory=list)
    min_engine: str | None = None
    scopes: list[str] = field(default_factory=list)

    @property
    def developer(self) -> str | None:
        return self.meta.get("developer")


def parse_manifest(source: str) -> ModuleManifest:
    """Extract the declarative manifest from a module's source header."""
    meta = {key.lower(): value for key, value in _META_RE.findall(source)}
    requires: list[str] = []
    for chunk in _REQUIRES_RE.findall(source):
        requires.extend(part for part in re.split(r"[\s,]+", chunk) if part)
    min_engine_match = _MIN_ENGINE_RE.search(source)
    scopes: list[str] = []
    for chunk in _SCOPE_RE.findall(source):
        scopes.extend(part for part in re.split(r"[\s,]+", chunk) if part)
    # De-duplicate while preserving order.
    seen: set[str] = set()
    requires = [r for r in requires if not (r in seen or seen.add(r))]
    return ModuleManifest(
        meta=meta,
        requires=requires,
        min_engine=min_engine_match.group(1) if min_engine_match else None,
        scopes=scopes,
    )


def _version_tuple(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in re.split(r"[.\-+]", value.strip()):
        if piece.isdigit():
            parts.append(int(piece))
        else:
            break
    return tuple(parts) or (0,)


def engine_satisfies(min_engine: str | None, engine_version: str) -> bool:
    if not min_engine:
        return True
    return _version_tuple(engine_version) >= _version_tuple(min_engine)


def _distribution_name(requirement: str) -> str:
    return re.split(r"[<>=!~;\[ ]", requirement, 1)[0].strip()


# -- supply-chain screening --------------------------------------------------
#
# The Telegram userbot ecosystem has been directly targeted by dependency
# supply-chain attacks (e.g. "Operation Navy Ghost", 2026, which shipped fake
# ``pyrogram`` look-alike packages on PyPI that installed a backdoor). Before
# we ever hand a module's requirements to pip we screen them: block known-bad
# and typosquatted names outright, and warn on unpinned versions.

_TRUSTED_TELEGRAM_LIBS = {
    "pyrogram", "kurigram", "pyrofork", "hydrogram", "telethon", "tgcrypto",
}
_MALICIOUS_NAMES = {
    "pyrogramm", "pyrograms", "pyrogam", "pyrogran", "pyrogrom", "pyro-gram",
    "kurigramm", "kurigran", "telethon2", "telethone", "tgcrypto2", "tg-crypto",
}


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb))
            )
        previous = current
    return previous[-1]


def screen_requirements(requires: list[str]) -> tuple[list[str], list[str]]:
    """Screen pip requirements for supply-chain risk.

    Returns ``(blocked, warnings)``:
    - ``blocked``: requirements that must not be installed (known-malicious or
      a typosquat of a trusted Telegram library).
    - ``warnings``: distribution names installed without a pinned version.
    """
    blocked: list[str] = []
    warnings: list[str] = []
    for requirement in requires:
        name = _distribution_name(requirement).lower()
        if not name:
            continue
        if name in _MALICIOUS_NAMES:
            blocked.append(requirement)
            continue
        if name in _TRUSTED_TELEGRAM_LIBS:
            continue
        if any(0 < _levenshtein(name, trusted) <= 2 for trusted in _TRUSTED_TELEGRAM_LIBS):
            blocked.append(requirement)
            continue
        if not re.search(r"([=<>~!]=|@)", requirement):
            warnings.append(name)
    return blocked, warnings


def missing_requirements(requires: list[str]) -> list[str]:
    missing: list[str] = []
    for requirement in requires:
        name = _distribution_name(requirement)
        if not name:
            continue
        import_name = _IMPORT_ALIASES.get(name.lower(), name.replace("-", "_"))
        try:
            importlib.import_module(import_name)
        except Exception:
            missing.append(requirement)
    return missing


def install_requirements(requires: list[str], *, timeout: int = 300) -> tuple[bool, list[str]]:
    """Best-effort pip install of the given requirements.

    Returns ``(ok, attempted)``. Never raises; a failed install simply reports
    ``False`` so the loader can surface a friendly message and abort cleanly.
    """
    missing = missing_requirements(requires)
    if not missing:
        return True, []
    logger.info("Installing module requirements: %s", ", ".join(missing))
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", *missing],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception:
        logger.exception("pip invocation failed for %s", missing)
        return False, missing
    if completed.returncode != 0:
        logger.error("pip install failed: %s", completed.stderr.strip()[-500:])
        return False, missing
    importlib.invalidate_caches()
    still_missing = missing_requirements(missing)
    return (not still_missing), missing
