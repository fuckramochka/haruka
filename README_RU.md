# Haruka Engine

> Современный движок для Telegram-юзерботов, а не очередной пресет модулей.

[![CI](https://github.com/fuxckramochka/haruka/actions/workflows/ci.yml/badge.svg)](https://github.com/fuxckramochka/haruka/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-2783DE)](https://www.python.org/)
[![Лицензия](https://img.shields.io/badge/license-AGPL--3.0-E56458)](LICENSE)
[![Версия](https://img.shields.io/badge/version-2.0.0-46A171)](CHANGELOG.md)

[English](README.md) · [Руководство пользователя](docs/USER_GUIDE_RU.md) · [Для разработчиков](docs/DEVELOPER_GUIDE.md) · [Архитектура](docs/ARCHITECTURE.md) · [Haruka против Heroku](docs/HARUKA_VS_HEROKU_RU.md)

Haruka — компактная платформа, на которой можно создавать, загружать и обслуживать возможности юзербота. Внутри есть единый диспетчер команд, транзакционный загрузчик, роли, SQLite, Control Center, API для расширений и доступ к raw MTProto через Kurigram.

## Главное отличие

В большинстве юзерботов ядро исторически растёт вокруг встроенных команд и совместимости. В Haruka сначала определяется контракт движка, а встроенные возможности используют тот же публичный API, что и сторонние расширения.

- чистый импорт для авторов: `haruka.api`;
- откат неудачной загрузки без «призрачных» команд;
- включение и отключение команд и возможностей без удаления файлов;
- единая обработка прав, лимитов, алиасов и ошибок;
- красивый встроенный Control Center;
- диагностика памяти, CPU, диска, БД и фоновых задач;
- адаптер части Hikka-модулей без переноса старой архитектуры в новое ядро.

## Установка в один клик

Редактировать `.env`, открывать `nano` или вводить настройки в терминале не нужно.

- **Windows:** дважды нажми `Install Haruka.cmd`.
- **macOS:** дважды нажми `Install Haruka.command`.
- **Linux с рабочим столом:** открой `Haruka Setup.desktop` или `launcher.pyw`.

Установщик сам проверит Python и окружение, исправит типовые ошибки и откроет браузерный мастер с кнопками для API, QR/телефонного входа и настроек движка.

## Быстрый запуск

Нужны Python 3.10+, Telegram-аккаунт и `API_ID`/`API_HASH` с [my.telegram.org](https://my.telegram.org/apps).

```bash
git clone https://github.com/fuxckramochka/haruka.git
cd haruka
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[full]'
cp .env.example .env
python -m haruka
```

При первом запуске Haruka запросит данные входа. По умолчанию база, сессия и загруженные расширения находятся в `~/.haruka`.

## Docker

```bash
cp .env.example .env
mkdir -p data
docker compose run --rm haruka
```

Первый запуск интерактивный. После авторизации:

```bash
docker compose up -d
```

## Панель управления

1. Создай бота через `@BotFather`.
2. Выполни `.setbot <token>` и перезапусти Haruka.
3. Один раз открой бота командой `/start`.
4. Используй `.menu` или `.dashboard`.

В панели доступны состояние движка, команды, feature gates, визуальные темы Aurora/Carbon/Minimal, безопасность и диагностика.

## Документация

- [Полное руководство пользователя](docs/USER_GUIDE_RU.md)
- [Руководство разработчика расширений](docs/DEVELOPER_GUIDE.md)
- [Архитектура ядра](docs/ARCHITECTURE.md)
- [Развёртывание](docs/DEPLOYMENT.md)
- [FAQ](docs/FAQ_RU.md)
- [Сравнение Haruka и Heroku](docs/HARUKA_VS_HEROKU_RU.md)
- [План развития](ROADMAP.md)

## Текущий статус

Haruka 2.0 — рабочий, но молодой движок. У него уже есть тестируемые контракты и современная архитектура, однако экосистема расширений и совместимость пока меньше, чем у зрелых Hikka-производных проектов.

## Безопасность

Сторонний `.py`-файл получает права процесса и доступ к Telegram-сессии. Устанавливай только проверенный код. Никогда не публикуй `.env`, `*.session`, базу или каталог `data`. Подробности — в [SECURITY.md](SECURITY.md).

Лицензия: [AGPL-3.0-or-later](LICENSE).
