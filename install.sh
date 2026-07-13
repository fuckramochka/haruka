#!/usr/bin/env sh
set -u
find_python(){ for p in python3 python; do command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys;raise SystemExit(sys.version_info<(3,10))' >/dev/null 2>&1 && { echo "$p"; return; }; done; }
PY="$(find_python || true)"
if [ -z "$PY" ]; then
 echo "Python bootstrap not found. Trying system package manager..."
 if command -v apt-get >/dev/null; then sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip git
 elif command -v dnf >/dev/null; then sudo dnf install -y python3 python3-pip git
 elif command -v pacman >/dev/null; then sudo pacman -S --needed --noconfirm python python-pip git
 elif command -v brew >/dev/null; then brew install python@3.12 git
 else echo "Install Python 3.10+ and rerun."; exit 1; fi
 PY="$(find_python)"
fi
exec "$PY" bootstrap.py "$@"
