# Changelog

## 2.2.0 — "Nova" (fresh Telegram features)

New user-facing modules mapped to Telegram's 2026 updates, chosen after
reviewing the Bot API changelog, client release notes and Kurigram's feature
set.

- **Stories module** — `.story` posts a replied photo/video as your Telegram
  Story, `.stories [@user]` lists active stories, `.savestory @user <id>`
  downloads one. Uses Kurigram's native story methods with graceful fallback
  when a build lacks them.
- **Checklists module** — collaborative, per-chat to-do lists inspired by
  Telegram's 2026 checklists: `.todo`, `.checklist`, `.check`, `.uncheck`,
  `.rmtask`, `.cleardone`, with a live progress bar. Works on any account
  (DB-backed, no Premium required).
- **AI chat summary** — `.summ` / `.tldr [count]` reads the last N messages and
  produces a TL;DR with decisions, questions and action items.
- **Supply-chain hardening for the loader** — after the 2026 fake-`pyrogram`
  PyPI attacks, module dependencies are now screened before install:
  known-malicious and typosquatted Telegram-library names are blocked
  outright, unpinned versions are warned about, and third-party installs are
  opt-in via `.installs on`.

## 2.1.1 — Heroku mini-module parity (user-facing)

Ported the behaviour of Heroku's everyday commands into Haruka's own modules,
not the invisible engine plumbing.

- **`.info` / `.status`** now shows a full Heroku-style card: version + build
  (git branch @ commit), uptime, RAM, CPU load *and* physical/logical cores,
  module/command counts, prefix, Python, OS pretty-name, kernel and
  `user@host`. Still fully templatable via `custom_message`.
- **`.about` (`.herokucmd`)** — compact "about the userbot" card.
- **`.ping`** keeps its configurable emoji/banner/template.
- **Blacklist family** like Heroku: `.blacklist`/`.unblacklist` (chats),
  `.blacklistuser`/`.unblacklistuser` (users, by id or reply) and `.blacklists`
  to list them. The dispatcher now ignores commands *and* watchers from
  blacklisted chats/users — the owner can never be blacklisted.
- **`utils`** gained `formatted_uptime`, `get_os_name`, `hostname`,
  `username`, `cpu_model`, `git_info` and `git_status` for module authors.
- `.help`, `.menu`, `.config`, `.lang`, alias and prefix commands remain and
  are now surfaced together in help.

## 2.1.0 — "Babel" (Heroku parity pass)

Deep analysis of the Heroku userbot and a matching upgrade of Haruka's weakest
areas, without importing Heroku's architectural debt.

- **Localization overhaul.** Replaced the tiny inline string table with a real
  language-pack system in `haruka/langpacks/*.yml`: full `en`, `ru`, `uk`,
  `de`, `ja` packs plus Heroku-style meme packs (`uwu`, `leet`, `tiktok`,
  `neofit`). Dependency-free loader (uses PyYAML when present, otherwise a
  built-in parser), per-key English fallback and runtime switching.
- **Localized engine.** `Translator` now exposes `available()`, `label`,
  `gettext`, `register_module_strings` and per-module `strings`. Settings, the
  language command and the web onboarding dropdown are all pack-driven.
- **New `Translations` module.** `.langlist`, `.langpicker` (inline keyboard via
  the companion bot) and `.uselang <code>` for switching interface language.
- **Module manifests.** New `haruka.core.metadata` parses Heroku/FTG-style
  headers: `# meta developer:`, `# requires:`, `# min_engine:`, `# scope:`.
- **Dependency provisioning.** The loader checks the minimum engine version and
  best-effort installs a module's `# requires:` before executing third-party
  code, aborting cleanly on failure instead of half-loading.
- **SDK surface.** `haruka.api` now exports `ModuleManifest`,
  `SUPPORTED_LANGUAGES` and `MEME_LANGUAGES`.

## 2.0.5

- Replaced partial personalization with a universal Hikka-style companion-bot Config Center.
- `.config` / `.cfg` now opens engine values and every native/compatible module option in one inline flow.
- Added direct typed input, boolean controls, defaults reset, secret masking and preference editing.
- Restored actual Heroku-style `.dlm` repository-name and raw URL module loading plus repository commands.
- Restored configurable Info/Ping fields as real module configuration options.

## 2.0.4

- Added a universal Hikka-style Config Center in the companion bot.
- `.config` / `.cfg` now opens one editor for engine values and every native or compatible module option.
- Added direct boolean controls, reset-to-default, typed inline input and secret masking.
- Added engine-level editing for prefix, language, appearance, help behavior, repositories and AI settings.
- Added Config Center entry point to the persistent Control Center.
- Exposed real Help and Modules tuning values through the same editor.

## 2.0.2

- Fixed the first-run Quickstart crash caused by calling the client wrapper incorrectly.
- Replaced disconnected startup messages with one persistent inline onboarding flow.
- Added first-run/repeat-run detection and startup counters.
- Added automatic private Haruka log channel creation and warning/error forwarding.
- Connected language, starter preset installation, visual theme, prefix and Control Center.
- Made repeat installer runs skip package downloads and full diagnostics when unchanged.
- Kept startup resilient when onboarding or log delivery is temporarily unavailable.

## 2.0.0

Haruka 2.0 is the first engine-first release.

- Browser-only first-run setup with API credentials, phone/code/2FA and QR flows.
- Button-driven web Control Center enabled by default; no `.env` or nano editing.
- Native inline forms, pagers and galleries with owner checks and expiry.
- Transactional extension loading, collision rejection and source rollback.
- Hikka compatibility adapter and common loader/validator shims.
- Seven-language localization layer.
- SQLite cache consistency, atomic writes and serialized audit operations.
- Bounded watcher concurrency and graceful handler cleanup.
- Extension manifests, checksums, compatibility checks and HTTPS catalogs.
- Cross-platform self-healing installer plus graphical launchers.
- Docker, GitHub Actions, security policy and developer documentation.

## 2.0.1

- Heroku-inspired parity pass started from a full repo study, not guesswork.
- Added Quickstart onboarding and curated Presets for external module discovery.
- Expanded the help atlas with module hiding, support links and better discovery.
- Added compatibility commands for prefix, aliases, language and web access.
- Extended updater with changelog, source and rollback flows.
- Added familiar backup/info/terminal compatibility aliases.
