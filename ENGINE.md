# Haruka engine contract

## Public surfaces

- `haruka.api`: `Module`, `Context`, decorators, roles, typed module config and stable utilities.
- `haruka.tl`: raw MTProto calls, entity cache and premium helpers.
- `Context`: message, quoted arguments, reply, topic id, client, database, loader and rendering helpers.

Everything below `haruka.core` is internal and may change between minor releases.

## Lifecycle

1. Module class is instantiated.
2. Runtime services and persisted config are injected.
3. Commands, watchers and callbacks are indexed.
4. `on_load()` runs. Failure rolls registration back.
5. `on_unload()` runs during unload and graceful engine shutdown.

Modules must cancel their own tasks in `on_unload()`.

## Watchers

`@watcher` supports direction, group/private scope, reply/forward/mention-only filtering, bot exclusion and command exclusion. Watchers are isolated in tasks; one failure does not stop dispatch.

## Runtime controls

- `.togglecmd <command>` persists a command feature gate.
- `.togglemod <module>` persists a module feature gate without deleting state.
- `.multiload <urls...>` and `.multiunload <names...>` handle batches.
- `.clearmodule <filename>` removes an unloaded module source.

## Compatibility

The Hikka adapter exists for migration. New code should target `haruka.api`; compatibility shims intentionally do not reproduce Hikka internals or monkey-patching.

## Telegram evolution

Kurigram owns layer updates. New Telegram methods should be exposed through a small facade in `haruka.tl`, then consumed by modules. Do not leak raw-client assumptions into the dispatcher or module loader.
