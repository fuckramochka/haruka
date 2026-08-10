"""Manual entry point for the integrated onboarding wizard."""
from __future__ import annotations

from haruka.api import Context, Module, command


class Quickstart(Module):
    name = "Quickstart"
    description = "Integrated first-run setup wizard"
    emoji = "🚀"

    @command(doc="Open the connected setup wizard again")
    async def quickstart(self, ctx: Context):
        bot = ctx.core.inline_bot if ctx.core else None
        if bot is None:
            await ctx.error("The companion bot is not ready. Run <code>.setbot</code>.")
            return
        await bot.control.send_onboarding(reset=True)
        await ctx.ok("Setup wizard opened in the companion bot.")
