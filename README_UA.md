<div align="center">
  <h1>🌸 Haruka Userbot</h1>
  <p>Незалежний юзербот для Telegram з повною сумісністю модулів усіх основних форків</p>
</div>

---

## ✨ Що таке Haruka

Haruka — це **юзербот** для Telegram: фреймворк автоматизації, що працює на вашому акаунті.
Побудований на активній бібліотеці [Telethon](https://github.com/LonamiWebs/Telethon)
(свіжий API-шар → повна підтримка форумів, преміум-емодзі, сторіс та інших нових фіч Telegram),
з власною системою модулів і **універсальним шаром сумісності**:

| Екосистема | Імпорти | Атрибути клієнта | Ключі БД |
|------------|---------|------------------|----------|
| 🌸 Haruka (нативні) | `haruka.*` | `client.haruka_*` | `haruka.*` |
| 🪐 Heroku | `heroku.*`, `herokutl.*` → авто | `client.heroku_*` → авто | `heroku.*` → авто-міграція |
| 💜 Hikka | `hikka.*`, `hikkatl.*` → авто | `client.hikka_*` → авто | `hikka.*` → авто-міграція |
| 🔮 FTG / GeekTG | переписування імпортів на льоту | — | — |

Модулі, написані для будь-якого з цих форків, **працюють без змін**.

## 🔓 Незалежність

- ✅ **Немає кілл-свитчів**: бот стартує завжди, навіть якщо сторонні сервери недоступні
- ✅ **Панель налаштувань — лише локально** (`127.0.0.1`); публічний тунель (serveo/localhost.run)
  піднімається тільки з явним прапорцем `--proxy-pass`
- ✅ **Власне джерело оновлень**: змініть `GIT_ORIGIN_URL` у конфігу `.updater`
  (або змінну оточення `HARUKA_REPO_URL`) — перевірка оновлень, посилання
  та версіювання автоматично вказуватимуть на *ваш* репозиторій
- ✅ Оголошення можна вимкнути/перенаправити ключем `"announcement_url"` у `config.json`
- ✅ Встановлення через pip: `pip install .`

## 🚀 Швидкий старт (Linux / macOS / WSL)

```bash
sudo apt update && sudo apt install git python3 python3-venv -y && \
git clone <repo-url> && cd Haruka && \
python3 -m venv .venv && source .venv/bin/activate && \
pip install -r requirements.txt && \
python3 -m haruka
```

Або через pyproject (замість requirements.txt):

```bash
pip install . && python3 -m haruka
```

### Docker

```bash
docker compose up -d --build
```

### Windows / Android

Використайте [WSL](https://learn.microsoft.com/uk-ua/windows/wsl/install) на Windows або
[UserLAnd](https://play.google.com/store/apps/details?id=tech.ula) на Android,
далі — інструкція для Linux вище. Запуск напряму на Windows також підтримується:
запустіть `install.bat` (створює venv, встановлює залежності, стартує бота).

## 🩺 Діагностика

| Команда | Опис |
|---------|------|
| `.health` / `.diag` | Аптайм, версії, CPU/RAM, лаг event-loop, розміри кешів, статистика модулів |
| `.gcstats` | Примусове збирання сміття + звільнена пам'ять |

## 🧰 Вбудовані можливості

| Інструмент / команда | Опис |
|----------------------|------|
| `.afk [причина]` | AFK-режим з авто-відповідями й антифлудом, переживає рестарт |
| `.note / .notes / .delnote` | Швидкі особисті нотатки |
| `.undo [N]` | Видалити останні N своїх повідомлень у чаті |
| Fuzzy-підказки | Тільки opt-in: «did you mean…?» для одруківок у командах (ключ `suggest_commands`, **вимкнено за замовчуванням** — будь-який текст із крапки, що не є командою, ігнорується мовчки) |
| `--dry-run` | Валідація конфіга й синтаксису модулів без підключення |
| `/healthz` | Healthcheck-endpoint для Docker/K8s (вже налаштований у compose) |
| `tools/selfcheck.py` | Офлайн-самоперевірка compat-шару та ядра |
| `tools/newmodule.py <Name>` | Генератор шаблону нового модуля за секунду |
| Сканер безпеки | Зовнішні модулі аналізуються (AST) при завантаженні; підозрілі патерни — у лог |

Самоперевірка без підключення до Telegram:

```bash
python tools/selfcheck.py
```

## 🔑 Отримання API-ключів

1. Відкрийте [my.telegram.org/apps](https://my.telegram.org/apps)
2. Створіть застосунок, щоб отримати `API_ID` та `API_HASH`
3. Уведіть їх під час першого запуску Haruka

## ♻️ Міграція з Hikka / Heroku

Просто запустіть Haruka поруч із наявною інсталяцією: сесії, конфіг та БД
розпізнаються автоматично, ключі `hikka.*` / `heroku.*` конвертуються в `haruka.*`.

## ⚠️ Безпека

> Встановлення модулів від недовірених розробників може зашкодити акаунту.
> Завантажуйте модулі лише з перевірених джерел. Будьте обережні з командами
> на кшталт `.terminal` та `.eval`. Увімкніть `.api_fw_protection`.

## 🙏 Подяки

- [**Lonami**](https://github.com/LonamiWebs) — Telethon
- [**Hikari**](https://gitlab.com/hikariatama) — Hikka (основа проєкту)
- **Coddrago** — Heroku (проміжний форк)
- **Haruka contributors** — цей проєкт

## 📄 Ліцензія

[AGPLv3](LICENSE)
