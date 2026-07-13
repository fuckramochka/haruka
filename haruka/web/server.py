"""Authenticated button-driven web control panel for a running engine."""
from __future__ import annotations

import html
import secrets
import socket
import webbrowser
from dataclasses import asdict
from typing import Optional

from aiohttp import web

from haruka.core.diagnostics import collect_health
from haruka.version import __version__

_STYLE = """
:root{color-scheme:dark;font:16px/1.5 Inter,ui-sans-serif,system-ui,sans-serif}
*{box-sizing:border-box}body{margin:0;background:#191919;color:#fff;padding:24px}.shell{width:min(100%,1040px);margin:auto}.brand{letter-spacing:.15em;color:#5e9fe8;font-size:13px;font-weight:800}.hero{display:flex;justify-content:space-between;align-items:end;gap:20px;margin:18px 0 28px}h1{font-size:clamp(30px,5vw,52px);line-height:1;margin:0}.muted{color:#a7a7a2}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:14px}.card{grid-column:span 6;background:#202020;border:1px solid #3b3b39;border-radius:14px;padding:20px}.wide{grid-column:span 12}.metric{font-size:30px;font-weight:800;color:#72bc8f}.list{display:grid;gap:8px}.item{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid #333}.item:last-child{border:0}button{border:1px solid #4c4c48;background:#383836;color:#fff;border-radius:9px;padding:9px 13px;cursor:pointer;font-weight:700}.primary{background:#5e9fe8;color:#102034;border-color:#5e9fe8}.on{color:#72bc8f}.off{color:#e97366}.row{display:flex;gap:8px;flex-wrap:wrap}code{background:#30302f;padding:3px 7px;border-radius:6px}@media(max-width:720px){.card{grid-column:span 12}.hero{align-items:start;flex-direction:column}}
"""


def _available_port(host: str, preferred: int) -> int:
    with socket.socket() as sock:
        try:
            sock.bind((host, preferred))
            return preferred
        except OSError:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])


