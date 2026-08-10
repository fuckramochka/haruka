"""Load, unload, reload and inspect modules at runtime."""

from __future__ import annotations

import aiohttp

from haruka.api import Context, Module, command, render
from haruka.utils import is_url

MAX_MODULE_SIZE = 512 * 1024


async def _download_module(url: str) -> str:
    if not is_url(url):
        raise ValueError("Only public HTTP(S) URLs are allowed")
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, allow_redirects=True) as resp:
            resp.raise_for_status()
            if not is_url(str(resp.url)):
                raise ValueError("Redirected to a non-public URL")
            if int(resp.headers.get("Content-Length", 0)) > MAX_MODULE_SIZE:
                raise ValueError("Module is larger than 512 KiB")
            raw = await resp.read()
    if len(raw) > MAX_MODULE_SIZE:
        raise ValueError("Module is larger than 512 KiB")
    return raw.decode("utf-8")


class ModuleManager(Module):
    name = "Modules"
    description = "Install and manage modules"
    emoji = "\N{ELECTRIC PLUG}"

    @command(aliases=["lm", "load"], doc="Install a module from a reply or URL", usage="[url]")
    async def loadmod(self, ctx: Context):
        code: str | None = None
        filename = "module.py"

        if ctx.reply and ctx.reply.document:
            if (ctx.reply.document.file_size or 0) > MAX_MODULE_SIZE:
                await ctx.error("Module is larger than 512 KiB.")
                return
            file = await ctx.app.download_media(ctx.reply, in_memory=True)
            code = bytes(file.getbuffer()).decode("utf-8", errors="replace")
            filename = ctx.reply.document.file_name or filename
        elif ctx.args:
            url = ctx.args[0]
            await ctx.loading("Downloading module...")
            try:
                code = await _download_module(url)
            except (aiohttp.ClientError, UnicodeError, ValueError) as exc:
                await ctx.error(f"Download failed: {render.escape(exc)}")
                return
            filename = url.rstrip("/").split("/")[-1] or filename

        if not code:
            await ctx.error("Reply to a .py file or pass a URL.")
            return

        try:
            names = await ctx.loader.install_from_source(code, filename)
        except Exception as exc:
            await ctx.error(f"Load failed: {render.escape(exc)}")
            return

        await ctx.ok(f"Loaded: {render.escape(', '.join(names))}")

    @command(doc="Install several modules from public URLs", usage="<url> [url...]")
    async def multiload(self, ctx: Context):
        if not ctx.args:
            await ctx.error("Pass one or more module URLs.")
            return
        loaded, failed = [], []
        for url in ctx.args[:10]:
            try:
                code = await _download_module(url)
                filename = url.rstrip("/").split("/")[-1] or "module.py"
                loaded.extend(await ctx.loader.install_from_source(code, filename))
            except Exception as exc:  # one bad module must not abort the batch
                failed.append(f"{url}: {type(exc).__name__}")
        await ctx.card(
            "Multi-load",
            {"Loaded": ", ".join(loaded) or "none", "Failed": ", ".join(failed) or "none"},
        )

    @command(aliases=["ulm", "unload"], doc="Unload a module by name", usage="<name>")
    async def unloadmod(self, ctx: Context):
        if not ctx.args_raw:
            await ctx.error("Which module?")
            return
        try:
            ok = await ctx.loader.unload(ctx.args_raw)
        except ValueError as exc:
            await ctx.error(str(exc))
            return
        if ok:
            await ctx.ok(f"Unloaded {render.mono(ctx.args_raw)}")
        else:
            await ctx.error("No such module.")

    @command(doc="Reload a module by name", usage="<name>")
    async def reloadmod(self, ctx: Context):
        if not ctx.args_raw:
            await ctx.error("Which module?")
            return
        ok = await ctx.loader.reload(ctx.args_raw)
        if ok:
            await ctx.ok(f"Reloaded {render.mono(ctx.args_raw)}")
        else:
            await ctx.error("Cannot reload that module.")

    @command(doc="Enable or disable a command", usage="<command>")
    async def togglecmd(self, ctx: Context):
        name = ctx.args_raw.strip().lower()
        bound = ctx.loader.find_command(name)
        if not bound:
            await ctx.error("No such command.")
            return
        enabled = not ctx.loader.is_command_enabled(bound.name)
        await ctx.loader.set_command_enabled(bound.name, enabled)
        await ctx.ok(f"{render.mono(bound.name)} is now {'enabled' if enabled else 'disabled'}")

    @command(doc="Enable or disable a module without unloading it", usage="<module>")
    async def togglemod(self, ctx: Context):
        name = ctx.loader.resolve_module_name(ctx.args_raw.strip())
        if not name:
            await ctx.error("No such module.")
            return
        if name == self.name:
            await ctx.error("The module manager cannot disable itself.")
            return
        enabled = not ctx.loader.is_module_enabled(name)
        await ctx.loader.set_module_enabled(name, enabled)
        await ctx.ok(f"{render.mono(name)} is now {'enabled' if enabled else 'disabled'}")

    @command(aliases=["mulm"], doc="Unload several user modules", usage="<name> [name...]")
    async def multiunload(self, ctx: Context):
        if not ctx.args:
            await ctx.error("Pass one or more module names.")
            return
        done, failed = [], []
        for name in ctx.args:
            try:
                (done if await ctx.loader.unload(name) else failed).append(name)
            except ValueError:
                failed.append(name)
        await ctx.card("Multi-unload", {"Unloaded": ", ".join(done) or "none", "Skipped": ", ".join(failed) or "none"})

    @command(doc="Delete an unloaded user module file", usage="<module|filename>")
    async def clearmodule(self, ctx: Context):
        raw = ctx.args_raw.strip()
        if not raw:
            await ctx.error("Pass a module or filename.")
            return
        source = ctx.loader.source_of(raw)
        if source is not None:
            await ctx.error("Unload the module first.")
            return
        from pathlib import Path
        target = ctx.loader.settings.modules_dir / Path(raw).name
        if target.suffix.lower() != ".py":
            target = target.with_suffix(".py")
        if not target.exists():
            await ctx.error("Module file not found.")
            return
        target.unlink()
        await ctx.ok(f"Deleted {render.mono(target.name)}")

    @command(aliases=["mods"], doc="List loaded modules")
    async def modules(self, ctx: Context):
        lines = []
        for name in ctx.loader.module_names():
            loaded = ctx.loader.modules[name]
            tag = "" if loaded.origin == "builtin" else " (user)"
            state = "" if ctx.loader.is_module_enabled(name) else " [disabled]"
            lines.append(f"{loaded.instance.emoji} {name}{tag}{state} — {len(loaded.commands)} cmd")
        await ctx.respond(render.bullet_list(lines, header="Loaded modules"))
