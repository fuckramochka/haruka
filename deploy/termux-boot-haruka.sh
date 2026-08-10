#!/data/data/com.termux/files/usr/bin/sh
# Haruka Userbot - Termux auto-start + auto-restart script.
#
# Termux has no systemd, so this script keeps Haruka alive with a restart loop
# and can be launched automatically on device boot via the Termux:Boot app.
#
# Setup:
#   1. Install the "Termux:Boot" app from F-Droid and open it once.
#   2. mkdir -p ~/.termux/boot
#   3. cp deploy/termux-boot-haruka.sh ~/.termux/boot/haruka
#   4. chmod +x ~/.termux/boot/haruka
#   Adjust HARUKA_DIR below if your clone is not at ~/Haruka.
#
# You can also run it manually:  sh ~/.termux/boot/haruka

HARUKA_DIR="$HOME/Haruka"

# Prevent Android from killing the process while the screen is off.
termux-wake-lock 2>/dev/null || true

cd "$HARUKA_DIR" || {
    echo "[haruka] directory $HARUKA_DIR not found"
    exit 1
}

while true; do
    sh ./start.sh
    code=$?
    echo "[haruka] process exited (code $code) - restarting in 5s..."
    sleep 5
done
