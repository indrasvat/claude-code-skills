#!/usr/bin/env bash
#
# chrome-agent.sh - run ONE persistent, authenticated Chrome with the DevTools
# Protocol enabled, shared by every coding agent and sub-agent on this machine.
# Tools attach to it instead of launching a fresh browser each task: no repeated
# macOS "Allow" prompts, no re-login, no duplicate browsers.
#
# Built to be shared and debuggable:
#   - concurrent-start safe (portable mkdir mutex; losers wait, never double-launch)
#   - structured, timestamped logs to files agents can read
#   - distinguishes down / running / WEDGED (alive but unresponsive)
#   - recovery commands scoped to THIS profile (your normal Chrome is never touched)
#
# Commands: start stop restart status health doctor recover kill login url logs
#
# Exit codes (stable, for agents):
#   0 ok   1 usage/error   3 down/not-running   4 wedged
#
# Config (env or defaults):
#   CHROME_AGENT_PORT     CDP port            (9222)
#   CHROME_AGENT_PROFILE  dedicated profile   (NON-default; see resolve_profile)
#   CHROME_AGENT_BIN      Chrome binary       (auto-detected)
#   CHROME_AGENT_HOST     CDP host            (127.0.0.1, loopback only)
#   CHROME_AGENT_STATE    state/log dir       (~/.local/state/chrome-agent)
#   CHROME_AGENT_DEBUG    1 = verbose debug logging

set -euo pipefail

PORT="${CHROME_AGENT_PORT:-9222}"
HOST="${CHROME_AGENT_HOST:-127.0.0.1}"
STATE_DIR="${CHROME_AGENT_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/chrome-agent}"
PIDFILE="$STATE_DIR/chrome.pid"
LOGFILE="$STATE_DIR/chrome.log"      # Chrome's own stdout/stderr
AGENT_LOG="$STATE_DIR/agent.log"     # this manager's structured log
LOCKDIR="$STATE_DIR/start.lock"      # mkdir-based start mutex

# Seconds to wait for the CDP endpoint after launching before declaring failure.
START_TIMEOUT=15
# Grace period between SIGTERM and SIGKILL on stop.
STOP_GRACE=5
# A start lock older than this with no live Chrome on the profile is stale and
# will be broken (covers a launcher killed mid-start).
LOCK_STALE_S=30
# Rotate a log once it crosses this size so disks never fill from chatty runs.
MAXLOG_BYTES=$((5 * 1024 * 1024))
# Health probe timeout: a healthy CDP endpoint answers in milliseconds on
# loopback; 2s cleanly separates "responsive" from "wedged".
PROBE_TIMEOUT=2

mkdir -p "$STATE_DIR"

# --- logging -----------------------------------------------------------------

_ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
_log() {
  local lvl="$1"; shift
  local line; line="$(_ts) [$lvl] (pid $$) $*"
  printf '%s\n' "$line" >>"$AGENT_LOG" 2>/dev/null || true
  printf '%s\n' "$line" >&2
}
log()   { _log INFO  "$*"; }
warn()  { _log WARN  "$*"; }
err()   { _log ERROR "$*"; }
debug() { if [[ "${CHROME_AGENT_DEBUG:-0}" == 1 ]]; then _log DEBUG "$*"; fi; }
die()   { err "$*"; exit 1; }

rotate_log() {
  local f="$1" sz
  [[ -f "$f" ]] || return 0
  sz="$(wc -c <"$f" 2>/dev/null || echo 0)"
  if (( sz > MAXLOG_BYTES )); then mv -f "$f" "$f.1"; fi
}

# --- os / config resolution --------------------------------------------------

os() { case "$(uname -s)" in Darwin) echo macos;; Linux) echo linux;; *) echo other;; esac; }

resolve_bin() {
  if [[ -n "${CHROME_AGENT_BIN:-}" ]]; then printf '%s' "$CHROME_AGENT_BIN"; return; fi
  local c
  if [[ "$(os)" == macos ]]; then
    for c in \
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
      "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta" \
      "/Applications/Chromium.app/Contents/MacOS/Chromium"; do
      [[ -x "$c" ]] && { printf '%s' "$c"; return; }
    done
  else
    for c in google-chrome google-chrome-stable chromium chromium-browser; do
      command -v "$c" >/dev/null 2>&1 && { command -v "$c"; return; }
    done
  fi
  return 1
}

