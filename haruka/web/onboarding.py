"""Zero-terminal browser onboarding for API credentials and Telegram login."""
from __future__ import annotations

import asyncio
import html
import logging
import secrets
import socket
import time
import webbrowser
from pathlib import Path
from typing import Optional

from aiohttp import web
from pyrogram import Client

from haruka.web.qr import QRLogin, qr_png

logger = logging.getLogger(__name__)

_STYLE = """
:root{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,sans-serif}
*{box-sizing:border-box}body{margin:0;background:#191919;color:#fff;min-height:100vh;display:grid;place-items:center;padding:24px}
main{width:min(100%,560px)}.brand{font-size:14px;letter-spacing:.16em;color:#5e9fe8;font-weight:800}.card{margin-top:16px;background:#202020;border:1px solid #3b3b39;border-radius:16px;padding:28px;box-shadow:0 12px 40px #0004}h1{font-size:28px;margin:0 0 8px}p{color:#b8b8b3;line-height:1.55}.grid{display:grid;gap:12px}label{font-size:13px;color:#c8c8c3}input{width:100%;margin-top:6px;padding:13px 14px;border:1px solid #4a4a47;border-radius:10px;background:#292929;color:#fff;font:inherit}button,.button{display:block;width:100%;padding:13px 16px;border:0;border-radius:10px;background:#5e9fe8;color:#101820;font-weight:750;font:inherit;text-align:center;text-decoration:none;cursor:pointer}.secondary{background:#383836;color:#fff}.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.notice{padding:12px;border-radius:10px;background:#302820;color:#f0b57a}.ok{background:#203028;color:#8ed4a9}.qr{display:block;width:min(100%,320px);margin:18px auto;border-radius:14px;background:#fff;padding:12px}@media(max-width:520px){.row{grid-template-columns:1fr}.card{padding:22px}}
"""


def _free_port(host: str, preferred: int) -> int:
    with socket.socket() as sock:
        try:
            sock.bind((host, preferred))
            return preferred
        except OSError:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])


