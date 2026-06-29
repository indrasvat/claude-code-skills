---
name: browsing-as-you
description: >
  Drive ONE persistent, already-authenticated Chrome — the user's real logged-in
  sessions — over the DevTools Protocol, instead of spawning a fresh unauthenticated
  browser per task. Use when a task needs the browser SIGNED IN AS THE USER:
  screenshotting a logged-in page, filling a form, posting a comment, uploading a
  file, attaching an image to a GitHub PR, or driving an app whose API can't —
  Gmail, Google Docs/Drive, Cloudflare, X, GitHub, Devin, or any site the user is
  signed into. Prefer over chrome-devtools-mcp, agent-browser, Playwright, or
  Puppeteer when they would open a new unauthenticated Chrome, hit a login wall, or
  cause repeated macOS Allow/keychain prompts. Bundles chrome-agent.sh
  (start/login/seed/autostart) and cdp.py (tabs, --front, navigate, eval,
  screenshot, seed logins). Triggers: "use my logged-in browser",
  "authenticated Chrome", "act as me on <site>", "share my cookies",
  "no API for this", "chrome-devtools-mcp", "browser-url", "stop the Allow popups".
---

# browsing-as-you

Run ONE long-lived, logged-in Chrome with remote debugging on; every agent and
tool attaches to it. No per-task browser launches, no re-login, no macOS "Allow"
prompts. Tabs and the window open in the background (`open -g`), never stealing
focus.

**Golden rule:** never launch your own Chrome — attach to the shared instance at
`http://127.0.0.1:9222`. Deep detail lives in `reference/integration.md`
(setup, concurrency, triage) and `reference/launchd.md` (autostart).

## 1. Start (idempotent, concurrent-safe)

```bash
scripts/chrome-agent.sh start      # prints http://127.0.0.1:9222 when live
```

Triage: `health` → `ok|down|wedged` (exit 0|3|4) · `doctor` for diagnostics ·
`recover` a wedged one · `stop`/`kill` touch only the bridge profile (your real
Chrome is safe). Full table + runbook: `reference/integration.md`.

> **Agent: bring it up yourself — don't bail, don't ask.** If you land mid-task
> and `health` is `down`/`wedged`, just run `start` (idempotent, concurrent-safe)
> and, for a cookie site, `seed` (prompt-free — see §2); then carry on and
> actually drive the browser. Reporting "the bridge was down" as a blocker, or
> asking the user to start it, defeats the whole point of the skill. The user
> should not be pinged for perms. The **only** human step is `login` (typing a
> password), and only for the localStorage/SSO sites flagged in §2 — never for
> plain cookie sites like GitHub.

## 2. Authenticate (the bridge starts logged out)

It uses a **dedicated profile** — it must, since Chrome 136 ignores the debug
port on your default profile. Give it your sessions one of two ways:

```bash
scripts/cdp.py seed                     # import logins from your Default Chrome
scripts/cdp.py seed --filter github.com #   (cookies only; also --profile/--dry-run)
scripts/chrome-agent.sh login           # OR sign in once in the bridge (stop first)
```

| Site type | via `seed` | durable answer |
| --- | --- | --- |
| Normal cookie sites (GitHub, most SaaS, X) | ✅ survives restart | `seed` once |
| DBSC (Google, YouTube) | live only — drops on restart | `login` once |
| **localStorage / SSO SPAs (Cloudflare, Devin)** | ❌ **not covered — looks authed, renders sign-in** | **`login` once** |

> **localStorage/SSO dashboards: prefer `login`, not `seed`.** Cloudflare and
> similar SPAs keep part of their auth in localStorage or a device-bound SSO key
> that cookie-only `seed` can't carry. The catch: `seed` reports success, cookies
> *are* injected, and `location.href` still reads as authed — but the SPA quietly
> renders its **sign-in screen** (no redirect, so a URL check is fooled). Don't
> trust a URL heuristic; confirm with a DOM probe:
> `cdp.py probe https://dash.cloudflare.com --front` → `login-wall |
> likely-authed`. (`--front` matters: CF's dash is visibility-gated and renders
> blank in a hidden tab, which reads as `unknown`.) A `login-wall` after `seed`
> means: run `chrome-agent.sh login` for that site.

`seed` is cookies-only and reads your real profile locally (nothing leaves the
machine, nothing is written back). `login` creates the device key *inside* the
bridge profile, so Gmail, Docs/Drive, X, and Cloudflare stay authed across
restarts **and reboots** — verified. **Adding a new site later:** `seed --filter
<host>` if you're already signed in there, else one `login`. At most one login
per site, then it persists; an agent can't type your password — that's the only
human step.

## 3. Drive it

Preferred: **chrome-devtools-mcp** pointed at the browser (`--browser-url
http://127.0.0.1:9222`; setup in `reference/integration.md`). Or `scripts/cdp.py`:

