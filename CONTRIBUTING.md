# Contributing

Haruka is an engine, not a command bundle. Contributions should improve reusable
cognition, storage, reliability, security, module SDKs or transport adapters.

1. Create a branch from `main`.
2. Install with `python install.py --dev`.
3. Add tests for behavior changes.
4. Run `python -m ruff check .` and `python -m pytest`.
5. Document public API or configuration changes.
6. Open a focused pull request.

Do not commit Telegram sessions, `.env`, API credentials, databases, personal
messages or generated memory. New module capabilities must be minimal and
explained in the pull request.

Compatibility policy: public engine interfaces follow semantic versioning.
Deprecations should remain for at least one minor release when practical.
