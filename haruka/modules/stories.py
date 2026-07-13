"""Stories: post, view and save Telegram Stories.

Stories are a Kurigram-native capability (Pyrogram core does not expose them).
Different Kurigram builds name the client methods slightly differently, so we
resolve them defensively at call time and degrade with a friendly message when
the running build lacks a method — never crashing the dispatcher.
"""
from __future__ import annotations

from haruka.api import Context, Module, command, render


class Stories(Module):
    name = "Stories"
    description = "Post, view and save Telegram Stories."
    emoji = "\U0001f4f8"  # camera

    async def _call(self, ctx: Context, names: tuple[str, ...], *args, **kwargs):
        """Invoke the first available Kurigram client method from ``names``."""
        for name in names:
            fn = getattr(ctx.app, name, None)
            if callable(fn):
                return await fn(*args, **kwargs)
        raise AttributeError(
            "This Kurigram build does not support stories ("
            + ", ".join(names)
            + "). Update Kurigram to use this command."
        )

    @command(aliases=["poststory"], usage="[caption]", doc="Post a replied photo/video as your Story.")
    async def story(self, ctx: Context):
        media = ctx.reply
        if media is None or not (media.photo or media.video):
            await ctx.respond(render.info("Reply to a photo or video to post it as a Story."))
            return
        caption = ctx.args_raw.strip()
        await ctx.loading("Posting story...")
        try:
            file = await ctx.app.download_media(media, in_memory=True)
            kwargs = {"caption": caption} if caption else {}
            if media.video:
                await self._call(ctx, ("send_story",), video=file, **kwargs)
            else:
                await self._call(ctx, ("send_story",), photo=file, **kwargs)
        except Exception as exc:  # noqa: BLE001 - report, never crash
            await ctx.error(f"Could not post story: {render.escape(exc)}")
            return
        await ctx.ok("Story posted.")

    @command(aliases=["viewstories"], usage="[@user]", doc="List a user's active Stories (default: yourself).")
    async def stories(self, ctx: Context):
        if ctx.args:
            target = ctx.args[0]
        elif ctx.reply is not None and ctx.reply.from_user:
            target = ctx.reply.from_user.id
        else:
            target = "me"
        await ctx.loading("Fetching stories...")
        try:
            result = await self._call(ctx, ("get_peer_stories", "get_chat_stories"), target)
        except Exception as exc:  # noqa: BLE001
            await ctx.error(f"Stories unavailable: {render.escape(exc)}")
            return
        items = getattr(result, "stories", result) or []
        if not isinstance(items, (list, tuple)):
            items = [items]
        if not items:
            await ctx.respond(render.info("No active stories found."))
            return
        rows = {}
        for st in items:
            sid = getattr(st, "id", "?")
            cap = (getattr(st, "caption", "") or "").strip() or "(no caption)"
            rows[f"#{sid}"] = cap[:60]
        await ctx.card(f"Stories · {render.escape(target)}", rows, emoji=self.emoji)

    @command(usage="<@user> <id>", doc="Download a specific Story into this chat.")
    async def savestory(self, ctx: Context):
        if len(ctx.args) < 2 or not ctx.args[1].lstrip("-").isdigit():
            await ctx.respond(render.info("Usage: <code>.savestory @user 123</code>"))
            return
        who, story_id = ctx.args[0], int(ctx.args[1])
        await ctx.loading("Downloading story...")
        try:
            result = await self._call(ctx, ("get_stories",), who, [story_id])
            story = result[0] if isinstance(result, (list, tuple)) else result
            file = await ctx.app.download_media(story, in_memory=True)
            await ctx.app.send_document(ctx.chat_id, file)
            await ctx.delete()
        except Exception as exc:  # noqa: BLE001
            await ctx.error(f"Could not save story: {render.escape(exc)}")
