# Integration & troubleshooting

How to point each agent/tool at the shared Chrome, plus failure modes and fixes.

## Contents
- The connection string
- Claude Code
- Codex CLI
- Gemini CLI
- agent-browser CLI
- Raw .mcp.json
- Why a dedicated profile (Chrome 136)
- Sharing your existing logins (seed)
- Failure modes and fixes
- Multiple agents and sub-agents on one Chrome
- Triage runbook: wedged or misbehaving Chrome

## The connection string

Everything connects to the same endpoint the launcher prints:

```
http://127.0.0.1:9222
```

chrome-devtools-mcp accepts it as `--browser-url` (alias `--browserUrl`, `-u`).
Confirm it is live first: `scripts/chrome-agent.sh start` then
`scripts/cdp.py ping`.

## Claude Code

Register the MCP server once; it attaches to the running browser:

```bash
claude mcp add --transport stdio chrome-devtools \
  -- npx -y chrome-devtools-mcp@latest \
     --browser-url=http://127.0.0.1:9222 \
     --no-usage-statistics
```

Then in a session, ensure the browser is up (`scripts/chrome-agent.sh start`)
and use the `chrome-devtools:*` tools. The `--` separates Claude Code's flags
from the server's args.

## Codex CLI

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.chrome-devtools]
command = "npx"
args = ["-y", "chrome-devtools-mcp@latest", "--browser-url=http://127.0.0.1:9222", "--no-usage-statistics"]
```

## Gemini CLI

Add to `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest", "--browser-url=http://127.0.0.1:9222", "--no-usage-statistics"]
    }
  }
}
```

## agent-browser CLI

Any CDP client connects to the same endpoint. Point it at the running browser
rather than letting it spawn one, e.g.:

```bash
agent-browser --cdp-endpoint http://127.0.0.1:9222 ...
# or, if it wants a websocket: use the ws url from
scripts/cdp.py endpoint
```

If the tool only accepts a websocket endpoint, pass the `wsEndpoint` line from
`cdp.py endpoint`. If it has no attach flag, fall back to `scripts/cdp.py`.

## Raw .mcp.json

Project-local `.mcp.json` consumed by MCP-aware clients:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest", "--browser-url=http://127.0.0.1:9222", "--no-usage-statistics"]
    }
  }
}
```

## Why a dedicated profile (Chrome 136)

Starting with Chrome 136 (mid-2025), `--remote-debugging-port` is ignored when
Chrome runs on the **default** user-data-dir, to stop malware from draining
cookies from your everyday profile. The fix is a separate `--user-data-dir`,
which is exactly what `chrome-agent.sh` uses (a dedicated path, never the
default). You log into that profile once; its cookies and sessions persist and
are reused on every headless/background run.

## Sharing your existing logins (seed)

The dedicated profile starts logged out. `scripts/cdp.py seed` imports the
sessions from one of your real Chrome profiles so the bridge acts as you, without
re-authenticating each site.

How it works (macOS):

1. Reads the AES key from the login keychain
   (`security find-generic-password -s 'Chrome Safe Storage' -w`), derives the
   cookie key (PBKDF2-HMAC-SHA1, salt `saltysalt`, 1003 iterations, 16 bytes).
2. Copies the source profile's `Cookies` SQLite to a temp file (so Chrome's own
   file is never locked) and decrypts each value: strip the `v10` prefix,
   AES-128-CBC with a 16-space IV, drop PKCS7 padding, then strip the 32-byte
   `sha256(host_key)` domain-binding prefix recent Chrome prepends.
3. Injects the cookies into the running bridge over CDP (`Storage.setCookies`),
   in batches with a per-cookie retry so one bad cookie can't sink the rest.

This is the local, same-machine half of what **agentcookie.dev** does (it syncs
the same decrypted cookies to a *second* Mac/VM over Tailscale). On one machine
you don't need the sync layer — `seed` is a one-shot local inject. Your real
cookies are read locally and pushed only into the local bridge; nothing is
written back to your real profile and nothing leaves the machine.

```bash
scripts/cdp.py seed                       # from Default
scripts/cdp.py seed --profile "Profile 1" # a specific profile
scripts/cdp.py seed --filter github.com   # only one host
scripts/cdp.py --json seed --dry-run      # counts only, machine-readable
```

