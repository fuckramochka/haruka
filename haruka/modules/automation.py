"""User-facing commands for the automation engine."""

from __future__ import annotations

import secrets

from haruka.api import Context, Module, command
from haruka.automation.engine import Job, Trigger
from haruka.ui import render

_MODES = {"contains", "exact", "regex"}
_SCOPES = {"all", "groups", "private"}


class Automation(Module):
    """Triggers and scheduled messages."""

    name = "Automation"
    emoji = "\u2699\ufe0f"

    def _engine(self, ctx: Context):
        core = ctx.core
        return core.automation if core else None

    @command(
        "trigger",
        usage='<pattern> :: <reply> [mode] [scope]',
        doc="Add a trigger. Modes: contains/exact/regex. Scopes: all/groups/private.",
    )
    async def trigger_cmd(self, ctx: Context) -> None:
        engine = self._engine(ctx)
        if engine is None:
            await ctx.respond(render.error("Automation engine is not running."))
            return
        if "::" not in ctx.args_raw:
            await ctx.respond(render.info(
                "Usage: <code>.trigger pattern :: reply [mode] [scope]</code>"
            ))
            return

        pattern_part, _, rest = ctx.args_raw.partition("::")
        pattern = pattern_part.strip()
        words = rest.strip().split()

        mode, scope = "contains", "all"
        # Trailing tokens may specify mode/scope; everything else is the reply.
        while words and (words[-1] in _MODES or words[-1] in _SCOPES):
            token = words.pop()
            if token in _MODES:
                mode = token
            else:
                scope = token
        reply = " ".join(words).strip()

        if not pattern or not reply:
            await ctx.respond(render.error("Both pattern and reply are required."))
            return

        trigger = Trigger(
            id=secrets.token_hex(3),
            pattern=pattern,
            reply=reply,
            mode=mode,
            scope=scope,
        )
        await engine.add_trigger(trigger)
        await ctx.respond(render.ok(
            f"Trigger <code>{trigger.id}</code> added "
            f"({render.escape(mode)}, {render.escape(scope)})."
        ))

    @command("triggers", doc="List active triggers.")
    async def triggers_cmd(self, ctx: Context) -> None:
        engine = self._engine(ctx)
        if engine is None or not engine.triggers:
            await ctx.respond(render.info("No triggers set."))
            return
        items = [
            f"<code>{t.id}</code> [{t.mode}/{t.scope}] "
            f"{render.escape(t.pattern)} → {render.escape(t.reply[:40])}"
            for t in engine.triggers.values()
        ]
        await ctx.respond(render.bullet_list(items, header="Triggers"))

    @command("deltrigger", usage="<id>", doc="Remove a trigger by id.")
    async def deltrigger_cmd(self, ctx: Context) -> None:
        engine = self._engine(ctx)
        if engine is None:
            await ctx.respond(render.error("Automation engine is not running."))
            return
        if await engine.remove_trigger(ctx.args_raw.strip()):
            await ctx.respond(render.ok("Trigger removed."))
        else:
            await ctx.respond(render.error("No trigger with that id."))

    @command(
        "schedule",
        usage="<minutes> <text>",
        doc="Send <text> to this chat every <minutes> minutes.",
    )
    async def schedule_cmd(self, ctx: Context) -> None:
        engine = self._engine(ctx)
        if engine is None:
            await ctx.respond(render.error("Automation engine is not running."))
            return
        args = ctx.args
        if len(args) < 2 or not args[0].isdigit() or int(args[0]) < 1:
            await ctx.respond(render.info(
                "Usage: <code>.schedule 60 your text</code> (minutes ≥ 1)"
            ))
            return
        minutes = int(args[0])
        text = ctx.args_raw.split(maxsplit=1)[1]
        job = Job(
            id=secrets.token_hex(3),
            chat_id=ctx.chat_id,
            text=text,
            interval=minutes * 60,
        )
        await engine.add_job(job)
        await ctx.respond(render.ok(
            f"Job <code>{job.id}</code> scheduled every {minutes} min."
        ))

    @command("jobs", doc="List scheduled jobs.")
    async def jobs_cmd(self, ctx: Context) -> None:
        engine = self._engine(ctx)
        if engine is None or not engine.jobs:
            await ctx.respond(render.info("No scheduled jobs."))
            return
        items = [
            f"<code>{j.id}</code> every {j.interval // 60} min in "
            f"<code>{j.chat_id}</code>: {render.escape(j.text[:40])}"
            for j in engine.jobs.values()
        ]
        await ctx.respond(render.bullet_list(items, header="Scheduled jobs"))

    @command("deljob", usage="<id>", doc="Remove a scheduled job by id.")
    async def deljob_cmd(self, ctx: Context) -> None:
        engine = self._engine(ctx)
        if engine is None:
            await ctx.respond(render.error("Automation engine is not running."))
            return
        if await engine.remove_job(ctx.args_raw.strip()):
            await ctx.respond(render.ok("Job removed."))
        else:
            await ctx.respond(render.error("No job with that id."))
