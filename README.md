<div align="center">
  <h1>🌸 Haruka Userbot</h1>
  <p>Independent Telegram userbot with universal module compatibility</p>

  <p>
    <a href="#"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"></a>
    <a href="#"><img src="https://img.shields.io/badge/modules-hikka%20%7C%20heroku%20%7C%20ftg%20%7C%20geektg-green" alt="Compatibility"></a>
    <a href="#"><img src="https://img.shields.io/badge/license-AGPLv3-red" alt="License"></a>
  </p>

  🇺🇦 [Українська версія](README_UA.md)
</div>

---

## ✨ What is Haruka

Haruka is a **Telegram userbot**: an automation framework running on your own
account. Built on the actively developed [Telethon](https://github.com/LonamiWebs/Telethon)
(fresh API layer → full support for forums, premium emojis, stories and other new
Telegram features), with its own module system and a **universal compatibility layer**:

| Ecosystem | Imports | Client attributes | DB keys |
|------------|---------|------------------|----------|
| 🌸 Haruka (native) | `haruka.*` | `client.haruka_*` | `haruka.*` |
| 🪐 Heroku | `heroku.*`, `herokutl.*` → auto | `client.heroku_*` → auto | `heroku.*` → auto-migrated |
| 💜 Hikka | `hikka.*`, `hikkatl.*` → auto | `client.hikka_*` → auto | `hikka.*` → auto-migrated |
| 🔮 FTG / GeekTG | imports rewritten on load | — | — |

Modules written for any of these forks **run unmodified**.

## 🔓 Independence

- ✅ **No kill switches**: the bot always starts, even when third-party servers are unreachable
- ✅ **Setup panel is localhost-only** (`127.0.0.1`); a public tunnel (serveo/localhost.run)
  is opened only with the explicit `--proxy-pass` flag
- ✅ **Your own update source**: change `GIT_ORIGIN_URL` in the `.updater` module config
  (or the `HARUKA_REPO_URL` environment variable) — update checks, compare links and
  version polling automatically follow *your* repository
- ✅ Announcements can be disabled/redirected via the `"announcement_url"` key in `config.json`
- ✅ pip-installable: `pip install .`

## 🚀 Quick start (Linux / macOS / WSL)

```bash
sudo apt update && sudo apt install git python3 python3-venv -y && \
git clone <repo-url> && cd Haruka && \
python3 -m venv .venv && source .venv/bin/activate && \
pip install -r requirements.txt && \
python3 -m haruka
```

Or via pyproject (instead of requirements.txt):

```bash
pip install . && python3 -m haruka
```

### Docker

```bash
docker compose up -d --build
```

### Windows / Android

Use [WSL](https://learn.microsoft.com/en-us/windows/wsl/install) on Windows or
[UserLAnd](https://play.google.com/store/apps/details?id=tech.ula) on Android, then
follow the Linux instructions above. Native Windows run is also supported:
double-click `install.bat` (creates venv, installs deps, starts the bot).

## 🩺 Diagnostics

| Command | Description |
|---------|------|
| `.health` / `.diag` | Uptime, versions, CPU/RAM, event-loop lag, cache sizes, module stats |
| `.gcstats` | Force garbage collection and report freed memory |

## 🧰 Built-in extras

| Tool / command | Description |
|----------------|-------------|
| `.afk [reason]` | AFK mode with anti-flood auto-replies, survives restart |
| `.note / .notes / .delnote` | Quick personal notes |
| `.undo [N]` | Delete your last N messages in a chat |
| Fuzzy suggestions | Opt-in "did you mean …?" hints for typos in commands (`suggest_commands` db key, **off by default** — unknown dotted text is always ignored silently) |
| `--dry-run` | Validate config + module syntax offline, no connection |
| `/healthz` | Liveness endpoint for Docker/K8s (healthcheck preconfigured) |
| `tools/selfcheck.py` | Offline self-test of the compatibility layer and core logic |
| `tools/newmodule.py <Name>` | Scaffold a new module template in seconds |
| Security scan | External modules are statically analyzed on load; dangerous patterns are logged |

Self-check without a Telegram connection:

```bash
python tools/selfcheck.py
```

## 🔑 API credentials

1. Open [my.telegram.org/apps](https://my.telegram.org/apps)
2. Create an application to get `API_ID` and `API_HASH`
3. Enter them on first Haruka launch

## ♻️ Migrating from Hikka / Heroku

Just run Haruka alongside your existing installation: sessions, config and database
are recognized automatically; `hikka.*` / `heroku.*` keys are converted to `haruka.*`.

## ⚠️ Security

> Installing modules from untrusted developers may harm your account.
> Download modules only from trusted sources. Be careful with commands like
> `.terminal` and `.eval`. Enable `.api_fw_protection`.

## 🙏 Acknowledgements

- [**Lonami**](https://github.com/LonamiWebs) — Telethon
- [**Hikari**](https://gitlab.com/hikariatama) — Hikka (project foundation)
- **Coddrago** — Heroku (intermediate fork)
- **Haruka contributors** — this project

## 📄 License

[AGPLv3](LICENSE)
