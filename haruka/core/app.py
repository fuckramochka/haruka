"""Application: composition root and lifecycle.

Wires everything together (client, db, loader, dispatcher, inline bot,
automation engine) and owns startup / graceful shutdown. This is the only
place where the object graph is constructed.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from haruka.core.client import HarukaClient
from haruka.core.config import Settings
from haruka.core.database import Database
from haruka.core.dispatcher import Dispatcher
from haruka.core.loader import Loader
from haruka.core.security import SecurityManager
from haruka.version import version_string

logger = logging.getLogger(__name__)


class Application:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings.from_env()
        self.started_at: float = 0.0

        self.db = Database(self.settings.db_path)
        self.client: Optional[HarukaClient] = None
        self.security: Optional[SecurityManager] = None
        self.loader: Optional[Loader] = None
        self.dispatcher: Optional[Dispatcher] = None
        self.inline_bot = None
        self.automation = None
        self.ai = None
        self.preferences = None
        self.translator = None
        self.plugins = None
        self.web = None
        self.telegram_log_handler = None
        self._stopped = False

    @property
    def uptime(self) -> float:
        return time.time() - self.started_at if self.started_at else 0.0

    # -- startup -----------------------------------------------------------

    async def start(self) -> None:
        self._stopped = False
        logger.info("Starting %s", version_string())
        self.started_at = time.time()

        await self.db.connect()
        boot_count = int(self.db.get("core", "boot_count", 0)) + 1
        await self.db.set_many(
            "core",
            {"boot_count": boot_count, "last_start_at": int(time.time())},
        )
        from haruka.core.preferences import PreferenceStore

        self.preferences = PreferenceStore(self.db)
        from haruka.i18n import Translator
        self.translator = Translator(self.db)

        # One-shot import from a legacy JSON database, if present.
        from haruka.compat.migrate import migrate_legacy_db

        await migrate_legacy_db(self.db, self.settings.data_dir)

        # Resolve API credentials and login entirely through the browser.
        api_id = self.settings.api_id or self.db.get("core", "api_id")
        api_hash = self.settings.api_hash or self.db.get("core", "api_hash")
        from haruka.web.onboarding import ensure_browser_login

        api_id, api_hash = await ensure_browser_login(
            self.settings.session_name, self.settings.data_dir, api_id, api_hash
        )
        await self.db.set_many("core", {"api_id": api_id, "api_hash": api_hash})

        self.client = HarukaClient(
            session_name=self.settings.session_name,
            api_id=api_id,
            api_hash=api_hash,
            workdir=self.settings.data_dir,
        )
        await self.client.start()

        self.security = SecurityManager(self.db)
        self.security.set_owner(self.client.me.id)

        self.loader = Loader(self.client, self.db, self.settings)
        self.loader.app_ref = self  # modules can reach uptime/restart via loader

        self.dispatcher = Dispatcher(self.client, self.db, self.loader, self.security)
        self.dispatcher.install()

        # Inline bot (Control Center) is optional: needs a bot token.
        await self._start_inline_bot()

        await self.loader.load_builtins()
        await self.loader.load_user_modules()

        # Behaviour plugins: hook the engine lifecycle to customise how the
        # userbot itself behaves (distinct from command modules).
        from haruka.core.plugins import PluginManager

        self.plugins = PluginManager(self, self.db)
        await self.plugins.load_builtins()
        await self.plugins.load_user_plugins(self.settings.plugins_dir)
        self.dispatcher.plugins = self.plugins

        await self._finish_startup_experience()

        # Automation engine (triggers + scheduler).
        from haruka.automation.engine import AutomationEngine

        self.automation = AutomationEngine(self)
        await self.automation.start()

        # AI provider (lazy: only does network I/O when a command uses it).
        from haruka.ai.provider import AIProvider

        self.ai = AIProvider(self.db)

        if self.settings.web_enabled:
            from haruka.web.server import WebServer
            self.web = WebServer(
                self,
                self.settings.web_host,
                self.settings.web_port,
                self.db.get("core", "web_token"),
                self.settings.web_open_browser,
            )
            await self.web.start()
            await self.db.set("core", "web_token", self.web.token)
            logger.info("Web dashboard: http://%s:%s/?token=%s", self.settings.web_host, self.settings.web_port, self.web.token)

        await self.db.audit("core.start", version_string())
        logger.info("Haruka is up. Prefix: '%s'", self.db.get("core", "prefix", "."))

    async def _start_inline_bot(self) -> None:
        from haruka.inline.provision import ensure_inline_bot_token
        from haruka.inline.bot import InlineBot

        token = self.db.get("core", "inline_bot_token")
        auto_created = False
        username = self.db.get("core", "inline_bot_username")
        if not token:
            token, username, auto_created = await ensure_inline_bot_token(self)
            if username:
                await self.db.set("core", "inline_bot_username", username)
            if not token:
                logger.info("No inline bot token set — automatic provisioning failed. "
                            "Set one with .setbot or open the web panel.")
                return

        for attempt in range(2):
            try:
                self.inline_bot = InlineBot(self, token)
                await self.inline_bot.start()
                self.loader.bot = self.inline_bot
                await self.db.set("core", "inline_bot_username", self.inline_bot.username)
                for loaded in self.loader.modules.values():
                    loaded.instance.bot = self.inline_bot
                # User-facing onboarding starts only after every module has loaded.
                return
            except Exception:
                logger.exception("Inline bot failed to start")
                self.inline_bot = None
                await self.db.set_many(
                    "core",
                    {
                        "inline_bot_token": None,
                        "inline_bot_username": None,
                        "inline_bootstrapped": False,
                    },
                )
                if attempt == 0:
                    token, username, auto_created = await ensure_inline_bot_token(self)
                    if username:
                        await self.db.set("core", "inline_bot_username", username)
                    if not token:
                        break
        logger.info("Continuing without inline bot")

    async def _finish_startup_experience(self) -> None:
        """Connect logs, onboarding and repeat-start summaries into one flow."""
        from haruka.runtime_logging import ensure_log_chat, install_telegram_logging

        log_chat_id = None
        try:
            log_chat_id = await ensure_log_chat(self)
            if log_chat_id is not None:
                install_telegram_logging(self, log_chat_id)
        except Exception:
            logger.exception("Could not initialise the Haruka log channel")

        boot_count = int(self.db.get("core", "boot_count", 1))
        completed = bool(self.db.get("onboarding", "completed", False))
        if self.inline_bot is not None:
            try:
                if not completed:
                    await self.inline_bot.bootstrap_owner(open_panel=False)
                    await self.inline_bot.control.send_onboarding(reset=False)
                elif not self.db.get("core", "inline_bootstrapped", False):
                    await self.inline_bot.bootstrap_owner(open_panel=True)
                await self.db.set("core", "inline_bootstrapped", True)
            except Exception:
                logger.exception("Could not open the startup experience; engine will continue")

        if log_chat_id is not None:
            try:
                await self.client.app.send_message(
                    log_chat_id,
                    "✅ <b>Haruka started</b>\n"
                    f"Startup: <b>#{boot_count}</b>\n"
                    f"Version: <code>{version_string()}</code>\n"
                    f"Modules: <b>{len(self.loader.modules)}</b>\n"
                    f"Commands: <b>{len(self.loader.command_names)}</b>\n"
                    f"Onboarding: <b>{'complete' if completed else 'waiting for user'}</b>",
                )
            except Exception:
                logger.exception("Could not write startup summary to the log channel")

    # -- shutdown / restart --------------------------------------------------

    async def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        logger.info("Shutting down...")
        if self.automation is not None:
            await self.automation.stop()
        if self.web is not None:
            await self.web.stop()
        if self.dispatcher is not None:
            await self.dispatcher.stop()
        if self.plugins is not None:
            await self.plugins.shutdown()
        if self.loader is not None:
            await self.loader.shutdown()
        if self.inline_bot is not None:
            await self.inline_bot.stop()
        if self.telegram_log_handler is not None:
            logging.getLogger().removeHandler(self.telegram_log_handler)
            self.telegram_log_handler = None
        if self.client is not None:
            await self.client.stop()
        await self.db.audit("core.stop")
        await self.db.close()

    async def restart(self) -> None:
        """Gracefully stop, then re-exec the current process in place."""
        import os
        import sys

        await self.db.audit("core.restart")
        await self.stop()
        os.execv(sys.executable, [sys.executable, "-m", "haruka", *sys.argv[1:]])

    async def run_forever(self) -> None:
        stop_event = asyncio.Event()
        try:
            await self.start()
            await stop_event.wait()
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            await self.stop()
