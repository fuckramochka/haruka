# ©️ Haruka contributors, 2024-2026
# This file is a part of Haruka Userbot
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

"""Quick personal notes stored in the internal database"""

import logging

from telethon.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)


class NotesMod(loader.Module):
    """Save and retrieve short text notes by name"""

    strings = {"name": "Notes"}

    @loader.command()
    async def note(self, message: Message):
        """<name> [text] — save a note, or show it if no text given"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(
                message,
                "✏️ <b>Usage:</b> <code>.note name text</code> to save,"
                " <code>.note name</code> to read",
            )
            return

        name, _, text = args.partition(" ")
        notes = self.get("notes", {})

        if not text:
            value = notes.get(name.lower())
            if value is None:
                await utils.answer(message, f"❔ <b>Note</b> <code>{name}</code> not found")
                return

            await utils.answer(
                message,
                f"📒 <b>NOTE:</b> <code>{utils.escape_html(name)}</code>\n\n{value}",
            )
            return

        notes[name.lower()] = text
        self.set("notes", notes)
        await utils.answer(message, f"✅ <b>Saved note</b> <code>{utils.escape_html(name)}</code>")

    @loader.command()
    async def notes(self, message: Message):
        """List all saved notes"""
        notes = self.get("notes", {})
        if not notes:
            await utils.answer(message, "📭 <b>No notes saved yet.</b>")
            return

        lines = "\n".join(
            f"• <code>{utils.escape_html(name)}</code> — {len(body)} chars"
            for name, body in sorted(notes.items())
        )
        await utils.answer(message, f"📒 <b>Your notes ({len(notes)}):</b>\n{lines}")

    @loader.command()
    async def delnote(self, message: Message):
        """<name> — delete a note"""
        name = utils.get_args_raw(message).strip()
        notes = self.get("notes", {})

        if name.lower() not in notes:
            await utils.answer(message, f"❔ <b>Note</b> <code>{name}</code> not found")
            return

        del notes[name.lower()]
        self.set("notes", notes)
        await utils.answer(message, f"🗑 <b>Deleted note</b> <code>{utils.escape_html(name)}</code>")
