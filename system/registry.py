import asyncio
import logging
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, field

# Setup logger
logger = logging.getLogger("Registry")

@dataclass
class CommandMeta:
    name: str
    handler: Callable[..., Any]
    # Fix: Додано значення за замовчуванням, щоб не ламалося при створенні декоратором
    module_name: str = "" 
    aliases: List[str] = field(default_factory=list)
    flags: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # [Validation] Ensure basic integrity
        if not self.name:
            raise ValueError("Command name cannot be empty")
        if not callable(self.handler):
            # Для відладки корисно бачити, що саме передали замість функції
            raise TypeError(f"Handler for '{self.name}' must be callable, got {type(self.handler)}")
        
        # Fix: Ця перевірка видалена, оскільки Loader заповнює це поле ПІЗНІШЕ
        # if not self.module_name:
        #     raise ValueError(f"Module name is missing for command '{self.name}'")

class Registry:
    def __init__(self):
        self._lock = asyncio.Lock()
        
        # Main dispatch table: trigger (name/alias) -> CommandMeta
        self.commands: Dict[str, CommandMeta] = {}
        
        # Stored module instances: module_name -> instance
        self.modules: Dict[str, Any] = {}
        
        # Reverse index for fast lookups/deletion: module_name -> Set[triggers]
        # Solves Performance Issue #8 (Iterating whole dict)
        self._module_index: Dict[str, Set[str]] = {}

    async def register_module(self, module_name: str, module_inst: Any, commands: List[CommandMeta]) -> bool:
        """
        Registers a module and its commands safely.
        Handles overwrites and updates internal indexes.
        """
        # [Validation] Fail fast before acquiring lock
        if not module_name:
            logger.error("Attempted to register module without a name")
            return False
        if module_inst is None:
            logger.error(f"Module instance for '{module_name}' is None")
            return False

        # Validate command list structure
        valid_commands = []
        for cmd in commands:
            if not isinstance(cmd, CommandMeta):
                logger.error(f"Invalid command object in '{module_name}': {cmd}")
                continue
            # Гарантуємо, що ім'я модуля встановлено перед реєстрацією
            if not cmd.module_name:
                cmd.module_name = module_name
            valid_commands.append(cmd)

        # Use asyncio.wait_for to prevent deadlocks (Issue #3)
        try:
            async with asyncio.timeout(5.0): # Python 3.11+ syntax
                async with self._lock:
                    return self._unsafe_register(module_name, module_inst, valid_commands)
        except asyncio.TimeoutError:
            logger.error(f"Timeout acquiring lock while registering '{module_name}'")
            return False
        except Exception as e:
            logger.exception(f"Critical error registering '{module_name}': {e}")
            return False

    def _unsafe_register(self, module_name: str, module_inst: Any, commands: List[CommandMeta]) -> bool:
        """Internal synchronous registration logic (executed under lock)."""
        
        # 1. Cleanup old version of this module (Hot-reload support)
        if module_name in self.modules:
            logger.info(f"Reloading module '{module_name}'...")
            self._unsafe_remove(module_name)

        # 2. Register module instance
        self.modules[module_name] = module_inst
        self._module_index[module_name] = set()

        count = 0
        
        for cmd in commands:
            # Collect all triggers (name + aliases)
            triggers = [cmd.name] + cmd.aliases
            
            for trigger in triggers:
                # [Conflict Detection] (Issue #1 & #6)
                if trigger in self.commands:
                    existing = self.commands[trigger]
                    if existing.module_name != module_name:
                        logger.warning(
                            f"Conflict: Module '{module_name}' is overwriting command/alias '{trigger}' "
                            f"previously owned by '{existing.module_name}'"
                        )

                # Update main table
                self.commands[trigger] = cmd
                # Update reverse index
                self._module_index[module_name].add(trigger)
                count += 1

        logger.info(f"Registered module '{module_name}' with {count} triggers.")
        return True

    async def remove_module(self, module_name: str) -> bool:
        """Safely removes a module and cleans up its commands."""
        try:
            async with asyncio.timeout(2.0):
                async with self._lock:
                    if module_name not in self.modules:
                        logger.warning(f"Attempted to remove non-existent module: '{module_name}'")
                        return False
                    return self._unsafe_remove(module_name)
        except asyncio.TimeoutError:
            logger.error(f"Timeout acquiring lock while removing '{module_name}'")
            return False

    def _unsafe_remove(self, module_name: str) -> bool:
        """
        Removes module commands using the reverse index.
        CRITICAL: Checks ownership before deletion to avoid deleting overwritten aliases.
        """
        # Get list of triggers registered by this module
        triggers = self._module_index.get(module_name, set())
        
        removed_count = 0
        for trigger in triggers:
            # [Safety] Only delete if the command still belongs to this module
            # If Module B overwrote this alias, self.commands[trigger].module_name would be 'Module B'
            # We must NOT delete Module B's command when removing Module A. (Issue #2 & #7)
            if trigger in self.commands:
                if self.commands[trigger].module_name == module_name:
                    del self.commands[trigger]
                    removed_count += 1
                else:
                    logger.debug(f"Skipping removal of '{trigger}': ownership changed to '{self.commands[trigger].module_name}'")

        # Clean up indexes
        if module_name in self.modules:
            del self.modules[module_name]
        if module_name in self._module_index:
            del self._module_index[module_name]

        logger.info(f"Removed module '{module_name}' ({removed_count} triggers cleaned).")
        return True

    async def get_command(self, trigger: str) -> Optional[CommandMeta]:
        """Thread-safe lookup."""
        # Dict lookup is atomic in Python, but lock ensures we don't read mid-update
        # async with self._lock: # Optional: strict consistency
        return self.commands.get(trigger)

    async def get_all_commands(self) -> Dict[str, CommandMeta]:
        """Returns a copy of commands."""
        async with self._lock:
            return self.commands.copy()