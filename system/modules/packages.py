import os
import asyncio
from system.decorators import command
from system.repo_manager import repo_manager
from system.config import Config

@command("add", aliases=["install"])
async def local_install(ctx):
    """
    Installs plugin via file reply.
    Usage: reply to a .py file + .add
    """
    reply = await ctx.event.get_reply_message()
    if not reply or not reply.file:
        return await ctx.err("Make a reply to a .py file")
    
    name = reply.file.name
    if not name:
        name = f"plugin_{reply.id}.py"

    if not name.endswith(".py"):
        return await ctx.err("This is not a Python file!")
        
    path = os.path.join(Config.PLUGINS_DIR, name)
    
    await ctx.warn(f"📥 Local installation of <b>{name}</b>...")
    await reply.download_media(file=path)
    
    ok, msg = await ctx.engine.loader.load_file(path)
    if ok:
        # Локальні файли не записуємо в repo_manager як "встановлені з репо"
        await ctx.ok(f"Plugin <b>{name}</b> installed!")
    else:
        await ctx.err(f"Error: {msg}")
        # Якщо не завантажився — видаляємо, щоб не смітити
        if os.path.exists(path): 
            os.remove(path)

@command("remove", aliases=["uninstall", "rm"])
async def remove_plugin(ctx):
    """
    Removes plugin.
    Usage: .remove <plugin_name>
    """
    if not ctx.args: 
        return await ctx.err("Specify module name")
    
    name = ctx.args[0]
    # Перевіряємо, чи це плагін (user) чи системний модуль
    full_name_plugin = f"plugins.{name}"
    
    path = os.path.join(Config.PLUGINS_DIR, f"{name}.py")
    
    # Видаляємо з реєстру
    if full_name_plugin in ctx.engine.registry.modules:
        await ctx.engine.registry.remove_module(full_name_plugin)
        
        # Видаляємо файл фізично
        if os.path.exists(path):
            os.remove(path)
            
        # Видаляємо запис з менеджера пакетів (якщо був встановлений з репо)
        repo_manager.remove_install_record(name)
        
        await ctx.ok(f"Module <b>{name}</b> removed.")
    else:
        await ctx.err(f"Module <b>{name}</b> not found or it is a system module (cannot remove system modules).")

@command("update", aliases=["up"])
async def update_plugin(ctx):
    """
    Updates specific plugin.
    1. .update (reply to file) -> Overwrite with file
    2. .update <name> -> Pull from repository (if tracked)
    """
    # Варіант 1: Оновлення через реплай файлом
    reply = await ctx.event.get_reply_message()
    if reply and reply.file:
        return await local_install(ctx)

    # Варіант 2: Оновлення за іменем з репозиторію
    if not ctx.args:
        return await ctx.err("Specify module name to update or use .haruka update for all.")
        
    name = ctx.args[0]
    url = repo_manager.get_installed_url(name)
    
    if not url:
        return await ctx.err(f"Module <b>{name}</b> was installed manually. Update it via .add (reply) or delete and install from repo.")
        
    await ctx.warn(f"🔄 Updating <b>{name}</b> from cloud...")
    content = await repo_manager.fetch_file(url)
    
    if not content:
        return await ctx.err("Failed to download file. Source link might be dead.")
        
    path = os.path.join(Config.PLUGINS_DIR, f"{name}.py")
    with open(path, "wb") as f:
        f.write(content)
        
    ok, msg = await ctx.engine.loader.load_file(path)
    if ok:
        await ctx.ok(f"Module <b>{name}</b> updated successfully!")
    else:
        await ctx.err(f"Update error: {msg}")

# === HARUKA PACKAGE MANAGER SYSTEM ===