# The default profile must NOT be used: since Chrome 136 the remote-debugging
# port is silently ignored on it. We use a dedicated directory.
default_chrome_dir() {
  case "$(os)" in
    macos) printf '%s' "$HOME/Library/Application Support/Google/Chrome" ;;
    linux) printf '%s' "$HOME/.config/google-chrome" ;;
    *)     printf '%s' "/nonexistent" ;;
  esac
}

resolve_profile() {
  if [[ -n "${CHROME_AGENT_PROFILE:-}" ]]; then printf '%s' "$CHROME_AGENT_PROFILE"; return; fi
  case "$(os)" in
    macos) printf '%s' "$HOME/Library/Application Support/chrome-agent-profile" ;;
    *)     printf '%s' "${XDG_DATA_HOME:-$HOME/.local/share}/chrome-agent-profile" ;;
  esac
}

PROFILE="$(resolve_profile)"
ENDPOINT="http://$HOST:$PORT"

# launchd LaunchAgent identity (autostart). Per-user label so two accounts on one
# machine never collide.
LAUNCHD_LABEL="com.chrome-agent.$(id -un 2>/dev/null || echo user)"
LAUNCHD_PLIST="$HOME/Library/LaunchAgents/$LAUNCHD_LABEL.plist"

# Absolute path to THIS script, so the generated LaunchAgent keeps working no
# matter the caller's cwd or how the skill was invoked.
self_abspath() { printf '%s/%s' "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)" "$(basename "${BASH_SOURCE[0]}")"; }

# Cookie/credential storage mode. DEFAULT is the REAL macOS keychain, so an
# interactive `login` establishes a DURABLE session - including Google's Device
# Bound Session Credentials (DBSC), whose device key must live in this profile -
# that survives restarts. `login` and `start` MUST share this mode or the key and
# cookies one writes the other cannot read. The first real-keychain access shows
# one "Chrome wants to use your keychain" dialog; click "Always Allow" once.
#
# Set CHROME_AGENT_MOCK_KEYCHAIN=1 for a prompt-free browser (antirez's
# ds4_web.c style): fine for `seed`ing non-DBSC cookie sites, but it cannot keep
# a durable Google login.
store_args() {
  if [[ "${CHROME_AGENT_MOCK_KEYCHAIN:-0}" == 1 ]]; then
    printf '%s\0' "--use-mock-keychain" "--password-store=basic"
  fi
}

# Background tabs are the whole point, so disable the throttling Chrome applies
# to background/occluded tabs - otherwise agent-driven tabs run slow and flaky.
# --remote-allow-origins avoids CDP WebSocket 403s from some clients.
chrome_args() {
  printf '%s\0' \
    "--user-data-dir=$PROFILE" \
    "--remote-debugging-port=$PORT" \
    "--remote-allow-origins=*" \
    "--no-first-run" \
    "--no-default-browser-check" \
    "--disable-sync" \
    "--mute-audio" \
    "--disable-background-timer-throttling" \
    "--disable-renderer-backgrounding" \
    "--disable-backgrounding-occluded-windows"
  store_args
}

# --- health primitives -------------------------------------------------------

# Responsive: CDP HTTP answered within PROBE_TIMEOUT.
cdp_up() { curl -sf --max-time "$PROBE_TIMEOUT" "$ENDPOINT/json/version" >/dev/null 2>&1; }
# A Chrome process is bound to OUR profile (matched by the unique --user-data-dir).
proc_on_profile() { pgrep -f -- "--user-data-dir=$PROFILE" >/dev/null 2>&1; }

# The main browser PID on our profile: it carries --user-data-dir but, unlike its
# renderer/GPU children, has no --type= flag. Needed because the macOS background
# launch (`open -g`) does not hand us Chrome's pid the way a direct exec does.
main_pid_on_profile() {
  local p
  for p in $(pgrep -f -- "--user-data-dir=$PROFILE" 2>/dev/null); do
    ps -p "$p" -o command= 2>/dev/null | grep -q -- '--type=' || { printf '%s' "$p"; return 0; }
  done
  return 1
}

# down    = no process and no endpoint
# wedged  = process alive but endpoint unresponsive (the dangerous case)
# ok      = endpoint responsive
health_state() {
  if cdp_up; then echo ok
  elif proc_on_profile; then echo wedged
  else echo down; fi
}

