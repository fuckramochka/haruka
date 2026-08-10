"""Native engine shell rendered through the companion bot."""
from __future__ import annotations

import html
from typing import TYPE_CHECKING

from pyrogram import filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from haruka.core.diagnostics import collect_health
from haruka.version import version_string

if TYPE_CHECKING:
    from haruka.core.app import Application
    from haruka.inline.bot import InlineBot


def _uptime(seconds: float) -> str:
    minutes, _ = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h {minutes}m" if days else f"{hours}h {minutes}m"


def _toggle(value: bool) -> str:
    return "ON  ●" if value else "OFF  ○"


def _bar(value: float, maximum: float, width: int = 8) -> str:
    ratio = max(0.0, min(1.0, value / maximum if maximum else 0))
    filled = round(ratio * width)
    return "▰" * filled + "▱" * (width - filled)


class ControlCenter:
    def __init__(self, app: "Application", bot: "InlineBot"):
        self.app = app
        self.bot = bot

    def register(self) -> None:
        self.bot.on("cc:", self._route)
        self.bot.on("ob:", self._onboarding_route)
        self.bot.bot.add_handler(
            MessageHandler(
                self._on_start,
                filters.command("start") & filters.private & self.bot._owner_only(),
            )
        )

    async def _on_start(self, _client, message: Message) -> None:
        if not self.app.db.get("onboarding", "completed", False):
            text, keyboard = self._onboarding_welcome()
        else:
            text, keyboard = self._home()
        await message.reply_text(text, reply_markup=keyboard)

    async def send_to_owner(self) -> None:
        text, keyboard = self._home()
        await self.bot.bot.send_message(
            self.app.security.owner_id,
            text,
            reply_markup=keyboard,
        )

    async def send_onboarding(self, reset: bool = False) -> None:
        if reset:
            await self.app.db.set_many(
                "onboarding",
                {"completed": False, "step": "welcome"},
            )
        text, keyboard = self._onboarding_welcome()
        await self.bot.bot.send_message(
            self.app.security.owner_id,
            text,
            reply_markup=keyboard,
        )

    async def _route(self, query: CallbackQuery) -> None:
        action = (query.data or "")[3:]
        if action == "close":
            await query.message.delete()
            await query.answer("Closed")
            return
        try:
            toast = None
            if action == "refresh":
                page, toast = self._home, "Refreshed"
            elif action.startswith("pref:"):
                key = action.split(":", 1)[1]
                if key == "style":
                    prefs = await self.app.preferences.cycle_style()
                    from haruka.ui.theme import set_theme
                    set_theme(prefs.style)
                else:
                    await self.app.preferences.toggle(key)
                page, toast = self._settings, "Saved"
            elif action.startswith("mod:"):
                name = action.split(":", 1)[1]
                enabled = not self.app.loader.is_module_enabled(name)
                await self.app.loader.set_module_enabled(name, enabled)
                page, toast = self._modules, f"{name}: {'on' if enabled else 'off'}"
            elif action.startswith("cmd:"):
                name = action.split(":", 1)[1]
                enabled = not self.app.loader.is_command_enabled(name)
                await self.app.loader.set_command_enabled(name, enabled)
                page, toast = self._engine, f"{name}: {'on' if enabled else 'off'}"
            else:
                page = {
                    "home": self._home,
                    "engine": self._engine,
                    "mods": self._modules,
                    "settings": self._settings,
                    "diag": self._diagnostics,
                    "sec": self._security,
                }.get(action, self._home)
            text, keyboard = page()
            if query.message is not None:
                await query.message.edit_text(text, reply_markup=keyboard)
            await query.answer(toast)
        except Exception as exc:
            await query.answer(f"{type(exc).__name__}: {exc}"[:180], show_alert=True)

    async def _onboarding_route(self, query: CallbackQuery) -> None:
        action = (query.data or "")[3:]
        await query.answer("Working…" if action.startswith("preset:") else None)
        if action == "language":
            page = self._onboarding_language
        elif action.startswith("lang:"):
            code = action.split(":", 1)[1]
            await self.app.translator.set_language(code)
            await self.app.db.set("onboarding", "step", "presets")
            page = self._onboarding_presets
        elif action == "presets":
            page = self._onboarding_presets
        elif action.startswith("preset:"):
            name = action.split(":", 1)[1]
            await self._install_preset(name)
            await self.app.db.set("onboarding", "preset", name)
            await self.app.db.set("onboarding", "step", "settings")
            page = self._onboarding_settings
        elif action == "skip_presets":
            await self.app.db.set("onboarding", "preset", "skipped")
            page = self._onboarding_settings
        elif action.startswith("theme:"):
            theme = action.split(":", 1)[1]
            await self.app.preferences.set("style", theme)
            from haruka.ui.theme import set_theme
            set_theme(theme)
            page = self._onboarding_settings
        elif action.startswith("prefix:"):
            prefix = action.split(":", 1)[1]
            if prefix not in {".", "!", "/"}:
                prefix = "."
            await self.app.db.set("core", "prefix", prefix)
            page = self._onboarding_settings
        elif action == "finish":
            await self.app.db.set_many(
                "onboarding",
                {"completed": True, "step": "complete", "completed_at": int(__import__('time').time())},
            )
            page = self._onboarding_done
        elif action == "home":
            page = self._home
        else:
            page = self._onboarding_welcome
        text, keyboard = page()
        if query.message is not None:
            await query.message.edit_text(text, reply_markup=keyboard)

    async def _install_preset(self, name: str) -> None:
        from haruka.modules.presets import PRESETS
        from haruka.modules.manager import _download_module

        urls = PRESETS.get(name, [])
        loaded, failed = [], []
        for url in urls:
            try:
                code = await _download_module(url)
                filename = url.rstrip("/").split("/")[-1] or "module.py"
                loaded.extend(await self.app.loader.install_from_source(code, filename))
            except Exception as exc:
                failed.append(f"{filename if 'filename' in locals() else url}: {type(exc).__name__}")
        await self.app.db.set_many(
            "onboarding",
            {"installed_modules": loaded, "failed_modules": failed},
        )

    def _onboarding_welcome(self):
        boot = self.app.db.get("core", "boot_count", 1)
        text = (
            self._header("WELCOME", "One connected setup instead of a box of unrelated commands")
            + "\n\nHaruka will now guide you through the important choices:\n"
            + "<blockquote>1. Interface language\n2. Starter module pack\n"
            + "3. Visual style and defaults\n4. Your Control Center and log channel</blockquote>"
            + f"\nThis is startup <b>#{boot}</b>. The wizard appears only until setup is complete."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Start setup →", callback_data="ob:language")],
            [InlineKeyboardButton("Open dashboard", callback_data="ob:home")],
        ])
        return text, keyboard

    def _onboarding_language(self):
        current = self.app.translator.language
        text = self._header("STEP 1 · LANGUAGE", f"Current language: {current}")
        text += "\n\nChoose the language used by Haruka management surfaces. You can change it later with <code>.lang</code>."
        labels = {"en":"🇬🇧 English", "ru":"🇷🇺 Русский", "uk":"🇺🇦 Українська", "de":"🇩🇪 Deutsch", "fr":"🇫🇷 Français", "es":"🇪🇸 Español", "ja":"🇯🇵 日本語"}
        buttons = [[InlineKeyboardButton(label, callback_data=f"ob:lang:{code}")] for code, label in labels.items()]
        return text, InlineKeyboardMarkup(buttons)

    def _onboarding_presets(self):
        text = self._header("STEP 2 · STARTER PACK", "Choose what Haruka should install for you")
        text += (
            "\n\n<blockquote><b>Fun</b> — quotes and entertainment\n"
            "<b>Chat</b> — moderation and group tools\n"
            "<b>Service</b> — links, files and utilities\n"
            "<b>Downloaders</b> — media download helpers</blockquote>"
            "\nModules are external code. Haruka validates loading, but you should still trust their authors."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎭 Fun", callback_data="ob:preset:fun"), InlineKeyboardButton("💬 Chat", callback_data="ob:preset:chat")],
            [InlineKeyboardButton("🧰 Service", callback_data="ob:preset:service"), InlineKeyboardButton("⬇️ Downloaders", callback_data="ob:preset:downloaders")],
            [InlineKeyboardButton("Skip for now", callback_data="ob:skip_presets")],
        ])
        return text, keyboard

    def _onboarding_settings(self):
        prefs = self.app.preferences.get()
        installed = self.app.db.get("onboarding", "installed_modules", [])
        failed = self.app.db.get("onboarding", "failed_modules", [])
        prefix = html.escape(self.app.db.get("core", "prefix", "."))
        text = self._header("STEP 3 · SETTINGS", "Choose appearance and command prefix")
        text += (
            f"\n\nCurrent style: <code>{prefs.style.upper()}</code>\n"
            f"Current prefix: <code>{prefix}</code>\n"
            f"Installed from preset: <b>{len(installed)}</b>\n"
            f"Could not install: <b>{len(failed)}</b>\n\n"
            "<blockquote>Aurora is balanced. Carbon is denser. Minimal removes visual noise. "
            "The prefix can be changed later with .prefix.</blockquote>"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✦ Aurora", callback_data="ob:theme:aurora"), InlineKeyboardButton("◼ Carbon", callback_data="ob:theme:carbon")],
            [InlineKeyboardButton("○ Minimal", callback_data="ob:theme:minimal")],
            [InlineKeyboardButton("Prefix .", callback_data="ob:prefix:."), InlineKeyboardButton("Prefix !", callback_data="ob:prefix:!")],
            [InlineKeyboardButton("Prefix /", callback_data="ob:prefix:/")],
            [InlineKeyboardButton("Finish setup ✓", callback_data="ob:finish")],
        ])
        return text, keyboard

    def _onboarding_done(self):
        prefix = html.escape(self.app.db.get("core", "prefix", "."))
        log_chat = self.app.db.get("core", "log_chat_id")
        text = self._header("READY", "Haruka is configured and connected")
        text += (
            "\n\n<blockquote>"
            f"<code>{prefix}help</code> — all commands\n"
            f"<code>{prefix}menu</code> — Control Center\n"
            f"<code>{prefix}presets</code> — more module packs\n"
            f"<code>{prefix}settings</code> — current settings\n"
            f"<code>{prefix}diagnostics</code> — health check"
            "</blockquote>"
            f"\nPrivate log channel: <code>{log_chat or 'not available'}</code>\n"
            "The onboarding will not interrupt future starts. Run <code>.quickstart</code> whenever you want it again."
        )
        return text, InlineKeyboardMarkup([[InlineKeyboardButton("Open Control Center", callback_data="ob:home")]])

    def _nav(self, active: str, extra=()) -> InlineKeyboardMarkup:
        def button(label: str, page: str) -> InlineKeyboardButton:
            mark = "• " if page == active else ""
            return InlineKeyboardButton(mark + label, callback_data=f"cc:{page}")

        rows = list(extra)
        rows += [
            [button("Overview", "home"), button("Engine", "engine")],
            [button("Features", "mods"), button("Settings", "settings")],
            [button("Health", "diag"), button("Security", "sec")],
            [
                InlineKeyboardButton("↻ Refresh", callback_data="cc:refresh"),
                InlineKeyboardButton("Close", callback_data="cc:close"),
            ],
        ]
        return InlineKeyboardMarkup(rows)

    def _header(self, section: str, subtitle: str) -> str:
        return (
            f"✦ <b>HARUKA</b>  <code>{version_string()}</code>\n"
            f"<blockquote><b>{html.escape(section)}</b>\n"
            f"{html.escape(subtitle)}</blockquote>"
        )

    def _home(self):
        me = self.app.client.me
        disabled = len(self.app.db.get("core", "disabled_commands", []))
        prefix = html.escape(self.app.db.get("core", "prefix", "."))
        text = self._header("CONTROL CENTER", "The engine is online and ready")
        text += f"\n\n<b>{html.escape(me.first_name)}</b>  ·  <code>{prefix}</code> prefix\n"
        text += f"<code>{_bar(self.app.uptime, 86400)}</code>  {_uptime(self.app.uptime)} uptime\n\n"
        text += (
            f"<b>{len(self.app.loader.modules)}</b> features   "
            f"<b>{len(self.app.loader.command_names)}</b> commands   "
            f"<b>{disabled}</b> paused"
        )
        text += "\n\n<blockquote>Engine-level settings survive updates.</blockquote>"
        return text, self._nav("home")

    def _engine(self):
        disabled = set(self.app.db.get("core", "disabled_commands", []))
        aliases = self.app.db.get("core", "aliases", {})
        text = self._header("ENGINE", "Command routing, gates and runtime policy")
        text += (
            f"\n\n<b>Command bus</b>  {len(self.app.loader.command_names)} routes\n"
            f"<b>Feature gates</b>  {len(disabled)} paused\n"
            f"<b>Aliases</b>  {len(aliases)} active\n"
            f"<b>Watchers</b>  {len(self.app.loader.watchers)} connected\n\n"
        )
        recent = sorted(disabled)[:4]
        text += "<b>Paused commands</b>\n"
        text += (
            "\n".join(f"○ <code>{html.escape(item)}</code>" for item in recent)
            if recent
            else "All command routes are active"
        )
        buttons = [
            [
                InlineKeyboardButton(
                    f"{'○' if name in disabled else '●'} {name}",
                    callback_data=f"cc:cmd:{name}",
                )
            ]
            for name in sorted(self.app.loader.command_names)[:6]
        ]
        return text, self._nav("engine", buttons)

    def _modules(self):
        text = self._header("FEATURES", "Built-in capabilities and loaded extensions") + "\n\n"
        buttons = []
        for name in self.app.loader.module_names():
            loaded = self.app.loader.modules[name]
            enabled = self.app.loader.is_module_enabled(name)
            kind = "core" if loaded.origin == "builtin" else "extension"
            text += (
                f"{'●' if enabled else '○'} <b>{html.escape(name)}</b>  "
                f"<code>{kind}</code>  · {len(loaded.commands)}\n"
            )
            if name != "Modules":
                buttons.append(
                    [
                        InlineKeyboardButton(
                            f"{'●' if enabled else '○'} {name}",
                            callback_data=f"cc:mod:{name}",
                        )
                    ]
                )
        return text, self._nav("mods", buttons[:8])

    def _settings(self):
        prefs = self.app.preferences.get()
        text = self._header("SETTINGS", "Appearance and engine behavior")
        text += (
            f"\n\n<b>Visual skin</b>\n<code>{prefs.style.upper()}</code> — shared UI language\n\n"
            f"<b>Compact help</b>  {_toggle(prefs.compact_help)}\n"
            f"<b>Error details</b>  {_toggle(prefs.reveal_errors)}\n"
            f"<b>Danger confirmations</b>  {_toggle(prefs.confirm_dangerous)}\n"
            f"<b>Quiet unknown commands</b>  {_toggle(prefs.quiet_unknown)}"
        )
        buttons = [
            [InlineKeyboardButton(f"Skin · {prefs.style.title()} ↻", callback_data="cc:pref:style")],
            [InlineKeyboardButton(f"Compact help · {_toggle(prefs.compact_help)}", callback_data="cc:pref:compact_help")],
            [InlineKeyboardButton(f"Error details · {_toggle(prefs.reveal_errors)}", callback_data="cc:pref:reveal_errors")],
            [InlineKeyboardButton(f"Confirm danger · {_toggle(prefs.confirm_dangerous)}", callback_data="cc:pref:confirm_dangerous")],
        ]
        return text, self._nav("settings", buttons)

    def _diagnostics(self):
        health = collect_health(self.app.settings.db_path)
        text = self._header("HEALTH", "Live runtime diagnostics")
        light = "🟢" if health.status == "healthy" else "🟠"
        text += f"\n\n{light} <b>{health.status.upper()}</b>\n\n"
        text += (
            f"RAM  <code>{_bar(health.memory_mb, 1024)}</code>  {health.memory_mb:.1f} MB\n"
            f"CPU  <code>{_bar(health.cpu_percent, 100)}</code>  {health.cpu_percent:.1f}%\n"
            f"DISK <code>{_bar(min(health.disk_free_gb, 20), 20)}</code>  {health.disk_free_gb:.1f} GB free\n\n"
            f"<b>Tasks</b>  {health.tasks}\n"
            f"<b>Database</b>  {health.database_kb:.1f} KiB\n"
            f"<b>Runtime</b>  Python {health.python} · {health.platform}"
        )
        return text, self._nav("diag")

    def _security(self):
        data = self.app.security.list_privileged()
        text = self._header("SECURITY", "Permissions and protected surfaces")
        text += (
            f"\n\n🔐 <b>Owner</b>  <code>{self.app.security.owner_id}</code>\n"
            f"◆ <b>Sudo</b>  {len(data.get('sudo', []))}\n"
            f"◇ <b>Support</b>  {len(data.get('support', []))}\n\n"
            "<blockquote>Service-account protection, rate limits, secret masking "
            "and audit logging are active.</blockquote>"
        )
        return text, self._nav("sec")