@command("haruka")
async def haruka_manager(ctx):
    """
    Haruka package manager.
    .haruka add <link> — Add repository (raw github link)
    .haruka install <name> — Install plugin from added repos
    .haruka list — List connected repositories
    .haruka update — Check updates for all repo-installed plugins
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
        if len(ctx.args) < 2: 
            return await ctx.err("Specify GitHub link (Raw or folder URL)!")
        
        url = ctx.args[1]
        # Проста нормалізація URL (якщо юзер кинув посилання на дерево файлів, а не raw)
        if "github.com" in url and "raw.githubusercontent.com" not in url:
             url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")

        if repo_manager.add_repo(url):
            await ctx.ok(f"Repository added!\n🔗 {url}")
        else:
            await ctx.warn("This repository is already in the list.")

    # --- LIST REPOS ---
    elif subcmd == "list":
        repos = repo_manager.get_all_repos()
        if not repos: 
            return await ctx.warn("Repository list is empty.")
        text = "🔗 <b>Connected repositories:</b>\n" + "\n".join([f"• {r}" for r in repos])
        await ctx.respond(text)

    # --- INSTALL PLUGIN ---
    elif subcmd == "install":
        if len(ctx.args) < 2: 
            return await ctx.err("Specify plugin name!")
        
        target_name = ctx.args[1]
        if target_name.endswith(".py"): 
            target_name = target_name[:-3]

        specific_repo = None
        
        # Підтримка синтаксису "install name repo:author"
        if "repo:" in " ".join(ctx.args):
            for arg in ctx.args:
                if arg.startswith("repo:"):
                    specific_repo = arg.split(":")[1]
                    target_name = target_name.replace(f" {arg}", "").strip() 
                    
        status = await ctx.warn(f"🔎 Searching for <b>{target_name}.py</b>...")
        
        repos = repo_manager.get_all_repos()
        found_in = []
        
        # Пошук файлу по всіх репозиторіях
        for repo in repos:
            if specific_repo and specific_repo.lower() not in repo.lower():
                continue
                
            # Формуємо URL (припускаємо структуру raw-репо)
            check_url = f"{repo}/{target_name}.py".replace("//", "/").replace("https:/", "https://")
            
            # Перевіряємо наявність (качаємо контент)
            content = await repo_manager.fetch_file(check_url)
            if content:
                found_in.append((repo, check_url, content))

        if not found_in:
            return await status.edit(f"❌ Plugin <b>{target_name}</b> not found in connected repos.")
            
        # Якщо знайдено більше 1 версії і не вказано конкретний репо
        if len(found_in) > 1 and not specific_repo:
            text = f"⚠️ <b>Found multiple versions of '{target_name}':</b>\n"
            for r, _, _ in found_in:
                repo_short = r.split("/")[-2] if len(r.split("/")) > 2 else r
                text += f"• In: <code>{repo_short}</code>\n"
            text += f"\nSpecify: <code>.haruka install {target_name} repo:PartialName</code>"
            return await status.edit(text)

        # Встановлення
        repo_url, dl_url, content = found_in[0]
        path = os.path.join(Config.PLUGINS_DIR, f"{target_name}.py")
        
        with open(path, "wb") as f:
            f.write(content)
            
        ok, msg = await ctx.engine.loader.load_file(path)
        if ok:
            repo_manager.record_install(target_name, dl_url)
            await status.edit(f"✅ Installed <b>{target_name}</b> from <code>{repo_url}</code>")
        else:
            await status.edit(f"❌ Loading error: {msg}")
            if os.path.exists(path):
                os.remove(path)

    # --- UPDATE ALL ---
    elif subcmd == "update":
        # Отримуємо список {plugin_name: source_url}
        installed = repo_manager.get_all_installed()
        
        if not installed:
            return await ctx.warn("No plugins installed via Package Manager.")
        
        status_msg = await ctx.respond(f"🔄 Checking updates for <b>{len(installed)}</b> plugins...")
        
        updated_count = 0
        failed = []
        
        for name, url in installed.items():
            try:
                # Завантажуємо нову версію
                content = await repo_manager.fetch_file(url)
                if not content:
                    failed.append(f"{name} (Link invalid/404)")
                    continue
                
                path = os.path.join(Config.PLUGINS_DIR, f"{name}.py")
                
                # Перезаписуємо
                with open(path, "wb") as f:
                    f.write(content)
                
                # Перезавантажуємо
                ok, msg = await ctx.engine.loader.load_file(path)
                if ok:
                    updated_count += 1
                else:
                    failed.append(f"{name} (Load Error: {msg})")
                    
            except Exception as e:
                failed.append(f"{name} (Exception: {e})")
                
        # Формуємо звіт
        text = f"📦 <b>Update finished</b>\n✅ Updated: <b>{updated_count}</b> plugins."
        
        if failed:
            text += "\n\n❌ <b>Failures:</b>\n"
            for f in failed:
                text += f"• {f}\n"
                
        await status_msg.edit(text)

    else:
        await ctx.err("Unknown subcommand. Usage: <code>.haruka [add|install|list|update]</code>")