import asyncio
import random
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
    cursor = " █"
    
    # Оптимізація:
    # Telegram дозволяє редагувати повідомлення десь раз на секунду без лімітів,
    # або чергами. Щоб ефект був гарним і безпечним, краще друкувати по 2-3 символи,
    # або робити затримку трохи більшою.
    
    try:
        for i, char in enumerate(text):
            current_text += char
            
            # Редагуємо повідомлення на кожному кроці
            # Але якщо текст довгий, краще пропускати деякі кроки, щоб не зловити флуд
            # (тут залишаємо посимвольно, але збільшимо sleep)
            
            try:
                await ctx.respond(f"{current_text}{cursor}")
            except Exception:
                # Ігноруємо помилки під час швидкого друку
                pass
            
            # Випадкова затримка для реалістичності (0.1 - 0.25 сек)
            # Це набагато безпечніше ніж 0.05
            await asyncio.sleep(random.uniform(0.1, 0.25))
        
        # Фінальний текст без курсора
        await ctx.respond(current_text)
        
    except Exception as e:
        pass