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

import git
import time
import psutil
import os
import glob
import requests
import re
import emoji
import logging
import contextlib

from bs4 import BeautifulSoup
from typing import Optional
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from io import BytesIO
from harukatl.tl.types import Message
from harukatl.utils import get_display_name
from .. import loader, utils, version
import platform as lib_platform
import getpass


logger = logging.getLogger(__name__)

@loader.tds
class HarukaInfoMod(loader.Module):
    """Show userbot info"""

    strings = {"name": "HarukaInfo"}

    def __init__(self):
        self._psutil_primed = False
        self._cpu_counts = None
        with contextlib.suppress(Exception):
            psutil.cpu_percent(interval=None)
            self._psutil_primed = True

        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "custom_message",
                doc=lambda: self.strings("_cfg_cst_msg"),
            ),

            loader.ConfigValue(
                "banner_url",
                "https://raw.githubusercontent.com/coddrago/assets/refs/heads/main/haruka/haruka_info.png",
                lambda: self.strings("_cfg_banner"),
            ),

            loader.ConfigValue(
                "show_haruka",
                True,
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "ping_emoji",
                "🪐",
                lambda: self.strings["ping_emoji"],
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "switchInfo",
                False,
                "Switch info to mode photo",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "imgSettings",
                ["Лапокапканот", 30, '#000', '0|0', "mm", 0, '#000'],
                "Image settings\n1. Дополнительный ник (если прежний ник не отображается)\n2. Размер шрифта\n3. Цвет шрифта в HEX формате '#000'\n4. Координаты текста '100|100', по умолчания в центре фотографии\n5. Якорь текста -> https://pillow.readthedocs.io/en/stable/_images/anchor_horizontal.svg\n6. Размер обводки, по умолчанию 0\n7. Цвет обводки в HEX формате '#000'",
                validator=loader.validators.Series(
                    fixed_len=7,
                ),
            ),
        )

    def _get_os_name(self):
        try:
            with open("/etc/os-release", "r") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME"):
                        return line.split("=")[1].strip().strip('"')
        except FileNotFoundError:
            return self.strings['non_detectable']
        
    def remove_emoji_and_html(self, text: str) -> str:
        reg = r'<[^<]+?>'
        text = f"{re.sub(reg, '', text)}"
        allchars = [str for str in text]
        emoji_list = [c for c in allchars if c in emoji.EMOJI_DATA]
        clean_text = ''.join([str for str in text if not any(i in str for i in emoji_list)])
        return clean_text
    
    def imgur(self, url: str) -> str:
        page = requests.get(
            url,
            stream=True,
            timeout=10,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                )
            },
        )
        soup = BeautifulSoup(page.text, 'html.parser')
        metatag = soup.find("meta", property="og:image")
        return metatag['content']

    def _download_banner(self) -> Optional[tuple[bytes, str]]:
        banner_url = str(self.config["banner_url"] or "").strip()
        if not banner_url:
            return None

        valid_exts = {"jpg", "jpeg", "png", "bmp", "webp"}
        fallback_banner_path = Path(os.getcwd()) / "assets" / "haruka.png"

        def _normalize_payload(payload: bytes, extension_hint: str) -> Optional[tuple[bytes, str]]:
            try:
                with Image.open(BytesIO(payload)) as img:
                    detected_extension = (img.format or "").lower()
            except Exception:
                return None

            extension = detected_extension if detected_extension in valid_exts else extension_hint
            if extension not in valid_exts:
                extension = "jpg"

            return payload, "jpg" if extension == "jpeg" else extension

        def _load_fallback_banner() -> Optional[tuple[bytes, str]]:
            if not fallback_banner_path.is_file():
                return None

            try:
                with open(fallback_banner_path, "rb") as f:
                    payload = f.read()
            except OSError:
                return None

            return _normalize_payload(payload, fallback_banner_path.suffix.lstrip(".").lower())

        if os.path.isfile(banner_url):
            try:
                with open(banner_url, "rb") as f:
                    payload = f.read()
            except OSError as e:
                logger.debug("Failed to read local info banner %s: %s", banner_url, e)
                return _load_fallback_banner()

            extension = Path(banner_url).suffix.lower().lstrip(".")
            if extension not in valid_exts:
                extension = "jpg"
            return _normalize_payload(payload, extension) or _load_fallback_banner()

        try:
            source_url = (
                banner_url
                if not banner_url.startswith("https://imgur")
                else self.imgur(banner_url)
            )
            response = requests.get(
                source_url,
                stream=True,
                timeout=15,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/91.0.4472.124 Safari/537.36"
                    )
                },
            )
            response.raise_for_status()

            content_type = (response.headers.get("Content-Type") or "").lower()
            if content_type and not content_type.startswith("image/"):
                logger.debug(
                    "Banner URL %s returned unexpected content type: %s",
                    source_url,
                    content_type,
                )

            extension = source_url.split("?")[0].split("#")[0].split(".")[-1].lower()
            if extension not in valid_exts and content_type.startswith("image/"):
                extension = content_type.split("/", maxsplit=1)[1].split(";", maxsplit=1)[0]
            if extension not in valid_exts:
                extension = "jpg"

            return _normalize_payload(response.content, extension) or _load_fallback_banner()
        except requests.RequestException as e:
            logger.debug("Failed to fetch info banner from %s: %s", banner_url, e)
            return _load_fallback_banner()
        except Exception as e:
            logger.debug("Unexpected error while fetching info banner %s: %s", banner_url, e)
            return _load_fallback_banner()

    def _build_banner_media(self) -> Optional[BytesIO]:
        banner = self._download_banner()
        if banner is None:
            return None

        payload, extension = banner
        media = BytesIO(payload)
        media.name = f"haruka_info.{extension}"
        media.seek(0)
        return media

    def _get_git_meta(self):
        try:
            repo = git.Repo(search_parent_directories=True)
            branch = (
                repo.active_branch.name
                if not repo.head.is_detached
                else version.branch
            )
            commit = repo.head.commit.hexsha[:7]
            return branch, commit
        except Exception:
            return version.branch, "unknown"

    def _get_cpu_ram_stats(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            if not self._psutil_primed:
                self._psutil_primed = True
                cpu = 0.0
            mem = psutil.virtual_memory()
            ram_used = mem.used / 1024 / 1024
            ram_total = mem.total / 1024 / 1024
            return cpu, ram_used, ram_total
        except Exception:
            return None

    def _get_cpu_counts(self):
        if self._cpu_counts is not None:
            return self._cpu_counts

        try:
            physical = psutil.cpu_count(logical=False) or 0
            logical = psutil.cpu_count() or physical
        except Exception:
            physical, logical = 0, 0

        self._cpu_counts = (physical, logical)
        return self._cpu_counts

    def _render_info(self, start: float) -> str:
        ping = round((time.perf_counter_ns() - start) / 10**6, 3)
        branch_name, commit_short = self._get_git_meta()

        if not self.config["custom_message"]:
            username = self._client.haruka_me.username or "none"
            first_name = (self._client.haruka_me.first_name or "user").lower()
            stats = self._get_cpu_ram_stats()
            stats_line = "cpu/ram  : n/a"
            if stats is not None:
                cpu, ram_used, ram_total = stats
                stats_line = f"cpu/ram  : {cpu:.1f}% | {ram_used:.1f}/{ram_total:.0f} MB"

            return (
                "<pre><code>"
                "HARUKA INFO\n\n"
                f"user     : @{utils.escape_html(username)}\n"
                f"name     : {utils.escape_html(first_name)}\n"
                "title    : HARUKA\n"
                f"branch   : {utils.escape_html(branch_name)}\n"
                f"prefix   : {utils.escape_html(self.get_prefix())}\n"
                f"uptime   : {utils.escape_html(utils.formatted_uptime())}\n"
                f"build    : #{utils.escape_html(commit_short)}\n"
                f"{utils.escape_html(stats_line)}\n"
                f"ping     : {int(ping)}ms"
                "</code></pre>"
            )

        try:
            repo = git.Repo(search_parent_directories=True)
            diff = repo.git.log([f"HEAD..origin/{version.branch}", "--oneline"])
            upd = (
                self.strings("update_required").format(prefix=self.get_prefix()) if diff else self.strings("up-to-date")
            )
        except Exception:
            upd = ""

        me = self.config['imgSettings'][0] if (self.config['imgSettings'][0] != "Лапокапканот") and self.config['switchInfo'] else '<b><a href="tg://user?id={}">{}</a></b>'.format(
            self._client.haruka_me.id,
            utils.escape_html(get_display_name(self._client.haruka_me)),
        ).replace('{', '').replace('}', '')
        build = utils.get_commit_url()
        _version = f'<i>{".".join(list(map(str, list(version.__version__))))}</i>'
        prefix = f"«<code>{utils.escape_html(self.get_prefix())}</code>»"
        cpu_stats = self._get_cpu_ram_stats()
        physical_cpu, logical_cpu = self._get_cpu_counts()
        cpu_load = f"{cpu_stats[0]:.1f}" if cpu_stats else "n/a"

        platform = utils.get_named_platform()

        for emoji, icon in [
            ("🍊", "<emoji document_id=5449599833973203438>🧡</emoji>"),
            ("🍇", "<emoji document_id=5449468596952507859>💜</emoji>"),
            ("😶‍🌫️", "<emoji document_id=5370547013815376328>😶‍🌫️</emoji>"),
            ("❓", "<emoji document_id=5407025283456835913>📱</emoji>"),
            ("🍀", "<emoji document_id=5395325195542078574>🍀</emoji>"),
            ("🦾", "<emoji document_id=5386766919154016047>🦾</emoji>"),
            ("🚂", "<emoji document_id=5359595190807962128>🚂</emoji>"),
            ("🐳", "<emoji document_id=5431815452437257407>🐳</emoji>"),
            ("🕶", "<emoji document_id=5407025283456835913>📱</emoji>"),
            ("🐈‍⬛", "<emoji document_id=6334750507294262724>🐈‍⬛</emoji>"),
            ("✌️", "<emoji document_id=5469986291380657759>✌️</emoji>"),
            ("💎", "<emoji document_id=5471952986970267163>💎</emoji>"),
            ("🛡", "<emoji document_id=5282731554135615450>🌩</emoji>"),
            ("🌼", "<emoji document_id=5224219153077914783>❤️</emoji>"),
            ("🎡", "<emoji document_id=5226711870492126219>🎡</emoji>"),
            ("🐧", "<emoji document_id=5361541227604878624>🐧</emoji>"),
            ("🧃", "<emoji document_id=5422884965593397853>🧃</emoji>"),
            ("💻", "<emoji document_id=5469825590884310445>💻</emoji>"),
            ("🍏", "<emoji document_id=5372908412604525258>🍏</emoji>")
        ]:
            platform = platform.replace(emoji, icon)
        return (
            (
                "🪐 Haruka\n"
                if self.config["show_haruka"]
                else ""
            )
            + self.config["custom_message"].format(
                me=me,
                version=_version,
                build=build,
                prefix=prefix,
                platform=platform,
                upd=upd,
                uptime=utils.formatted_uptime(),
                cpu_usage=utils.get_cpu_usage(),
                ram_usage=f"{utils.get_ram_usage()} MB",
                branch=branch_name,
                hostname=lib_platform.node(),
                user=getpass.getuser(),
                os=self._get_os_name() or self.strings('non_detectable'),
                kernel=lib_platform.release(),
                cpu=f"{physical_cpu} ({logical_cpu}) core(-s); {cpu_load}% total",
                ping=ping
            )
            if self.config["custom_message"]
            else ""
        )
    
    def _get_info_photo(self, start: float) -> Optional[Path]:
        banner = self._download_banner()
        if banner is None:
            return None

        payload, imgform = banner
        imgset = self.config['imgSettings']
        try:
            img = Image.open(BytesIO(payload))
            img.load()

            font_files = glob.glob(f"{os.getcwd()}/assets/font.*")
            if font_files:
                font = ImageFont.truetype(
                    font_files[0],
                    size=int(imgset[1]),
                    encoding="unic",
                )
            else:
                font = ImageFont.load_default()

            w, h = img.size
            draw = ImageDraw.Draw(img)
            draw.text(
                (int(w / 2), int(h / 2))
                if imgset[3] == "0|0"
                else tuple([int(i) for i in imgset[3].split("|")]),
                f"{utils.remove_html(self._render_info(start))}",
                anchor=imgset[4],
                font=font,
                fill=imgset[2] if imgset[2].startswith("#") else "#000",
                stroke_width=int(imgset[5]),
                stroke_fill=imgset[6] if imgset[6].startswith("#") else "#000",
                embedded_color=True,
            )

            path = f"{os.getcwd()}/assets/imginfo.{imgform}"
            img.save(path)
            return Path(path).absolute()
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            IndexError,
        ) as e:
            logger.debug("Failed to build info image from %s: %s", self.config["banner_url"], e)
            return None
        except Exception as e:
            logger.debug("Unexpected error while building info image: %s", e)
            return None

    async def _send_info_with_optional_banner(self, message: Message, rendered_info: str):
        banner_media = self._build_banner_media()
        if banner_media is None:
            return await utils.answer(
                message,
                rendered_info,
                reply_to=getattr(message, "reply_to_msg_id", None),
            )

        return await utils.answer_file(
            message,
            banner_media,
            caption=rendered_info,
            parse_mode="html",
            reply_to=getattr(message, "reply_to_msg_id", None),
        )
    
    @loader.command()
    async def insfont(self, message: Message):
        "<Url|Reply to font> - Install font"
        if message.is_reply:
            reply = await message.get_reply_message()
            fontform = reply.document.mime_type.split("/")[1]
            if not fontform in ['ttf', 'otf']:
                await utils.answer(
                    message,
                    self.strings["incorrect_format_font"]
                )
                return
            origpath = glob.glob(f'{os.getcwd()}/assets/font.*')[0]
            ptf = f'{os.getcwd()}/font.{fontform}'
            os.rename(origpath, ptf)
            photo = await reply.download_media(origpath)
            if photo is None:
                os.rename(ptf, origpath)
                await utils.answer(
                    message,
                    self.strings["no_font"]
                )
                return
            os.remove(ptf)
        elif utils.check_url(utils.get_args_raw(message)):
            fontform = utils.get_args_raw(message).split('.')[-1]
            if not fontform in ['ttf', 'otf']:
                await utils.answer(
                    message,
                    self.strings["incorrect_format_font"]
                )
                return
            response = requests.get(utils.get_args_raw(message), stream=True, timeout=10)
            os.remove(glob.glob(f'{os.getcwd()}/assets/font.*')[0])
            with open(f'{os.getcwd()}/assets/font.{fontform}', 'wb') as file:
                file.write(response.content)
        else:
            await utils.answer(
                message,
                self.strings["no_font"]
            )
            return
        await utils.answer(
            message,
            self.strings["font_installed"]
        )

    @loader.command()
    async def infocmd(self, message: Message):
        start = time.perf_counter_ns()
        rendered_info = self._render_info(start)
        if self.config['switchInfo']:
            photo_path = self._get_info_photo(start)
            if photo_path is None:
                await utils.answer(
                    message, 
                    rendered_info
                )
                return
           
            await utils.answer_file(
                message,
                photo_path,
                reply_to=getattr(message, "reply_to_msg_id", None),
            )
        elif self.config["custom_message"] is None:
            await self._send_info_with_optional_banner(message, rendered_info)
        else:
            if '{ping}' in self.config["custom_message"]:
                message = await utils.answer(message, self.config["ping_emoji"])
            await self._send_info_with_optional_banner(message, rendered_info)

    @loader.command()
    async def harukainfo(self, message: Message):
        await utils.answer(message, self.strings("desc"))

    @loader.command()
    async def setinfo(self, message: Message):
        if not (args := utils.get_args_html(message)):
            return await utils.answer(message, self.strings("setinfo_no_args"))

        self.config["custom_message"] = args
        await utils.answer(message, self.strings("setinfo_success"))

    @loader.command()
    async def switchinfo(self, message: Message):
        """| switch Image info state"""
        self.config["switchInfo"] = not self.config["switchInfo"]
        if self.config["switchInfo"]:
            await utils.answer(message, self.strings["switchinfo_on"])
        else:
            await utils.answer(message, self.strings["switchinfo_off"])
