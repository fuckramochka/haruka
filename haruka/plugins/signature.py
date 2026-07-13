"""Signature plugin: append a personal footer to every reply the userbot sends.

A clear example of a behaviour plugin — it changes how *all* output looks
without adding any command. Configure the footer text with:

    .plugset Signature text ✨ sent via Haruka

Leave the text empty (the default) to disable the footer while the plugin
stays loaded.
"""
from __future__ import annotations

from haruka.core.plugins import Plugin


class Signature(Plugin):
    name = "Signature"
    description = "Appends a configurable signature to every outgoing message."
    emoji = "\N{LOWER LEFT FOUNTAIN PEN}"
    author = "haruka"
    version = "1.0.0"
    priority = 900  # run late, after other transforms
    options = {"text": "", "only_commands": True}

    async def transform_outgoing(self, text: str, ctx=None) -> str:
        footer = str(self.option("text", "")).strip()
        if not footer:
            return text
        if self.option("only_commands", True) and ctx is None:
            return text
        marker = footer  # rendered as italic HTML
        if marker in text:
            return text
        return f"{text}\n\n<i>{marker}</i>"
