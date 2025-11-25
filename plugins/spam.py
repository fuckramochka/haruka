import asyncio
from system.decorators import command

спамим = False
отправленные = []

@command("delspam", aliases=[])
async def delspam(ctx):
    global спамим, отправленные
    if спамим:
        return await ctx.err("⚠️ Уже спамлю. Напиши `.stopspam`, чтобы остановить.")

    if not ctx.input:
        return await ctx.err("⚠️ Напиши сообщение для спама: `.delspam текст`")

    текст = ctx.input
    спамим = True
    отправленные = []
    задержка = 0.5

    await ctx.respond("🚀 Начал обычный спам. Напиши `.stopspam`, чтобы остановить и удалить.")

    async def spam_loop():
        global спамим
        while спамим:
            try:
                msg = await ctx.send_message(текст)  # Надсилаємо точно
                отправленные.append(msg.id)
            except Exception as e:
                await ctx.respond(f"❌ Ошибка: {e}")
            await asyncio.sleep(задержка)

    asyncio.create_task(spam_loop())  # Запускаємо у фоновому таску

@command("fastspam", aliases=[])
async def fastspam(ctx):
    global спамим, отправленные
    if спамим:
        return await ctx.err("⚠️ Уже спамлю. Напиши `.stopspam`, чтобы остановить.")

    if not ctx.input:
        return await ctx.err("⚠️ Напиши сообщение для спама: `.fastspam текст`")

    текст = ctx.input
    спамим = True
    отправленные = []
    задержка = 0.01

    await ctx.respond("🚀 Начал быстрый спам. Напиши `.stopspam`, чтобы остановить и удалить.")

    async def spam_loop():
        global спамим
        while спамим:
            try:
                msg = await ctx.send_message(текст)
                отправленные.append(msg.id)
            except Exception as e:
                await ctx.respond(f"❌ Ошибка: {e}")
            await asyncio.sleep(задержка)

    asyncio.create_task(spam_loop())

@command("spam", aliases=[])
async def spam(ctx):
    global спамим
    if спамим:
        return await ctx.err("⚠️ Уже спамлю. Напиши `.stopspam`, чтобы остановить.")

    if not ctx.input:
        return await ctx.err("⚠️ Напиши сообщение для спама: `.spam текст`")

    текст = ctx.input
    спамим = True
    задержка = 0.1

    await ctx.respond("📢 Начал спам. Напиши `.stopspam`, чтобы остановить.")

    async def spam_loop():
        global спамим
        while спамим:
            try:
                await ctx.send_message(текст)
            except Exception as e:
                await ctx.respond(f"❌ Ошибка: {e}")
            await asyncio.sleep(задержка)

    asyncio.create_task(spam_loop())

@command("stopspam", aliases=[])
async def stopspam(ctx):
    global спамим, отправленные
    if not спамим:
        return await ctx.err("❌ Сейчас я не спамлю.")

    спамим = False
    await ctx.respond("🛑 Спам остановлен.")

    if отправленные:
        await ctx.respond("🧹 Удаляю спам-сообщения...")
        for msg_id in отправленные:
            try:
                await ctx.client.delete_messages(ctx.chat_id, msg_id)
            except:
                pass
        отправленные = []
        await ctx.respond("✅ Всё удалено.")