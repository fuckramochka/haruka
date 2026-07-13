# Deployment Guide

## Supported model

Haruka is a long-running process with persistent Telegram session and SQLite files. A deployment is correct only if its data directory survives restarts.

## VPS/systemd

```bash
git clone https://github.com/fuxckramochka/haruka.git /opt/haruka
cd /opt/haruka
python3 -m venv .venv
.venv/bin/pip install -e '.[full]'
cp .env.example .env
.venv/bin/python -m haruka
```

After interactive login, create `/etc/systemd/system/haruka.service`:

```ini
[Unit]
Description=Haruka Telegram userbot engine
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=haruka
WorkingDirectory=/opt/haruka
EnvironmentFile=/opt/haruka/.env
ExecStart=/opt/haruka/.venv/bin/python -m haruka
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Then run `sudo systemctl daemon-reload && sudo systemctl enable --now haruka`.

## Docker Compose

```bash
cp .env.example .env
mkdir -p data
docker compose run --rm haruka   # interactive login
docker compose up -d
```

The compose file mounts `./data` to `/data/haruka`. Back up that host directory.

## Secrets

- Do not commit `.env`, session files or database files.
- Prefer host secret stores or protected environment variables.
- Restrict the data directory to the service account (`chmod 700`).
- Rotate the companion bot token if it appears in logs or chat history.

## Updates and rollback

1. Back up the data directory.
2. Pull or check out the target tag.
3. Rebuild/install dependencies.
4. Run tests.
5. Restart one process.
6. Roll back code without replacing the persistent data unless a migration requires it.

## GitHub release flow

- Pull requests run compile, unit tests, Ruff and package build.
- Tag `vX.Y.Z` to build wheel/source artifacts and create a GitHub Release.
- Docker workflow verifies the image on pull requests and pushes GHCR images on version tags.

## Hosting caveats

Ephemeral platforms are unsuitable unless a persistent volume is available. A Telegram userbot also requires an interactive first login; plan a secure one-time console session.
