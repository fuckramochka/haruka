import random
import re
import asyncio
from telethon import events
from system.decorators import command
from system.config import Config

# -----------------------
# Settings & Data
# -----------------------

THEMES = {
    "pastel": {
        "emojis": ["🌸", "🧁", "🍼", "🩰", "🎀", "🧸", "🍦", "🫧", "🤍", "🩷", "🩵", "🫐", "🐇"],
        "actions": ["*обнимает*", "*нежно обнимает*", "*гладит по голове*", "*хихикает*", "*мурлычет*", "*улыбается*", "*подмигивает*", "*машет лапкой*", "*краснеет*", "*прыгает от радости*"],
        "ascii": ["(✿◠‿◠)", "(＾◡＾)", "(｡♥‿♥｡)", "(づ｡◕‿‿◕｡)づ", "ヽ(＾Д＾)ﾉ", "＼(^-^)／", "(´｡• ᵕ •｡`)"]
    },
    "magical": {
        "emojis": ["✨", "🌟", "🔮", "🧚", "⭐", "🌙", "🪄", "🦄", "🧿", "🪞", "🔆"],
        "actions": ["*танцует от счастья*", "*делает милое личико*", "*радостно вздыхает*", "*хихикает*", "*улыбается*", "*подмигивает*"],
        "ascii": ["(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧", "✧٩(ˊωˋ*)و✧", "(❁´◡`❁)", "(◕‿◕✿)", "(⌒‿⌒)", "(✧ω✧)"]
    },
    "nature": {
        "emojis": ["🌷", "🌱", "🍄", "🦋", "🐝", "🌻", "🪴", "🌿", "🍃", "🌺", "🌼"],
        "actions": ["*играет с волосами*", "*качает хвостиком*", "*делает милое личико*", "*прячется за лапками*", "*улыбается*"],
        "ascii": ["(◕ᴗ◕✿)", "(⁄ ⁄>⁄ω⁄<⁄ ⁄)", "(✿´ ꒳ `)", "(꒦ິ⌑꒦ີ)", "(≧◡≦)", "(*^‿^*)"]
    }
}

ASCII_STICKERS = [
    "＼(^-^)／", "(≧◡≦)", "(｡♥‿♥｡)", "(づ｡◕‿‿◕｡)づ", "(✿◠‿◠)", "(＾◡＾)", "(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧",
    "(=^･ω･^=)", "(◕‿◕)", "ʕ•ᴥ•ʔ", "(❁´◡`❁)", "(●´ω｀●)", "(⌒‿⌒)", "✧٩(ˊωˋ*)و✧"
]

SUFFIXES = [
    "~", " nya~", " uwu", " owo", " >w<", " :3", " nyaaa", "σωσ", "◡ ω ◡", " OwO", " UwU~",
    " hehe~", " rawr~", " mew", " purr~", " ehehe", " uwu~", " (⁄ ⁄>⁄ω⁄<⁄ ⁄)", " kyaa~", " nyaa",
    " nyuu~", " mya~", " (◕ᴗ◕✿)", " teehee", " hehehe", " awoo~", " *blushes*", " purrr", " pwease", " nya?"
]

VOWELS = "аеёиоуыэюяАЕЁИОУЫЭЮЯaeiouyAEIOUY"

# -----------------------
# Logic
# -----------------------

def stretch_vowels(word: str, max_repeat: int = 3, chance: float = 0.3) -> str:
    if not word: return word
    out = []
    for ch in word:
        out.append(ch)
        if ch in VOWELS and random.random() < chance:
            out.append(ch * random.randint(1, max_repeat))
    return "".join(out)

def apply_speech_defect(word: str, chance: float = 0.45) -> str:
    if random.random() > chance:
        return word
    # Russian replacement
    word = re.sub(r"[рлРЛ]", "в", word)
    # English replacement
    word = re.sub(r"[rlRL]", "w", word)
    return word

def decorate_text(text: str) -> str:
    if not text or not text.strip(): return text

    theme_key = random.choice(list(THEMES.keys()))
    theme = THEMES[theme_key]
    weak_mode = len(text) >= 200

    words = text.split()
    decorated_words = []
    used_recent = []

    for word in words:
        # Ignore links and usernames
        if word.startswith("@") or "http" in word:
            decorated_words.append(word)
            continue

        # Transformations
        w = stretch_vowels(word, max_repeat=2 if weak_mode else 3, chance=0.25 if weak_mode else 0.35)
        w = apply_speech_defect(w, chance=0.45)

        # Decorations
        choice_type = random.choices(
            ["emoji", "ascii_sticker", "action"],
            weights=[0.35 if weak_mode else 0.55, 0.25, 0.10 if weak_mode else 0.20],
            k=1
        )[0]

        symbol = ""
        if choice_type == "emoji":
            symbol = random.choice(theme["emojis"])
        elif choice_type == "ascii_sticker":
            pool = theme.get("ascii", []) + ASCII_STICKERS
            symbol = random.choice(pool)
        else:
            pool = theme.get("actions", ["*улыбается*"])
            symbol = random.choice(pool)
            w = f"{w} "

        if symbol in used_recent:
            symbol = random.choice(theme["emojis"])
        
        used_recent.append(symbol)
        if len(used_recent) > 6: used_recent.pop(0)

        decorated = f"{w}{symbol}"
        
        if random.random() < (0.10 if weak_mode else 0.18):
            decorated += random.choice(SUFFIXES)

        decorated_words.append(decorated)

    base_text = " ".join(decorated_words)
    border_start = random.choice(["🌸 ", "✧･ﾟ: ", "— ♡ ", "꒰ ", "₊˚⊹ ", "⋆⭒˚｡⋆ ", "─── ⋆⋅☆⋅⋆ "])
    border_end = random.choice([" 🌸", " :･ﾟ✧", " ♡ —", " ꒱", " ⊹˚₊", " ⋆｡˚⭒⋆", " ⋆⋅☆⋅⋆ ───"])
    
    return f"{border_start}{base_text}{border_end}"[:4000]

# -----------------------
# Commands & Middleware
# -----------------------

@command("cute")
async def toggle_cute(ctx):
    """
    Toggles Cute Mode ON/OFF.
    Usage: .cute
    """
    current_state = await ctx.engine.db.get("cute_mode_enabled", False)
    new_state = not current_state
    
    await ctx.engine.db.set("cute_mode_enabled", new_state)
    
    # Using HTML tags now
    status = "✅ <b>Cute Mode Enabled!</b>" if new_state else "❌ <b>Cute Mode Disabled.</b>"
    await ctx.respond(status)

def register(engine):
    """
    Middleware hook automatically called by Haruka Loader.
    Listens for outgoing messages to decorate them.
    """
    
    @engine.client.on(events.NewMessage(outgoing=True))
    async def cute_middleware(event):
        # 1. Check DB state
        is_enabled = await engine.db.get("cute_mode_enabled", False)
        if not is_enabled: return

        text = event.raw_text
        
        # 2. Ignore commands
        if not text or text.startswith(Config.PREFIX): 
            return

        # 3. Process text
        try:
            new_text = decorate_text(text)
            if new_text and new_text != text:
                await asyncio.sleep(0.1) 
                # Note: parse_mode is usually handled by client, 
                # but raw edit might need explicit html if engine config isn't global enough.
                # However, engine dispatcher handles ctx, here we handle raw event.
                await event.edit(new_text, parse_mode='html')
        except Exception:
            pass