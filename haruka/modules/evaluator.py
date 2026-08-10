"""Python evaluation for debugging modules (owner-only)."""

from __future__ import annotations

import io
import sys
import traceback
from contextlib import redirect_stdout

from haruka.api import Context, Module, Role, command, render


class Evaluator(Module):
    name = "Eval"
    description = "Evaluate Python code in the userbot context"
    emoji = "\N{SNAKE}"

    @command(aliases=["e", "py"], role=Role.OWNER, doc="Evaluate Python code", usage="<code>")
    async def eval(self, ctx: Context):
        code = ctx.args_raw
        if not code:
            await ctx.error("Give me some code to evaluate.")
            return

        env = {
            "ctx": ctx,
            "app": ctx.app,
            "db": ctx.db,
            "loader": ctx.loader,
            "message": ctx.message,
            "reply": ctx.reply,
        }

        buffer = io.StringIO()
        wrapped = "async def __haruka_eval():\n" + "\n".join(
            f"    {line}" for line in code.splitlines()
        )

        try:
            exec(wrapped, env)  # noqa: S102 - owner-only debug tool
            with redirect_stdout(buffer):
                result = await env["__haruka_eval"]()
        except Exception:
            tb = traceback.format_exc()
            await ctx.respond(
                f"{render.error('Exception')}\n{render.code_block(tb, 'python')}"
            )
            return

        printed = buffer.getvalue()
        parts = [render.ok("Evaluated")]
        if printed:
            parts.append(render.code_block(printed, "python"))
        if result is not None:
            parts.append(render.code_block(repr(result), "python"))
        await ctx.respond("\n".join(parts))