ensure_not_default_profile() {
  local def; def="$(default_chrome_dir)"
  [[ "$PROFILE" == "$def" ]] && die "profile equals the default Chrome dir ($def); \
remote debugging is blocked there since Chrome 136. Set CHROME_AGENT_PROFILE to a dedicated path."
  return 0
}

clean_profile_locks() {
  rm -f "$PROFILE/SingletonLock" "$PROFILE/SingletonSocket" "$PROFILE/SingletonCookie" 2>/dev/null || true
}

force_kill_profile() {
  pkill -9 -f -- "--user-data-dir=$PROFILE" 2>/dev/null || true
  rm -f "$PIDFILE" 2>/dev/null || true
}

# --- start mutex (portable: mkdir is atomic on macOS and Linux) --------------

# Prints one of: own | done | timeout
acquire_start_lock() {
  local tries=0 now ts age
  while true; do
    if mkdir "$LOCKDIR" 2>/dev/null; then
      date +%s >"$LOCKDIR/ts"; echo "$$" >"$LOCKDIR/pid"; echo "own"; return 0
    fi
    if cdp_up; then echo "done"; return 0; fi
    if [[ -f "$LOCKDIR/ts" ]]; then
      now="$(date +%s)"; ts="$(cat "$LOCKDIR/ts" 2>/dev/null || echo 0)"; age=$((now - ts))
      if (( age > LOCK_STALE_S )) && ! proc_on_profile; then
        warn "breaking stale start lock (age ${age}s)"; rm -rf "$LOCKDIR"; continue
      fi
    fi
    sleep 0.3; tries=$((tries + 1))
    if (( tries > START_TIMEOUT * 5 )); then echo "timeout"; return 0; fi
  done
}
release_start_lock() { rm -rf "$LOCKDIR" 2>/dev/null || true; }

# --- commands ----------------------------------------------------------------

