"""Updater: restart in place or pull the latest code from git.

Restart notes survive the re-exec through the database, so the user gets a
"restarted successfully" edit on the original message after boot.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

from haruka.api import Context, Module, Role, command, render
from haruka.version import version_string

ROOT = Path(__file__).resolve().parents[2]


async def _git(*args: str) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=ROOT,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    return proc.returncode or 0, out.decode("utf-8", "replace").strip()


class Updater(Module):
    name = "Updater"
    description = "Restart and update the userbot"
    emoji = "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}"

    async def on_load(self):
        note = self.db.get("updater", "restart_note")
        if not note:
            return
        await self.db.set("updater", "restart_note", None)
        try:
            elapsed = time.time() - note["ts"]
            await self.app.app.edit_message_text(
                note["chat_id"],
                note["message_id"],
                render.ok(f"Restarted in {elapsed:.1f}s — {version_string()}"),
            )
        except Exception:
            pass

    async def _restart(self, ctx: Context, text: str) -> None:
        msg = await ctx.loading(text)
        await self.db.set(
            "updater",
            "restart_note",
            {"chat_id": ctx.chat_id, "message_id": msg.id, "ts": time.time()},
        )
        await ctx.core.restart()

    async def _install_requirements(self) -> tuple[bool, str]:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "pip",
            "install",
            "-e",
            ".",
            cwd=ROOT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await proc.communicate()
        return proc.returncode == 0, out.decode("utf-8", "replace")

    async def _after_code_changed(self, ctx: Context, text: str) -> None:
        ok, dependency_output = await self._install_requirements()
        if not ok:
            await ctx.error(text + "\n" + render.code_block(dependency_output[-1200:], "text"))
            return
        await self._restart(ctx, text)

    @command(role=Role.OWNER, doc="Restart the userbot")
    async def restart(self, ctx: Context):
        await self._restart(ctx, "Restarting...")

    @command(role=Role.OWNER, doc="Pull the latest code and restart")
    async def update(self, ctx: Context):
        await ctx.loading("Checking for updates...")
        code, out = await _git("pull", "--ff-only")
        if code != 0:
            await ctx.error(f"<code>git pull</code> failed:\n<pre>{render.escape(out[-1000:])}</pre>")
            return
        if "Already up to date" in out:
            await ctx.ok(f"Already up to date — {version_string()}")
            return
        await self._after_code_changed(ctx, "Update pulled, restarting...")

    @command(role=Role.OWNER, doc="Reset to the previous git commit and restart")
    async def rollback(self, ctx: Context):
        code, out = await _git("rev-parse", "--is-inside-work-tree")
        if code != 0 or out.strip() != "true":
            await ctx.error("Rollback requires a git checkout.")
            return
        code, out = await _git("reset", "--hard", "HEAD~1")
        if code != 0:
            await ctx.error(render.code_block(out[-1200:], "text"))
            return
        await self._after_code_changed(ctx, "Rollback applied, restarting...")

    @command(role=Role.SUDO, doc="Show latest changelog section")
    async def changelog(self, ctx: Context):
        path = ROOT / "CHANGELOG.md"
        if not path.exists():
            await ctx.error("CHANGELOG.md not found.")
            return
        text = path.read_text(encoding="utf-8", errors="replace")
        if "## " in text:
            section = text.split("## ", 1)[1]
            if "\n## " in section:
                section = section.split("\n## ", 1)[0]
            section = "## " + section
        else:
            section = text[:3000]
        await ctx.respond(render.title("Changelog", self.emoji) + "\n" + render.code_block(section[-3200:], "markdown"))

    @command(role=Role.SUDO, doc="Show source repository and docs")
    async def source(self, ctx: Context):
        await ctx.card(
            "Source",
            {
                "Repository": "https://github.com/fuxckramochka/haruka",
                "Docs": "README.md / docs/",
                "Version": version_string(),
            },
        )

    @command(role=Role.SUDO, doc="Show current version and git revision")
    async def version(self, ctx: Context):
        _, rev = await _git("rev-parse", "--short", "HEAD")
        _, branch = await _git("rev-parse", "--abbrev-ref", "HEAD")
        await ctx.card("Version", {"Haruka": version_string(), "Branch": branch or "?", "Commit": rev or "?"})
