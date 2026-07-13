"""Collaborative checklists / to-do lists.

Inspired by Telegram's 2026 collaborative checklists, but implemented as
database-backed per-chat lists so they work on every account (native Telegram
checklists are Premium-only and not exposed uniformly by client libraries).
Each chat keeps its own list; items can be checked, unchecked and cleared.
"""
from __future__ import annotations

from haruka.api import Context, Module, command, render

_DONE = "\u2611\ufe0f"   # ballot box with check
_OPEN = "\u2b1c"          # white large square


class Checklists(Module):
    name = "Checklists"
    description = "Per-chat collaborative checklists and to-do lists."
    emoji = "\u2705"

    def _items(self, ctx: Context) -> list[dict]:
        return list(ctx.db.get("checklists", str(ctx.chat_id), []))

    async def _save(self, ctx: Context, items: list[dict]) -> None:
        await ctx.db.set("checklists", str(ctx.chat_id), items)

    def _render(self, items: list[dict]) -> str:
        if not items:
            return render.info("Checklist is empty. Add an item with <code>.todo buy milk</code>.")
        lines: list[str] = []
        done = 0
        for i, it in enumerate(items, 1):
            text = render.escape(it.get("text", ""))
            if it.get("done"):
                text = f"<s>{text}</s>"
                done += 1
            box = _DONE if it.get("done") else _OPEN
            lines.append(f"{box} <b>{i}.</b> {text}")
        header = render.title("Checklist", emoji=self.emoji)
        bar = render.progress(done / len(items))
        body = "\n".join(lines)
        return f"{header}\n{render.divider()}\n{body}\n{render.divider()}\n{bar}"

    def _pick(self, ctx: Context, items: list[dict]) -> int | None:
        """Validate a 1-based index argument; return 0-based index or None."""
        if not ctx.args or not ctx.args[0].lstrip("-").isdigit():
            return None
        n = int(ctx.args[0])
        if not 1 <= n <= len(items):
            return None
        return n - 1

    @command(aliases=["addtask"], usage="[text]", doc="Add an item to this chat's checklist (or show it).")
    async def todo(self, ctx: Context):
        text = ctx.args_raw.strip()
        items = self._items(ctx)
        if not text:
            await ctx.respond(self._render(items))
            return
        items.append({"text": text, "done": False})
        await self._save(ctx, items)
        await ctx.respond(self._render(items))

    @command(aliases=["todos", "tasks"], doc="Show this chat's checklist.")
    async def checklist(self, ctx: Context):
        await ctx.respond(self._render(self._items(ctx)))

    @command(usage="<n>", doc="Mark checklist item <n> as done.")
    async def check(self, ctx: Context):
        await self._set_done(ctx, True)

    @command(usage="<n>", doc="Mark checklist item <n> as not done.")
    async def uncheck(self, ctx: Context):
        await self._set_done(ctx, False)

    async def _set_done(self, ctx: Context, done: bool):
        items = self._items(ctx)
        idx = self._pick(ctx, items)
        if idx is None:
            await ctx.error("Usage: pass a valid item number, e.g. <code>.check 2</code>.")
            return
        items[idx]["done"] = done
        await self._save(ctx, items)
        await ctx.respond(self._render(items))

    @command(aliases=["rmtask", "deltask"], usage="<n>", doc="Remove checklist item <n>.")
    async def untodo(self, ctx: Context):
        items = self._items(ctx)
        idx = self._pick(ctx, items)
        if idx is None:
            await ctx.error("Usage: pass a valid item number, e.g. <code>.rmtask 2</code>.")
            return
        items.pop(idx)
        await self._save(ctx, items)
        await ctx.respond(self._render(items))

    @command(aliases=["cleardone"], doc="Remove all completed items from the checklist.")
    async def clearchecklist(self, ctx: Context):
        items = [it for it in self._items(ctx) if not it.get("done")]
        await self._save(ctx, items)
        await ctx.respond(self._render(items))
