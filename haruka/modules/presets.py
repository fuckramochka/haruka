"""Curated external module packs and alias portability."""

from __future__ import annotations

import json
from pathlib import Path

from haruka.api import Context, Module, command, render
from haruka.modules.manager import _download_module

PRESETS = {
    "fun": [
        "https://github.com/amm1edev/ame_repo/raw/refs/heads/main/aniquotes.py",
        "https://github.com/amm1edev/ame_repo/raw/refs/heads/main/tictactoe.py",
        "https://github.com/amm1edev/ame_repo/raw/refs/heads/main/quotes.py",
    ],
    "chat": [
        "https://github.com/amm1edev/ame_repo/raw/refs/heads/main/tagall.py",
        "https://github.com/amm1edev/ame_repo/raw/refs/heads/main/filter.py",
        "https://raw.githubusercontent.com/coddrago/modules/main/chatmodule.py",
    ],
    "service": [
        "https://github.com/amm1edev/ame_repo/raw/refs/heads/main/surl.py",
        "https://github.com/amm1edev/ame_repo/raw/refs/heads/main/latex.py",
        "https://raw.githubusercontent.com/Ruslan-Isaev/modules/refs/heads/main/whois.py",
    ],
    "downloaders": [
        "https://github.com/amm1edev/ame_repo/raw/refs/heads/main/uploader.py",
        "https://github.com/amm1edev/ame_repo/raw/refs/heads/main/downloader.py",
        "https://github.com/amm1edev/ame_repo/raw/refs/heads/main/instsave.py",
    ],
}


class Presets(Module):
    name = "Presets"
    description = "Curated module packs and alias portability"
    emoji = "📦"

    @command(doc="List curated module packs")
    async def presets(self, ctx: Context):
        lines = [
            f"<code>{name}</code> — {len(urls)} modules"
            for name, urls in PRESETS.items()
        ]
        lines.append("")
        lines.append("Use <code>.loadpreset name</code> to install a pack.")
        lines.append("Use <code>.aliasexport</code> and reply with <code>.aliasimport</code> to migrate aliases.")
        await ctx.respond(render.title("Presets", self.emoji) + "\n" + render.divider() + "\n" + "\n".join(lines))

    @command(doc="Install a curated module pack", usage="<fun|chat|service|downloaders>")
    async def loadpreset(self, ctx: Context):
        if not ctx.args:
            await ctx.error("Pass a preset name: fun, chat, service, downloaders.")
            return
        name = ctx.args[0].lower()
        urls = PRESETS.get(name)
        if not urls:
            await ctx.error("Unknown preset.")
            return
        await ctx.loading(f"Installing preset {render.mono(name)}...")
        loaded, failed = [], []
        for url in urls:
            try:
                code = await _download_module(url)
                filename = url.rstrip("/").split("/")[-1] or "module.py"
                loaded.extend(await ctx.loader.install_from_source(code, filename))
            except Exception as exc:
                failed.append(f"{Path(url).name}: {type(exc).__name__}")
        await ctx.card(
            "Preset install",
            {
                "Preset": name,
                "Loaded": ", ".join(loaded) or "none",
                "Failed": ", ".join(failed) or "none",
            },
        )

    @command(doc="Export aliases to Saved Messages")
    async def aliasexport(self, ctx: Context):
        aliases = ctx.db.get("core", "aliases", {})
        if not aliases:
            await ctx.error("No aliases configured.")
            return
        blob = json.dumps(aliases, ensure_ascii=False, indent=2)
        await ctx.app.send_message(
            "me",
            render.title("Haruka alias export", self.emoji) + "\n" + render.code_block(blob, "json"),
        )
        await ctx.ok("Alias export sent to Saved Messages.")

    @command(doc="Import aliases from a replied JSON message")
    async def aliasimport(self, ctx: Context):
        text = await ctx.reply_text_or_none()
        if not text:
            await ctx.error("Reply to a JSON alias export.")
            return
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            await ctx.error("Reply must contain valid JSON.")
            return
        if not isinstance(data, dict):
            await ctx.error("Alias export must be an object.")
            return
        clean = {str(k).lower(): str(v) for k, v in data.items()}
        await ctx.db.set("core", "aliases", clean)
        await ctx.ok(f"Imported {len(clean)} aliases.")
