# Haruka 2.0 — final audit

The repository was re-read from the composition root down and then passed through the automated ten-pass audit in `tools/audit.py`.

## Significant defects found and fixed

- Removed terminal credential prompts; first login is now a local browser wizard.
- Added phone/code/2FA and QR paths, automatic browser opening and existing-session verification.
- Fixed setup and dashboard URLs that contained malformed braces.
- Fixed repeated login-code submission accidentally requesting a new code with an empty phone.
- Fixed a database cache/disk consistency bug when SQLite writes fail.
- Serialized audit writes and tightened database permissions to `0600` where supported.
- Made extension replacement rollback-safe and restored overwritten source after failed installs.
- Rejected command collisions instead of silently stealing routes.
- Fixed reload so a broken replacement does not first discard the working module.
- Fixed shared import cleanup for files exporting multiple modules.
- Rebuilt the Hikka adapter so commands survive index rebuilds and unload/reload.
- Bounded watcher concurrency, tracked tasks and removed handlers during shutdown.
- Removed automation handlers during shutdown and reduced schedule drift.
- Fixed terminal timeout so continuous output cannot bypass the five-minute limit.
- Killed the whole Unix process group on terminal timeout rather than only the shell.
- Blocked module redirects to non-public URLs and bounded replied module files.
- Fixed help pagination, which previously displayed only the first page.
- Fixed updater working-directory assumptions and added dependency refresh after pulls.
- Added backup-size limits and closed restored files deterministically.
- Removed hardcoded runtime versions from the web API.
- Added button controls for every feature, every command gate and core settings.
- Added one-click Windows, macOS and desktop launchers plus a repairing bootstrap.

## Remaining limitations

These are architectural or external integration constraints, not known local code-breakers:

- Telegram phone and QR authorization still require live integration tests against Telegram after each major Kurigram layer change.
- Compatibility shims cover common Hikka contracts but cannot safely reproduce every historical monkey patch.
- Third-party Python extensions remain trusted in-process code; real sandboxing requires separate worker processes.
- Some interface strings still use English fallbacks even though seven language packs are available.
- Browser auto-opening depends on a graphical session; on a headless server the private URL is written to logs.

## Verification

- ten automated audit passes;
- Python bytecode compilation;
- regression tests;
- AST duplicate-definition scan;
- zero `input()`/`getpass()` configuration paths;
- version consistency check;
- documentation-link check;
- dependency metadata check;
- secret/runtime-file scan;
- whitespace and Git staging check;
- shell syntax checks;
- ZIP integrity check.
