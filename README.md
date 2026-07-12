# Haruka Engine 0.3

Haruka is a **framework/engine**, not a finished userbot. It provides persistent
identity, memory, planning and Telegram adapters; a product decides policies,
commands, permissions, UI and deployment.

## What is included

- Telethon/MTProto adapter for user or bot sessions.
- Forward-compatible Telegram Bot API 10.1 client.
- People, self, world and recency-weighted vector memory.
- Persistent emotions, relationships, goals and per-chat lore.
- Chat-style learning from up to 500 recent messages.
- Deliberate planning: observe, react, short answer, long answer.
- Optional initiative (disabled by default).
- Versioned module SDK with manifests, dependency validation and command routing.
- Deny-by-default capability security and source-digest verification.
- Priority event bus, composable middleware pipeline and plugin manager.
- Circuit breakers, metrics and per-key rate limiting.
- SQLite WAL persistence and JSON snapshots.

## Installation

After cloning, use the cross-platform installer:

```bash
# Linux, macOS, WSL, Termux
./install.sh

# universal fallback
python install.py
```

On Windows PowerShell run `.\install.ps1`. The installer creates an isolated
`.venv`, installs dependencies with retries, creates a protected `.env`, prepares
runtime directories and performs an import/compile doctor check. Full recovery
instructions and options are in [`docs/INSTALL.md`](docs/INSTALL.md).

Do not commit `.env`, session files, databases or the virtual environment.

## Engine boundaries

`HarukaRuntime` is the reference composition root, not mandatory product logic.
Use modules independently or replace adapters/providers. Telegram-only features
are isolated in `haruka.telegram`; Bot API capabilities are never silently
activated. See `docs/TELEGRAM_2026.md`.

## Architecture

```text
Product / application
├── HarukaRuntime (reference composition)
├── PluginManager
├── cognition
│   ├── personality + emotion + planning
│   ├── relationships + goals + lore
│   └── people + self + world + vector memory
├── providers
│   └── ModelProvider (Gemma/OpenAI-compatible adapter included)
├── persistence
│   └── SQLite + snapshots
└── Telegram adapters
    ├── TelegramEngine (Telethon / MTProto)
    └── BotAPIClient (Bot API 10.1)
```

## Safe defaults

- initiative is off;
- chat allowlist is supported;
- scans are bounded and style refresh is no longer run every scan;
- network calls retry with Telegram `retry_after` support;
- graceful shutdown closes scheduler, Telegram and database resources;
- generated archive excludes secrets, sessions, databases, caches and `.venv`.

## Competitive direction

Haruka does not compete by bundling more commands. Compared with Heroku/Hikka/Dragon, it moves the hard parts into reusable engine primitives: transport neutrality, cognition, capability security, deterministic module lifecycle, event isolation, resilience and observability. See `docs/COMPETITOR_GAP.md`.