cmd_start() {
  rotate_log "$AGENT_LOG"; rotate_log "$LOGFILE"
  ensure_not_default_profile
  debug "start requested; state=$(health_state)"

  if cdp_up; then log "already running at $ENDPOINT"; cmd_url; return 0; fi

  if [[ "$(health_state)" == wedged ]]; then
    warn "wedged Chrome detected on this profile; force-recovering before start"
    force_kill_profile; clean_profile_locks; sleep 1
  fi

  local tok; tok="$(acquire_start_lock)"
  case "$tok" in
    done)    log "started by a concurrent caller"; cmd_url; return 0 ;;
    timeout) die "timed out waiting for a concurrent start to finish (see $AGENT_LOG)" ;;
    own)
      # Double-checked locking: another caller may have finished bringing the
      # endpoint up between our first check and acquiring the lock. Without this
      # re-check, a late acquirer would launch a redundant second browser.
      if cdp_up; then release_start_lock; log "already running (started concurrently)"; cmd_url; return 0; fi
      debug "acquired start lock"
      ;;
  esac
  trap 'release_start_lock' EXIT

  local bin; bin="$(resolve_bin)" || die "Chrome binary not found; set CHROME_AGENT_BIN"
  if ! { [[ -x "$bin" ]] || command -v "$bin" >/dev/null 2>&1; }; then
    die "Chrome binary not executable: $bin"
  fi

  proc_on_profile || clean_profile_locks

  log "starting Chrome: $bin"
  log "  profile: $PROFILE"
  log "  cdp:     $ENDPOINT"

  local args=(); local a
  while IFS= read -r -d '' a; do args+=("$a"); done < <(chrome_args)

  # Launch a separate instance keyed to the dedicated profile; the user's normal
  # Chrome is untouched. On macOS we go through `open -g` so the window launches
  # in the BACKGROUND and never steals focus (the same trick antirez uses in
  # ds4_web.c) - critical for hands-free, non-interrupting agent sessions. `open`
  # does not relay Chrome's stdout, so chrome.log stays empty there; agent.log
  # and cdp.log still carry the full trail, and crashes land in ~/Library/Logs.
  # Elsewhere a detached nohup gives us Chrome's stdout and a deterministic PID.
  if [[ "$(os)" == macos && "$bin" == *.app/* ]]; then
    local app="${bin%.app/*}.app"
    debug "background launch via: open -g -na $app"
    open -g -na "$app" --args "${args[@]}" \
      || die "open -g failed for $app (try CHROME_AGENT_BIN, or see $AGENT_LOG)"
  else
    nohup "$bin" "${args[@]}" >>"$LOGFILE" 2>&1 &
    echo $! >"$PIDFILE"
    debug "launched pid $(cat "$PIDFILE")"
  fi

  local waited=0
  until cdp_up; do
    sleep 0.5; waited=$((waited + 1))
    if (( waited > START_TIMEOUT * 2 )); then
      err "CDP endpoint did not come up within ${START_TIMEOUT}s; last Chrome log:"
      tail -n 15 "$LOGFILE" >&2 || true
      die "start failed (chrome log: $LOGFILE, manager log: $AGENT_LOG)"
    fi
  done

  # Record the real browser PID (under `open -g` we never saw it at launch).
  local mpid; mpid="$(main_pid_on_profile || true)"
  [[ -n "$mpid" ]] && echo "$mpid" >"$PIDFILE"

  release_start_lock; trap - EXIT
  log "ready at $ENDPOINT"
  cmd_url
}

cmd_stop() {
  local stopped=0 pid
  if [[ -f "$PIDFILE" ]]; then
    pid="$(cat "$PIDFILE")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      local waited=0
      while kill -0 "$pid" 2>/dev/null && (( waited < STOP_GRACE * 2 )); do sleep 0.5; waited=$((waited + 1)); done
      kill -9 "$pid" 2>/dev/null || true
      stopped=1
    fi
    rm -f "$PIDFILE"
  fi
  if proc_on_profile; then
    pkill -f -- "--user-data-dir=$PROFILE" 2>/dev/null || true
    stopped=1
  fi
  if (( stopped )); then log "stopped."; else log "not running."; fi
}

cmd_kill() {
  warn "force-killing any Chrome on this profile"
  force_kill_profile; clean_profile_locks
  log "killed."
}

cmd_restart() { cmd_stop; sleep 1; cmd_start; }

cmd_recover() {
  warn "recover: force-killing wedged/stale Chrome on this profile, then restarting"
  force_kill_profile; clean_profile_locks; release_start_lock; sleep 1
  cmd_start
}

cmd_health() {
  local s; s="$(health_state)"
  printf '%s\n' "$s"
  case "$s" in ok) return 0 ;; wedged) return 4 ;; *) return 3 ;; esac
}

# Minimal JSON string escaper (handles the only specials our values can contain).
jstr() { local s="$1"; s="${s//\\/\\\\}"; s="${s//\"/\\\"}"; printf '"%s"' "$s"; }

cmd_status() {
  local state version tabs pid
  state="$(health_state)"
  version="null"; tabs="null"; pid="null"
  if [[ "$state" == ok ]]; then
    version="$(jstr "$(curl -sf "$ENDPOINT/json/version" | sed -n 's/.*"Browser": *"\([^"]*\)".*/\1/p')")"
    tabs="$(curl -sf "$ENDPOINT/json/list" | grep -c '"type": "page"' || true)"; tabs="${tabs:-0}"
  fi
  if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then pid="$(cat "$PIDFILE")"; fi

  if [[ "${1:-}" == "--json" ]]; then
    printf '{"state":%s,"endpoint":%s,"profile":%s,"port":%s,"pid":%s,"tabs":%s,"version":%s,"chromeLog":%s,"agentLog":%s}\n' \
      "$(jstr "$state")" "$(jstr "$ENDPOINT")" "$(jstr "$PROFILE")" "$PORT" "$pid" "$tabs" "$version" \
      "$(jstr "$LOGFILE")" "$(jstr "$AGENT_LOG")"
  else
    log "state     $state"
    log "endpoint  $ENDPOINT"
    log "profile   $PROFILE"
    log "pid       ${pid//\"/}"
    [[ "$state" == ok ]] && log "version   ${version//\"/}"
    [[ "$state" == ok ]] && log "tabs      $tabs"
    log "logs      $LOGFILE | $AGENT_LOG"
  fi
  case "$state" in ok) return 0 ;; wedged) return 4 ;; *) return 3 ;; esac
}

cmd_url() { printf '%s\n' "$ENDPOINT"; }

cmd_login() {
  ensure_not_default_profile
  local bin; bin="$(resolve_bin)" || die "Chrome binary not found; set CHROME_AGENT_BIN"
  cdp_up && die "agent Chrome is running on this profile; run 'stop' first, then 'login'."
  log "opening Chrome for interactive login (profile: $PROFILE)"
  log "log into your sites, then quit Chrome and run: $0 start"
  # Run the binary directly in the foreground; blocks until you quit Chrome.
  # No remote-debugging port here, so logins are not flagged as automation. The
  # storage mode MUST match cmd_start (store_args) or the session/DBSC key written
  # here is unreadable after `start`. The array is always non-empty, so "${a[@]}"
  # is safe under `set -u` on macOS bash 3.2.
  local args=(--user-data-dir="$PROFILE" --no-first-run --no-default-browser-check)
  local s; while IFS= read -r -d '' s; do args+=("$s"); done < <(store_args)
  "$bin" "${args[@]}"
}

