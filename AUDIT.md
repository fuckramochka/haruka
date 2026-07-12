# Audit and merge report

## Archive reality

The supplied archive contains one populated Python project under `haruka/haruka`.
The apparent legacy folders `config/`, `core/`, `db/`, `modules/`, and `utils/`
are empty, so there was no second source tree to merge line-by-line. The review
therefore preserved every useful implemented subsystem from the populated tree
and removed packaging/runtime debris.

## Preserved

AI provider abstraction, Telegram history/replies/files/stickers/reactions,
people/self/world/vector memory, emotions, personality, style learning,
planning, scheduler, snapshots, relationships, goals, lore and initiative.

## Reworked or removed

- excluded the 22 MB checked-in virtual environment, bytecode, live `.env`,
  SQLite/WAL files and Telegram session;
- removed empty legacy directories from the deliverable;
- bounded expensive dialog scans and separated scan/style/snapshot schedules;
- made initiative opt-in instead of surprising default behavior;
- added allowlists, graceful shutdown, retry behavior and deduplication index;
- added installable package metadata, tests, docs and ignore rules;
- replaced the placeholder-only Telegram tool direction with adapters and a
  plugin extension surface.

## Telegram 2026

Based on Telegram's official Bot API changelog (10.1, 11 June 2026), the new
Bot API adapter includes rich messages and streaming drafts. It also covers the
10.0 guest-query and reaction-deletion additions, media/member-only polls, and
9.x private topics, checklists and business-message methods. Generic `call()`
keeps future methods usable without waiting for a release.

References:
- https://core.telegram.org/bots/api-changelog
- https://core.telegram.org/bots/api
- https://core.telegram.org/api/layers

## Validation

All Python files were parsed and byte-compiled successfully with Python 3.13.
Runtime tests could not be executed in the build sandbox because third-party
runtime packages were not installed globally; `pyproject.toml` and
`requirements.txt` declare them for a normal virtual environment.
