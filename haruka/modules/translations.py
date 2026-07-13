"""Interface localization control.

Brings Heroku-style language switching to Haruka: list every installed pack
(real languages plus meme packs), switch with a command, or pick from an inline
keyboard rendered through the companion bot. All strings themselves are pulled
from the active language pack, so this module is fully localized too.
"""
from __future__ import annotations

from haruka.api import Context, Module, command, render


class Translations(Module):
    name = "Translations"
    description = "Interface language packs and switching"
    emoji = "\N{GLOBE WITH MERIDIANS}"
    author = "haruka"
    version = "1.0.0"

    def _translator(self, ctx: Context):
        return ctx.core.translator

    @command(aliases=["languages", "langs"], doc="List every installed language pack")
    async def langlist(self, ctx: Context) -> None:
        translator = self._translator(ctx)
        current = translator.language
        rows = {}
        for code, label in sorted(translator.available().items()):
            marker = " \N{WHITE HEAVY CHECK MARK}" if code == current else ""
            rows[code] = f"{label}{marker}"
        await ctx.card(translator.t("lang.title"), rows)

    @command(aliases=["translations", "langmenu"], doc="Open the inline language picker")
    async def langpicker(self, ctx: Context) -> None:
        translator = self._translator(ctx)
        bot = ctx.core.inline_bot
        if bot is None or not getattr(bot, "units", None):
            # No companion bot: fall back to the textual list.
            await self.langlist(ctx)
            return

        available = translator.available()

        def _make_handler(code: str):
            async def _handler(query):
                try:
                    await translator.set_language(code)
                except ValueError:
                    await query.answer(translator.t("common.error"), show_alert=True)
                    return
                label = translator.available().get(code, code)
                await query.answer(translator.t("lang.changed", name=label))
                await query.message.edit_text(
                    render.ok(translator.t("lang.changed", name=label))
                )

            return _handler

        codes = sorted(available)
        buttons = []
        row: list = []
        for code in codes:
            row.append((available[code], _make_handler(code)))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)

        _unit, markup = bot.units.form(
            render.title(translator.t("lang.choose")), buttons
        )
        await bot.bot.send_message(
            ctx.core.security.owner_id,
            render.title(translator.t("lang.choose")),
            reply_markup=markup,
        )
        await ctx.ok(translator.t("lang.title"))

    @command(aliases=["setlanguage"], usage="<code>", doc="Switch the interface language pack")
    async def uselang(self, ctx: Context) -> None:
        translator = self._translator(ctx)
        if not ctx.args:
            await self.langlist(ctx)
            return
        code = ctx.args[0].lower()
        try:
            await translator.set_language(code)
        except ValueError as exc:
            await ctx.error(str(exc))
            return
        label = translator.available().get(code, code)
        await ctx.ok(translator.t("lang.changed", name=label))