class WebServer:
    def __init__(
        self,
        app,
        host: str = "127.0.0.1",
        port: int = 8080,
        token: Optional[str] = None,
        open_browser: bool = True,
    ):
        self.app = app
        self.host = host
        self.port = _available_port(host, port)
        self.token = token or secrets.token_urlsafe(24)
        self.open_browser = open_browser
        self.runner: Optional[web.AppRunner] = None

    @property
    def url(self) -> str:
        return "http://" + self.host + f":{self.port}/?token={self.token}"

    @web.middleware
    async def auth(self, request: web.Request, handler):
        if request.path == "/health":
            return await handler(request)
        supplied = (
            request.headers.get("Authorization", "").removeprefix("Bearer ")
            or request.cookies.get("haruka_web", "")
            or request.query.get("token", "")
        )
        if not secrets.compare_digest(supplied, self.token):
            raise web.HTTPUnauthorized(text="Open the private dashboard URL from Haruka")
        response = await handler(request)
        response.set_cookie(
            "haruka_web", self.token, httponly=True, samesite="Strict"
        )
        return response

    async def start(self) -> None:
        api = web.Application(middlewares=[self.auth], client_max_size=128 * 1024)
        api.add_routes(
            [
                web.get("/", self.index),
                web.get("/health", self.health),
                web.get("/api/status", self.status),
                web.get("/api/modules", self.modules),
                web.post("/action/module/{name}", self.toggle_module),
                web.post("/action/command/{name}", self.toggle_command),
                web.post("/action/preference/{key}", self.toggle_preference),
                web.post("/action/style", self.cycle_style),
                web.post("/action/core", self.update_core),
            ]
        )
        self.runner = web.AppRunner(api, access_log=None)
        await self.runner.setup()
        await web.TCPSite(self.runner, self.host, self.port).start()
        if self.open_browser and self.host in {"127.0.0.1", "localhost", "::1"}:
            webbrowser.open(self.url)

    async def stop(self) -> None:
        if self.runner:
            await self.runner.cleanup()
            self.runner = None

    async def health(self, _request: web.Request) -> web.Response:
        return web.json_response({"ok": True, "version": __version__})

    async def status(self, _request: web.Request) -> web.Response:
        health = collect_health(self.app.settings.db_path)
        return web.json_response(
            {
                "version": __version__,
                "uptime": self.app.uptime,
                "modules": len(self.app.loader.modules),
                "commands": len(self.app.loader.command_names),
                "health": asdict(health),
            }
        )

    async def modules(self, _request: web.Request) -> web.Response:
        return web.json_response(
            [
                {
                    "name": name,
                    "enabled": self.app.loader.is_module_enabled(name),
                    "origin": loaded.origin,
                }
                for name, loaded in self.app.loader.modules.items()
            ]
        )

    async def toggle_module(self, request: web.Request) -> web.Response:
        name = request.match_info["name"]
        canonical = self.app.loader.resolve_module_name(name)
        if canonical is None or canonical == "Modules":
            raise web.HTTPBadRequest(text="Unknown or protected feature")
        enabled = not self.app.loader.is_module_enabled(canonical)
        await self.app.loader.set_module_enabled(canonical, enabled)
        raise web.HTTPFound("/")

    async def toggle_command(self, request: web.Request) -> web.Response:
        name = request.match_info["name"].lower()
        if self.app.loader.find_command(name) is None:
            raise web.HTTPBadRequest(text="Unknown command")
        await self.app.loader.set_command_enabled(
            name, not self.app.loader.is_command_enabled(name)
        )
        raise web.HTTPFound("/")

    async def toggle_preference(self, request: web.Request) -> web.Response:
        key = request.match_info["key"]
        if key not in {"compact_help", "reveal_errors", "confirm_dangerous", "quiet_unknown"}:
            raise web.HTTPBadRequest(text="Unsupported preference")
        await self.app.preferences.toggle(key)
        raise web.HTTPFound("/")

    async def cycle_style(self, _request: web.Request) -> web.Response:
        prefs = await self.app.preferences.cycle_style()
        from haruka.ui.theme import set_theme

        set_theme(prefs.style)
        raise web.HTTPFound("/")

    async def update_core(self, request: web.Request) -> web.Response:
        data = await request.post()
        prefix = str(data.get("prefix", "")).strip()
        language = str(data.get("language", "")).strip().lower()
        bot_token = str(data.get("bot_token", "")).strip()
        updates = {}
        if prefix:
            if len(prefix) > 3 or any(char.isspace() for char in prefix):
                raise web.HTTPBadRequest(text="Prefix must be 1-3 non-space characters")
            updates["prefix"] = prefix
        if language:
            await self.app.translator.set_language(language)
        if bot_token:
            if ":" not in bot_token or len(bot_token) < 30:
                raise web.HTTPBadRequest(text="Bot token format is invalid")
            updates["inline_bot_token"] = bot_token
        if updates:
            await self.app.db.set_many("core", updates)
        raise web.HTTPFound("/")

    @staticmethod
    def _form(action: str, label: str, primary: bool = False) -> str:
        kind = " class='primary'" if primary else ""
        return (
            f"<form method='post' action='{html.escape(action)}'>"
            f"<button{kind}>{html.escape(label)}</button></form>"
        )

    async def index(self, request: web.Request) -> web.Response:
        # Remove token from the address bar after establishing the secure cookie.
        if request.query.get("token"):
            response = web.HTTPFound("/")
            response.set_cookie(
                "haruka_web", self.token, httponly=True, samesite="Strict"
            )
            raise response
        health = collect_health(self.app.settings.db_path)
        prefs = self.app.preferences.get()
        feature_rows = []
        for name in self.app.loader.module_names():
            enabled = self.app.loader.is_module_enabled(name)
            action = self._form(
                f"/action/module/{name}", "Disable" if enabled else "Enable"
            )
            feature_rows.append(
                f"<div class='item'><span><b>{html.escape(name)}</b> "
                f"<small class='{'on' if enabled else 'off'}'>"
                f"{'ON' if enabled else 'OFF'}</small></span>{action}</div>"
            )
        preference_rows = []
        for key, label in (
            ("compact_help", "Compact help"),
            ("reveal_errors", "Detailed errors"),
            ("confirm_dangerous", "Danger confirmations"),
            ("quiet_unknown", "Quiet unknown commands"),
        ):
            value = bool(getattr(prefs, key))
            preference_rows.append(
                f"<div class='item'><span>{html.escape(label)} "
                f"<small class='{'on' if value else 'off'}'>"
                f"{'ON' if value else 'OFF'}</small></span>"
                f"{self._form(f'/action/preference/{key}', 'Toggle')}</div>"
            )
        command_rows = []
        for name in self.app.loader.command_names:
            enabled = self.app.loader.is_command_enabled(name)
            command_rows.append(
                f"<div class='item'><span><code>{html.escape(name)}</code> "
                f"<small class='{'on' if enabled else 'off'}'>"
                f"{'ON' if enabled else 'OFF'}</small></span>"
                f"{self._form(f'/action/command/{name}', 'Disable' if enabled else 'Enable')}</div>"
            )
        document = f"""<!doctype html><html><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Haruka Control Center</title><style>{_STYLE}</style></head><body>
<div class='shell'><div class='brand'>✦ HARUKA ENGINE · {__version__}</div>
<div class='hero'><div><h1>Control Center</h1><div class='muted'>Everything is managed with buttons.</div></div>
<div class='row'>{self._form('/action/style', f'Skin · {prefs.style.title()}', True)}</div></div>
<div class='grid'><section class='card'><div class='muted'>STATUS</div><div class='metric'>{html.escape(health.status.upper())}</div>
<p>{health.memory_mb:.1f} MB RAM · {health.cpu_percent:.1f}% CPU<br>{health.disk_free_gb:.1f} GB disk free · {health.tasks} tasks</p></section>
<section class='card'><div class='muted'>ENGINE</div><div class='metric'>{len(self.app.loader.command_names)}</div>
<p>commands across {len(self.app.loader.modules)} capabilities<br>Database {health.database_kb:.1f} KiB</p></section>
<section class='card wide'><h2>Capabilities</h2><div class='list'>{''.join(feature_rows)}</div></section>
<section class='card wide'><h2>Command gates</h2><div class='list'>{''.join(command_rows)}</div></section>
<section class='card wide'><h2>Preferences</h2><div class='list'>{''.join(preference_rows)}</div></section>
<section class='card wide'><h2>Core settings</h2>
<form method='post' action='/action/core' class='list'>
<label>Command prefix<br><input name='prefix' maxlength='3' placeholder='{html.escape(self.app.db.get("core", "prefix", "."))}'></label>
<label>Language<br><select name='language'><option value=''>Keep {html.escape(self.app.translator.language)}</option>{''.join(f"<option value='{html.escape(code)}'>{html.escape(label)}</option>" for code, label in self.app.translator.available().items())}</select></label>
<label>Companion bot token<br><input type='password' name='bot_token' autocomplete='off' placeholder='Leave empty to keep current'></label>
<button class='primary'>Save settings</button></form><p class='muted'>A new companion bot token activates after restart.</p></section>
</div></div></body></html>"""
        return web.Response(text=document, content_type="text/html")
