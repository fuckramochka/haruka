# Haruka Userbot — Documentation (EN)

Haruka is a fast, modular Telegram userbot — a modern fork of Heroku/Hikka,
rebranded and heavily optimized. It keeps full module (plugin) compatibility
while being noticeably faster to boot and lighter on memory.

---

## ✨ Key features

- **Full module support** — install plugins with a single command; old
  Heroku/Hikka plugins keep working thanks to a transparent import redirect.
- **`harukatl` engine** — the Telegram layer is exposed as `harukatl`; any
  `harukatl` / `telethon` / `hikkatl` import is transparently redirected to the
  real high-performance library.
- **Fast startup** — compiled-bytecode cache, `uvloop`, and `orjson` make warm
  restarts dramatically quicker.
- **Low memory** — bounded LRU+TTL entity cache and `__slots__` on hot objects.
- **Inline mode** — control the bot through inline buttons and forms.
- **Web dashboard** — configure everything from a browser.
- **Built-in modules** — system info, `neofetch` card, personal notes,
  translations, terminal, updater, security, presets and more.
- **Cross-platform** — Linux, macOS, FreeBSD, Termux (Android), UserLAnd,
  Windows.

---

## 🚀 Quick install

### Linux / macOS / FreeBSD / Termux / UserLAnd

```sh
git clone https://github.com/coddrago/Heroku Haruka
cd Haruka
chmod +x start.sh
./start.sh
```

### Windows

```bat
git clone https://github.com/coddrago/Heroku Haruka
cd Haruka
start.bat
```

Or with PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

The **first run** automatically installs system dependencies, creates a virtual
environment (`.venv`) and downloads every required library. Later runs just
start the bot.

> Requires **Python 3.10+**.

---

## 🔑 How to get API ID and API HASH

Haruka logs into your Telegram account through the official API, so you need a
personal **API ID** and **API HASH**:

1. Open **https://my.telegram.org** in a browser.
2. Log in with your phone number (you'll get a code in Telegram).
3. Click **API development tools**.
4. Fill in the form:
   - **App title**: `Haruka` (anything)
   - **Short name**: `haruka`
   - **Platform**: Desktop
5. Press **Create application**.
6. Copy your **`api_id`** (a number) and **`api_hash`** (a long string).

During the first launch Haruka will ask for these values (or open the web setup
page). Keep them **private** — they are tied to your account.

---

## 🔄 Keeping it running 24/7

See `deploy/README.md` for ready-to-use auto-restart setups:

- **Linux**: `systemd` user service (`deploy/haruka.service`)
- **Android/Termux**: boot script with restart loop (`deploy/termux-boot-haruka.sh`)
- **Windows**: Task Scheduler recipe

---

## 🧩 Managing modules

- Send your bot `.help` to list commands.
- Install a module: reply to a `.py` file with `.loadmod`, or use
  `.dlmod <name>` from a repo.
- Remove a module: `.unloadmod <name>`.

---

## ❓ Troubleshooting

- **Python 3.10+ not found** — install it and re-run the launcher.
- **First run is slow** — that's the one-time dependency download; subsequent
  starts are fast.
- **git errors** — set the environment variable `HARUKA_NO_GIT=1` to run
  without git.
