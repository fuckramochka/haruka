"""Universal inline configuration center inspired by Heroku's configurator."""
from __future__ import annotations

import html
import json
from dataclasses import dataclass
from typing import Any

from pyrogram import filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message


@dataclass(frozen=True)
class EngineField:
    group: str
    key: str
    label: str
    default: Any
    doc: str
    secret: bool = False


ENGINE_FIELDS = (
    EngineField("core", "prefix", "Command prefix", ".", "1–3 characters before commands."),
    EngineField("core", "language", "Language", "en", "en, ru, uk, de, fr, es or ja."),
    EngineField("core", "inline_bot_token", "Companion bot token", None, "BotFather token. Hidden in the UI.", True),
    EngineField("preferences", "style", "Visual style", "aurora", "aurora, carbon or minimal."),
    EngineField("preferences", "compact_help", "Compact help", False, "Use the compact command atlas."),
    EngineField("preferences", "reveal_errors", "Error details", False, "Show traceback details in command errors."),
    EngineField("preferences", "confirm_dangerous", "Danger confirmations", True, "Require confirmation for dangerous actions."),
    EngineField("preferences", "quiet_unknown", "Quiet unknown commands", False, "Hide suggestions for unknown commands."),
    EngineField("modules", "repos", "Additional repositories", [], "JSON list of Heroku-compatible full.txt repositories."),
    EngineField("ai", "api_key", "AI API key", None, "OpenAI-compatible API key.", True),
    EngineField("ai", "base_url", "AI endpoint", None, "OpenAI-compatible base URL."),
    EngineField("ai", "model", "AI model", "gpt-4o-mini", "Model used by AI commands."),
)


