FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HARUKA_DATA_DIR=/data/haruka

RUN groupadd --system haruka && useradd --system --gid haruka --home /app haruka
WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY haruka ./haruka
RUN pip install --no-cache-dir .

RUN mkdir -p /data/haruka && chown -R haruka:haruka /app /data/haruka
USER haruka
VOLUME ["/data/haruka"]
CMD ["python", "-m", "haruka"]
