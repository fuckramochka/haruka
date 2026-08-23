#!/usr/bin/env bash
# Haruka Userbot — one-command installer (Linux / macOS / WSL)
# Usage: bash install.sh
set -e

BLUE="\033[34m"; CYAN="\033[36m"; GREEN="\033[32m"; RED="\033[31m"; YELLOW="\033[33m"; PURPLE="\033[35m"; RESET="\033[0m"

REPO_URL="${HARUKA_REPO:-https://github.com/fuckramochka/haruka}"
DIR="$(cd "$(dirname "$0")" && pwd)/Haruka"

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; fi
fi

echo -e "${PURPLE}✨ Haruka Userbot installer${RESET}"

# --- Python detection -------------------------------------------------------
PY=""
for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
            PY="$candidate"
            break
        fi
    fi
done

if [ -z "$PY" ]; then
    echo -e "${YELLOW}Python 3.10+ not found. Installing...${RESET}"
    if command -v apt-get >/dev/null 2>&1; then
        $SUDO apt-get update && $SUDO apt-get install -y python3 python3-venv python3-pip
    elif command -v dnf >/dev/null 2>&1; then
        $SUDO dnf install -y python3
    elif command -v pacman >/dev/null 2>&1; then
        $SUDO pacman -Syu --noconfirm python git
    else
        echo -e "${RED}Please install Python 3.10+ manually: https://python.org${RESET}"
        exit 1
    fi
    PY=python3
fi

echo -e "${CYAN}Using $($PY --version)${RESET}"

# --- Clone -------------------------------------------------------------------
if [ ! -d "$DIR" ]; then
    if command -v git >/dev/null 2>&1; then
        git clone "$REPO_URL" "$DIR"
    else
        echo -e "${YELLOW}git not found, installing...${RESET}"
        if command -v apt-get >/dev/null 2>&1; then
            $SUDO apt-get update && $SUDO apt-get install -y git
        fi
        git clone "$REPO_URL" "$DIR"
    fi
else
    echo -e "${YELLOW}Directory $DIR already exists — reusing it.${RESET}"
fi

cd "$DIR"

# --- Venv + deps -------------------------------------------------------------
if [ ! -d ".venv" ]; then
    "$PY" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt

echo -e ""
echo -e "${GREEN}✔ Installation complete! Starting Haruka...${RESET}"
echo -e "${CYAN}Next time run:${RESET} cd $DIR && source .venv/bin/activate && python -m haruka"
echo -e ""

exec python -m haruka "$@"
