"""Command atlas with a Heroku-like visual layout."""
from __future__ import annotations

import difflib
import html

from haruka.api import Context, Module, command


class Help(Module):
    name = "Help"
    description = "Visual command atlas and module reference"
    emoji = "🪐"

    def __init__(self):
        super().__init__()
        from haruka.core.config import ConfigOption, ModuleConfig
        self.config = ModuleConfig(
            ConfigOption("show_empty_modules", False, "Show modules with no commands in .help -f."),
            ConfigOption("max_catalog_items", 160, "Maximum module names displayed by a catalog page.", int),
        )

    def _module_display_name(self, loaded) -> str:
        return html.escape(loaded.instance.name)

    def _module_line(self, ctx: Context, loaded, prefix: str, force: bool = False) -> str:
        commands = [item for item in loaded.commands if not item.spec.hidden]
        if not commands:
            return ""
        names = []
        for item in sorted(commands, key=lambda value: value.name):
            if force or ctx.loader.is_command_enabled(item.name):
                names.append(item.name)
        if not names:
            return ""
        bullet = "▪️" if loaded.origin == "builtin" else "▫️"
        return f"\n{bullet} <code>{self._module_display_name(loaded)}</code>: ( {' | '.join(names)} )"

    async def _module_help(self, ctx: Context, query: str, prefix: str) -> None:
        target = None
        exact = True
        canonical = ctx.loader.resolve_module_name(query)
        if canonical:
            target = ctx.loader.modules[canonical]
        if target is None:
            bound = ctx.loader.find_command(query.lower().lstrip(prefix))
            if bound is not None:
                canonical = ctx.loader.resolve_module_name(bound.module.name)
                target = ctx.loader.modules.get(canonical) if canonical else None
            else:
                names = ctx.loader.module_names()
                if names:
                    guesses = sorted(
                        names,
                        key=lambda value: difflib.SequenceMatcher(None, query.casefold(), value.casefold()).ratio(),
                    )
                    canonical = guesses[-1]
                    target = ctx.loader.modules.get(canonical)
                    exact = False
        if target is None:
            await ctx.error(ctx.t("help.not_found", name=f"<code>{html.escape(query)}</code>"))
            return

        commands = [item for item in target.commands if not item.spec.hidden]
        title = self._module_display_name(target)
        lines = [f"🪐 <b>{title}</b>"]
        if target.instance.description:
            lines.append(f"<i>ℹ️ {html.escape(target.instance.description)}</i>")
        cmd_lines = []
        for item in sorted(commands, key=lambda value: value.name):
            aliases = f" ({', '.join(item.spec.aliases)})" if item.spec.aliases else ""
            doc = html.escape(item.spec.doc or 'No description')
            cmd_lines.append(
                f"▫️ <code>{html.escape(prefix + item.name)}</code>{html.escape(aliases)} {doc}"
            )
        if cmd_lines:
            lines.append("<blockquote expandable>" + "\n".join(cmd_lines) + "</blockquote>")
        if not exact:
            lines.append(f"<i>{html.escape(ctx.t('help.closest_match'))}</i>")
        if target.origin == "builtin":
            lines.append(f"<i>{html.escape(ctx.t('help.core_module'))}</i>")
        await ctx.respond("\n".join(lines))

    @command(aliases=["h", "commands"], doc="[args] | Help with your modules", usage="[feature|command|-f|-c|-l]")
    async def help(self, ctx: Context):
        prefix = ctx.db.get("core", "prefix", ".")
        query = ctx.args_raw.strip()
        if query and query not in {"-f", "-c", "-l"}:
            await self._module_help(ctx, query, prefix)
            return

        force = query == "-f"
        only_core = query == "-c"
        only_loaded = query == "-l"
        hidden = set(ctx.db.get("help", "hidden_modules", []))
        total = len(ctx.loader.modules)
        hidden_count = 0 if force else sum(name in hidden for name in ctx.loader.module_names())

        reply = ctx.t("help.summary", total=f"<b>{total}</b>", hidden=f"<b>{hidden_count}</b>")
        core_lines, user_lines, empty_lines = [], [], []

        for name in ctx.loader.module_names():
            loaded = ctx.loader.modules[name]
            if name in hidden and not force and not only_core and not only_loaded:
                continue
            commands = [item for item in loaded.commands if not item.spec.hidden]
            if not commands:
                empty_lines.append(f"\n🟠 <code>{self._module_display_name(loaded)}</code>")
                continue
            line = self._module_line(ctx, loaded, prefix, force=force)
            if not line:
                continue
            if loaded.origin == "builtin":
                core_lines.append(line)
            else:
                user_lines.append(line)

        core_block = ''.join(sorted(core_lines, key=str.casefold))
        user_block = ''.join(sorted(user_lines, key=str.casefold))
        empty_block = ''.join(sorted(empty_lines, key=str.casefold)) if (force and self.config['show_empty_modules']) else ''

        no_core = ctx.t("help.no_core")
        no_external = ctx.t("help.no_external")
        none_available = ctx.t("help.none_available")
        if only_core:
            body = f"🪐 {reply}\n<blockquote expandable>{core_block or no_core}</blockquote>"
        elif only_loaded:
            body = f"🪐 {reply}\n<blockquote expandable>{user_block or no_external}</blockquote>"
        else:
            body = (
                f"🪐 {reply}\n"
                f"<blockquote expandable>{core_block or no_core}</blockquote>"
                f"<blockquote expandable>{user_block + empty_block or none_available}</blockquote>"
                f"<blockquote expandable>"
                f"<code>{html.escape(prefix)}help module</code> — {html.escape(ctx.t('help.open_details'))}\n"
                f"<code>{html.escape(prefix)}help -c</code> — {html.escape(ctx.t('help.only_core_hint'))}\n"
                f"<code>{html.escape(prefix)}help -l</code> — {html.escape(ctx.t('help.only_loaded_hint'))}\n"
                f"<code>{html.escape(prefix)}help -f</code> — {html.escape(ctx.t('help.ignore_hidden_hint'))}\n"
                f"<code>{html.escape(prefix)}lang</code> • <code>{html.escape(prefix)}menu</code> • <code>{html.escape(prefix)}presets</code>"
                f"</blockquote>"
            )
        await ctx.respond(body)

    @command(doc="Hide or unhide modules in help", usage="<module> [module...]")
    async def helphide(self, ctx: Context):
        if not ctx.args:
            hidden = ctx.db.get("help", "hidden_modules", [])
            await ctx.respond(f"🪐 <b>Hidden modules:</b> <code>{html.escape(', '.join(hidden) or 'none')}</code>")
            return
        hidden = set(ctx.db.get("help", "hidden_modules", []))
        changed = []
        for raw in ctx.args:
            canonical = ctx.loader.resolve_module_name(raw)
            if not canonical:
                continue
            if canonical in hidden:
                hidden.remove(canonical)
                changed.append(f"show:{canonical}")
            else:
                hidden.add(canonical)
                changed.append(f"hide:{canonical}")
        await ctx.db.set("help", "hidden_modules", sorted(hidden))
        await ctx.ok(', '.join(changed) if changed else 'Nothing changed.')

    @command(doc="Show support and documentation links")
    async def support(self, ctx: Context):
        prefix = ctx.db.get("core", "prefix", ".")
        await ctx.respond(
            "🪐 <b>Haruka support</b>\n"
            "<blockquote expandable>"
            "GitHub: <code>https://github.com/fuxckramochka/haruka</code>\n"
            "Docs: <code>README.md</code> • <code>docs/</code>\n"
            f"Quickstart: <code>{html.escape(prefix)}quickstart</code>\n"
            f"Control Center: <code>{html.escape(prefix)}menu</code>"
            "</blockquote>"
        )
