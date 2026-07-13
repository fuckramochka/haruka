# Haruka Engine

> A modern, engine-first runtime for Telegram userbots.

[![CI](https://github.com/fuxckramochka/haruka/actions/workflows/ci.yml/badge.svg)](https://github.com/fuxckramochka/haruka/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-2783DE)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-AGPL--3.0-E56458)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.0.0-46A171)](CHANGELOG.md)

[Русский](README_RU.md) · [User guide](docs/USER_GUIDE_RU.md) · [Developer guide](docs/DEVELOPER_GUIDE.md) · [Architecture](docs/ARCHITECTURE.md) · [Haruka vs Heroku](docs/HARUKA_VS_HEROKU_RU.md)

Haruka is not a userbot assembled from a preset pack. It is a compact runtime for building, loading and operating userbot capabilities: a stable module SDK, transactional hot loading, centralized dispatch, permissions, SQLite persistence, inline management UI and raw MTProto access through Kurigram.

## Why Haruka

- **Engine-first:** infrastructure and contracts are primary; bundled capabilities use the same public SDK.
- **Transactional loading:** failed imports and lifecycle hooks roll back cleanly.
- **One command bus:** parsing, aliases, roles, rate limits, feature gates and errors live in one dispatcher.
- **Native Control Center:** engine health, settings, security and feature management in a polished inline shell.
- **Stable author API:** modules import from `haruka.api`, not private internals.
- **Compatibility boundary:** selected Hikka modules can run through an adapter without shaping the new core.
- **Modern Telegram escape hatch:** `haruka.tl` exposes raw MTProto when high-level Kurigram APIs are not enough.

## One-click setup

No `nano`, `.env` editing or terminal configuration is required.

- **Windows:** double-click `Install Haruka.cmd`.
- **macOS:** double-click `Install Haruka.command`.
- **Linux desktop:** open `Haruka Setup.desktop`, or double-click `launcher.pyw`.

The installer repairs Python and the virtual environment, then opens a button-driven browser wizard for API credentials, QR/phone login and engine settings.

## Quick start

Requirements: Python 3.10+, a Telegram account and API credentials from [my.telegram.org](https://my.telegram.org/apps).

```bash
git clone https://github.com/fuxckramochka/haruka.git
cd haruka
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[full]'
cp .env.example .env
python -m haruka
```

On first run, Haruka asks for `API_ID`, `API_HASH`, phone, code and 2FA password when applicable. Runtime data is stored in `~/.haruka` unless `HARUKA_DATA_DIR` is set.

### Docker

```bash
cp .env.example .env
mkdir -p data
docker compose run --rm haruka
```

The first run must be interactive. Afterwards:

```bash
docker compose up -d
```

## Control Center

Set a companion bot token with `.setbot <token>`, restart Haruka, open the bot once with `/start`, then use `.menu` or `.dashboard`. The shell contains overview, command gates, features, visual skins, diagnostics and security state.

## Minimal extension

```python
from haruka.api import Context, Module, command

class Hello(Module):
    name = "Hello"
    author = "you"
    version = "1.0.0"
    description = "A minimal Haruka extension"

    @command(aliases=["hi"], doc="Say hello")
    async def hello(self, ctx: Context):
        await ctx.ok(f"Hello, {ctx.sender_name}!")
```

Drop the file into `~/.haruka/modules/` or load a reviewed public URL with `.loadmod`.

## Documentation

| Audience | Document |
|---|---|
| Users | [Russian user guide](docs/USER_GUIDE_RU.md) |
| Module authors | [Developer guide](docs/DEVELOPER_GUIDE.md) |
| Core contributors | [Architecture](docs/ARCHITECTURE.md) |
| Operators | [Deployment guide](docs/DEPLOYMENT.md) |
| Security researchers | [Security policy](SECURITY.md) |
| Contributors | [Contributing guide](CONTRIBUTING.md) |
| Project comparison | [Haruka vs Heroku](docs/HARUKA_VS_HEROKU_RU.md) |

## Project status

Haruka 2.0 is an early, working engine. Core contracts and tests exist, but the ecosystem is smaller than mature Hikka-derived projects. Review the [roadmap](ROADMAP.md) before depending on unfinished compatibility or web onboarding features.

## Security

A userbot controls a real Telegram account. Third-party Python modules run with the process permissions and cannot be made safe by branding alone. Review sources, isolate the host, protect session files and never publish `.env`, `*.session` or the data directory. See [SECURITY.md](SECURITY.md).

## License

Haruka is distributed under the [GNU AGPL-3.0-or-later](LICENSE).