### What seed can and cannot carry

- **Cookies only** — not localStorage/IndexedDB, and not device-bound SSO keys.
  SPAs that keep their session token in localStorage or behind a device-bound
  single-sign-on (e.g. **Cloudflare dashboard**, Devin) will still hit a login
  wall after `seed`, even though cookies were injected. Use `chrome-agent.sh
  login` once for those — it creates the device key *inside* the bridge profile,
  so they stay authed across restarts and reboots.
- **DBSC (Device Bound Session Credentials).** Google and YouTube bind the
  session to a device key stored in the *source* profile. A seeded cookie
  authenticates for the current session, but on the next bridge restart Chrome
  re-validates against that key, fails to find it, and signs out. Re-run `seed`
  at the start of a session, or `login` once into the bridge for durability.
- **Normal cookie sessions** (GitHub and most apps) seed durably and survive
  restarts.

### Verify with a DOM probe, not the URL

A URL-only "loggedIn" check is **unreliable for SPAs**. `seed` reports success
and injects cookies, but a localStorage/SSO app (Cloudflare) renders its sign-in
screen *without redirecting* — so `location.href` still reads as authed and the
agent only discovers the wall after trying to act. `scripts/cdp.py probe`
inspects the DOM (visible password fields, sign-in text, login forms) instead:

```bash
scripts/cdp.py probe https://dash.cloudflare.com --front
#   verdict: login-wall | likely-authed | unknown
```

- `login-wall` after `seed` → that site needs `chrome-agent.sh login` (its auth
  isn't in cookies). This is the common Cloudflare case.
- `--front` matters for visibility-gated SPAs: the Cloudflare dash renders blank
  in a hidden background tab, which the probe reports as `unknown`. Front it so
  the SPA hydrates, then the verdict is real. (`probe` already waits for load and
  re-checks for a few seconds while the SPA hydrates.)
- `unknown` = the probe couldn't find sign-in markers *or* confirm content —
  treat it as "look closer" (screenshot, check a known authed-only selector),
  not as a pass.

## Trusted input (click / type / key)

Synthetic `MouseEvent`/`KeyboardEvent` dispatched through `eval` are
`isTrusted: false`; modern widgets — react-select dropdowns, `role=combobox`
inputs, native checkboxes — ignore them. The Input verbs use the CDP **Input**
domain, which emits OS-level trusted events that drive these widgets exactly like
a human:

```bash
cdp.py click '#submit' -t <id>              # selector: scrolled into view, center-clicked
cdp.py click 240,180 -t <id>                # or raw viewport x,y
cdp.py type 'us-east-1' --into '[role=combobox]' --enter -t <id>   # focus, insertText, Enter
cdp.py type 'hello' -t <id>                 # into whatever is focused
cdp.py key ArrowDown -t <id>                # Enter Tab Escape Backspace Delete Arrow* Home End PageUp PageDown Space
```

- `click`/`type --into` accept a CSS selector (scrolled to center first) or `x,y`
  coords. react-select options are often portaled/virtualized — typing to filter
  then `key ArrowDown` + `key Enter` (or `type --enter`) is more robust than
  hunting for the option's coordinates.
- **CAPTCHA is a hard stop.** `click` refuses any target inside a reCAPTCHA /
  hCaptcha / Cloudflare Turnstile widget and exits 2. Human-verification stays a
  human step — don't reach for coordinate-clicks to bypass the guard; back off
  and tell the user.
- Visibility-gated SPAs (Cloudflare dash) must be `--front`ed before driving
  them, or the elements you click won't have rendered.

## Failure modes and fixes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `cdp.py` says "cannot reach Chrome" | not started | `scripts/chrome-agent.sh start` |
| Port 9222 already in use | another Chrome/tool owns it | `lsof -i :9222`; stop the other, or set `CHROME_AGENT_PORT` and match it in your MCP `--browser-url` |
| MCP launches its own empty Chrome | missing/typo'd `--browser-url` | re-add the server with the exact flag; confirm with `scripts/cdp.py ping` |
| Debugging silently disabled, no `/json` | profile is the default Chrome dir | use the dedicated profile (default behavior); never set `CHROME_AGENT_PROFILE` to the real Chrome dir |
| WebSocket 403 / host-header rejected | connecting via a hostname | always use `127.0.0.1`, not `localhost`-as-hostname tricks or LAN IPs |
| Google login blocked as "insecure browser" | logging in inside the debug instance | use `chrome-agent.sh login` (a normal window, no debug port), then `start` |
| Need a visible window | macOS launches in background | bring it up from the Dock, or run the binary without `nohup` for that session |
| Stale `SingletonLock`, won't start | previous crash | `start` clears it automatically when no live process owns the profile |
| Process alive but all calls hang/time out | browser **wedged** | `chrome-agent.sh health` shows `wedged` (exit 4); run `chrome-agent.sh recover` |
| Concurrent agents stomping each other's tab | sharing one tab | each agent uses its own `targetId` (`-t`); set `CHROME_AGENT_STRICT=1` to enforce |
| `seed` runs but a site is still logged out | token in localStorage / device-bound SSO, not cookies (Cloudflare, Devin) | `chrome-agent.sh login` once for that site; confirm with `cdp.py probe <url> --front` |
| `seed` looked fine but the SPA shows its sign-in screen | URL didn't redirect, so a `location.href` check read as authed | don't trust the URL — `cdp.py probe <url> --front` reads the DOM (`login-wall` ⇒ needs `login`) |
| Synthetic click/type doesn't open a dropdown / check a box | `eval`-dispatched events are `isTrusted:false` | use the Input verbs: `cdp.py click`/`type`/`key` (trusted events) |
| `cdp.py click` exits 2 on a "verify you're human" box | target is a CAPTCHA/Turnstile widget (guarded) | this is intended — solving the challenge is a human step; stop and hand off |
| Google/YouTube authed after `seed` but logged out after a restart | DBSC device-bound session | re-run `seed` each session, or `login` once into the bridge (durable — the device key is created in this profile) |
| `seed` errors reading the keychain | login keychain locked / access denied | unlock the keychain and approve the `security` access prompt, then retry |
| Authed (cookies present) but a dashboard renders blank/loader forever | tab is a background tab, `visibilityState: hidden`; some SPAs (e.g. Cloudflare dash) won't render until visible | foreground it: `cdp.py open <url> --front` or `cdp.py front -t <id>` (not bot detection; don't loop-reload) |
| Need to know what happened/when | — | read `<state>/agent.log`, `<state>/cdp.log` (trace ids); on macOS `chrome.log` is empty under `open -g` |