# Generate and (un)load a LaunchAgent that runs `start` at login. No hand-edited
# paths: the plist is written with this script's resolved absolute path and the
# active port/profile, so it is correct by construction.
cmd_autostart() {
  [[ "$(os)" == macos ]] || die "autostart uses macOS launchd; on Linux see reference/launchd.md (systemd --user)"
  local action="${1:-on}" self; self="$(self_abspath)"
  case "$action" in
    on)
      mkdir -p "$HOME/Library/LaunchAgents"
      {
        printf '<?xml version="1.0" encoding="UTF-8"?>\n'
        printf '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        printf '<plist version="1.0"><dict>\n'
        printf '  <key>Label</key><string>%s</string>\n' "$LAUNCHD_LABEL"
        printf '  <key>ProgramArguments</key><array>\n'
        printf '    <string>/bin/bash</string><string>%s</string><string>start</string>\n' "$self"
        printf '  </array>\n'
        printf '  <key>EnvironmentVariables</key><dict>\n'
        printf '    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>\n'
        printf '    <key>CHROME_AGENT_PORT</key><string>%s</string>\n' "$PORT"
        [[ -n "${CHROME_AGENT_PROFILE:-}" ]] && printf '    <key>CHROME_AGENT_PROFILE</key><string>%s</string>\n' "$CHROME_AGENT_PROFILE"
        [[ -n "${CHROME_AGENT_STATE:-}" ]] && printf '    <key>CHROME_AGENT_STATE</key><string>%s</string>\n' "$CHROME_AGENT_STATE"
        printf '  </dict>\n'
        printf '  <key>RunAtLoad</key><true/>\n'
        printf '  <key>StandardOutPath</key><string>%s/launchd.out.log</string>\n' "$STATE_DIR"
        printf '  <key>StandardErrorPath</key><string>%s/launchd.err.log</string>\n' "$STATE_DIR"
        printf '</dict></plist>\n'
      } >"$LAUNCHD_PLIST"
      launchctl unload "$LAUNCHD_PLIST" 2>/dev/null || true
      launchctl load -w "$LAUNCHD_PLIST" || die "launchctl load failed for $LAUNCHD_PLIST"
      log "autostart enabled -> $LAUNCHD_PLIST"
      log "  runs '$self start' at every login (and just now); idempotent."
      ;;
    off)
      launchctl unload "$LAUNCHD_PLIST" 2>/dev/null || true
      rm -f "$LAUNCHD_PLIST"
      log "autostart disabled (removed $LAUNCHD_PLIST)"
      ;;
    status)
      if launchctl list 2>/dev/null | grep -q "$LAUNCHD_LABEL"; then
        log "autostart loaded ($LAUNCHD_LABEL)"
      else
        log "autostart not loaded"
      fi
      if [[ -f "$LAUNCHD_PLIST" ]]; then log "plist $LAUNCHD_PLIST"; else log "plist none"; fi
      ;;
    *) die "usage: autostart [on|off|status]" ;;
  esac
}

