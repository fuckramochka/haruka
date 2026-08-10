# Haruka Architecture

## Design goals

1. Keep the composition root explicit.
2. Give extension authors one stable import surface.
3. Centralize policy in the dispatcher rather than every command.
4. Make hot loading reversible.
5. Keep compatibility outside the native core.
6. Expose new Telegram features through focused TL facades.

## Runtime graph

```text
Application
├── Database (SQLite + cache + audit)
├── HarukaClient (Kurigram lifecycle + safe raw invoke)
├── SecurityManager (roles + rate limits)
├── Loader (discovery + lifecycle + indexes + feature gates)
├── Dispatcher (parse + authorize + execute + watchers)
├── InlineBot / ControlCenter
├── AutomationEngine
├── AIProvider
└── PreferenceStore
```

`Application` is the only composition root. Modules receive services through injection.

## Startup

1. Open SQLite and warm the read cache.
2. Import a legacy JSON database once, if present.
3. Resolve Telegram API credentials and start Kurigram.
4. Set the owner identity and install the master dispatcher.
5. Start the optional companion bot.
6. Load built-ins, then user extensions.
7. Start automation and lazy AI services.
8. Write an audit event.

## Dispatch path

```text
Telegram update
  → master handler
  → prefix/alias resolution
  → command lookup
  → protected-account check
  → module/command feature gate
  → role check
  → rate limit
  → Context construction
  → audit
  → handler
  → centralized error renderer
```

Non-command messages fan out to filtered watchers in isolated tasks.

## Loader transaction

A module is imported under a dedicated runtime name, instantiated, injected, indexed and then receives `on_load()`. If import or `on_load()` fails, its registry entries and dynamic import are removed. Unload rebuilds indexes and calls `on_unload()`.

## Persistence

SQLite stores JSON values under `(owner, key)` and maintains an in-memory cache for synchronous reads. Writes are serialized. `set_many` provides an atomic multi-key primitive. The audit table is separate and prunable.

## Security boundary

Haruka can enforce roles and policy at command dispatch, but a loaded Python extension is inside the process trust boundary. True untrusted-module isolation requires a separate process/container and a capability protocol; this is a roadmap item.

## Compatibility boundary

`haruka.compat` installs minimal Hikka-style `loader`, `utils` and `translations` shims, then adapts discovered commands. Native components never depend on those shims.

## Telegram evolution

Kurigram tracks the high-level client and Telegram layer. Missing features belong in `haruka.tl` facades. Modules should not scatter raw peer conversion and retry logic.

## Known constraints

- One account per process.
- No browser/QR onboarding yet.
- Compatibility is intentionally partial.
- SQLite is optimized for a single engine process, not a cluster.
- Inline Control Center requires a companion bot.
