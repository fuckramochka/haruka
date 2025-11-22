import os
import asyncio
from system.decorators import command
from system.repo_manager import repo_manager
from system.config import Config

@command("add", aliases=["install"])
async def local_install(ctx):
    """
    Installs plugin via file reply.
    Usage: reply + .add
    """
    reply = await ctx.event.get_reply_message()
    if not reply or not reply.file:
        return await ctx.err("Make a reply to a .py file")
    
    name = reply.file.name
    if not name.endswith(".py"):
        return await ctx.err("This is not a Python file!")
        
    path = os.path.join(Config.PLUGINS_DIR, name)
    
    await ctx.warn(f"📥 Local installation of <b>{name}</b>...")
    await reply.download_media(file=path)
    
    ok, msg = await ctx.engine.loader.load_file(path)
    if ok:
        # If this is a local file, we don't write it to repo_manager (or can write as local)
        await ctx.ok(f"Plugin <b>{name}</b> installed!")
    else:
        await ctx.err(f"Error: {msg}")
        if os.path.exists(path): os.remove(path)

@command("remove", aliases=["uninstall", "rm"])
async def remove_plugin(ctx):
    """Removes plugin: .remove cute"""
    if not ctx.args: return await ctx.err("Specify module name")
    
    name = ctx.args[0]
    full_name = f"plugins.{name}"
    path = os.path.join(Config.PLUGINS_DIR, f"{name}.py")
    
    if full_name in ctx.engine.registry.modules:
        await ctx.engine.registry.remove_module(full_name)
        if os.path.exists(path):
            os.remove(path)
        await ctx.ok(f"Module <b>{name}</b> removed.")
    else:
        await ctx.err("Module not found or it's a system module.")

@command("update", aliases=["up"])
async def update_plugin(ctx):
    """
    Updates plugin.
    .update (reply to file) -> overwrites file
    .update <name> -> pulls from repository (if installed from there)
    """
    # Option 1: Update via file reply
    reply = await ctx.event.get_reply_message()
    if reply and reply.file:
        return await local_install(ctx)

    # Option 2: Update by name
    if not ctx.args:
        return await ctx.err("Specify module name to update or .haruka update for all.")
        
    name = ctx.args[0]
    url = repo_manager.get_installed_url(name)
    
    if not url:
        return await ctx.err(f"Module <b>{name}</b> was installed manually. Update it via .add (reply).")
        
    await ctx.warn(f"🔄 Updating <b>{name}</b> from cloud...")
    content = await repo_manager.fetch_file(url)
    
    if not content:
        return await ctx.err("Failed to download file. Link is inactive.")
        
    path = os.path.join(Config.PLUGINS_DIR, f"{name}.py")
    with open(path, "wb") as f:
        f.write(content)
        
    ok, msg = await ctx.engine.loader.load_file(path)
    if ok:
        await ctx.ok(f"Module <b>{name}</b> updated!")
    else:
        await ctx.err(f"Update error: {msg}")

# === HARUKA PACKAGE MANAGER SYSTEM ===

@command("haruka")
async def haruka_manager(ctx):
    """
    Haruka package manager.
    .haruka add <link> — add repo
    .haruka install <name> — install from repo
    .haruka update — update all plugins
    """
    if not ctx.args:
        return await ctx.respond(
            "📦 <b>Haruka Package Manager</b>\n"
            "<code>.haruka add (link)</code> - Add repository\n"
            "<code>.haruka install (name)</code> - Install plugin\n"
            "<code>.haruka list</code> - List of repositories\n"
            "<code>.haruka update</code> - Update all installed"
        )
    
    subcmd = ctx.args[0].lower()
    
    # --- ADD REPO ---
    if subcmd == "add":
        if len(ctx.args) < 2: return await ctx.err("Specify GitHub link!")
        url = ctx.args[1]
        if repo_manager.add_repo(url):
            await ctx.ok(f"Repository added!\n🔗 {url}")
        else:
            await ctx.warn("This repository is already in the list.")

    # --- LIST REPOS ---
    elif subcmd == "list":
        repos = repo_manager.get_all_repos()
        if not repos: return await ctx.warn("Repository list is empty.")
        text = "🔗 <b>Connected repositories:</b>\n" + "\n".join(repos)
        await ctx.respond(text)

    # --- INSTALL PLUGIN ---
    elif subcmd == "install":
        if len(ctx.args) < 2: return await ctx.err("Specify plugin name!")
        target_name = ctx.args[1]
        specific_repo = None
        
        # Check repo:Name
        if "repo:" in " ".join(ctx.args):
            for arg in ctx.args:
                if arg.startswith("repo:"):
                    specific_repo = arg.split(":")[1]
                    target_name = target_name.replace(f" {arg}", "").strip() # remove from name
                    
        await ctx.warn(f"🔎 Searching for <b>{target_name}.py</b> in repositories...")
        
        repos = repo_manager.get_all_repos()
        found_in = []
        
        # File search (this might be slow if many repos)
        # We check file availability in each repo
        valid_url = None
        
        for repo in repos:
            # Form URL
            # If specific_repo is specified, check if repo name matches
            if specific_repo and specific_repo.lower() not in repo.lower():
                continue
                
            check_url = f"{repo}/{target_name}.py"
            # Make HEAD request (or just GET first bytes) for check
            # (Simplified here: just download, if 404 then continue)
            content = await repo_manager.fetch_file(check_url)
            if content:
                found_in.append((repo, check_url, content))

        if not found_in:
            return await ctx.err(f"Plugin <b>{target_name}</b> not found in connected repos.")
            
        if len(found_in) > 1 and not specific_repo:
            # Conflict
            text = f"⚠️ <b>Found multiple versions of '{target_name}':</b>\n"
            for r, _, _ in found_in:
                repo_short = r.split("/")[-2] + "/" + r.split("/")[-1]
                text += f"• <code>{repo_short}</code>\n"
            text += f"\nSpecify: <code>.haruka install {target_name} repo:User/Repo</code>"
            return await ctx.respond(text)

        # Installation
        repo_url, dl_url, content = found_in[0]
        path = os.path.join(Config.PLUGINS_DIR, f"{target_name}.py")
        
        with open(path, "wb") as f:
            f.write(content)
            
        ok, msg = await ctx.engine.loader.load_file(path)
        if ok:
            repo_manager.record_install(target_name, dl_url)
            await ctx.ok(f"Installed <b>{target_name}</b> from {repo_url}")
        else:
            await ctx.err(f"Loading error: {msg}")
            os.remove(path)

    # --- UPDATE ALL ---
    elif subcmd == "update":
        installed = repo_manager.get_all_installed()
        if not installed: