# Публикация Haruka на GitHub

## 1. Создай репозиторий

На GitHub создай пустой публичный репозиторий `haruka` без автоматически созданных README и LICENSE.

## 2. Отправь подготовленный проект

```bash
cd haruka
git init
git branch -M main
git add .
git commit -m "release: Haruka Engine 2.0.0"
git remote add origin https://github.com/fuxckramochka/haruka.git
git push -u origin main
```

Если имя аккаунта или репозитория другое, замени `fuxckramochka/haruka` во всех badges, workflow image tags, `pyproject.toml`, `CITATION.cff` и документации.

## 3. Настройки репозитория

- About: `Engine-first runtime and SDK for Telegram userbots`.
- Topics: `telegram`, `userbot`, `python`, `kurigram`, `mtproto`, `framework`.
- Включи Issues, Discussions и Private vulnerability reporting.
- Включи branch protection для `main`: обязательный PR и успешный workflow `CI`.
- Запрети force push и удаление `main`.
- Для GitHub Actions оставь read/write permissions, необходимые release и GHCR workflows.

## 4. Первый релиз

```bash
git tag -a v2.0.0 -m "Haruka Engine 2.0.0"
git push origin v2.0.0
```

Tag запустит сборку Python-артефактов, GitHub Release и GHCR Docker image.

## 5. Проверка перед публикацией

```bash
python -m compileall -q haruka tests
python -m unittest discover -s tests -v
# после установки dev dependencies:
pytest
ruff check haruka tests
docker build -t haruka:local .
```

Никогда не добавляй `.env`, `data/`, базу, Telegram session или backup-файлы.