class ConfigCenter:
    """One private-bot UI for engine, native and compatible module options."""

    def __init__(self, app, inline_bot) -> None:
        self.app = app
        self.inline_bot = inline_bot
        self.pending: dict[int, tuple[str, ...]] = {}
        self.inline_bot.on("cfg:", self.route)
        self.inline_bot.bot.add_handler(
            MessageHandler(self.on_text, filters.text & filters.private & self.inline_bot._owner_only()),
            group=3,
        )

    def _masked(self, value: Any, secret: bool = False) -> str:
        if secret and value:
            return "••••••••"
        if value is None:
            return "not set"
        text = json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else str(value)
        return html.escape(text[:64] + ("…" if len(text) > 64 else ""))

    def _engine_value(self, field: EngineField) -> Any:
        if field.group == "preferences":
            return getattr(self.app.preferences.get(), field.key)
        return self.app.db.get(field.group, field.key, field.default)

    async def _set_engine_value(self, field: EngineField, value: Any) -> None:
        if field.group == "preferences":
            await self.app.preferences.set(field.key, value)
            if field.key == "style":
                from haruka.ui.theme import set_theme
                set_theme(value)
            return
        await self.app.db.set(field.group, field.key, value)
        if field.key == "language":
            await self.app.translator.set_language(value)

    def _options(self, loaded) -> dict[str, Any]:
        config = getattr(loaded.instance, "config", None)
        if config is None:
            return {}
        if hasattr(config, "options"):
            return config.options
        if isinstance(config, dict):
            return {
                str(key): type("LegacyOption", (), {"default": value, "doc": "Legacy Hikka/Heroku module option"})()
                for key, value in config.items()
            }
        return {}

    def _module(self, name: str):
        canonical = self.app.loader.resolve_module_name(name)
        return self.app.loader.modules.get(canonical or "")

    def _module_value(self, loaded, key: str) -> Any:
        return loaded.instance.config[key]

    async def _set_module_value(self, loaded, key: str, value: Any) -> None:
        config = loaded.instance.config
        if hasattr(config, "set") and hasattr(config, "options"):
            await config.set(key, value)
        else:
            config[key] = value
            await self.app.db.set(f"legacy_config.{loaded.instance.name}", key, value)

    def _main(self):
        text = "✦ <b>HARUKA CONFIG CENTER</b>\n<blockquote>Every engine value and every native/compatible module option is edited here through the companion bot.</blockquote>"
        rows = [
            [InlineKeyboardButton("Engine settings", callback_data="cfg:engine:0")],
            [InlineKeyboardButton("Module settings", callback_data="cfg:modules:0")],
            [InlineKeyboardButton("Close", callback_data="cfg:close")],
        ]
        return text, InlineKeyboardMarkup(rows)

    def _engine(self, page: int):
        size = 7
        items = ENGINE_FIELDS[page * size : (page + 1) * size]
        text = "✦ <b>CONFIG · ENGINE</b>\n<blockquote>Tap a value to edit it. Boolean fields offer direct ON/OFF buttons.</blockquote>"
        rows = []
        for index, field in enumerate(items, start=page * size):
            text += f"\n<b>{html.escape(field.label)}</b> — <code>{self._masked(self._engine_value(field), field.secret)}</code>"
            rows.append([InlineKeyboardButton(field.label, callback_data=f"cfg:enginefield:{index}")])
        nav = []
        if page:
            nav.append(InlineKeyboardButton("← Previous", callback_data=f"cfg:engine:{page - 1}"))
        if (page + 1) * size < len(ENGINE_FIELDS):
            nav.append(InlineKeyboardButton("Next →", callback_data=f"cfg:engine:{page + 1}"))
        if nav:
            rows.append(nav)
        rows.append([InlineKeyboardButton("← Config Center", callback_data="cfg:home")])
        return text, InlineKeyboardMarkup(rows)

    def _modules(self, page: int):
        modules = [item for item in self.app.loader.modules.values() if self._options(item)]
        size = 8
        subset = modules[page * size : (page + 1) * size]
        text = "✦ <b>CONFIG · MODULES</b>\n<blockquote>Native modules and compatible Hikka/Heroku modules that expose configuration.</blockquote>"
        rows = []
        for loaded in subset:
            name = loaded.instance.name
            text += f"\n• <b>{html.escape(name)}</b> — {len(self._options(loaded))} options"
            rows.append([InlineKeyboardButton(name, callback_data=f"cfg:module:{name}")])
        nav = []
        if page:
            nav.append(InlineKeyboardButton("← Previous", callback_data=f"cfg:modules:{page - 1}"))
        if (page + 1) * size < len(modules):
            nav.append(InlineKeyboardButton("Next →", callback_data=f"cfg:modules:{page + 1}"))
        if nav:
            rows.append(nav)
        rows.append([InlineKeyboardButton("← Config Center", callback_data="cfg:home")])
        return text, InlineKeyboardMarkup(rows)

    def _module_page(self, name: str):
        loaded = self._module(name)
        if loaded is None or not self._options(loaded):
            return "❌ <b>Configuration unavailable.</b>", InlineKeyboardMarkup([[InlineKeyboardButton("← Modules", callback_data="cfg:modules:0")]])
        text = f"✦ <b>{html.escape(loaded.instance.name)} · CONFIG</b>\n<blockquote>{html.escape(loaded.instance.description or 'Module options')}</blockquote>"
        rows = []
        for key, spec in self._options(loaded).items():
            text += f"\n<b>{html.escape(key)}</b> — <code>{self._masked(self._module_value(loaded, key))}</code>\n<i>{html.escape(getattr(spec, 'doc', '') or 'No description')}</i>"
            rows.append([InlineKeyboardButton(key, callback_data=f"cfg:option:{loaded.instance.name}:{key}")])
        rows.append([InlineKeyboardButton("← Modules", callback_data="cfg:modules:0")])
        return text, InlineKeyboardMarkup(rows)

    def _edit_engine(self, index: int):
        field = ENGINE_FIELDS[index]
        text = (
            f"✦ <b>EDIT · {html.escape(field.label)}</b>\n"
            f"<blockquote>{html.escape(field.doc)}</blockquote>\n"
            f"Current: <code>{self._masked(self._engine_value(field), field.secret)}</code>"
        )
        rows = []
        if isinstance(field.default, bool):
            rows.append([InlineKeyboardButton("Set ON", callback_data=f"cfg:enginebool:{index}:1"), InlineKeyboardButton("Set OFF", callback_data=f"cfg:enginebool:{index}:0")])
        rows += [[InlineKeyboardButton("Enter value…", callback_data=f"cfg:engineinput:{index}")], [InlineKeyboardButton("← Engine", callback_data="cfg:engine:0")]]
        return text, InlineKeyboardMarkup(rows)

    def _edit_option(self, name: str, key: str):
        loaded = self._module(name)
        if loaded is None:
            return "❌ <b>Configuration unavailable.</b>", InlineKeyboardMarkup([[InlineKeyboardButton("← Modules", callback_data="cfg:modules:0")]])
        spec = self._options(loaded)[key]
        value = self._module_value(loaded, key)
        text = (
            f"✦ <b>{html.escape(name)} · {html.escape(key)}</b>\n"
            f"<blockquote>{html.escape(getattr(spec, 'doc', '') or 'No description')}</blockquote>\n"
            f"Default: <code>{self._masked(spec.default)}</code>\nCurrent: <code>{self._masked(value)}</code>"
        )
        rows = []
        if isinstance(value, bool):
            rows.append([InlineKeyboardButton("Set ON", callback_data=f"cfg:bool:{name}:{key}:1"), InlineKeyboardButton("Set OFF", callback_data=f"cfg:bool:{name}:{key}:0")])
        rows += [[InlineKeyboardButton("Enter value…", callback_data=f"cfg:input:{name}:{key}")], [InlineKeyboardButton("Reset default", callback_data=f"cfg:reset:{name}:{key}")], [InlineKeyboardButton("← Module", callback_data=f"cfg:module:{name}")]]
        return text, InlineKeyboardMarkup(rows)

    async def open(self) -> None:
        text, markup = self._main()
        await self.inline_bot.bot.send_message(self.app.security.owner_id, text, reply_markup=markup)

    async def route(self, query) -> None:
        parts = (query.data or "").split(":")
        try:
            action = parts[1]
            if action == "close":
                await query.message.delete(); await query.answer("Closed"); return
            if action == "home": text, markup = self._main()
            elif action == "engine": text, markup = self._engine(int(parts[2]))
            elif action == "modules": text, markup = self._modules(int(parts[2]))
            elif action == "module": text, markup = self._module_page(parts[2])
            elif action == "enginefield": text, markup = self._edit_engine(int(parts[2]))
            elif action == "option": text, markup = self._edit_option(parts[2], parts[3])
            elif action == "engineinput":
                self.pending[self.app.security.owner_id] = ("engine", parts[2]); text = "✦ <b>ENTER VALUE</b>\n<blockquote>Send the new value as your next private message to this bot.</blockquote>"; markup = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cfg:engine:0")]])
            elif action == "input":
                self.pending[self.app.security.owner_id] = ("module", parts[2], parts[3]); text = "✦ <b>ENTER VALUE</b>\n<blockquote>Send the new value as your next private message to this bot.</blockquote>"; markup = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data=f"cfg:module:{parts[2]}")]])
            elif action == "enginebool":
                await self._set_engine_value(ENGINE_FIELDS[int(parts[2])], parts[3] == "1"); text, markup = self._edit_engine(int(parts[2])); await query.answer("Saved")
            elif action == "bool":
                loaded = self._module(parts[2]); await self._set_module_value(loaded, parts[3], parts[4] == "1"); text, markup = self._edit_option(parts[2], parts[3]); await query.answer("Saved")
            elif action == "reset":
                loaded = self._module(parts[2]); await self._set_module_value(loaded, parts[3], self._options(loaded)[parts[3]].default); text, markup = self._edit_option(parts[2], parts[3]); await query.answer("Reset")
            else: return
            await query.message.edit_text(text, reply_markup=markup)
        except Exception as exc:
            await query.answer(f"{type(exc).__name__}: {exc}"[:160], show_alert=True)

    def _parse(self, raw: str, default: Any) -> Any:
        if raw.lower() in {"off", "none", "null", "disable"}: return None
        if isinstance(default, bool):
            if raw.lower() not in {"true", "false", "1", "0", "yes", "no", "on", "off"}: raise ValueError("Expected true or false")
            return raw.lower() in {"true", "1", "yes", "on"}
        if isinstance(default, int) and not isinstance(default, bool): return int(raw)
        if isinstance(default, float): return float(raw)
        if isinstance(default, (list, dict)):
            value = json.loads(raw)
            if not isinstance(value, type(default)): raise ValueError(f"Expected JSON {type(default).__name__}")
            return value
        return raw

    async def on_text(self, _client, message: Message) -> None:
        pending = self.pending.pop(self.app.security.owner_id, None)
        if not pending or (message.text or "").startswith("/"): return
        raw = (message.text or "").strip()
        try:
            if pending[0] == "engine":
                index = int(pending[1]); field = ENGINE_FIELDS[index]; value = self._parse(raw, field.default)
                if field.key == "prefix" and (not isinstance(value, str) or not value or len(value) > 3 or any(char.isspace() for char in value)): raise ValueError("Prefix must contain 1–3 non-space characters")
                if field.key == "language" and value not in {"en", "ru", "uk", "de", "fr", "es", "ja"}: raise ValueError("Unsupported language")
                await self._set_engine_value(field, value); text, markup = self._edit_engine(index)
            else:
                loaded = self._module(pending[1]); key = pending[2]; default = self._options(loaded)[key].default
                await self._set_module_value(loaded, key, self._parse(raw, default)); text, markup = self._edit_option(pending[1], key)
            await message.reply_text("✅ Saved.")
            await self.inline_bot.bot.send_message(self.app.security.owner_id, text, reply_markup=markup)
        except Exception as exc:
            self.pending[self.app.security.owner_id] = pending
            await message.reply_text(f"❌ {html.escape(str(exc))}. Try again.")
