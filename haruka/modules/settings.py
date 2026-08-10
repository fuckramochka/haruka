"""Settings: prefix, aliases, theme, inline bot token."""

from __future__ import annotations

from haruka.api import Context, Module, command, render
from haruka.ui.theme import THEMES, set_theme


class Settings(Module):
    name = "Settings"
    description = "Core userbot settings"
    emoji = "\N{GEAR}\ufe0f"

    async def on_load(self) -> None:
        prefs = self.loader.app_ref.preferences.get()
        if prefs.style in THEMES:
            set_theme(prefs.style)

    @command(doc="Get or set the command prefix", usage="[new prefix]")
    async def prefix(self, ctx: Context):
        if not ctx.args:
            current = ctx.db.get("core", "prefix", ".")
            await ctx.respond(render.info(f"Current prefix: {render.mono(current)}"))
            return
        new = ctx.args[0]
        if len(new) > 3 or " " in new:
            await ctx.error("Prefix must be 1-3 characters, no spaces.")
            return
        await ctx.db.set("core", "prefix", new)
        await ctx.ok(f"Prefix set to {render.mono(new)}")

    @command(aliases=["setprefix"], doc="Compatibility wrapper for prefix", usage="<new prefix>")
    async def prefixcompat(self, ctx: Context):
        await self.prefix(ctx)

    @command(doc="Manage command aliases", usage="add <alias> <command> | del <alias> | list")
    async def alias(self, ctx: Context):
        aliases: dict = dict(ctx.db.get("core", "aliases", {}))
        action = ctx.args[0].lower() if ctx.args else "list"

        if action == "add" and len(ctx.args) >= 3:
            alias_name = ctx.args[1].lower()
            target = " ".join(ctx.args[2:])
            if ctx.loader.find_command(alias_name):
                await ctx.error(f"{render.mono(alias_name)} is already a command.")
                return
            aliases[alias_name] = target
            await ctx.db.set("core", "aliases", aliases)
            await ctx.ok(f"Alias {render.mono(alias_name)} {render.escape('->')} {render.mono(target)}")
        elif action == "del" and len(ctx.args) >= 2:
            removed = aliases.pop(ctx.args[1].lower(), None)
            await ctx.db.set("core", "aliases", aliases)
            if removed:
                await ctx.ok(f"Removed alias {render.mono(ctx.args[1])}")
            else:
                await ctx.error("No such alias.")
        else:
            if not aliases:
                await ctx.respond(render.info("No aliases set."))
                return
            await ctx.respond(
                render.bullet_list(
                    [f"{a} -> {t}" for a, t in sorted(aliases.items())], header="Aliases"
                )
            )

    @command(aliases=["aliases"], doc="List command aliases")
    async def aliaslist(self, ctx: Context):
        ctx.args_raw = "list"
        await self.alias(ctx)

    @command(aliases=["addalias"], doc="Add an alias", usage="<alias> <command>")
    async def aliasadd(self, ctx: Context):
        if len(ctx.args) < 2:
            await ctx.error("Usage: <code>.addalias alias command</code>")
            return
        ctx.args_raw = f"add {' '.join(ctx.args)}"
        await self.alias(ctx)

    @command(aliases=["delalias"], doc="Delete an alias", usage="<alias>")
    async def aliasdel(self, ctx: Context):
        if not ctx.args:
            await ctx.error("Usage: <code>.delalias alias</code>")
            return
        ctx.args_raw = f"del {ctx.args[0]}"
        await self.alias(ctx)

    @command(aliases=["panel", "control"], doc="Open the native engine Control Center")
    async def menu(self, ctx: Context):
        bot = ctx.core.inline_bot if ctx.core else None
        if bot is None:
            await ctx.error("Control Center needs an inline bot token. Configure it with <code>.setbot</code>.")
            return
        try:
            await bot.open_control_center()
            await ctx.ok("Control Center opened in the bot dialog.")
        except Exception:
            await ctx.error("Open the inline bot once with /start, then repeat this command.")

    @command(doc="Switch visual skin", usage="[aurora|carbon|minimal]")
    async def theme(self, ctx: Context):
        if not ctx.args:
            await ctx.respond(render.bullet_list(THEMES.keys(), header="Available themes"))
            return
        name = ctx.args[0].lower()
        try:
            set_theme(name)
        except KeyError:
            await ctx.error(f"Unknown theme {render.mono(name)}")
            return
        await ctx.core.preferences.set("style", name)
        await ctx.ok(f"Visual skin switched to {render.mono(name)}")

    @command(aliases=["bot", "inline"], doc="Set or auto-create the companion bot", usage="[bot token]")
    async def setbot(self, ctx: Context):
        if not ctx.args:
            if ctx.core.inline_bot is not None:
                await ctx.ok("The companion bot is already connected.")
                return
            await ctx.loading("Creating the companion bot via BotFather...")
            try:
                from haruka.inline.provision import provision_inline_bot

                _, username = await provision_inline_bot(ctx.core)
            except Exception as exc:
                await ctx.error(f"Automatic provisioning failed: {render.escape(exc)}")
                return
            await ctx.delete()
            await ctx.core._start_inline_bot()
            await ctx.app.send_message(
                "me",
                render.ok(f"Companion bot @{render.escape(username)} created and connected."),
            )
            return

        token = ctx.args[0].strip()
        await ctx.db.set_many(
            "core",
            {
                "inline_bot_token": token,
                "inline_bot_username": None,
                "inline_bootstrapped": False,
            },
        )
        await ctx.delete()
        if ctx.core.inline_bot is not None:
            await ctx.core.inline_bot.stop()
            ctx.core.inline_bot = None
        await ctx.core._start_inline_bot()
        await ctx.app.send_message("me", render.ok("Companion bot token saved and activated."))

    @command(aliases=["weburl"], doc="Open the local web Control Center")
    async def web(self, ctx: Context):
        if not ctx.core.web:
            await ctx.error("The web Control Center is disabled.")
            return
        import webbrowser

        webbrowser.open(ctx.core.web.url)
        await ctx.ok("Web Control Center opened on this device.")

    @command(aliases=["lang", "locale", "setlang"], doc="Show or change the engine language", usage="[en|ru|uk|ja|de|fr|es]")
    async def language(self, ctx: Context):
        translator = ctx.core.translator
        if not ctx.args:
            await ctx.card("Language", {"Current": translator.language, "Available": "en, ru, uk, ja, de, fr, es"})
            return
        try:
            await translator.set_language(ctx.args[0].lower())
        except ValueError as exc:
            await ctx.error(str(exc))
            return
        await ctx.ok(translator.t("common.saved"))

    @command(aliases=["settings"], doc="Show core engine settings")
    async def settingscard(self, ctx: Context):
        prefs = ctx.core.preferences.get()
        aliases = ctx.db.get("core", "aliases", {})
        await ctx.card(
            "Engine settings",
            {
                "Prefix": ctx.db.get("core", "prefix", "."),
                "Language": ctx.core.translator.language,
                "Theme": prefs.style,
                "Compact help": "on" if prefs.compact_help else "off",
                "Reveal errors": "on" if prefs.reveal_errors else "off",
                "Quiet unknown": "on" if prefs.quiet_unknown else "off",
                "Aliases": len(aliases),
                "Companion bot": "ready" if ctx.core.inline_bot else "not connected",
            },
        )
