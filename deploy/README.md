# Haruka auto-restart / auto-start

Keep Haruka running 24/7 and bring it back automatically after a crash or reboot.

## Linux (systemd, recommended)

```sh
mkdir -p ~/.config/systemd/user
cp deploy/haruka.service ~/.config/systemd/user/haruka.service
# edit WorkingDirectory / ExecStart if your clone is not at ~/Haruka
systemctl --user daemon-reload
systemctl --user enable --now haruka.service
loginctl enable-linger "$USER"   # keep running after logout
```

- Follow logs: `journalctl --user -u haruka -f`
- Restart: `systemctl --user restart haruka`
- Stop: `systemctl --user stop haruka`

`Restart=always` + `RestartSec=5` restarts Haruka within 5 seconds of any exit.

## Android (Termux)

Termux has no systemd, so use the restart-loop script (optionally on boot):

```sh
pkg install termux-api        # for wake-lock (optional but recommended)
mkdir -p ~/.termux/boot
cp deploy/termux-boot-haruka.sh ~/.termux/boot/haruka
chmod +x ~/.termux/boot/haruka
```

Install the **Termux:Boot** app (F-Droid) and open it once so scripts run on
device boot. To start immediately: `sh ~/.termux/boot/haruka`.

## UserLAnd / other Linux without systemd

Run the same restart loop manually or from `~/.profile`:

```sh
while true; do bash ~/Haruka/start.sh; sleep 5; done
```

## macOS (launchd)

Use the restart loop, or create a `launchd` agent with `KeepAlive=true` that runs
`start.sh`. The loop is simplest:

```sh
while true; do bash ~/Haruka/start.sh; sleep 5; done
```

## Windows (Task Scheduler)

1. Open **Task Scheduler** -> Create Task.
2. Trigger: **At log on**.
3. Action: Start a program -> `powershell.exe`
   Arguments: `-ExecutionPolicy Bypass -File "C:\path\to\Haruka\start.ps1"`
4. Settings: enable **If the task fails, restart every 1 minute**.

Haruka also restarts itself for updates/`.restart`; these supervisors only add
crash/reboot recovery on top.
