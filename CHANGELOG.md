# Changelog

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
