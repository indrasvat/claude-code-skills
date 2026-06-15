# Hands-free autostart

Start the shared Chrome automatically at login so it is always ready and you
never see a launch prompt.

## macOS — the easy way (recommended)

```bash
scripts/chrome-agent.sh autostart on       # install + load the LaunchAgent now
scripts/chrome-agent.sh autostart status   # is it loaded?
scripts/chrome-agent.sh autostart off      # remove it
```

`autostart on` writes `~/Library/LaunchAgents/com.chrome-agent.<user>.plist` with
**this script's resolved absolute path** and your current port/profile, then
loads it — no hand-edited paths. It runs `start` at every login (and immediately).
The launcher is idempotent, so an extra load is harmless. Re-run `autostart on`
if you move the skill to a new location (the path is baked into the plist).

Notes:
- Override port/profile by setting `CHROME_AGENT_PORT` / `CHROME_AGENT_PROFILE` /
  `CHROME_AGENT_STATE` in the environment when you run `autostart on`; they are
  written into the plist's `EnvironmentVariables`.
- launchd stdout/stderr go to `~/.local/state/chrome-agent/launchd.{out,err}.log`.
  Under the background `open -g` launch, Chrome's own stdout is not captured;
  `agent.log` and `cdp.log` carry the full trail.

There is no plist to hand-edit: `autostart on` is the whole interface. To inspect
what it generated, look at `~/Library/LaunchAgents/com.chrome-agent.<user>.plist`.

## Linux (systemd --user)

```ini
# ~/.config/systemd/user/chrome-agent.service
[Unit]
Description=Persistent authenticated Chrome with CDP

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=%h/path/to/browsing-as-you/scripts/chrome-agent.sh start
ExecStop=%h/path/to/browsing-as-you/scripts/chrome-agent.sh stop

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now chrome-agent.service
```
