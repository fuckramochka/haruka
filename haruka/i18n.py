"""Engine localization.

Heroku-inspired language packs, but dependency-free and engine-first:

* Packs live in ``haruka/langpacks/*.yml`` and are flattened to ``section.key``.
* A tiny, controlled YAML subset parser is used so the engine ships without a
  YAML runtime dependency (PyYAML is used automatically when present).
* Meme packs (uwu / leet / tiktok / neofit) fall back to English per-key,
  exactly like Heroku's meme languages.
* Modules may register their own strings with :meth:`Translator.extend` or by
  declaring a ``strings`` mapping on the module class.

The public surface (``language``, ``set_language``, ``t``, ``extend``) is
backward compatible with earlier Haruka releases.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Mapping

logger = logging.getLogger(__name__)

_PACK_DIR = Path(__file__).parent / "langpacks"

# Real, human languages.
SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "\U0001F1EC\U0001F1E7 English",
    "ru": "\U0001F1F7\U0001F1FA \u0420\u0443\u0441\u0441\u043a\u0438\u0439",
    "uk": "\U0001F1FA\U0001F1E6 \u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430",
    "de": "\U0001F1E9\U0001F1EA Deutsch",
    "ja": "\U0001F1EF\U0001F1F5 \u65e5\u672c\u8a9e",
}

# Fun packs. They intentionally cover only a handful of keys and fall back to en.
MEME_LANGUAGES: dict[str, str] = {
    "uwu": "\U0001F3F4\u200D\u2620\uFE0F UwU",
    "leet": "\U0001F3F4\u200D\u2620\uFE0F 1337",
    "tiktok": "\U0001F3F4\u200D\u2620\uFE0F TikTokKid",
    "neofit": "\U0001F3F4\u200D\u2620\uFE0F Neofit",
}

DEFAULT_LANGUAGE = "en"


def _parse_yaml_subset(text: str) -> dict[str, str]:
    """Parse the controlled two-level pack format into flat ``section.key``.

    Supports only what our own packs use: top-level ``section:`` headers and
    two-space indented ``key: "value"`` entries with ``#`` comments. This keeps
    the engine free of a YAML dependency while remaining forgiving.
    """
    flat: dict[str, str] = {}
    section = ""
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            head, _, rest = line.partition(":")
            head = head.strip()
            rest = rest.strip()
            if rest:  # top-level key: value (rare) -> its own section-less key
                flat[head] = _unquote(rest)
                section = ""
            else:
                section = head
            continue
        key, _, value = line.strip().partition(":")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        full = f"{section}.{key}" if section else key
        flat[full] = _unquote(value)
    return flat


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")


def _load_pack(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        flat: dict[str, str] = {}
        for section, body in data.items():
            if isinstance(body, Mapping):
                for key, value in body.items():
                    flat[f"{section}.{key}"] = str(value)
            else:
                flat[str(section)] = str(body)
        return flat
    except ModuleNotFoundError:
        return _parse_yaml_subset(text)
    except Exception:
        logger.exception("Falling back to builtin parser for %s", path.name)
        return _parse_yaml_subset(text)


def _discover_packs() -> dict[str, dict[str, str]]:
    packs: dict[str, dict[str, str]] = {}
    if not _PACK_DIR.exists():
        return packs
    for path in sorted(_PACK_DIR.glob("*.yml")):
        try:
            packs[path.stem] = _load_pack(path)
        except Exception:
            logger.exception("Could not load language pack %s", path.name)
    return packs


# Loaded once at import; modules can extend at runtime.
PACKS: dict[str, dict[str, str]] = _discover_packs()
if DEFAULT_LANGUAGE not in PACKS:
    PACKS[DEFAULT_LANGUAGE] = {}


def all_languages() -> dict[str, str]:
    """Every selectable language code mapped to its display label."""
    labels = {**SUPPORTED_LANGUAGES, **MEME_LANGUAGES}
    # Include any pack that exists on disk even without a friendly label.
    for code in PACKS:
        labels.setdefault(code, code)
    return labels


class Translator:
    """Runtime language switching with English fallback."""

    def __init__(self, db):
        self.db = db

    @property
    def language(self) -> str:
        code = self.db.get("core", "language", DEFAULT_LANGUAGE)
        return code if code in PACKS else DEFAULT_LANGUAGE

    @property
    def label(self) -> str:
        return all_languages().get(self.language, self.language)

    @staticmethod
    def available() -> dict[str, str]:
        return all_languages()

    async def set_language(self, code: str) -> None:
        if code not in PACKS:
            raise ValueError(f"Unsupported language: {code}")
        await self.db.set("core", "language", code)

    def t(self, key: str, default: str | None = None, **values) -> str:
        pack = PACKS.get(self.language, {})
        value = pack.get(key)
        if value is None:
            value = PACKS.get(DEFAULT_LANGUAGE, {}).get(key, default if default is not None else key)
        try:
            return value.format(**values) if values else value
        except (KeyError, IndexError, ValueError):
            return value

    # Alias mirroring Heroku's ``gettext`` naming for ported modules.
    def gettext(self, key: str, **values) -> str:
        return self.t(key, **values)

    def extend(self, code: str, items: Mapping[str, str]) -> None:
        PACKS.setdefault(code, {}).update(items)

    def extend_many(self, items_by_lang: Mapping[str, Mapping[str, str]]) -> None:
        for code, items in items_by_lang.items():
            self.extend(code, items)

    def register_module_strings(self, module_name: str, strings: Mapping) -> None:
        """Accept a Hikka/Heroku-style ``strings``/``strings_xx`` mapping.

        ``{"key": "value"}`` registers under English; a nested mapping keyed by
        language code registers per language. Keys are namespaced by module.
        """
        prefix = f"module.{module_name}."
        for key, value in strings.items():
            if isinstance(value, Mapping):
                for code, text in value.items():
                    self.extend(code, {f"{prefix}{key}": str(text)})
            else:
                self.extend(DEFAULT_LANGUAGE, {f"{prefix}{key}": str(value)})

    def keys(self) -> Iterable[str]:
        return PACKS.get(DEFAULT_LANGUAGE, {}).keys()
