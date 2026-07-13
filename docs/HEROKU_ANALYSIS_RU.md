# Аналіз Heroku і покращення Haruka (2.1.0 “Babel”)

Цей документ — результат розбору Heroku “від шапки до трусів” та перелік
того, що було додано / змінено в Haruka.

## 1. Heroku — архітектура (що там є)

Heroku — це зрілий форк Hikka (~30k рядків). Ключові підсистеми:

| Підсистема | Файл(и) | Суть |
|---|---|---|
| Ядро / бутстрап | `main.py` (1266) | запуск, авторизація, сесії |
| Завантажувач | `loader.py` (1738), `modules/loader.py` (1517) | завантаження модулів, `# requires:`, `# meta` |
| Типи SDK | `types.py` (1623) | `Module`, `InfiniteLoop`, декоратори |
| Диспетчер | `dispatcher.py` (696) | обробка команд, watchers, ліміти |
| Безпека | `security.py` (652), `modules/heroku_security.py` (1295) | групи доступу, маски |
| Inline | `inline/*` (~4k) | forms, galleries, lists, bot_pm |
| Локалізація | `translations.py` + `langpacks/*.yml` | 9 мовних пакетів |
| Конфіг | `configurator.py`, `validators.py` (874) | типовані опції |
| Web/QR | `web/*`, `qr.py` (1566) | авторизація через браузер |
| База | `database.py` (445), `tl_cache.py` (729) | сховище + кеш entity |
| Утиліти | `utils/*` | args, entity, git, network, platform |

### Сильні сторони Heroku

1. Величезна екосистема Hikka/FTG/GeekTG-модулів.
2. 9 мовних пакетів (включно з мемними: uwu, leet, tiktok, neofit).
3. `# requires:` — автовстановлення залежностей модуля.
4. Web/QR onboarding замість консолі.
5. Багатий inline (forms/galleries/lists).

### Слабкі сторони (архітектурний борг, який НЕ копіюємо)

- Монкі-патчі та глобальний стан Hikka.
- Модулі напряму лізуть у внутрішні об'єкти.
- Велика зв'язність між loader/types/dispatcher.

## 2. Що було додано / змінено в Haruka

### Локалізація (найбільший розрив)
- `haruka/langpacks/*.yml` — повні `en, ru, uk, de, ja` + мемні `uwu, leet, tiktok, neofit`.
- `haruka/i18n.py` переписано: завантаження пакетів з диска (PyYAML або
  вбудований парсер), fallback на англійську, `available()`, `label`,
  `register_module_strings`, `gettext`.
- Модуль `Translations`: `.langlist`, `.langpicker` (inline), `.uselang`.
- Web-onboarding і `.language` тепер беруть мови динамічно.

### Маніфести модулів (як у Heroku, але явно)
- `haruka/core/metadata.py`: парсинг `# meta developer:`, `# requires:`,
  `# min_engine:`, `# scope:`.
- Завантажувач перевіряє мінімальну версію рушія та встановлює
  `# requires:` ПЕРЕД виконанням чужого коду, чисто відкочуючись при помилці.

### SDK
- `haruka.api` експортує `ModuleManifest`, `SUPPORTED_LANGUAGES`, `MEME_LANGUAGES`.
- `Module` отримав `strings` (локалізація) та `manifest`.

## 3. Що СВІДОМО НЕ зроблено за один прохід

Повна заміна “абсолютно всього” на 30k рядків Heroku без живого Telegram-
тестування була б безвідповідальною. Залишається для наступних ітерацій:

- Повна Hikka-сумісність усіх історичних монкі-патчів.
- QR-авторизація потребує живого тесту після кожного layer-оновлення Kurigram.
- Пісочниця для недовірених розширень (окремі процеси).
- Мультиакаунт (зараз — один акаунт на процес).

## 4. Верифікація

- `python -m compileall haruka` — OK.
- 9/9 regression-тестів пройдено.
- Завантаження всіх 9 мовних пакетів та перемикання перевірено.
- Парсер маніфестів та перевірка версій перевірені.
