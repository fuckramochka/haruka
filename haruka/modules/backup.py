"""Encrypted database backups.

``.backup <passphrase>`` sends an encrypted snapshot of the settings database
to Saved Messages. ``.restore <passphrase>`` (as a reply to a backup file)
decrypts and imports it. Files use authenticated encryption (scrypt + Fernet),
so a wrong passphrase fails loudly instead of importing garbage.
"""

from __future__ import annotations

import io
import json
import time

from haruka.api import Context, Module, Role, command, render
from haruka.core.crypto import BackupCryptoError, decrypt, encrypt


class Backup(Module):
    name = "Backup"
    description = "Encrypted database backups"
    emoji = "\N{FLOPPY DISK}"

    @command(aliases=["backupdb", "backupall"], role=Role.OWNER, doc="Send an encrypted DB backup to Saved Messages", usage="<passphrase>")
    async def backup(self, ctx: Context):
        if not ctx.args_raw:
            await ctx.error("Usage: <code>.backup &lt;passphrase&gt;</code>")
            return
        await ctx.loading("Encrypting backup...")

        payload = json.dumps(
            {"format": 1, "created_at": int(time.time()), "data": ctx.db.export_all()},
            ensure_ascii=False,
        ).encode("utf-8")
        blob = encrypt(payload, ctx.args_raw.strip())

        file = io.BytesIO(blob)
        file.name = f"haruka-backup-{time.strftime('%Y%m%d-%H%M%S')}.hrk"
        await ctx.app.send_document(
            "me",
            file,
            caption=render.title("Encrypted Haruka backup", self.emoji),
        )
        await ctx.ok("Backup sent to <b>Saved Messages</b>. Keep the passphrase safe — it cannot be recovered.")

    @command(aliases=["restoredb", "restoreall"], role=Role.OWNER, doc="Restore a backup (reply to a .hrk file)", usage="<passphrase>")
    async def restore(self, ctx: Context):
        if not ctx.args_raw:
            await ctx.error("Usage: reply to a backup file with <code>.restore &lt;passphrase&gt;</code>")
            return
        reply = ctx.reply
        if reply is None or not reply.document:
            await ctx.error("Reply to a <code>.hrk</code> backup file.")
            return

        await ctx.loading("Downloading and decrypting...")
        raw = await ctx.app.download_media(reply, in_memory=True)
        if isinstance(raw, io.BytesIO):
            blob = bytes(raw.getbuffer())
        else:
            with open(raw, "rb") as backup_file:
                blob = backup_file.read()
        if len(blob) > 50 * 1024 * 1024:
            await ctx.error("Backup is larger than the 50 MiB safety limit.")
            return

        try:
            payload = json.loads(decrypt(blob, ctx.args_raw.strip()))
        except BackupCryptoError as exc:
            await ctx.error(render.escape(str(exc)))
            return
        except (json.JSONDecodeError, UnicodeDecodeError):
            await ctx.error("Backup file is corrupted.")
            return

        count = await ctx.db.import_all(payload.get("data", {}))
        created = time.strftime("%Y-%m-%d %H:%M", time.localtime(payload.get("created_at", 0)))
        await ctx.card(
            "Backup restored",
            {"Entries": count, "Created": created},
        )
