import asyncio
import shlex
import logging
import html
import re
from typing import List, Union, Optional, Any

# Безпечний імпорт Telethon
try:
    from telethon import errors
    from telethon.tl.types import MessageService
except ImportError:
    errors = None
    MessageService = None

from .config import Config

# Базовий логер
base_logger = logging.getLogger("Context")

class Context:
    # Налаштування за замовчуванням
    DEFAULT_TIMEOUT = 30
    MAX_RETRIES = 5
    MAX_FLOOD_WAIT = 60
    
    def __init__(self, event, engine, timeout: int = None, max_retries: int = None):
        self.event = event
        self.engine = engine
        self.client = engine.client
        self.db = engine.db
        
        self.timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else self.MAX_RETRIES
        
        # Контейнери стану
        self.raw_text: str = ""
        self.parts: List[str] = []
        self.trigger: str = ""
        self.prefix: str = ""
        self.args: List[str] = []
        self.input: str = ""
        self.valid: bool = False
        self.last_error: Optional[Exception] = None

        # 1. Валідація події
        if not event or (MessageService and isinstance(event, MessageService)):
            return

        # 2. Витяг тексту
        self.raw_text = getattr(event, 'raw_text', "") or ""
        if not self.raw_text.strip():
            return

        # 3. Парсинг команди
        self._parse_command()
        
        # Логер з контекстом
        self.logger = logging.getLogger(f"Context.{self.trigger or 'Unknown'}")

    def _parse_command(self):
        """
        Розбирає raw_text на префікс, команду, аргументи та інпут.
        """
        prefixes = Config.PREFIX if isinstance(Config.PREFIX, list) else [Config.PREFIX]
        
        full_cmd = ""
        for p in prefixes:
            if self.raw_text.startswith(p):
                self.prefix = p
                first_split = self.raw_text.split(maxsplit=1)
                full_cmd = first_split[0]
                self.trigger = full_cmd[len(p):]
                break
        
        if not self.prefix:
            return

        cmd_len = len(full_cmd)
        self.input = self.raw_text[cmd_len:].lstrip()

        self.parts = [full_cmd]
        if self.input:
            try:
                lexed_args = shlex.split(self.input)
                self.parts.extend(lexed_args)
            except ValueError:
                self.parts.extend(self.input.split())

        self.args = self.parts[1:]
        self.valid = True

    def _detect_parse_mode(self, text: str) -> str:
        """Автоматичне визначення режиму парсингу."""
        if re.search(r"<[a-z][\s\S]*>", text):
            return 'html'
        if re.search(r"(\*\*|__|`|```)", text):
            return 'md'
        return 'html'

    @staticmethod
    def escape(text: str) -> str:
        return html.escape(str(text))

    async def respond(
        self, 
        text: str, 
        delay: int = 0, 
        web_preview: bool = False, 
        parse_mode: str = 'auto', 
        reply_to: Optional[int] = None,
        force_new: bool = False,
        edit_only: bool = False
    ):
        """
        Універсальний метод відповіді.
        Виправлено: Видалено використання lambda та складних обгорток для надійності.
        """
        if not text or not self.client:
            return None

        # Приведення до рядка (на випадок, якщо передали число)
        text = str(text)

        # Обмеження Telegram
        if len(text) > 4096:
            text = text[:4096]

        if parse_mode == 'auto':
            parse_mode = self._detect_parse_mode(text)

        # Логіка Reply ID
        if reply_to is None and not self.event.out:
            reply_to = self.event.id
            
        # Рішення: Редагувати чи Відправляти нове
        should_edit = self.event.out and not force_new
        
        if edit_only and not should_edit:
            self.logger.warning("edit_only=True but message is not outgoing.")
            return None

        attempt = 0
        total_waited = 0
        current_parse_mode = parse_mode
        
        while attempt < self.max_retries:
            try:
                msg = None
                
                # === ОСНОВНА ДІЯ ===
                if should_edit:
                    msg = await self.event.edit(
                        text, 
                        parse_mode=current_parse_mode, 
                        link_preview=web_preview
                    )
                else:
                    msg = await self.client.send_message(
                        self.event.chat_id,
                        text,
                        reply_to=reply_to,
                        parse_mode=current_parse_mode,
                        link_preview=web_preview
                    )
                # ===================

                # Успіх
                if msg and delay > 0:
                    self._schedule_delete(msg, delay)
                return msg

            except asyncio.TimeoutError:
                self.logger.error(f"Timeout ({self.timeout}s) responding.")
                return None

            except Exception as e:
                self.last_error = e
                err_str = str(e).lower()
                error_class = e.__class__.__name__.lower()
                
                # 1. Обробка FloodWait
                if errors and isinstance(e, errors.FloodWaitError):
                    wait_time = e.seconds
                    if total_waited + wait_time > self.MAX_FLOOD_WAIT:
                        self.logger.error(f"FloodWait limit reached. Aborting.")
                        return None
                    
                    self.logger.warning(f"FloodWait: sleeping {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    total_waited += wait_time
                    attempt += 1
                    continue

                # 2. Помилки парсингу (HTML/MD Failed) -> Спроба Plain Text
                if ("parse" in err_str or "cant parse" in err_str) and current_parse_mode is not None:
                    self.logger.warning(f"Parse error ({current_parse_mode}). Retrying as plain text.")
                    current_parse_mode = None 
                    continue

                # 3. MessageNotModified (Коли текст редагування такий самий)
                if "messagenotmodified" in error_class:
                    return self.event

                # Логування інших помилок
                self.logger.error(f"Error in respond: {e}")
                return None

        return None

    def _schedule_delete(self, msg, delay):
        """Планує видалення повідомлення."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._del(msg, delay))
        except RuntimeError:
            pass

    async def _del(self, msg, t):
        """Безпечне видалення."""
        if not msg: return
        
        await asyncio.sleep(t)
        try:
            # Видаляємо тільки свої повідомлення
            if hasattr(msg, 'out') and msg.out:
                await msg.delete()
        except Exception:
            pass

    async def get_reply_message(self):
        """Аліас для зручності."""
        return await self.event.get_reply_message()

    # --- Скорочені методи ---

    async def err(self, text: str):
        """Помилка (червоний хрестик)."""
        # Тут ми явно вказуємо html, щоб заголовок був жирним
        # Але сам текст помилки екрануємо, щоб спецсимволи юзера не ламали верстку
        await self.respond(f"<b>⛔ Error:</b> {self.escape(text)}", parse_mode='html')

    async def ok(self, text: str):
        """Успіх (зелена галочка)."""
        await self.respond(f"<b>✅ Success:</b> {self.escape(text)}", parse_mode='html')
        
    async def warn(self, text: str):
        """Попередження (жовтий трикутник)."""
        await self.respond(f"<b>⚠️ Warning:</b> {self.escape(text)}", parse_mode='html')

    def __bool__(self):
        return self.valid