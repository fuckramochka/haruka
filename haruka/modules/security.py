"""Security: roles, audit log and session hardening (owner only)."""

from __future__ import annotations

from datetime import datetime, timezone

from haruka.api import Context, Module, Role, command, render


def _fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


async def _resolve_target(ctx: Context) -> int | None:
    """Resolve a target user id from a reply or the first argument."""
    if ctx.reply and ctx.reply.from_user:
        return ctx.reply.from_user.id
    if ctx.args:
        raw = ctx.args[0]
        if raw.lstrip("-").isdigit():
            return int(raw)
        try:
            user = await ctx.app.get_users(raw)
            return user.id
        except Exception:
            return None
    return None


class Security(Module):
    name = "Security"
    description = "Access control, audit log and hardening"
    emoji = "\N{SHIELD}"

    @command(role=Role.OWNER, doc="Grant sudo access", usage="<reply|user>")
    async def addsudo(self, ctx: Context):
        target = await _resolve_target(ctx)
        if target is None:
            await ctx.error("Reply to a user or pass an id/username.")
            return
        await ctx.security.grant(target, Role.SUDO)
        await ctx.ok(f"Granted SUDO to {render.mono(target)}")

    @command(role=Role.OWNER, doc="Grant support access", usage="<reply|user>")
    async def addsupport(self, ctx: Context):
        target = await _resolve_target(ctx)
        if target is None:
            await ctx.error("Reply to a user or pass an id/username.")
            return
        await ctx.security.grant(target, Role.SUPPORT)
        await ctx.ok(f"Granted SUPPORT to {render.mono(target)}")

    @command(role=Role.OWNER, doc="Revoke elevated access", usage="<reply|user>")
    async def revoke(self, ctx: Context):
        target = await _resolve_target(ctx)
        if target is None:
            await ctx.error("Reply to a user or pass an id/username.")
            return
        await ctx.security.revoke(target)
        await ctx.ok(f"Revoked access for {render.mono(target)}")

    @command(role=Role.SUDO, doc="List privileged users")
    async def perms(self, ctx: Context):
        data = ctx.security.list_privileged()
        rows = {
            "Owner": ", ".join(map(str, data["owner"])) or "-",
            "Sudo": ", ".join(map(str, data["sudo"])) or "-",
            "Support": ", ".join(map(str, data["support"])) or "-",
        }
        await ctx.card("Privileged users", rows, emoji=self.emoji)

    @command(role=Role.SUDO, doc="Show the recent audit log", usage="[count]")
    async def audit(self, ctx: Context):
        limit = int(ctx.args[0]) if ctx.args and ctx.args[0].isdigit() else 15
        entries = await ctx.db.audit_tail(limit)
        if not entries:
            await ctx.respond(render.info("Audit log is empty."))
            return
        lines = [
            f"{render.mono(_fmt_ts(e['ts']))} <b>{render.escape(e['action'])}</b>"
            + (f" — {render.escape(e['detail'])}" if e["detail"] else "")
            for e in entries
        ]
        await ctx.respond(render.title("Audit log", self.emoji) + "\n" + render.divider() + "\n" + "\n".join(lines))

    @command(role=Role.OWNER, doc="List active login sessions")
    async def sessions(self, ctx: Context):
        from pyrogram.raw.functions.account import GetAuthorizations

        auths = await ctx.app.invoke(GetAuthorizations())
        lines = []
        for a in auths.authorizations:
            flag = render.ok("current") if a.current else render.mono("other")
            lines.append(f"{flag} {render.escape(a.device_model)} — {render.escape(a.app_name)} ({render.escape(a.ip)})")
        await ctx.respond(
            render.title(f"Active sessions ({len(lines)})", self.emoji)
            + "\n" + render.divider() + "\n" + "\n".join(lines)
        )

    @command(role=Role.OWNER, doc="Terminate all other login sessions")
    async def killsessions(self, ctx: Context):
        from pyrogram.raw.functions.auth import ResetAuthorizations

        await ctx.app.invoke(ResetAuthorizations())
        await ctx.db.audit("security.killsessions", actor=ctx.sender_id)
        await ctx.ok("Terminated all other sessions.")
