import os
import json
import aiohttp
import logging
import asyncio
from typing import List, Dict, Optional
from urllib.parse import urlparse
from system.config import Config

# Setup logger
logger = logging.getLogger("RepoManager")

class RepoManager:
    def __init__(self):
        self.db_path = os.path.join(Config.BASE_DIR, "haruka_repos.json")
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Структура даних в пам'яті
        self.data = {
            "repos": [
                "https://raw.githubusercontent.com/Senko-Userbot/Plugins/master"
            ],
            "installed": {} 
        }
        
        # Завантажуємо дані одразу при старті (синхронно, щоб бути готовими до запитів)
        self._load()

    def _load(self):
        """Завантажує базу даних з диску."""
        if not os.path.exists(self.db_path):
            self._save()
            return

        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                self.data.update(loaded)
        except Exception as e:
            logger.error(f"Failed to load repo DB: {e}")
            # Якщо файл пошкоджено — робимо бекап
            if os.path.exists(self.db_path):
                os.rename(self.db_path, self.db_path + ".bak")

    def _save(self):
        """Зберігає базу даних на диск."""
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save repo DB: {e}")

    async def get_session(self) -> aiohttp.ClientSession:
        """Лінива ініціалізація сесії."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _normalize_url(self, url: str) -> str:
        """Перетворює посилання GitHub на Raw-посилання."""
        url = url.strip()
        if not url.startswith("http"):
            url = "https://" + url
            
        parsed = urlparse(url)
        
        if parsed.netloc == "github.com":
            # https://github.com/User/Repo -> https://raw.githubusercontent.com/User/Repo/master
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2:
                user, repo = parts[0], parts[1]
                # Спрощена логіка: якщо це blob, беремо гілку, інакше master
                branch = "master"
                path_suffix = ""
                
                if len(parts) > 3 and parts[2] == "blob":
                    branch = parts[3]
                    path_suffix = "/".join(parts[4:])
                
                new_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}"
                if path_suffix:
                    new_url += f"/{path_suffix}"
                return new_url
        
        return url.rstrip("/")

    # --- API (Сумісне з packages.py) ---

    def get_all_repos(self) -> List[str]:
        """Повертає список репозиторіїв."""
        return self.data.get("repos", [])

    def add_repo(self, url: str) -> bool:
        """
        Додає репозиторій.
        ПРИМІТКА: Метод синхронний, щоб працювати в packages.py без await.
        Валідація тут спрощена (тільки формат URL).
        """
        norm_url = self._normalize_url(url)
        
        if norm_url in self.data["repos"]:
            return False
            
        self.data["repos"].append(norm_url)
        self._save()
        return True

    def record_install(self, name: str, url: str):
        """Записує, звідки встановлено плагін."""
        self.data["installed"][name] = url
        self._save()

    def remove_install_record(self, name: str):
        """Видаляє запис про встановлення."""
        if name in self.data["installed"]:
            del self.data["installed"][name]
            self._save()

    def get_installed_url(self, name: str) -> Optional[str]:
        """Отримує URL оновлення для плагіна."""
        return self.data["installed"].get(name)

    def get_all_installed(self) -> Dict[str, str]:
        """Повертає всі встановлені через менеджер плагіни."""
        return self.data.get("installed", {})

    async def fetch_file(self, url: str) -> Optional[bytes]:
        """
        Завантажує файл (Асинхронно).
        Використовується в: .haruka install / update
        """
        session = await self.get_session()
        try:
            # Timeout 10 секунд, щоб не вішати бота
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    logger.warning(f"Fetch failed {url}: Status {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"Fetch error {url}: {e}")
            return None
            
    async def close(self):
        """Закриває сесію при вимкненні бота."""
        if self._session:
            await self._session.close()

# Singleton instance
repo_manager = RepoManager()