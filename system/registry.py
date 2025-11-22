import asyncio
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class CommandMeta:
    name: str
    handler: Any
    module_name: str
    aliases: List[str]
    flags: Dict[str, Any]

class Registry:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.commands: Dict[str, CommandMeta] = {}
        self.modules: Dict[str, Any] = {}

    async def register_module(self, module_name: str, module_inst: Any, commands: List[CommandMeta]):
        async with self._lock:
            # Rollback logic: clean old cmds first
            self._remove_unsafe(module_name)
            
            for cmd in commands:
                self.commands[cmd.name] = cmd
                for alias in cmd.aliases:
                    self.commands[alias] = cmd
            
            self.modules[module_name] = module_inst

    async def remove_module(self, module_name: str):
        async with self._lock:
            self._remove_unsafe(module_name)

    def _remove_unsafe(self, module_name: str):
        keys = [k for k, v in self.commands.items() if v.module_name == module_name]
        for k in keys: del self.commands[k]
        if module_name in self.modules: del self.modules[module_name]