"""Configurable Info, Ping and Diagnostics surfaces."""
from __future__ import annotations

import platform
import time

import psutil

from haruka import utils
from haruka.api import Context, Module, command, render
from haruka.core.config import ConfigOption, ModuleConfig
from haruka.core.diagnostics import collect_health
from haruka.version import CODENAME, __version__, version_string


def _uptime(seconds: float) -> str:
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h {minutes}m" if days else f"{hours}h {minutes}m" if hours else f"{minutes}m {seconds}s"


class _Values(dict):
    def __missing__(self, key):
        return "{" + key + "}"


class Info(Module):
    name = "Info"
    description = "Customizable status, ping and diagnostics"
    emoji = "💡"

    def __init__(self):
        super().__init__()
        self.config = ModuleConfig(
            ConfigOption("banner_url", None, "Direct image URL used by .info."),
            ConfigOption("custom_message", None, "Template for .info. Placeholders: {owner}, {version}, {prefix}, {uptime}, {ram}, {cpu}, {modules}, {commands}, {python}, {platform}."),
            ConfigOption("ping_emoji", "🪐", "Emoji used by .ping."),
            ConfigOption("ping_banner", None, "Direct image URL used by .ping."),
            ConfigOption("ping_message", "{emoji} <b>Pong: {ping} ms</b>\n<code>Haruka v{version}</code>", "Template for .ping. Placeholders: {emoji}, {ping}, {version}."),
        )

    def _values(self, ctx: Context, ping: float = 0) -> dict[str, str]:
        process = psutil.Process()
        me = ctx.client.me
        return {
            "owner": f"{me.first_name} (id {me.id})",
            "version": version_string(), "version_raw": __version__, "codename": CODENAME,
            "prefix": ctx.db.get("core", "prefix", "."),
            "uptime": utils.formatted_uptime(ctx.core.uptime), "ram": f"{process.memory_info().rss / 1024 / 1024:.1f} MB",
            "cpu": f"{psutil.cpu_percent():.1f}%", "modules": str(len(ctx.loader.modules)),
            "commands": str(len(ctx.loader.command_names)), "python": platform.python_version(),
            "platform": platform.system(), "ping": f"{ping:.0f}", "emoji": str(self.config["ping_emoji"]),
            "os": utils.get_os_name(), "kernel": platform.release(), "cpu_cores": utils.cpu_model(),
            "hostname": utils.hostname(), "user": utils.username(), "build": utils.git_status(),
            "branch": utils.git_info()["branch"] or "release",
        }

    @command(aliases=["haruka", "status", "infocmd", "ubinfo"], doc="Show configurable userbot status card")
    async def info(self, ctx: Context):
        values = self._values(ctx)
        template = self.config["custom_message"]
        text = template.format_map(_Values(values)) if template else render.card(
            values["version"],
            {
                "Owner": values["owner"], "Uptime": values["uptime"], "Build": values["build"],
                "RAM": values["ram"], "CPU": f"{values['cpu']} · {values['cpu_cores']}",
                "Modules": values["modules"], "Commands": values["commands"], "Prefix": values["prefix"],
                "Python": values["python"], "OS": values["os"], "Kernel": values["kernel"],
                "Host": f"{values['user']}@{values['hostname']}",
            },
            emoji=self.emoji,
        )
        banner = self.config["banner_url"]
        if banner:
            await ctx.delete(); await ctx.app.send_photo(ctx.chat_id, banner, caption=text)
        else:
            await ctx.respond(text)

    @command(aliases=["herokucmd", "aboutcmd"], doc="Show a compact about card for the engine")
    async def about(self, ctx: Context):
        values = self._values(ctx)
        await ctx.card(
            "Haruka userbot",
            {
                "Version": f"{values['version_raw']} \u00ab{values['codename']}\u00bb",
                "Build": values["build"],
                "Prefix": render.mono(values["prefix"]),
                "Modules": values["modules"],
                "Uptime": values["uptime"],
                "Engine": "Kurigram / Haruka core",
            },
            emoji="\N{RINGED PLANET}",
        )

    @command(doc="Measure Telegram round-trip time with configured appearance")
    async def ping(self, ctx: Context):
        started = time.perf_counter(); message = await ctx.respond(render.loading("Pinging..."))
        text = self.config["ping_message"].format_map(_Values(self._values(ctx, (time.perf_counter() - started) * 1000)))
        if self.config["ping_banner"]:
            await message.delete(); await ctx.app.send_photo(ctx.chat_id, self.config["ping_banner"], caption=text)
        else:
            await message.edit_text(text)

    @command(aliases=["health"], doc="Show engine health snapshot")
    async def diagnostics(self, ctx: Context):
        health = collect_health(ctx.core.settings.db_path)
        await ctx.card("Engine health", {"Status": health.status, "Memory": f"{health.memory_mb:.1f} MB", "CPU": f"{health.cpu_percent:.1f}%", "Disk free": f"{health.disk_free_gb:.1f} GB", "Async tasks": health.tasks, "Database": f"{health.database_kb:.1f} KiB"}, emoji="🟢" if health.status == "healthy" else "🟠")

    @command(aliases=["engine"], doc="Open Control Center")
    async def dashboard(self, ctx: Context):
        if ctx.core.inline_bot is None:
            await ctx.error("Configure the companion bot with <code>.setbot</code>."); return
        await ctx.core.inline_bot.open_control_center(); await ctx.ok("Control Center opened.")
