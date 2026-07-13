"""Open the universal companion-bot configuration center."""
from __future__ import annotations

from haruka.api import Context, Module, command


class Configurator(Module):
    name = "Configurator"
    description = "Configure every native module through the inline bot"
    emoji = "⚙️"

    @command(aliases=["cfg", "config"], doc="Open universal inline configuration center", usage="[module]")
    async def configcmd(self, ctx: Context):
        center = getattr(ctx.core.inline_bot, "config_center", None) if ctx.core and ctx.core.inline_bot else None if ctx.core else None
        if center is None:
            await ctx.error("Companion configuration is not ready. Run <code>.setbot</code>.")
            return
        await center.open()
        await ctx.ok("Configuration Center opened in the companion bot.")

    @command(doc="Set a module option without opening the UI", usage="<module> <option> <value>")
    async def fconfig(self, ctx: Context):
        if len(ctx.args) < 3:
            await ctx.error("Usage: <code>.fconfig Module option value</code>")
            return
        module_name, option = ctx.args[0], ctx.args[1]
        value = ctx.args_raw.split(maxsplit=2)[2]
        canonical = ctx.loader.resolve_module_name(module_name)
        loaded = ctx.loader.modules.get(canonical or "")
        if loaded is None or not getattr(loaded.instance, "config", None) or option not in loaded.instance.config.options:
            await ctx.error("Module or option not found.")
            return
        from haruka.inline.config_center import ConfigCenter
        converted = ConfigCenter._parse(ConfigCenter, value, loaded.instance.config.options[option].default)
        await loaded.instance.config.set(option, converted)
        await ctx.ok("Saved.")
