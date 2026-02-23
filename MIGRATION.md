# Haruka Merge Migration

This project was switched to `Haruka-1.0` core and renamed as `haruka`.

## Legacy Backup

- Old project backup path: `../haruka_legacy_20260218_205252`

## Migrated Features

The following features were moved from legacy Haruka into:
- `haruka/modules/haruka_features.py`

Included commands:
- `.afk`, `.online`
- `.dotreplace` (aliases: `.dr`, `.dots`)
- RP aliases: `.обнять`, `.обняти`, `.поцеловать`, `.поцілувати`, `.ударить`, `.вдарити`, `.тыкнуть`, `.тикнути`
- `.export`
- `.стата` (also `.stata`)
- `.type` (alias: `.print`)
- Troll suite: `.trol`, `.addtrol`, `.remtrol`, `.listtrol`, `.les`, `.cleartrol`
- `.tt` (alias: `.tiktok`)
- `.give`, `.fullgive`

## Dependency Updates

- Added `yt-dlp` to `requirements.txt`
- Added `yt-dlp` to `pyproject.toml`