| Need | Command |
| --- | --- |
| open background tab, wait for load | `cdp.py open <url> -w` → prints `targetId` |
| open + foreground a visibility-gated SPA | `cdp.py open <url> --front -w` |
| eval JS · screenshot · navigate | `cdp.py eval '<js>' -t <id>` · `shot out.png -t <id>` · `nav <url> -t <id>` |
| **trusted click** (coords or selector) | `cdp.py click '#submit' -t <id>` · `click 240,180 -t <id>` |
| **trusted type** (into focused / a selector) | `cdp.py type 'hello' -t <id>` · `type 'us-east' --into '[role=combobox]' --enter -t <id>` |
| **trusted key** (Enter/Tab/Arrow…) | `cdp.py key ArrowDown -t <id>` · `key Enter -t <id>` |
| **auth probe** (is it really logged in?) | `cdp.py probe <url> --front` → `login-wall \| likely-authed \| unknown` |
| **upload files to a GitHub issue/PR** (no submit click) | `cdp.py --json gh-attach --repo o/r --pr 19 -f a.png -f b.log` → asset URLs |
| foreground · close · sweep blanks | `cdp.py front -t <id>` · `close <id>` · `gc` |
| isolated context | `cdp.py ctx new` → `open <url> --context <id>` → `ctx close <id>` |

Trusted verbs (`click`/`type`/`key`) use the CDP **Input** domain — real
`isTrusted` events — so they drive react-select dropdowns, `role=combobox`
widgets, and native checkboxes that ignore synthetic `eval`-dispatched events.
`click`/`type --into` take a CSS selector (scrolled into view) or `x,y` coords.

`--json` (before the subcommand) for machine-readable output. **Concurrency:**
each agent owns its `targetId` and passes `-t`; set `CHROME_AGENT_STRICT=1` to
make `eval`/`nav` refuse an implicit tab. Full rules: `reference/integration.md`.

## GitHub attachments — safe two-phase upload

To attach local files (screenshots, logs, **any** file type) to a GitHub issue
or PR without committing binaries to the repo, **never** drive the page's submit
button: GitHub puts **Close / Merge / Delete / Reopen / Submit-review** controls
right next to the comment box, and a broad "first enabled submit" selector can
click a destructive one after the upload. Split it in two:

**Phase 1 — upload only (browser), prints the `user-attachments` URLs:**

```bash
cdp.py --json gh-attach --repo OWNER/REPO --pr 19 -f ./shot-1.png -f ./trace.log
#   --issue N for issues · --url <full link> · -t <tab already on the page>
```

`gh-attach` sets the files on GitHub's hidden file input over CDP and reads the
URL(s) back from the composer — it issues **zero clicks**, so destructive
controls are unreachable by construction. It **fails closed**: if the comment
box isn't found (logged out / no permission) or a URL never appears, it restores
the composer, leaves the page untouched, and exits non-zero. It uploads any file
type (`assets/<uuid>` for images, `files/<n>/<name>` otherwise); it never posts.

**Phase 2 — post the comment yourself via the API** (no page button). `gh-attach`
prints the ready line; it uses the issues endpoint (PR comments included):

```bash
gh api repos/OWNER/REPO/issues/19/comments -f body="$(...uploaded markdown...)"
```

> Posting through the browser is intentionally unsupported — `--allow-submit` is
> refused. Treat PR Close/Merge/Reopen/Delete as out of scope unless the user
> explicitly asks. Self-test the helper logic with `make test-browsing`.

## Guardrails

- **Be a good citizen.** Human pace, not machine-gun. A CAPTCHA / "unusual
  traffic" / interstitial is a STOP sign, not a retry trigger — back off and tell
  the user. Prefer official APIs for bulk work. A blank/stuck SPA is usually just
  a hidden background tab → `--front`, not bot detection.
- **Trusted input is not for CAPTCHA.** `click`/`type`/`key` are for app forms,
  not human-verification. `click` refuses any target inside a reCAPTCHA /
  hCaptcha / Cloudflare Turnstile widget (exit 2) — solving a challenge stays a
  human step. Don't try to coordinate-click around the guard.
- **Dedicated profile, loopback only.** `seed` reads your real profile but never
  writes to it; the debug port binds to `127.0.0.1` — never expose it. `stop`/
  `kill`/`recover` only ever touch the bridge profile.
- **Real keychain by default** so `login` is durable (one "Always Allow" at
  most). `CHROME_AGENT_MOCK_KEYCHAIN=1` gives a prompt-free, seed-only browser.
- **Clean up** tabs you open (`gc` / `close`).

## Setup & autostart (human, once)

`seed` or `login` to authenticate, wire up chrome-devtools-mcp
(`reference/integration.md`), and for hands-free use
`scripts/chrome-agent.sh autostart on` — a self-pathing login LaunchAgent
(Linux: systemd, see `reference/launchd.md`). Needs `uv`; chrome-devtools-mcp
needs Node 22+; `seed` is macOS-only.