cmd_doctor() {
  local issues=0 bin state port_owner lock_age du_profile errcount
  printf 'os          %s\n' "$(os)"
  if bin="$(resolve_bin)"; then printf 'binary      %s\n' "$bin"; else printf 'binary      NOT FOUND (set CHROME_AGENT_BIN)\n'; issues=$((issues+1)); fi
  printf 'profile     %s\n' "$PROFILE"
  if [[ "$PROFILE" == "$(default_chrome_dir)" ]]; then printf '            ISSUE: default profile - CDP blocked since Chrome 136\n'; issues=$((issues+1)); fi
  printf 'endpoint    %s\n' "$ENDPOINT"
  state="$(health_state)"; printf 'state       %s\n' "$state"
  [[ "$state" == wedged ]] && { printf '            ISSUE: wedged - run "%s recover"\n' "$0"; issues=$((issues+1)); }

  if command -v lsof >/dev/null 2>&1; then
    port_owner="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | awk 'NR==2{print $1" (pid "$2")"}')"
    printf 'port owner  %s\n' "${port_owner:-none}"
  fi
  if [[ -f "$PIDFILE" ]]; then
    if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then printf 'pidfile     %s (alive)\n' "$(cat "$PIDFILE")"
    else printf 'pidfile     %s (stale)\n' "$(cat "$PIDFILE")"; fi
  else printf 'pidfile     none\n'; fi

  if [[ -d "$LOCKDIR" ]]; then
    lock_age=$(( $(date +%s) - $(cat "$LOCKDIR/ts" 2>/dev/null || date +%s) ))
    printf 'start lock  present (age %ss)%s\n' "$lock_age" "$( (( lock_age > LOCK_STALE_S )) && printf ' - STALE' )"
  else printf 'start lock  none\n'; fi

  if [[ -d "$PROFILE" ]]; then du_profile="$(du -sh "$PROFILE" 2>/dev/null | cut -f1)"; printf 'profile sz  %s\n' "${du_profile:-?}"; fi
  if [[ "$state" == ok ]]; then printf 'tabs        %s\n' "$(curl -sf "$ENDPOINT/json/list" | grep -c '"type": "page"' || true)"; fi

  if command -v node >/dev/null 2>&1; then printf 'node        %s (chrome-devtools-mcp needs 22+)\n' "$(node --version)"; else printf 'node        not found (chrome-devtools-mcp needs Node 22+)\n'; fi
  if command -v uv >/dev/null 2>&1; then printf 'uv          %s (cdp.py needs uv)\n' "$(uv --version)"; else printf 'uv          not found (cdp.py needs uv)\n'; fi

  printf 'chrome log  %s\n' "$LOGFILE"
  printf 'agent log   %s\n' "$AGENT_LOG"
  if [[ -f "$AGENT_LOG" ]]; then errcount="$(grep -c '\[ERROR\]' "$AGENT_LOG" || true)"; printf 'log errors  %s\n' "${errcount:-0}"; fi

  if (( issues )); then printf '\nRESULT: %s issue(s) found\n' "$issues"; return 1; else printf '\nRESULT: ok\n'; fi
}

cmd_logs() {
  local which="${1:-agent}" n="${2:-40}" f
  case "$which" in
    chrome) f="$LOGFILE" ;;
    agent)  f="$AGENT_LOG" ;;
    *)      n="$which"; which="agent"; f="$AGENT_LOG" ;;  # `logs 100` shorthand
  esac
  printf '== %s (last %s) ==\n' "$f" "$n" >&2
  tail -n "$n" "$f" 2>/dev/null || log "no log at $f"
}

main() {
  local sub="${1:-}"; shift || true
  case "$sub" in
    start)   cmd_start "$@" ;;
    stop)    cmd_stop "$@" ;;
    restart) cmd_restart "$@" ;;
    status)  cmd_status "$@" ;;
    health)  cmd_health "$@" ;;
    doctor)  cmd_doctor "$@" ;;
    recover) cmd_recover "$@" ;;
    kill)    cmd_kill "$@" ;;
    login)   cmd_login "$@" ;;
    autostart) cmd_autostart "$@" ;;
    url)     cmd_url "$@" ;;
    logs)    cmd_logs "$@" ;;
    ""|-h|--help)
      cat >&2 <<EOF
chrome-agent.sh - persistent authenticated Chrome with CDP, shared by all agents

usage: $0 <command>
  start        launch the shared Chrome (idempotent, concurrent-start safe)
  stop         graceful stop (this profile only; your main Chrome is safe)
  restart      stop then start
  recover      force-kill a wedged/stale instance and restart
  kill         hard stop (SIGKILL, this profile only)
  status       human status; 'status --json' for machine-readable health
  health       print down|wedged|ok; exit 3|4|0 for agent decisioning
  doctor       full diagnostics (binary, profile, port owner, locks, logs)
  login        open a normal window to log into sites once (run before start)
  autostart [on|off|status]  install/remove a login LaunchAgent (macOS; self-pathing)
  url          print the CDP browser-url
  logs [chrome|agent] [N]   tail a log

exit codes: 0 ok | 1 usage/error | 3 down | 4 wedged
env: CHROME_AGENT_PORT PROFILE BIN HOST STATE DEBUG
EOF
      [[ -z "$sub" ]] && return 1 || return 0 ;;
    *) die "unknown command: $sub (try --help)" ;;
  esac
}

main "$@"
