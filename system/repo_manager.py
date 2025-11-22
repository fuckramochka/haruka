import os
import json
import aiohttp
import asyncio
from system.config import Config

CONFIG_PATH = os.path.join(Config.BASE_DIR, "configs")
REPO_FILE = os.path.join(CONFIG_PATH, "repos.json")

class RepoManager:
    def __init__(self):
        if not os.path.exists(CONFIG_PATH):
            os.makedirs(CONFIG_PATH)
        
        self._ensure_config()

    def _ensure_config(self):
        if not os.path.exists(REPO_FILE):
            self._save_data({"repos": [], "installed": {}})

    def _get_data(self):
        with open(REPO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_data(self, data):
        with open(REPO_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def add_repo(self, url: str):
        """Adds repository link"""
        data = self._get_data()
        # URL normalization (GitHub to Raw)
        raw_url = self._normalize_url(url)
        if raw_url not in data["repos"]:
            data["repos"].append(raw_url)
            self._save_data(data)
            return True
        return False

    def record_install(self, plugin_name: str, source_url: str):
        """Records where the plugin was installed from"""
        data = self._get_data()
        data["installed"][plugin_name] = source_url
        self._save_data(data)

    def get_installed_url(self, plugin_name: str):
        data = self._get_data()
        return data["installed"].get(plugin_name)

    def get_all_repos(self):
        return self._get_data()["repos"]

    def get_all_installed(self):
        return self._get_data()["installed"]

    def _normalize_url(self, url: str):
        """Converts github.com links to raw.githubusercontent.com"""
        if "raw.githubusercontent.com" in url:
            return url.rstrip("/")
        
        # https://github.com/User/Repo -> https://raw.githubusercontent.com/User/Repo/master
        if "github.com" in url:
            url = url.replace("github.com", "raw.githubusercontent.com")
            if "/blob/" in url:
                url = url.replace("/blob/", "/")
            else:
                # Assume master branch if not specified
                url += "/master"
        return url.rstrip("/")

    async def fetch_file(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
                return None

# Singleton
repo_manager = RepoManager()