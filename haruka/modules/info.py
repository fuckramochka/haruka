"""Info: status card of the userbot."""

from __future__ import annotations

import platform
import time

import psutil

from haruka.api import Context, Module, command, render
from haruka.core.diagnostics import collect_health
from haruka.version import __version__, version_string


def _fmt_uptime(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    if d:
        return f"{d}d {h}h {m}m"
    if h:
        return f"{h}h {m}m"
    return f"{m}m {s}s"


class Info(Module):
    name = "Info"
    description = "Userbot status and system info"
    emoji = "\N{ELECTRIC LIGHT BULB}"

    @command(aliases=["haruka", "status", "infocmd", "ubinfo"], doc="Show userbot status card")
    async def info(self, ctx: Context):
        proc = psutil.Process()
        ram_mb = proc.memory_info().rss / 1024 / 1024
        app_ref = getattr(ctx.loader, "app_ref", None)
        uptime = _fmt_uptime(app_ref.uptime) if app_ref else "?"
        me = ctx.client.me

        await ctx.respond(
            render.card(
                version_string(),
                {
                    "Owner": f"{me.first_name} (id {me.id})",
                    "Premium": "yes" if ctx.client.is_premium else "no",
                    "Uptime": uptime,
                    "RAM": f"{ram_mb:.1f} MB",
                    "Modules": len(ctx.loader.modules),
                    "Commands": len(ctx.loader.command_names),
                    "Python": platform.python_version(),
                    "Platform": platform.system(),
                },
                emoji=self.emoji,
            )
        )

    @command(doc="Measure round-trip time to Telegram")
    async def ping(self, ctx: Context):
        start = time.perf_counter()
        msg = await ctx.respond(render.loading("Pinging..."))
        delta_ms = (time.perf_counter() - start) * 1000
        await msg.edit_text(
            render.ok(f"Pong: {delta_ms:.0f} ms") + f"\n{render.info(f'v{__version__}')}",
        )

    @command(aliases=["health"], doc="Show the engine health snapshot")
    async def diagnostics(self, ctx: Context):
        health = collect_health(ctx.core.settings.db_path)
        await ctx.card(
            "Engine health",
            {
                "Status": health.status,
                "Memory": f"{health.memory_mb:.1f} MB",
                "CPU": f"{health.cpu_percent:.1f}%",
                "Disk free": f"{health.disk_free_gb:.1f} GB",
                "Async tasks": health.tasks,
                "Database": f"{health.database_kb:.1f} KiB",
            },
            emoji="🟢" if health.status == "healthy" else "🟠",
        )

    @command(aliases=["engine"], doc="Open the native engine management surface")
    async def dashboard(self, ctx: Context):
        bot = ctx.core.inline_bot if ctx.core else None
        if bot is None:
            await ctx.error("Configure the inline bot to use Control Center.")
            return
        try:
            await bot.open_control_center()
            await ctx.ok("Engine dashboard opened in the bot dialog.")
        except Exception:
            await ctx.error("Open the companion bot with /start first.")
