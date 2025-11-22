from .registry import CommandMeta

def command(name: str = None, aliases: list = None, **flags):
    if aliases is None: aliases = []
    def wrapper(func):
        trigger = name if name else func.__name__
        func.haruka_meta = CommandMeta(
            name=trigger,
            handler=func,
            module_name="pending",
            aliases=aliases,
            flags=flags
        )
        return func
    return wrapper