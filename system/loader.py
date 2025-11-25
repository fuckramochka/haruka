import os
import sys
import importlib.util
import logging
import asyncio
import inspect
from .registry import CommandMeta
from .config import Config

logger = logging.getLogger("Loader")

class Loader:
    def __init__(self, engine):
        self.engine = engine

    def _exec_module_sync(self, spec, mod):
        """
        Синхронна функція для виконання коду модуля.
        Виконується в окремому потоці, щоб не блокувати loop.
        """
        # Додаємо в sys.modules ДО виконання, щоб уникнути циклічних імпортів всередині модуля
        sys.modules[spec.name] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            # Якщо виконання впало, прибираємо з sys.modules, щоб не лишати "битий" модуль
            del sys.modules[spec.name]
            raise e

    async def load_file(self, path: str):
        filename = os.path.basename(path)
        
        # Визначення імені модуля
        if "system" in path:
            name = "system.modules." + filename[:-3]
        else:
            name = "plugins." + filename[:-3]

        # Очистка старого модуля (Hot Reloading)
        if name in sys.modules:
            del sys.modules[name]

        try:
            spec = importlib.util.spec_from_file_location(name, path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load spec for {path}")

            mod = importlib.util.module_from_spec(spec)

            # 1. Виконуємо тіло модуля в окремому потоці (Fix: блокування)
            await asyncio.to_thread(self._exec_module_sync, spec, mod)

            cmds = []
            # Збираємо команди
            for obj_name, obj in vars(mod).items():
                if hasattr(obj, 'haruka_meta'):
                    meta = obj.haruka_meta
                    meta.module_name = name
                    cmds.append(meta)

            # Реєструємо команди
            if cmds:
                # (Fix: Error Handling) Можна обгорнути це, якщо registry не гарантує безпеку
                try:
                    await self.engine.registry.register_module(name, mod, cmds)
                except Exception as reg_err:
                    logger.error(f"Registry error in {name}: {reg_err}")
                    return False, f"Registry failed: {reg_err}"
            
            # 2. Виконання хука register (Fix: async/sync сумісність)
            if hasattr(mod, 'register'):
                if inspect.iscoroutinefunction(mod.register):
                    await mod.register(self.engine)
                else:
                    # Якщо хук синхронний, теж можна винести в thread, якщо він важкий
                    # Але зазвичай це легка функція налаштування
                    mod.register(self.engine)

            return True, f"Loaded {len(cmds)} commands"

        except Exception as e:
            logger.error(f"Load Fail [{name}]: {e}", exc_info=True)
            return False, str(e)

    async def _load_directory(self, directory: str):
        """Допоміжний метод для завантаження папки з сортуванням"""
        if not os.path.exists(directory):
            return

        # 4. Сортування та фільтрація (Fix: порядок та приховані файли)
        files = sorted(os.listdir(directory))
        
        for f in files:
            if f.endswith(".py") and not f.startswith(".") and not f.startswith("__"):
                full_path = os.path.join(directory, f)
                await self.load_file(full_path)

    async def load_all(self):
        # 1. System modules
        sys_mod_path = os.path.join(Config.SYSTEM_DIR, "modules")
        await self._load_directory(sys_mod_path)

        # 2. User plugins
        if not os.path.exists(Config.PLUGINS_DIR):
            os.makedirs(Config.PLUGINS_DIR)
        
        await self._load_directory(Config.PLUGINS_DIR)