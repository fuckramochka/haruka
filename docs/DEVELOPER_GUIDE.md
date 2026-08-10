# Haruka Extension Developer Guide

## Contract

New extensions should import only from `haruka.api`. Treat `haruka.core.*` as private unless you are contributing to the engine itself.

```python
from haruka.api import ConfigOption, Context, Module, ModuleConfig, Role, command, watcher
```

## Module metadata

```python
class Weather(Module):
    name = "Weather"
    description = "Current weather and forecasts"
    author = "your-name"
    version = "1.0.0"
    emoji = "☁️"
```

Names are resolved case-insensitively. Do not reuse a built-in module name.

## Commands

```python
@command(
    name="weather",
    aliases=["w"],
    role=Role.OWNER,
    usage="<city>",
    doc="Show weather for a city",
)
async def weather(self, ctx: Context):
    city = " ".join(ctx.args)
    await ctx.loading("Loading weather…")
    await ctx.card("Weather", {"City": city, "Temperature": "18°C"})
```

Arguments use shell-like parsing, so `.weather "New York"` becomes one argument. `ctx.args_raw` preserves the original tail.

## Context essentials

| Property/method | Purpose |
|---|---|
| `ctx.message` | raw Kurigram message |
| `ctx.app` | underlying Kurigram client |
| `ctx.db` | namespaced SQLite store |
| `ctx.loader` | runtime module registry |
| `ctx.reply` | replied-to message |
| `ctx.topic_id` | forum topic id, if present |
| `ctx.respond()` | edit outgoing command or reply |
| `ctx.ok/error/loading/card()` | consistent UI builders |
| `ctx.security` | shared security manager |

## Watchers

```python
@watcher(
    incoming=True,
    outgoing=False,
    only_groups=True,
    only_reply=False,
    only_forward=False,
    only_mention=True,
    no_bots=True,
    no_commands=True,
)
async def mentions(self, ctx: Context):
    ...
```

Watchers run in isolated tasks. Catch expected network/domain errors yourself; unexpected failures are logged by the dispatcher.

## Persistent config

```python
class Example(Module):
    def __init__(self):
        super().__init__()
        self.config = ModuleConfig(
            ConfigOption("interval", 60, "Polling interval", int),
        )

    async def command_handler(self, ctx):
        await self.config.set("interval", 120)
```

The loader binds config to `config.<ModuleName>` in SQLite.

## Lifecycle

- `on_load()` runs after services are injected and handlers indexed. If it fails, registration is rolled back.
- `on_unload()` runs on hot unload and graceful engine shutdown.
- Cancel tasks, close sessions and release files in `on_unload()`.

```python
async def on_load(self):
    self.task = asyncio.create_task(self.worker())

async def on_unload(self):
    self.task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await self.task
```

## Raw MTProto

Use `haruka.tl.RawAPI` when Kurigram lacks a high-level method. Keep raw types inside a small adapter so Telegram layer changes do not spread through your module.

## Security rules

- Use the least privileged `Role` that fits.
- Never print tokens, session strings or passwords.
- Bound downloads by size and timeout.
- Avoid `shell=True`; use argument arrays.
- Do not join channels, message users or upload data during import.
- Make network behavior explicit in help text.
- Do not bypass feature gates or call private dispatcher indexes.

## Compatibility

The Hikka adapter is a migration aid, not a complete reimplementation. Native Haruka extensions get predictable lifecycle, typed config and stable context. If a compatibility module depends on deep Hikka internals, port it instead of extending the shim.

## Tests

```bash
pip install -e '.[dev]'
pytest
ruff check haruka tests
```

Test handler logic with fake contexts and lifecycle behavior with fake database/client objects. Every bug fix should receive a regression test.
