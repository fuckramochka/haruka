from system.decorators import command

@command("help", aliases=["h"])
async def help_cmd(ctx):
    """
    Shows command list or module help.
    Usage: .help or .help <module/command>
    """
    registry = ctx.engine.registry
    
    # 1. If no arguments - show module list
    if not ctx.args:
        modules = {}
        # Group commands by modules
        for name, cmd in registry.commands.items():
            mod_name = cmd.module_name.split('.')[-1] # plugins.ping -> ping
            if mod_name not in modules:
                modules[mod_name] = []
            if name not in modules[mod_name]: # Avoid alias duplicates
                modules[mod_name].append(name)

        count_mods = len(modules)
        count_cmds = len(registry.commands)
        
        text = (
            f"🌸 <b>Haruka Help</b>\n"
            f"Modules: {count_mods} | Commands: {count_cmds}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        for mod, cmds in sorted(modules.items()):
            # Sort commands and show first 3 + count
            preview = ", ".join(sorted(cmds)[:4])
            if len(cmds) > 4: preview += "..."
            
            text += f"📦 <b>{mod}:</b> <code>{preview}</code>\n"
            
        text += "\nℹ️ Write <code>.help name</code> for details."
        await ctx.respond(text)
        return

    # 2. If there's an argument - search for module or command
    query = ctx.args[0].lower()

    # A) Search for command
    if query in registry.commands:
        cmd = registry.commands[query]
        aliases = ", ".join(cmd.aliases) if cmd.aliases else "None"
        text = (
            f"📑 <b>Command:</b> <code>.{cmd.name}</code>\n"
            f"📦 <b>Module:</b> {cmd.module_name}\n"
            f"🔗 <b>Aliases:</b> {aliases}\n"
            f"📝 <b>Description:</b>\n{cmd.doc.strip()}"
        )
        await ctx.respond(text)
        return

    # B) Search for module
    # (Need to go through all commands and find those belonging to the module)
    found_cmds = []
    for name, cmd in registry.commands.items():
        if query in cmd.module_name:
            found_cmds.append(f"<code>.{name}</code>")
    
    # Remove duplicates (due to aliases)
    found_cmds = sorted(list(set(found_cmds)))

    if found_cmds:
        text = (
            f"📦 <b>Module:</b> {query}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{', '.join(found_cmds)}"
        )
        await ctx.respond(text)
    else:
        await ctx.err(f"Nothing found for query <b>{query}</b>")