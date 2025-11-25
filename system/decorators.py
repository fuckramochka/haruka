import logging
from typing import Optional, List, Callable, Any
from .registry import CommandMeta

# Logger for warnings during import time
logger = logging.getLogger("Haruka.Decorator")

def command(name: Optional[str] = None, aliases: Optional[List[str]] = None, **flags: Any):
    """
    Decorator to register a function as a command.
    
    Args:
        name: Explicit command trigger. If None, function name is used.
        aliases: List of alternative triggers.
        **flags: Custom flags (e.g., admin_only=True, hidden=True).
    """
    # [2] Fix mutable default argument & freeze it
    # Converting to tuple prevents modification of the list reference later
    safe_aliases = tuple(aliases) if aliases else ()

    def wrapper(func: Callable):
        # [4] Validate that we are decorating a function/coroutine
        if not callable(func):
            raise TypeError(f"@command can only be applied to functions, got {type(func)}")

        # [5] Prevent double decoration
        if hasattr(func, "haruka_meta"):
            raise ValueError(f"Function '{func.__name__}' is already decorated as a command.")

        # [3] Validate command trigger
        trigger = name if name else func.__name__
        trigger = trigger.strip()

        if not trigger:
            raise ValueError(f"Command name cannot be empty for function '{func.__name__}'")
        
        # Optional: Warn about spaces in command names (depends on your parser)
        if ' ' in trigger:
            logger.warning(f"Command '{trigger}' contains spaces. Ensure your parser supports this.")

        # [1] Set module_name to empty/None initially.
        # The Registry.register_module() method MUST update this field later.
        func.haruka_meta = CommandMeta(
            name=trigger,
            handler=func,
            module_name="",  # Placeholder, will be injected by Registry
            aliases=list(safe_aliases), # Convert back to list if CommandMeta expects list
            flags=flags
        )
        return func

    return wrapper