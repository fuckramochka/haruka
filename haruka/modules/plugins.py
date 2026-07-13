"""Manage behaviour plugins from chat.

Plugins customise how the userbot itself behaves (they hook the engine
lifecycle). This module lets the owner list, inspect, toggle, configure,
install and reload them. Installing accepts a replied ``.py`` file, exactly
like module installation but routed to the plugin manager.
"""
from __future__ import annotations

from haruka.api import Context, Module, command, render


class Plugins(Module):
    name = "Plugins"
    description = "Install and control userbot behaviour plugins."
    emoji = "\N{ELECTRIC PLUG}"
    author = "haruka"
    version = "1.0.0"

    def _manager(self, ctx: Context):
        return getattr(ctx.core, "plugins", None)

    @command(aliases=["pluglist", "pl"], doc="List every installed behaviour plugin.")
    async def plugins(self, ctx: Context):
        manager = self._manager(ctx)
        if manager is None:
            await ctx.error("Plugin system is not available.")
            return
        if not manager.plugins:
            await ctx.respond(render.info(
                "No plugins installed. Reply to a <code>.py</code> plugin with "
                "<code>.ploadplugin</code> to add one."
            ))
            return
        rows = {}
        for loaded in sorted(manager.plugins.values(), key=lambda p: p.instance.priority):
            inst = loaded.instance
            state = "\N{WHITE HEAVY CHECK MARK}" if manager.is_enabled(inst.name) else "\N{HEAVY MULTIPLICATION X}"
            tag = "core" if loaded.origin == "builtin" else "user"
            rows[f"{inst.emoji} {inst.name}"] = f"{state} <i>{render.escape(inst.description)}</i> · {tag}"
        await ctx.card("Behaviour plugins", rows, emoji=self.emoji)

    @command(usage="<name>", doc="Show details and options for one plugin.")
    async def plugin(self, ctx: Context):
        manager = self._manager(ctx)
        if manager is None or not ctx.args:
            await ctx.respond(render.info("Usage: <code>.plugin &lt;name&gt;</code>"))
            return
        loaded = manager._find(ctx.args[0])
        if loaded is None:
            await ctx.error(f"No plugin named <code>{render.escape(ctx.args[0])}</code>.")
            return
        inst = loaded.instance
        rows = {
            "Status": "enabled" if manager.is_enabled(inst.name) else "disabled",
            "Version": inst.version,
            "Author": inst.author,
            "Priority": str(inst.priority),
            "Source": "built-in" if loaded.origin == "builtin" else "user",
        }
        for key in inst.options:
            rows[f"option: {key}"] = render.escape(str(inst.option(key)))
        await ctx.card(f"{inst.emoji} {inst.name}", rows)

    @command(aliases=["plugenable"], usage="<name>", doc="Enable a plugin.")
    async def plugon(self, ctx: Context):
        await self._toggle(ctx, True)

    @command(aliases=["plugdisable"], usage="<name>", doc="Disable a plugin (keeps it installed).")
    async def plugoff(self, ctx: Context):
        await self._toggle(ctx, False)

    async def _toggle(self, ctx: Context, enabled: bool):
        manager = self._manager(ctx)
        if manager is None or not ctx.args:
            await ctx.respond(render.info("Usage: <code>.plugon &lt;name&gt;</code> / <code>.plugoff &lt;name&gt;</code>"))
            return
        if not await manager.set_enabled(ctx.args[0], enabled):
            await ctx.error(f"No plugin named <code>{render.escape(ctx.args[0])}</code>.")
            return
        await ctx.ok(f"Plugin {'enabled' if enabled else 'disabled'}.")

    @command(usage="<name> <key> <value>", doc="Set a plugin option.")
    async def plugset(self, ctx: Context):
        manager = self._manager(ctx)
        if manager is None or len(ctx.args) < 2:
            await ctx.respond(render.info("Usage: <code>.plugset &lt;name&gt; &lt;key&gt; &lt;value&gt;</code>"))
            return
        loaded = manager._find(ctx.args[0])
        if loaded is None:
            await ctx.error(f"No plugin named <code>{render.escape(ctx.args[0])}</code>.")
            return
        key = ctx.args[1]
        if key not in loaded.instance.options:
            await ctx.error(f"Plugin has no option <code>{render.escape(key)}</code>.")
            return
        raw = ctx.args_raw.split(maxsplit=2)
        value: object = raw[2] if len(raw) > 2 else ""
        low = str(value).lower()
        if low in {"true", "on", "yes", "1"}:
            value = True
        elif low in {"false", "off", "no", "0"}:
            value = False
        await loaded.instance.set_option(key, value)
        await ctx.ok(f"Set <code>{render.escape(key)}</code> = <code>{render.escape(str(value))}</code>.")

    @command(aliases=["installplugin", "plugadd"], doc="Install a plugin from a replied .py file.")
    async def ploadplugin(self, ctx: Context):
        manager = self._manager(ctx)
        if manager is None:
            await ctx.error("Plugin system is not available.")
            return
        doc = ctx.reply.document if ctx.reply else None
        if doc is None or not (doc.file_name or "").endswith(".py"):
            await ctx.respond(render.info("Reply to a <code>.py</code> plugin file."))
            return
        await ctx.loading("Installing plugin...")
        try:
            path = await ctx.app.download_media(ctx.reply, in_memory=True)
            code = bytes(path.getbuffer()).decode("utf-8") if hasattr(path, "getbuffer") else open(path, encoding="utf-8").read()
            names = await manager.install_from_source(code, doc.file_name, ctx.core.settings.plugins_dir)
        except Exception as exc:  # noqa: BLE001
            await ctx.error(f"Could not install plugin: {render.escape(exc)}")
            return
        await ctx.ok(f"Installed plugin(s): {render.escape(', '.join(names))}.")

    @command(usage="<name>", doc="Reload a user plugin from disk.")
    async def plugreload(self, ctx: Context):
        manager = self._manager(ctx)
        if manager is None or not ctx.args:
            await ctx.respond(render.info("Usage: <code>.plugreload &lt;name&gt;</code>"))
            return
        try:
            ok = await manager.reload(ctx.args[0])
        except Exception as exc:  # noqa: BLE001
            await ctx.error(f"Reload failed: {render.escape(exc)}")
            return
        if not ok:
            await ctx.error("Plugin not found or has no source file.")
            return
        await ctx.ok("Plugin reloaded.")

    @command(aliases=["uninstallplugin"], usage="<name>", doc="Remove a user plugin.")
    async def plugunload(self, ctx: Context):
        manager = self._manager(ctx)
        if manager is None or not ctx.args:
            await ctx.respond(render.info("Usage: <code>.plugunload &lt;name&gt;</code>"))
            return
        if not await manager.unload(ctx.args[0]):
            await ctx.error("Plugin not found.")
            return
        await ctx.ok("Plugin unloaded.")
