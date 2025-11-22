import time
import sys
import os
from system.decorators import command
from system.config import Config

# Start time for uptime calculation
START_TIME = time.time()

def get_uptime():
    delta = int(time.time() - START_TIME)
    days, rem = divmod(delta, 86400)
    hours, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)
    return f"{days}d {hours}h {mins}m"

@command("info", aliases=["stats", "bot"])
async def haruka_info(ctx):
    """
    Shows system status and user info with a photo.
    Usage: .info
    """
    # 1. Animation / Loading
    await ctx.respond("⚡️ <b>Haruka</b> is collecting data...")
    start_ms = time.time()
    
    # 2. Gather Data
    me = await ctx.client.get_me()
    end_ms = time.time()
    ping = int((end_ms - start_ms) * 1000)
    
    # Count plugins
    plugin_count = len([f for f in os.listdir(Config.PLUGINS_DIR) if f.endswith(".py")])
    
    # 3. Formatting the Text (Dashboard Style)
    caption = (
        f"🌸 <b>HARUKA CORE v4</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>USER PROFILE</b>\n"
        f"┣ <b>Name:</b> {me.first_name}\n"
        f"┣ <b>ID:</b> <code>{me.id}</code>\n"
        f"┣ <b>DC:</b> {me.photo.dc_id if me.photo else 'N/A'}\n"
        f"┗ <b>Username:</b> @{me.username if me.username else 'None'}\n\n"
        
        f"⚙️ <b>SYSTEM STATUS</b>\n"
        f"┣ <b>Uptime:</b> <code>{get_uptime()}</code>\n"
        f"┣ <b>Ping:</b> <code>{ping}ms</code>\n"
        f"┗ <b>Plugins:</b> <code>{plugin_count}</code> active\n\n"
        
        f"🚀 <i>Plug-and-Play Edition</i>"
    )
    
    # 4. Sending Photo + Text
    # We delete the command message and send a fresh one with media
    await ctx.event.delete()
    
    # Download profile photo to cache (or use fallback)
    photo = await ctx.client.download_profile_photo("me")
    
    if photo:
        await ctx.client.send_file(
            ctx.event.chat_id,
            photo,
            caption=caption,
            parse_mode="html"
        )
        os.remove(photo) # Clean up
    else:
        # If no pfp, just send text
        await ctx.client.send_message(
            ctx.event.chat_id,
            caption,
            parse_mode="html"
        )

# --- MANAGEMENT COMMANDS ---

@command("setname")
async def set_name(ctx):
    """
    Changes your Telegram name.
    Usage: .setname New Name
    """
    if not ctx.input:
        return await ctx.err("Please provide a new name.")
    
    try:
        await ctx.client.update_profile(first_name=ctx.input)
        await ctx.ok(f"Name changed to: <b>{ctx.input}</b>")
    except Exception as e:
        await ctx.err(f"Failed to change name: {e}")

@command("setbio")
async def set_bio(ctx):
    """
    Changes your Telegram bio (about).
    Usage: .setbio I am using Haruka!
    """
    if not ctx.input:
        return await ctx.err("Please provide a bio text.")
    
    try:
        # Bio length limit is 70 chars usually
        if len(ctx.input) > 70:
            return await ctx.warn("Bio is too long (max 70 chars).")
            
        await ctx.client.update_profile(about=ctx.input)
        await ctx.ok("Bio updated successfully!")
    except Exception as e:
        await ctx.err(f"Failed to update bio: {e}")

@command("setpfp", aliases=["setava"])
async def set_pfp(ctx):
    """
    Sets a new profile picture from reply.
    Usage: Reply to an image with .setpfp
    """
    reply = await ctx.get_reply()
    if not reply or not reply.media:
        return await ctx.err("Reply to an image!")
    
    await ctx.warn("🔄 Updating profile picture...")
    
    try:
        # Download media
        photo = await reply.download_media()
        # Upload as profile photo
        await ctx.client.upload_profile_photo(file=photo)
        # Cleanup
        os.remove(photo)
        
        await ctx.ok("Profile picture updated! ✨")
    except Exception as e:
        await ctx.err(f"Error: {e}")