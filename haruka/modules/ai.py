"""AI commands: ask, summarize, rewrite, translate — provider-agnostic."""

from __future__ import annotations

from haruka.ai.provider import AIError
from haruka.api import Context, Module, command
from haruka.ui import render

_MAX_CHARS = 6000  # keep prompts sane for context windows


class AI(Module):
    """Chat-completion helpers backed by any OpenAI-compatible endpoint."""

    name = "AI"
    emoji = "\U0001f9e0"

    def _provider(self, ctx: Context):
        core = ctx.core
        return core.ai if core else None

    async def _run(self, ctx: Context, prompt: str, system: str) -> None:
        provider = self._provider(ctx)
        if provider is None:
            await ctx.error("AI provider is not initialised.")
            return
        await ctx.loading("Thinking...")
        try:
            answer = await provider.chat(prompt[:_MAX_CHARS], system=system)
        except AIError as exc:
            await ctx.error(str(exc))
            return
        await ctx.respond(
            f"{render.title('AI', emoji=self.emoji)}\n{render.divider()}\n{render.escape(answer)}"
        )

    @command("ask", usage="<question>", doc="Ask the AI anything.")
    async def ask_cmd(self, ctx: Context) -> None:
        prompt = ctx.args_raw.strip()
        replied = await ctx.reply_text_or_none()
        if replied and prompt:
            prompt = f"{prompt}\n\nContext:\n{replied}"
        elif replied and not prompt:
            prompt = replied
        if not prompt:
            await ctx.respond(render.info("Usage: <code>.ask your question</code>"))
            return
        await self._run(
            ctx, prompt,
            system="You are a concise, helpful assistant inside a Telegram userbot. "
                   "Answer directly. Use short paragraphs.",
        )

    @command("summarize", aliases=["sum"], doc="Summarize the replied message.")
    async def summarize_cmd(self, ctx: Context) -> None:
        text = await ctx.reply_text_or_none() or ctx.args_raw.strip()
        if not text:
            await ctx.respond(render.info("Reply to a message or pass text to summarize."))
            return
        await self._run(
            ctx, text,
            system="Summarize the following into 3-5 crisp bullet points. "
                   "Preserve key facts, names and numbers.",
        )

    @command("summ", aliases=["tldr"], usage="[count]", doc="Summarize the last N messages in this chat.")
    async def summ_cmd(self, ctx: Context) -> None:
        provider = self._provider(ctx)
        if provider is None:
            await ctx.error("AI provider is not initialised.")
            return
        count = 40
        if ctx.args and ctx.args[0].isdigit():
            count = max(1, min(200, int(ctx.args[0])))
        await ctx.loading(f"Reading the last {count} messages...")
        lines: list[str] = []
        try:
            async for msg in ctx.app.get_chat_history(ctx.chat_id, limit=count):
                body = msg.text or msg.caption
                if not body:
                    continue
                who = msg.from_user.first_name if msg.from_user else "?"
                lines.append(f"{who}: {body}")
        except Exception as exc:  # noqa: BLE001
            await ctx.error(f"Could not read chat history: {render.escape(exc)}")
            return
        lines.reverse()  # oldest-first reads better for a summary
        convo = "\n".join(lines)
        if not convo.strip():
            await ctx.respond(render.info("Nothing to summarize in this chat."))
            return
        await self._run(
            ctx, convo,
            system="You are summarizing a Telegram chat. Produce a short TL;DR as "
                   "3-6 bullet points capturing decisions, questions and action items. "
                   "Attribute important points to who said them when it matters.",
        )

    @command("rewrite", usage="[tone]", doc="Rewrite the replied message (optional tone).")
    async def rewrite_cmd(self, ctx: Context) -> None:
        text = await ctx.reply_text_or_none()
        if not text:
            await ctx.respond(render.info("Reply to a message you want rewritten."))
            return
        tone = ctx.args_raw.strip() or "clear and natural"
        await self._run(
            ctx, text,
            system=f"Rewrite the user's message to be {tone}. "
                   "Return only the rewritten text, no preamble.",
        )

    @command("translate", aliases=["tr"], usage="<lang>", doc="Translate replied text to <lang>.")
    async def translate_cmd(self, ctx: Context) -> None:
        text = await ctx.reply_text_or_none()
        args = ctx.args
        if not text or not args:
            await ctx.respond(render.info(
                "Reply to a message and specify a target language: <code>.tr english</code>"
            ))
            return
        lang = args[0]
        await self._run(
            ctx, text,
            system=f"Translate the user's message into {lang}. "
                   "Return only the translation, preserving formatting.",
        )

    @command(
        "aiconfig",
        usage="[key|url|model] [value]",
        doc="Show or change AI settings. Protect the local Haruka data directory.",
    )
    async def aiconfig_cmd(self, ctx: Context) -> None:
        provider = self._provider(ctx)
        if provider is None:
            await ctx.error("AI provider is not initialised.")
            return

        args = ctx.args
        if not args:
            await ctx.card("AI configuration", {
                "Endpoint": provider.base_url,
                "Model": provider.model,
                "API key": "set" if provider.api_key else "not set",
                "Status": "ready" if provider.is_configured else "needs a key",
            })
            return

        field, value = args[0].lower(), ctx.args_raw.split(maxsplit=1)[1:]
        value = value[0].strip() if value else ""
        mapping = {"key": "api_key", "url": "base_url", "model": "model"}
        if field not in mapping or not value:
            await ctx.respond(render.info(
                "Usage: <code>.aiconfig key sk-...</code>, "
                "<code>.aiconfig url https://...</code>, "
                "<code>.aiconfig model gpt-4o-mini</code>"
            ))
            return

        await ctx.db.set("ai", mapping[field], value)
        await ctx.delete()  # never leave the raw key visible in chat
