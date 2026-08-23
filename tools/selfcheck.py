# ©️ Haruka contributors, 2024-2026
# This file is a part of Haruka Userbot
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

"""
Haruka self-check tool.

Verifies, without any Telegram connection:
  1. Legacy import aliases (hikka/heroku/ftg/geektg → haruka,
     hikkatl/herokutl → telethon);
  2. Client attribute alias sync;
  3. Database key migration rules;
  4. Cache record hashing;
  5. Updater repository override helpers;
  6. patched_import legacy mapping.

Usage:
    python tools/selfcheck.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CHECKS = []


def check(name):
    def decorator(func):
        CHECKS.append((name, func))
        return func

    return decorator


@check("package import installs compat layer")
def _(haruka):
    assert hasattr(haruka, "__ForkAuthor__")


@check("legacy imports: hikka.loader → haruka.loader")
def _(haruka):
    import importlib

    assert importlib.import_module("hikka.loader") is haruka.loader


@check("legacy imports: heroku.utils → haruka.utils")
def _(haruka):
    import importlib

    assert importlib.import_module("heroku.utils") is haruka.utils


@check("legacy imports: ftg/geektg roots → haruka")
def _(haruka):
    import importlib

    assert importlib.import_module("ftg.version") is haruka.version
    assert importlib.import_module("geektg.types") is haruka.types


@check("legacy imports: hikkatl/herokutl → telethon")
def _(haruka):
    import importlib
    import telethon
    import telethon.tl.types

    assert importlib.import_module("hikkatl") is telethon
    assert importlib.import_module("herokutl.tl.types") is telethon.tl.types


@check("client attribute aliases sync")
def _(haruka):
    from haruka.compat import sync_client_attributes

    class FakeClient:
        haruka_me = "ME"
        haruka_db = "DB"
        haruka_inline = None

    c = FakeClient()
    sync_client_attributes(c)
    assert c.hikka_me == c.heroku_me == "ME"
    assert c.hikka_db == c.heroku_db == "DB"
    assert getattr(c, "hikka_inline", None) is None


@check("database key migration regexes")
def _(haruka):
    sample = json.dumps(
        {
            "hikka.main": {"a": 1},
            "heroku.inline": {"b": 2},
            "legacy.x": {},
            "haruka.keep": {"c": 3},
        }
    )
    for prefix in ("hikka", "heroku", "legacy"):
        sample = re.sub(
            rf'"{prefix}\.([^"]+)":', lambda m: f'"haruka.{m.group(1)}":', sample
        )
    parsed = json.loads(sample)
    assert set(parsed) == {
        "haruka.main",
        "haruka.inline",
        "haruka.x",
        "haruka.keep",
    }, parsed.keys()


@check("cache record hashing")
def _(haruka):
    from haruka.types import CacheRecordFullChannel, CacheRecordFullUser

    rec = CacheRecordFullChannel(123, None, 60)
    usr = CacheRecordFullUser(456, None, 60)
    assert hash(rec) and hash(usr)
    assert len({rec, rec}) == 1


@check("updater repository override helpers")
def _(haruka):
    from haruka.modules.updater import DEFAULT_REPO_URL, _repo_slug, _repo_url

    class Cfg(dict):
        def __getitem__(self, k):
            return dict.get(self, k)

    cfg = Cfg({"GIT_ORIGIN_URL": "https://github.com/myuser/MyFork"})
    assert _repo_slug(cfg) == "myuser/MyFork"
    assert _repo_url(cfg) == "https://github.com/myuser/MyFork"
    assert _repo_slug(Cfg({"GIT_ORIGIN_URL": None})) == _repo_slug(Cfg())
    assert DEFAULT_REPO_URL.startswith("https://github.com/")


@check("patched_import legacy mapping")
def _(haruka):
    import builtins

    from haruka.loader import native_import, patched_import

    saved = builtins.__import__
    try:
        builtins.__import__ = patched_import
        mod = __import__("heroku.validators")
        assert mod is haruka
        assert mod.validators is haruka.validators
    finally:
        builtins.__import__ = saved


@check("new core modules import (afk, notes, undo, diagnostics)")
def _(haruka):
    import importlib

    for name in (
        "haruka_afk",
        "haruka_notes",
        "haruka_undo",
        "haruka_diagnostics",
    ):
        mod = importlib.import_module(f"haruka.modules.{name}")
        assert any(
            isinstance(obj, type) and issubclass(obj, haruka.loader.Module)
            for obj in vars(mod).values()
        ), name


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    import haruka

    failed = 0
    for name, func in CHECKS:
        try:
            func(haruka)
            print(f"  [OK]   {name}")
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {name}: {type(e).__name__}: {e}")

    total = len(CHECKS)
    print(f"\n{total - failed}/{total} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