### macOS permission prompts ("Allow")

The repeated prompts come from launching a new Chrome (or AppleScript-driven
automation) each task. This setup removes that: Chrome starts **once** (ideally
at login via `chrome-agent.sh autostart on`, see `reference/launchd.md`) and all
tools attach over CDP, which is plain HTTP/WebSocket on loopback — no Apple
Events, so no automation permission dialog, and no first-run prompts on every
task. New tabs and the initial window launch in the background (`open -g`), so
nothing ever steals focus.

By default the browser uses the **real** macOS keychain (so a `login` session,
including Google's device-bound key, is durable). That may show one "Chrome wants
to use your keychain → Always Allow" dialog the first time — usually not even
that, since your everyday Chrome already authorized the same binary. If you only
`seed` non-DBSC cookie sites and want a guaranteed prompt-free browser, set
`CHROME_AGENT_MOCK_KEYCHAIN=1` (the antirez `ds4_web.c` mode).

## Multiple agents and sub-agents on one Chrome

The browser process is multi-client by design; the risk is two agents driving the
same **tab**. Rules that make concurrent use safe (all verified in-sandbox):

- **One tab per agent.** Each agent/sub-agent calls `cdp.py open` to get its own
  `targetId` and passes `-t <targetId>` to every `eval`/`nav`/`shot`. Capturing
  and reusing that id is the whole game.
- **Enforce ownership.** Export `CHROME_AGENT_STRICT=1` (or pass `--strict`).
  `eval`/`nav` then refuse to act on an implicit "most recent" tab, so a careless
  sub-agent errors out (exit 2) instead of hijacking a peer's tab.
- **Isolate sessions with contexts.** When two agents need different
  cookies/storage, give each its own browser context:
  `id=$(cdp.py ctx new)` → `cdp.py open <url> --context "$id"` →
  `cdp.py ctx close "$id"`. A context is an isolated cookie jar and does **not**
  inherit the default profile's logins; for shared-login work use the default
  context with owned tabs instead. `cdp.py open --isolated` does context+tab in
  one step and prints both ids.
- **Start is race-safe.** If several agents call `start` at once, a portable
  mkdir mutex plus a double-checked `cdp_up` guarantees exactly one launch; the
  others wait for the endpoint and return success.

### chrome-devtools-mcp with several agents

Multiple `chrome-devtools-mcp` instances attached to the same `--browser-url`
**share every tab** and may select the same page — there is no per-instance tab
ownership. For genuinely parallel sub-agents, prefer one of:

1. `cdp.py` with explicit per-agent `targetId`s (simplest, fully isolated calls).
2. One isolated **browser context** per sub-agent (`ctx new` + `open --context`).
3. One MCP instance as the single browser driver, with sub-agents handing it work
   serially rather than each opening their own MCP connection.

## Lifecycle commands

`chrome-agent.sh` is the control plane (exit codes: **0** ok · **1** usage/error ·
**3** down · **4** wedged):

| Need | Command |
| --- | --- |
| Start (idempotent, race-safe) | `chrome-agent.sh start` |
| Machine-readable health | `chrome-agent.sh status --json` |
| One-word health + exit code | `chrome-agent.sh health` → `ok\|down\|wedged` |
| Full diagnostics | `chrome-agent.sh doctor` |
| Recover a wedged/stale instance | `chrome-agent.sh recover` |
| Graceful stop (this profile only) | `chrome-agent.sh stop` |
| Hard stop (SIGKILL, this profile) | `chrome-agent.sh kill` |
| Sign in once inside the bridge | `chrome-agent.sh login` |
| Install/remove login autostart | `chrome-agent.sh autostart on\|off\|status` |
| Tail logs | `chrome-agent.sh logs agent` / `logs chrome` |

`cdp.py` requirements: runs via **uv** (PEP 723 deps: httpx, websockets, click,
loguru, cryptography; first run resolves in ~1s). `seed` is **macOS-only** (reads
the "Chrome Safe Storage" keychain key) — on Linux use `login`. chrome-devtools-mcp
needs **Node 22+**.

## Triage runbook: wedged or misbehaving Chrome

Background Chrome can hang (GPU stall, OOM, a runaway page) so the process lives
but CDP stops responding. Triage in order:

1. **Classify** — `chrome-agent.sh health` (or `status --json`):
   - `ok` → browser is fine; the bug is your tab or script. Open `<state>/cdp.log`,
     find your `trace=` id, read the failing call and its error.
   - `wedged` → `chrome-agent.sh recover`. This SIGKILLs only this profile's
     Chrome, clears `Singleton*` locks and the pidfile, then restarts.
   - `down` → `chrome-agent.sh start`.
2. **Diagnose** — `chrome-agent.sh doctor` prints binary, profile, port owner
   (`lsof`), pidfile/lock state and ages, profile size, log locations, and an
   error count, then `RESULT: ok` or `RESULT: N issue(s)` (nonzero exit on issues).
3. **Trace** — three logs under `<state>` (default `~/.local/state/chrome-agent`,
   override `CHROME_AGENT_STATE`), all timestamped and rotated at 5 MB:
   - `agent.log` — every lifecycle action by the manager.
   - `cdp.log` — every `cdp.py` call with pid, duration, and `trace` id.
   - `chrome.log` — Chrome's own stdout/stderr (crash output lands here).
4. **Reset** — if all else fails, `chrome-agent.sh kill` then `start`. Your normal
   Chrome is never affected; kills are scoped to the dedicated `--user-data-dir`.

### Exit codes (for scripting agents)

`chrome-agent.sh`: `0` ok · `1` usage/error · `3` down · `4` wedged.
`cdp.py`: `0` ok · `2` bad usage/target (incl. strict-mode refusal) · `3` cannot
reach Chrome (down or wedged — message says which).
