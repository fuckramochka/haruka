FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN useradd --create-home --uid 10001 haruka
WORKDIR /app

COPY pyproject.toml README.md main.py ./
COPY haruka ./haruka
RUN python -m pip install --no-cache-dir .

USER haruka
RUN mkdir -p /home/haruka/data/snapshots /home/haruka/data/lore
ENV HARUKA_DATA_DIR=/home/haruka/data \
    HARUKA_DB_PATH=/home/haruka/data/haruka.sqlite3 \
    HARUKA_SNAPSHOT_DIR=/home/haruka/data/snapshots \
    TELEGRAM_SESSION=/home/haruka/data/haruka.session

VOLUME ["/home/haruka/data"]
CMD ["haruka"]
