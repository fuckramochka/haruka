# ©️ Codrago, 2024-2030
# This file is a part of Haruka Userbot
# 🌐 https://github.com/coddrago/Heroku
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import logging
import time

from harukatl.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)

_KEY = "notes"


@loader.tds
class HarukaNotesMod(loader.Module):
    """Simple notepad: save, list and delete personal notes"""

    strings = {
        "name": "HarukaNotes",
        "saved": "\ud83d\udcd3 <b>Note #{n} saved.</b>",
        "empty": "\ud83d\udcd3 <b>Your notepad is empty.</b>",
        "no_text": "\ud83d\udeab <b>Provide note text or reply to a message.</b>",
        "list": "\ud83d\udcd3 <b>Your notes ({count}):</b>\n\n{items}",
        "item": "<b>{n}.</b> {text} <i>({date})</i>",
        "deleted": "\ud83d\uddd1 <b>Note #{n} deleted.</b>",
        "bad_index": "\ud83d\udeab <b>No note with index {n}.</b>",
        "need_index": "\ud83d\udeab <b>Provide the note number.</b>",
        "cleared": "\ud83e\uddf9 <b>Cleared {count} note(-s).</b>",
    }

    strings_ru = {
        "saved": "\ud83d\udcd3 <b>\u0417\u0430\u043c\u0435\u0442\u043a\u0430 #{n} \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0430.</b>",
        "empty": "\ud83d\udcd3 <b>\u0411\u043b\u043e\u043a\u043d\u043e\u0442 \u043f\u0443\u0441\u0442.</b>",
        "no_text": "\ud83d\udeab <b>\u0423\u043a\u0430\u0436\u0438 \u0442\u0435\u043a\u0441\u0442 \u0438\u043b\u0438 \u043e\u0442\u0432\u0435\u0442\u044c \u043d\u0430 \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435.</b>",
        "list": "\ud83d\udcd3 <b>\u0422\u0432\u043e\u0438 \u0437\u0430\u043c\u0435\u0442\u043a\u0438 ({count}):</b>\n\n{items}",
        "item": "<b>{n}.</b> {text} <i>({date})</i>",
        "deleted": "\ud83d\uddd1 <b>\u0417\u0430\u043c\u0435\u0442\u043a\u0430 #{n} \u0443\u0434\u0430\u043b\u0435\u043d\u0430.</b>",
        "bad_index": "\ud83d\udeab <b>\u041d\u0435\u0442 \u0437\u0430\u043c\u0435\u0442\u043a\u0438 \u0441 \u043d\u043e\u043c\u0435\u0440\u043e\u043c {n}.</b>",
        "need_index": "\ud83d\udeab <b>\u0423\u043a\u0430\u0436\u0438 \u043d\u043e\u043c\u0435\u0440 \u0437\u0430\u043c\u0435\u0442\u043a\u0438.</b>",
        "cleared": "\ud83e\uddf9 <b>\u0423\u0434\u0430\u043b\u0435\u043d\u043e \u0437\u0430\u043c\u0435\u0442\u043e\u043a: {count}.</b>",
    }

    def _load(self) -> list:
        notes = self.get(_KEY, [])
        return notes if isinstance(notes, list) else []

    def _save(self, notes: list):
        self.set(_KEY, notes)

    @loader.command(ru_doc="<\u0442\u0435\u043a\u0441\u0442> \u2014 \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u0437\u0430\u043c\u0435\u0442\u043a\u0443 (\u0438\u043b\u0438 \u043e\u0442\u0432\u0435\u0442\u043e\u043c)")
    async def note(self, message: Message):
        """<text> — save a note (or reply to a message)"""
        text = utils.get_args_raw(message)
        if not text:
            reply = await message.get_reply_message()
            if reply and reply.raw_text:
                text = reply.raw_text
        if not text:
            await utils.answer(message, self.strings("no_text"))
            return
        notes = self._load()
        notes.append({"text": text, "date": time.strftime("%Y-%m-%d %H:%M")})
        self._save(notes)
        await utils.answer(message, self.strings("saved").format(n=len(notes)))

    @loader.command(ru_doc="\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u044c \u0432\u0441\u0435 \u0437\u0430\u043c\u0435\u0442\u043a\u0438")
    async def notes(self, message: Message):
        """Show all saved notes"""
        notes = self._load()
        if not notes:
            await utils.answer(message, self.strings("empty"))
            return
        items = "\n".join(
            self.strings("item").format(
                n=i + 1,
                text=utils.escape_html(
                    (note.get("text", "")[:200] + "\u2026")
                    if len(note.get("text", "")) > 200
                    else note.get("text", "")
                ),
                date=note.get("date", ""),
            )
            for i, note in enumerate(notes)
        )
        await utils.answer(
            message, self.strings("list").format(count=len(notes), items=items)
        )

    @loader.command(ru_doc="<\u2116> \u2014 \u0443\u0434\u0430\u043b\u0438\u0442\u044c \u0437\u0430\u043c\u0435\u0442\u043a\u0443")
    async def delnote(self, message: Message):
        """<n> — delete a note by its number"""
        arg = utils.get_args_raw(message)
        if not arg.strip().isdigit():
            await utils.answer(message, self.strings("need_index"))
            return
        idx = int(arg.strip())
        notes = self._load()
        if idx < 1 or idx > len(notes):
            await utils.answer(message, self.strings("bad_index").format(n=idx))
            return
        notes.pop(idx - 1)
        self._save(notes)
        await utils.answer(message, self.strings("deleted").format(n=idx))

    @loader.command(ru_doc="\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u0432\u0435\u0441\u044c \u0431\u043b\u043e\u043a\u043d\u043e\u0442")
    async def clearnotes(self, message: Message):
        """Delete all notes"""
        count = len(self._load())
        self._save([])
        await utils.answer(message, self.strings("cleared").format(count=count))
