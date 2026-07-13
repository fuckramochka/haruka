#!/bin/sh
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
  exec python3 launcher.pyw
fi
if command -v brew >/dev/null 2>&1; then
  brew install python@3.12
  exec python3 launcher.pyw
fi
osascript -e 'display alert "Haruka" message "Install Python 3.10 or newer, then double-click this file again."'
exit 1
