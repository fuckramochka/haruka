# 🌸 Haruka v4 Core: Plug-and-Play Edition

**The Next-Generation Telegram Userbot Framework.**

Haruka v4 is designed to be the most stable, fast, and user-friendly userbot. It requires **zero configuration**. Just download, run, and enjoy.

---

## 🚀 Quick Start (For Users)

### 1. Installation

You need **Python 3.8 or higher**.

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run Haruka
python main.py
```

2. First Run

On the first launch, Haruka will ask for your:

· Phone Number
· Telegram Code

This happens only once. A session file (HARUKA.session) will be created automatically.

Once logged in, you will see:
✅ Logged in as: YourName

3. Basic Commands

Command Description
.help Show all available modules and commands
.ping Check if the bot is alive and see response speed
.alive Show system statistics (Uptime, Version)
.cute Toggle "Cute Mode" (makes your messages kawaii)

4. 📦 Plugin Manager (How to install plugins)

Haruka has a powerful package manager built-in. You don't need to touch files manually.

Install from Chat:

1. Send a .py file to "Saved Messages"
2. Reply to it with .add (or .install)
3. Done! The plugin is active immediately

Install from GitHub:

· .haruka add <link> — Add a repository
· .haruka install <name> — Install a plugin from the repo
· .haruka update — Update all installed plugins

Remove Plugin:

· .remove <name> — Deletes the plugin instantly

---

🛠 Developer Guide (How to write Plugins)

Haruka v4 uses a strictly typed, event-driven architecture.

Key Principles:

· HTML Only: All responses use HTML (<b>bold</b>, not bold)
· Context-Based: You interact with ctx, not raw events
· Hot Reload: Changes apply instantly upon .update

📂 File Structure Overview

File Purpose
main.py The entry point. Initializes the Engine
plugins/ YOUR PLAYGROUND. Put your custom .py files here
system/config.py Hardcoded API keys and settings. Zero-config for users
system/engine.py The Kernel. Manages Client, DB, and Dispatcher
system/loader.py Hot Reload Logic. Safely imports/unloads modules
system/context.py API Layer. Wraps Telethon events into the ctx object
system/database.py Async SQLite wrapper (kv table)
system/registry.py Thread-safe command storage

📝 Writing Your First Plugin

Create a file plugins/example.py

```python
from system.decorators import command

# 1. Basic Command
@command("hello", aliases=["hi", "hey"])
async def hello_handler(ctx):
    """
    Sends a greeting.
    Usage: .hello
    """
    # Use HTML tags for formatting!
    await ctx.respond("👋 Hello! I am <b>Haruka v4</b>.")

# 2. Command with Arguments
@command("echo")
async def echo_handler(ctx):
    """
    Repeats your text.
    Usage: .echo <text>
    """
    # ctx.input contains everything after the command
    if not ctx.input:
        return await ctx.err("Please provide some text!")
    
    await ctx.ok(f"You said: <code>{ctx.input}</code>")

# 3. Database Interaction
@command("setbio")
async def bio_handler(ctx):
    # Save data to SQLite (Async)
    # The DB is available via ctx.engine.db
    await ctx.engine.db.set("my_bio", ctx.input)
    await ctx.ok("Bio saved to database!")
```

🧠 The Context Object API

The ctx object is passed to every command handler.

Attribute/Method Description
ctx.args List of arguments (e.g., .cmd arg1 arg2 → ['arg1', 'arg2'])
ctx.input Raw string after command (e.g., .cmd Hello World → "Hello World")
ctx.respond(text) Edits (if outgoing) or Replies (if incoming). Supports HTML
ctx.err(text) Sends an error message: ⛔ Error: text
ctx.ok(text) Sends a success message: ✅ Success: text
ctx.warn(text) Sends a warning: ⚠️ Warning: text
ctx.delete() Deletes the command message
ctx.get_reply() Returns the message object you replied to (async)
ctx.engine.db Access to the Database (.get(key), .set(key, val))

⚡ Advanced: Middleware & Listeners

If you need to listen to every message (like for AFK or Cute Mode), use the register hook.

```python
from telethon import events
from system.config import Config

# This function is automatically called by the Loader
async def register(engine):
    
    @engine.client.on(events.NewMessage(outgoing=True))
    async def my_middleware(event):
        # Ignore commands
        if event.raw_text.startswith(Config.PREFIX):
            return
        
        # Do logic...
        print(f"I saw a message: {event.raw_text}")
```

---

⚠️ Common Pitfalls

Do not use Markdown:

· ❌ ctx.respond("**Bold**") → Will print stars
· ✅ ctx.respond("<b>Bold</b>") → Correct

Database Keys:

· Always prefix your DB keys to avoid collisions
· Example: Use afk_status or notes_list

Imports:

· Always import from system.decorators and system.config
· Do not try to import main.py

---

💎 Why Haruka v4 is Better?

· Atomic Loading: If your plugin has a syntax error, Haruka catches it and keeps the old version running. No crashes
· Rate Limiter: Built-in protection against Telegram FloodWait bans
· Zero Config: Users don't need to edit .env files
· Plug-and-Play: Drop a file in plugins/, and it works instantly
