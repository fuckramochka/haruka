# Haruka vs Heroku — сравнение 1.0

Дата среза: 13 июля 2026 года.

## Короткий вывод

**Heroku** сегодня сильнее как зрелый готовый юзербот: большая Hikka-наследуемая экосистема, совместимость, много лет функций, web/QR onboarding, локализации и широкий inline-инструментарий.

**Haruka** сильнее как новое компактное основание: явный composition root, публичный SDK, транзакционный загрузчик, централизованный dispatcher, SQLite и встроенные feature gates. Но Haruka моложе, имеет меньше совместимых модулей и пока не обладает всем продуктовым покрытием Heroku.

Это не честная гонка «кто лучше вообще». Heroku оптимизирована для пользователя и совместимости; Haruka — для контролируемого развития нового движка.

## Таблица

| Область | Heroku | Haruka 2.0 |
|---|---|---|
| Происхождение | Fork Hikka | Новое Kurigram-ядро |
| Клиент | Heroku-TL/Telethon lineage | Kurigram (`pyrogram` namespace) |
| Главная модель | Готовый юзербот + большая совместимость | Engine-first runtime + SDK |
| Зрелость | Высокая, публичная история и сообщество | Молодой проект, ранняя стадия |
| Модули | FTG/GeekTG/Hikka compatibility, пресеты и развитая экосистема | Нативный Haruka API + ограниченный Hikka adapter |
| Загрузка | Богатая историческая loader-система | Транзакционная регистрация и откат lifecycle |
| Конфигурация | Развитые validators/config flows | Простой typed `ModuleConfig`, SQLite persistence |
| Интерфейс | Inline forms, galleries, lists, web onboarding | Native Control Center, command atlas, skins, feature gates |
| Авторизация | Web/QR/console flows | Console/Kurigram first login |
| Мультиаккаунт | Поддерживался в ветке Heroku | Один аккаунт на процесс |
| Telegram-функции | Свой Telethon fork и долгий слой совместимости | Kurigram + компактный `haruka.tl` escape hatch |
| Безопасность | Targeted security, API limiter, module warnings, session protection | Roles, centralized gates, rate limit, audit, masking, protected service IDs |
| Хранилище | Исторически Hikka DB и развитая совместимость | Async SQLite KV + cache + audit |
| Наблюдаемость | Логи, tester/debugging tooling | Health snapshot, audit, centralized errors |
| Локализации | Много языков и packs | UI в основном английский, русская документация |
| Деплой | VPS, Docker, hostings, install scripts | VPS/systemd, Docker Compose, GitHub Actions |
| Тесты/контракты | Большая кодовая база, качество зависит от подсистемы | Маленькое ядро и regression tests, покрытие пока скромное |

## Где Heroku объективно впереди

1. **Экосистема.** Heroku наследует огромный пласт Hikka/FTG/GeekTG-модулей и пользовательских привычек.
2. **Onboarding.** Web и QR сценарии удобнее консольной авторизации Haruka.
3. **Inline platform.** Forms, galleries, lists и совместимость старых inline units шире.
4. **Проверенное покрытие.** У Heroku есть длинный changelog исправлений Telegram edge cases, форумов, хостингов и модулей.
5. **Локализация и готовность для конечного пользователя.** Больше языков, сценариев установки и готовых core-функций.

## Где архитектура Haruka интереснее

1. **Явный object graph.** Все сервисы собирает `Application`; расширения не ищут магические globals.
2. **Один публичный API.** Новые расширения зависят от `haruka.api`, а не от случайных внутренних объектов.
3. **Транзакционная загрузка.** Ошибка `on_load()` откатывает индексы и import state.
4. **Централизованная политика.** Права, лимиты, alias expansion, feature gates, audit и ошибки проходят через один dispatcher.
5. **Compatibility at the edge.** Hikka shim не диктует устройство нового ядра.
6. **SQLite и диагностика.** Отдельные KV/audit таблицы и встроенный health surface проще сопровождать.

## Где Haruka пока проигрывает

- неполная Hikka-совместимость;
- нет web/QR onboarding;
- нет полноценного sandbox для недоверенных расширений;
- нет зрелого каталога расширений и системы доверия/подписей;
- один аккаунт на процесс;
- мало языков интерфейса;
- тестовое покрытие нужно расширять интеграционными Telegram mock tests;
- Control Center зависит от companion-бота.

## Что стоит перенять у Heroku без копирования архитектурного долга

- QR/web onboarding отдельным сервисом;
- richer inline primitives как стабильный Haruka UI API;
- package manifest с зависимостями, минимальной версией движка и подписью;
- локализацию через отдельный слой;
- topic-aware helpers и расширенный Telegram feature facade;
- migration tooling для распространённых Hikka конфигов;
- преднастроенные deployment targets, но без встраивания хостинг-логики в core.

## Рекомендуемое позиционирование

Не заявлять «Haruka уже заменила Heroku». Сильная и честная формулировка:

> Haruka — новый engine-first runtime для авторов, которым нужны понятные контракты, управляемый lifecycle и современное ядро. Heroku остаётся ориентиром по зрелости, совместимости и пользовательскому покрытию.

## Источники

- Heroku repository: https://github.com/coddrago/Heroku
- Heroku changelog: https://github.com/coddrago/Heroku/blob/master/CHANGELOG.md
- Heroku developer documentation: https://dev.heroku-ub.xyz/
- Haruka source and docs in this repository.

Сравнение основано на публичной документации и changelog Heroku, а также на фактическом коде Haruka 2.0. Некоторые Heroku-подсистемы не проверялись runtime-тестом в этой среде.
