# ©️ Dan Gazizullin, 2021-2023
# This file is a part of Hikka Userbot
# 🌐 https://github.com/hikariatama/Hikka
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

# ©️ Codrago, 2024-2025
# This file is a part of Haruka Userbot
# 🌐 https://github.com/fuckramochka/haruka
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import asyncio
import contextlib
import logging
import re
import os

from harukatl.errors.rpcerrorlist import YouBlockedUserError
from harukatl.tl.functions.contacts import UnblockRequest

from .. import utils
from .._internal import fw_protect
from .types import InlineUnit

logger = logging.getLogger(__name__)


class TokenObtainment(InlineUnit):
    async def _notify_inline_bot_failure(self, reason: str):
        """Notify owner when inline bot creation/lookup failed."""
        owner = getattr(self._client, "tg_id", None)
        if not owner:
            return

        text = (
            "⚠️ <b>Haruka couldn't create/find inline bot.</b>\n\n"
            f"<b>Reason:</b> <code>{utils.escape_html(reason)}</code>\n\n"
            "<b>What to do:</b>\n"
            "1) Open <code>@BotFather</code> and check available bots\n"
            "2) Set your bot manually with <code>.ch_haruka_bot usernamebot</code>\n"
            "3) If you already have a token, set it with <code>.ch_bot_token 123:ABC</code>\n"
            "4) Restart Haruka"
        )

        with contextlib.suppress(Exception):
            await self._client.send_message(owner, text)

    async def _create_bot(self):
        logger.info("User doesn't have bot, attempting creating new one")
        async with self._client.conversation("@BotFather", exclusive=False) as conv:
            await fw_protect()
            m = await conv.send_message("/newbot")
            r = await conv.get_response()

            logger.debug(">> %s", m.raw_text)
            logger.debug("<< %s", r.raw_text)

            if "20" in r.raw_text:
                await self._notify_inline_bot_failure(
                    "BotFather limit reached (20 bots per account)"
                )
                return False

            await fw_protect()

            await m.delete()
            await r.delete()

            if self._db.get("haruka.inline", "custom_bot", False):
                username = self._db.get("haruka.inline", "custom_bot").strip("@")
                username = f"@{username}"
                try:
                    await self._client.get_entity(username)
                except ValueError:
                    pass
                else:
                    uid = utils.rand(6)
                    username = f"@haruka_{uid}_bot"
            else:
                uid = utils.rand(6)
                username = f"@haruka_{uid}_bot"

            for msg in [
                f"🪐 Haruka userbot"[:64],
                username,
                "/setuserpic",
                username,
            ]:
                await fw_protect()
                m = await conv.send_message(msg)
                r = await conv.get_response()

                logger.debug(">> %s", m.raw_text)
                logger.debug("<< %s", r.raw_text)

                await fw_protect()
                await m.delete()
                await r.delete()

            try:
                await fw_protect()
                from .. import main

                m = await conv.send_file(f"{os.getcwd()}/assets/haruka.png")
                r = await conv.get_response()

                logger.debug(">> <Photo>")
                logger.debug("<< %s", r.raw_text)
            except Exception:
                await fw_protect()
                m = await conv.send_message("/cancel")
                r = await conv.get_response()

                logger.debug(">> %s", m.raw_text)
                logger.debug("<< %s", r.raw_text)

            await fw_protect()

            await m.delete()
            await r.delete()

        result = await self._assert_token(False)
        if not result:
            await self._notify_inline_bot_failure(
                "Bot was created, but token could not be obtained from BotFather"
            )
        return result

    async def _assert_token(
        self,
        create_new_if_needed: bool = True,
        revoke_token: bool = False,
    ) -> bool:
        if self._token:
            return True

        logger.info("Bot token not found in db, attempting search in BotFather")

        if not self._db.get(__name__, "no_mute", False):
            await utils.dnd(
                self._client,
                await self._client.get_entity("@BotFather"),
                True,
            )
            self._db.set(__name__, "no_mute", True)

        async with self._client.conversation("@BotFather", exclusive=False) as conv:
            try:
                await fw_protect()
                m = await conv.send_message("/token")
            except YouBlockedUserError:
                await self._client(UnblockRequest(id="@BotFather"))
                await fw_protect()
                m = await conv.send_message("/token")

            r = await conv.get_response()

            logger.debug(">> %s", m.raw_text)
            logger.debug("<< %s", r.raw_text)

            await fw_protect()

            await m.delete()
            await r.delete()

            if not hasattr(r, "reply_markup") or not hasattr(r.reply_markup, "rows"):
                await conv.cancel_all()

                if create_new_if_needed:
                    return await self._create_bot()

                await self._notify_inline_bot_failure(
                    "BotFather didn't return bot list (/token has no buttons)"
                )
                return False

            for row in r.reply_markup.rows:
                for button in row.buttons:
                    if self._db.get(
                        "haruka.inline", "custom_bot", False
                    ) and self._db.get(
                        "haruka.inline", "custom_bot", False
                    ) != button.text.strip("@"):
                        continue

                    if not self._db.get(
                        "haruka.inline",
                        "custom_bot",
                        False,
                    ) and not re.search(r"@haruka_[0-9a-zA-Z]{6}_bot", button.text):
                        continue

                    await fw_protect()

                    m = await conv.send_message(button.text)
                    r = await conv.get_response()

                    logger.debug(">> %s", m.raw_text)
                    logger.debug("<< %s", r.raw_text)

                    if revoke_token:
                        await fw_protect()
                        await m.delete()
                        await r.delete()

                        await fw_protect()

                        m = await conv.send_message("/revoke")
                        r = await conv.get_response()

                        logger.debug(">> %s", m.raw_text)
                        logger.debug("<< %s", r.raw_text)

                        await fw_protect()

                        await m.delete()
                        await r.delete()

                        await fw_protect()

                        m = await conv.send_message(button.text)
                        r = await conv.get_response()

                        logger.debug(">> %s", m.raw_text)
                        logger.debug("<< %s", r.raw_text)

                    token = r.raw_text.splitlines()[1]

                    self._db.set("haruka.inline", "bot_token", token)
                    self._token = token

                    await fw_protect()

                    await m.delete()
                    await r.delete()

                    for msg in [
                        "/setinline",
                        button.text,
                        "user@haruka:~$",
                        "/setinlinefeedback",
                        button.text,
                        "Enabled",
                    ]:
                        await fw_protect()
                        m = await conv.send_message(msg)
                        r = await conv.get_response()

                        logger.debug(">> %s", m.raw_text)
                        logger.debug("<< %s", r.raw_text)

                        await fw_protect()

                        await m.delete()
                        await r.delete()


                    return True

        if create_new_if_needed:
            result = await self._create_bot()
            if not result:
                await self._notify_inline_bot_failure(
                    "Automatic inline bot creation failed"
                )
            return result

        await self._notify_inline_bot_failure(
            "Inline bot token was not found in BotFather list"
        )
        return False

    async def _reassert_token(self):
        is_token_asserted = await self._assert_token(revoke_token=True)
        if not is_token_asserted:
            self.init_complete = False
        else:
            await self.register_manager(ignore_token_checks=True)

    async def _dp_revoke_token(self, already_initialised: bool = True):
        if already_initialised:
            await self._stop()
            logger.error("Got polling conflict. Attempting token revocation...")

        self._db.set("haruka.inline", "bot_token", None)
        self._token = None
        if already_initialised:
            asyncio.ensure_future(self._reassert_token())
        else:
            return await self._reassert_token()
