#!/usr/bin/env bash
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${1:-$SRC_DIR/.public_release}"
TARGET_REPO="${TARGET_REPO:-https://github.com/fuckramochka/haruka.git}"
TARGET_BRANCH="${TARGET_BRANCH:-main}"
FORCE_PUSH="${FORCE_PUSH:-1}"

EXCLUDES=(
  ".git"
  ".venv"
  "venv"
  "__pycache__"
  "*.pyc"
  "*.pyo"
  "*.session"
  "*.session-journal"
  "config.json"
  "config-*.json"
  "database-*.json"
  "haruka.log"
  "haruka.log.*"
  "unknown_errors.txt"
  ".haruka"
  "loaded_modules"
  "haruka/loaded_modules"
  "haruka/debug_modules"
  ".pytest_cache"
  ".mypy_cache"
  ".ruff_cache"
  ".public_release"
)

echo "[1/5] Building sanitized copy in: $OUT_DIR"
mkdir -p "$OUT_DIR"

if command -v rsync >/dev/null 2>&1; then
  RSYNC_ARGS=("-a" "--delete")
  for pattern in "${EXCLUDES[@]}"; do
    RSYNC_ARGS+=("--exclude=$pattern")
  done
  rsync "${RSYNC_ARGS[@]}" "$SRC_DIR/" "$OUT_DIR/"
else
  echo "rsync is not installed; using tar fallback"
  TAR_EXCLUDES=()
  for pattern in "${EXCLUDES[@]}"; do
    TAR_EXCLUDES+=("--exclude=$pattern")
  done
  tar -C "$SRC_DIR" -cf - "${TAR_EXCLUDES[@]}" . | tar -C "$OUT_DIR" -xf -
fi

cd "$OUT_DIR"

# Final hard cleanup in case any sensitive files slipped through
rm -rf .git .venv venv loaded_modules haruka/loaded_modules haruka/debug_modules
find . -type f \( \
  -name '*.session' -o \
  -name '*.session-journal' -o \
  -name 'config.json' -o \
  -name 'config-*.json' -o \
  -name 'database-*.json' -o \
  -name 'haruka.log' -o \
  -name 'haruka.log.*' -o \
  -name 'unknown_errors.txt' \
\) -delete
find . -type d -name '__pycache__' -prune -exec rm -rf {} +

if [[ ! -f README.md || ! -d haruka ]]; then
  echo "Sanitized output does not look like Haruka repo root: $OUT_DIR"
  exit 1
fi

echo "[2/5] Initializing git repository"
git init -b "$TARGET_BRANCH" >/dev/null
git config user.name "${GIT_AUTHOR_NAME:-Haruka Release Bot}"
git config user.email "${GIT_AUTHOR_EMAIL:-haruka-release@localhost}"

echo "[3/5] Creating release commit"
git add .
git commit -m "release: Haruka 1.0.0 sanitized export" >/dev/null

auth_repo="$TARGET_REPO"
if [[ -n "${GITHUB_TOKEN:-}" && "$TARGET_REPO" == https://github.com/* ]]; then
  auth_repo="https://x-access-token:${GITHUB_TOKEN}@${TARGET_REPO#https://}"
fi

echo "[4/5] Pushing to $TARGET_REPO ($TARGET_BRANCH)"
git remote add origin "$auth_repo"

if [[ "$FORCE_PUSH" == "1" ]]; then
  git push -u origin "$TARGET_BRANCH" --force
else
  git push -u origin "$TARGET_BRANCH"
fi

if [[ "$auth_repo" != "$TARGET_REPO" ]]; then
  git remote set-url origin "$TARGET_REPO"
fi

echo "[5/5] Done"
echo "Sanitized release has been published to: $TARGET_REPO"
echo "Local export directory: $OUT_DIR"
