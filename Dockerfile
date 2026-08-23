FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    DOCKER=true \
    GIT_PYTHON_REFRESH=quiet

# Runtime deps: git for the updater, ffmpeg for media handling
RUN apt-get update && apt-get install --no-install-recommends -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /data

COPY requirements.txt /data/Haruka/requirements.txt
RUN pip install --no-warn-script-location --no-cache-dir -U -r /data/Haruka/requirements.txt

COPY . /data/Haruka
WORKDIR /data/Haruka

EXPOSE 8080
CMD ["python", "-m", "haruka", "--root"]
