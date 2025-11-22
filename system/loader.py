import os
import sys
import importlib.util
import logging
from .registry import CommandMeta
from .config import Config

logger = logging.getLogger("Loader")

class Loader:
    def __init__(self, engine):
        self.engine = engine

    async def load_file(self, path: str):
        # Determine module name
        if "system" in path:
            name = "system.modules." + os.path.basename(path)[:-3]
        else:
            name = "plugins." + os.path.basename(path)[:-3]

        if name in sys.modules: del sys.modules[name]

        try:
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)

            cmds = []
            for obj_name, obj in vars(mod).items():
                if hasattr(obj, 'haruka_meta'):
                    meta = obj.haruka_meta
                    meta.module_name = name
                    cmds.append(meta)

            # Register commands (if any)
            if cmds:
                await self.engine.registry.register_module(name, mod, cmds)
            
            # 🔥 IMPORTANT: Run register() hook if it exists in the module
            # This is needed for middlewares (like in .cute or .afk)
            if hasattr(mod, 'register'):
                await mod.register(self.engine)

            return True, f"Loaded {len(cmds)} commands"

        except Exception as e:
            logger.error(f"Load Fail: {e}")
            return False, str(e)

    async def load_all(self):
        # 1. System modules
        sys_mod_path = os.path.join(Config.SYSTEM_DIR, "modules")
        for f in os.listdir(sys_mod_path):
            if f.endswith(".py") and not f.startswith("__"):
                await self.load_file(os.path.join(sys_mod_path, f))

        # 2. User plugins
        if not os.path.exists(Config.PLUGINS_DIR):
            os.makedirs(Config.PLUGINS_DIR)
            
        for f in os.listdir(Config.PLUGINS_DIR):
            if f.endswith(".py"):
                await self.load_file(os.path.join(Config.PLUGINS_DIR, f))