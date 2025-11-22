import asyncio
from system.decorators import command

@command("type", aliases=["print"])
async def typewriter(ctx):
    """
    Typewriter effect.
    Usage: .type <text>
    """
    if not ctx.input:
        return await ctx.err("Enter text to type!")

    text = ctx.input
    current_text = ""
    
    # Cursor symbol
    cursor = " █" 
    
    try:
        for char in text:
            current_text += char
            # Edit message: add letter + cursor
            await ctx.respond(f"{current_text}{cursor}")
            # Small delay for effect (0.05 - 0.1 sec)
            await asyncio.sleep(0.05)
        
        # Remove cursor at the end
        await ctx.respond(current_text)
        
    except Exception as e:
        # If message was deleted during typing - no problem
        pass