#!/usr/bin/env sh
set -eu

cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

find_python() {
  for candidate in python3.14 python3.13 python3.12 python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' 2>/dev/null; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

PYTHON="$(find_python || true)"
if [ -z "$PYTHON" ]; then
  echo "[error] Python 3.11+ was not found."
  echo "Install it with one of:"
  echo "  Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
  echo "  Fedora:        sudo dnf install python3 python3-pip"
  echo "  Arch:          sudo pacman -S python python-pip"
  echo "  Alpine:        sudo apk add python3 py3-pip py3-virtualenv"
  echo "  macOS:         brew install python"
  echo "  Termux:        pkg install python"
  exit 1
fi

exec "$PYTHON" install.py "$@"
