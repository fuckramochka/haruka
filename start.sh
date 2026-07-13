#!/usr/bin/env sh
# ©️ Codrago, 2024-2030 — Haruka Userbot
# Universal launcher for Linux / macOS / FreeBSD / Termux / UserLAnd.
#
# On the FIRST run it:
#   1. detects the OS and package manager,
#   2. installs system dependencies (python 3.10+, pip, venv, git, ffmpeg, ...),
#   3. creates a virtual environment (.venv),
#   4. runs install.py which downloads ALL required + optional libraries.
# On every later run it just activates the venv and starts Haruka.

set -e
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

VENV=".venv"
SENTINEL=".haruka_installed"
export GIT_PYTHON_REFRESH=quiet

info() { printf '\033[36m[haruka]\033[0m %s\n' "$1"; }
warn() { printf '\033[33m[haruka]\033[0m %s\n' "$1"; }
err()  { printf '\033[31m[haruka]\033[0m %s\n' "$1" 1>&2; }

OS="$(uname -s 2>/dev/null || echo unknown)"
PKG=""
SUDO=""
if [ "$(id -u 2>/dev/null || echo 1)" != "0" ] && command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
fi

detect_pkg() {
    if [ -n "${PREFIX:-}" ] && printf '%s' "$PREFIX" | grep -q "com.termux"; then
        PKG="termux"
    elif [ "$OS" = "FreeBSD" ] && command -v pkg >/dev/null 2>&1; then
        PKG="freebsd"
    elif command -v apt-get >/dev/null 2>&1; then PKG="apt"
    elif command -v dnf >/dev/null 2>&1; then PKG="dnf"
    elif command -v yum >/dev/null 2>&1; then PKG="yum"
    elif command -v pacman >/dev/null 2>&1; then PKG="pacman"
    elif command -v zypper >/dev/null 2>&1; then PKG="zypper"
    elif command -v apk >/dev/null 2>&1; then PKG="apk"
    elif command -v brew >/dev/null 2>&1; then PKG="brew"
    else PKG=""; fi
}

install_system_deps() {
    info "Installing system dependencies via '${PKG:-none}' (best-effort)..."
    case "$PKG" in
        termux)
            pkg update -y || true
            pkg install -y python git ffmpeg libjpeg-turbo libwebp clang rust || true
            ;;
        apt)
            $SUDO apt-get update -y || true
            $SUDO apt-get install -y python3 python3-pip python3-venv python3-dev \
                git ffmpeg build-essential libjpeg-dev zlib1g-dev libwebp-dev \
                libffi-dev libssl-dev || true
            ;;
        freebsd)
            $SUDO pkg install -y python3 py311-pip py311-sqlite3 git ffmpeg || \
                $SUDO pkg install -y python311 git ffmpeg || true
            ;;
        dnf)
            $SUDO dnf install -y python3 python3-pip python3-devel git ffmpeg \
                gcc gcc-c++ libjpeg-turbo-devel zlib-devel || true
            ;;
        yum)
            $SUDO yum install -y python3 python3-pip python3-devel git ffmpeg gcc || true
            ;;
        pacman)
            $SUDO pacman -Sy --noconfirm python python-pip git ffmpeg base-devel \
                libjpeg-turbo zlib || true
            ;;
        zypper)
            $SUDO zypper install -y python3 python3-pip python3-devel git ffmpeg \
                gcc libjpeg8-devel zlib-devel || true
            ;;
        apk)
            $SUDO apk add --no-cache python3 py3-pip python3-dev git ffmpeg \
                build-base jpeg-dev zlib-dev libffi-dev openssl-dev || true
            ;;
        brew)
            brew install python git ffmpeg jpeg webp || true
            ;;
        *)
            warn "Unknown package manager. Ensure Python 3.10+, pip, venv and git are installed."
            ;;
    esac
}

PY=""
find_python() {
    for cand in python3.13 python3.12 python3.11 python3.10 python3 python; do
        if command -v "$cand" >/dev/null 2>&1; then
            ver="$("$cand" -c 'import sys;print(sys.version_info[0]*100+sys.version_info[1])' 2>/dev/null || echo 0)"
            if [ "$ver" -ge 310 ] 2>/dev/null; then
                PY="$cand"
                return 0
            fi
        fi
    done
    return 1
}

if [ ! -f "$SENTINEL" ] || [ ! -d "$VENV" ]; then
    info "First run detected — setting everything up. This can take a few minutes."
    detect_pkg
    info "Platform: $OS | package manager: ${PKG:-none}"
    install_system_deps

    if ! find_python; then
        err "Python 3.10+ was not found. Install it and run ./start.sh again."
        exit 1
    fi
    info "Using interpreter: $PY ($("$PY" --version 2>&1))"

    if [ ! -d "$VENV" ]; then
        info "Creating virtual environment in $VENV ..."
        "$PY" -m venv "$VENV" || {
            warn "venv module failed; retrying with --system-site-packages"
            "$PY" -m venv --system-site-packages "$VENV" || {
                err "Could not create a virtual environment."
                exit 1
            }
        }
    fi

    # shellcheck disable=SC1090
    . "$VENV/bin/activate"
    python install.py --force || {
        err "Dependency installation failed. See the log above."
        exit 1
    }
else
    # shellcheck disable=SC1090
    . "$VENV/bin/activate"
fi

info "Starting Haruka..."
exec python -m haruka "$@"