class BrowserOnboarding:
    """Owns an unauthorised client until a browser flow completes."""

    def __init__(
        self,
        session_name: str,
        workdir: Path,
        api_id: Optional[int] = None,
        api_hash: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8088,
    ):
        self.session_name = session_name
        self.workdir = workdir
        self.api_id = api_id
        self.api_hash = api_hash
        self.host = host
        self.port = _free_port(host, port)
        self.secret = secrets.token_urlsafe(18)
        self.client: Optional[Client] = None
        self.phone = ""
        self.phone_code_hash = ""
        self.error = ""
        self.qr_link = ""
        self._runner: Optional[web.AppRunner] = None
        self._done: Optional[asyncio.Future[tuple[int, str]]] = None
        self._qr_task: Optional[asyncio.Task] = None
        self._phone_lock = asyncio.Lock()
        self._last_code_request = 0.0

    @property
    def url(self) -> str:
        return "http://" + self.host + f":{self.port}/?key={self.secret}"

    def _page(self, title: str, body: str, refresh: int = 0) -> web.Response:
        refresh_tag = f'<meta http-equiv="refresh" content="{refresh}">' if refresh else ""
        error = f'<div class="notice">{html.escape(self.error)}</div>' if self.error else ""
        document = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"{refresh_tag}<title>{html.escape(title)} · Haruka</title>"
            f"<style>{_STYLE}</style></head><body><main>"
            "<div class='brand'>✦ HARUKA · SETUP</div>"
            f"<section class='card'><h1>{html.escape(title)}</h1>{error}{body}</section>"
            "</main></body></html>"
        )
        return web.Response(text=document, content_type="text/html")

    @web.middleware
    async def _guard(self, request: web.Request, handler):
        supplied = request.query.get("key") or request.cookies.get("haruka_setup") or ""
        if not secrets.compare_digest(supplied, self.secret):
            raise web.HTTPForbidden(text="Invalid setup link")
        try:
            response = await handler(request)
        except web.HTTPException as response:
            response.set_cookie(
                "haruka_setup", self.secret, httponly=True, samesite="Strict"
            )
            raise response
        response.set_cookie("haruka_setup", self.secret, httponly=True, samesite="Strict")
        return response

    async def run(self, timeout: float = 1200) -> tuple[int, str]:
        self.workdir.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_running_loop()
        self._done = loop.create_future()
        app = web.Application(middlewares=[self._guard], client_max_size=64 * 1024)
        app.add_routes(
            [
                web.get("/", self.index),
                web.post("/credentials", self.credentials),
                web.get("/login", self.login),
                web.post("/phone", self.send_phone),
                web.post("/code", self.submit_code),
                web.post("/password", self.submit_password),
                web.get("/qr", self.qr_page),
                web.get("/qr.png", self.qr_image),
            ]
        )
        self._runner = web.AppRunner(app, access_log=None)
        await self._runner.setup()
        await web.TCPSite(self._runner, self.host, self.port).start()
        logger.info("Open Haruka Setup in your browser: %s", self.url)
        webbrowser.open(self.url)
        try:
            result = await asyncio.wait_for(self._done, timeout)
            await asyncio.sleep(1)
            return result
        finally:
            if self._qr_task:
                self._qr_task.cancel()
            await self._disconnect()
            if self._runner:
                await self._runner.cleanup()

    async def _connect(self) -> None:
        if self.client:
            return
        if not self.api_id or not self.api_hash:
            raise ValueError("API credentials are required")
        self.client = Client(
            self.session_name,
            api_id=self.api_id,
            api_hash=self.api_hash,
            workdir=str(self.workdir),
            no_updates=True,
        )
        await self.client.connect()

    async def _disconnect(self) -> None:
        if self.client:
            try:
                await self.client.disconnect()
            except ConnectionError:
                pass
            self.client = None

    async def _finish(self) -> None:
        if self._done and not self._done.done() and self.api_id and self.api_hash:
            await self._disconnect()
            self._done.set_result((self.api_id, self.api_hash))

    async def index(self, _request: web.Request) -> web.Response:
        if self.api_id and self.api_hash:
            raise web.HTTPFound("/login")
        return self._page(
            "Connect Telegram API",
            "<p>Paste the two values from <b>my.telegram.org → API development tools</b>. "
            "They are stored only in your local Haruka database.</p>"
            "<form class='grid' method='post' action='/credentials'>"
            "<label>API ID<input name='api_id' inputmode='numeric' required></label>"
            "<label>API HASH<input name='api_hash' autocomplete='off' required></label>"
            "<button>Continue</button></form>",
        )

    async def credentials(self, request: web.Request) -> web.Response:
        data = await request.post()
        try:
            api_id = int(str(data.get("api_id", "")))
            api_hash = str(data.get("api_hash", "")).strip()
            if api_id <= 0 or len(api_hash) < 20:
                raise ValueError
        except ValueError:
            self.error = "Check API ID and API HASH."
            return await self.index(request)
        self.api_id, self.api_hash, self.error = api_id, api_hash, ""
        # Existing sessions only need API credentials; detect that without
        # asking the user to log in again.
        if (self.workdir / f"{self.session_name}.session").exists():
            try:
                await self._connect()
                await self.client.get_me()
                await self._finish()
                return self._page(
                    "Ready",
                    "<div class='ok'>Existing Telegram session verified. You can close this page.</div>",
                )
            except Exception:
                await self._disconnect()
        raise web.HTTPFound("/login")

    async def login(self, _request: web.Request) -> web.Response:
        return self._page(
            "Sign in to Telegram",
            "<p>Choose the easiest method. Nothing needs to be entered in a terminal.</p>"
            "<div class='grid'><a class='button' href='/qr'>Scan QR code</a>"
            "<form class='grid' method='post' action='/phone'>"
            "<label>Phone number<input name='phone' placeholder='+380…' autocomplete='tel' required></label>"
            "<button class='secondary'>Send login code</button></form></div>",
        )

    async def send_phone(self, request: web.Request) -> web.Response:
        data = await request.post()
        self.phone = str(data.get("phone", "")).strip().replace(" ", "")
        try:
            async with self._phone_lock:
                now = time.monotonic()
                if now - self._last_code_request < 10:
                    raise RuntimeError("Wait a few seconds before requesting another code")
                await self._connect()
                sent = await self.client.send_code(self.phone)
                self.phone_code_hash = sent.phone_code_hash
                self._last_code_request = now
                self.error = ""
        except Exception as exc:
            self.error = f"Telegram rejected the phone request: {type(exc).__name__}"
            return await self.login(request)
        return self._page(
            "Enter the login code",
            "<p>Use the code sent by Telegram. It is submitted directly to Telegram.</p>"
            "<form class='grid' method='post' action='/code'>"
            "<label>Code<input name='code' inputmode='numeric' autocomplete='one-time-code' required></label>"
            "<button>Sign in</button></form>",
        )

    async def submit_code(self, request: web.Request) -> web.Response:
        data = await request.post()
        code = str(data.get("code", "")).replace(" ", "")
        try:
            await self.client.sign_in(self.phone, self.phone_code_hash, code)
        except Exception as exc:
            if type(exc).__name__ == "SessionPasswordNeeded":
                return self._page(
                    "Two-step verification",
                    "<p>Your account uses a cloud password.</p>"
                    "<form class='grid' method='post' action='/password'>"
                    "<label>Password<input type='password' name='password' autocomplete='current-password' required></label>"
                    "<button>Finish sign in</button></form>",
                )
            self.error = f"The code was not accepted: {type(exc).__name__}"
            return self._page(
                "Enter the login code",
                "<p>Try the newest code sent by Telegram.</p>"
                "<form class='grid' method='post' action='/code'>"
                "<label>Code<input name='code' inputmode='numeric' autocomplete='one-time-code' required></label>"
                "<button>Try again</button></form>",
            )
        await self._finish()
        return self._page("Ready", "<div class='ok'>Telegram is connected. You can close this page.</div>")

    async def submit_password(self, request: web.Request) -> web.Response:
        data = await request.post()
        try:
            await self.client.check_password(str(data.get("password", "")))
        except Exception as exc:
            self.error = f"Password was not accepted: {type(exc).__name__}"
            return self._page(
                "Two-step verification",
                "<form class='grid' method='post' action='/password'>"
                "<label>Password<input type='password' name='password' required></label>"
                "<button>Try again</button></form>",
            )
        await self._finish()
        return self._page("Ready", "<div class='ok'>Telegram is connected. You can close this page.</div>")

    async def qr_page(self, _request: web.Request) -> web.Response:
        if not self._qr_task:
            await self._connect()
            self._qr_task = asyncio.create_task(self._run_qr())
        return self._page(
            "Scan the QR code",
            "<p>Telegram → Settings → Devices → Link Desktop Device.</p>"
            "<img class='qr' src='/qr.png' alt='Telegram login QR code'>"
            "<p>This page refreshes automatically until Telegram confirms the login.</p>",
            refresh=3,
        )

    async def _run_qr(self) -> None:
        async def update(link: str) -> None:
            self.qr_link = link

        try:
            await QRLogin(self.client, self.api_id, self.api_hash).wait(180, update)
            await self._finish()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.error = f"QR login failed: {type(exc).__name__}"

    async def qr_image(self, _request: web.Request) -> web.Response:
        if not self.qr_link:
            return web.Response(status=503, text="QR token is being generated")
        return web.Response(body=qr_png(self.qr_link), content_type="image/png")


async def ensure_browser_login(
    session_name: str,
    workdir: Path,
    api_id: Optional[int],
    api_hash: Optional[str],
) -> tuple[int, str]:
    """Return credentials and guarantee that a local session is authorized."""
    session_path = workdir / f"{session_name}.session"
    if api_id and api_hash and session_path.exists():
        probe = Client(
            session_name,
            api_id=api_id,
            api_hash=api_hash,
            workdir=str(workdir),
            no_updates=True,
        )
        try:
            await probe.connect()
            await probe.get_me()
            return api_id, api_hash
        except Exception:
            logger.warning("Existing session is not authorized; opening setup")
        finally:
            try:
                await probe.disconnect()
            except ConnectionError:
                pass
    wizard = BrowserOnboarding(session_name, workdir, api_id, api_hash)
    return await wizard.run()
