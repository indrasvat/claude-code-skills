#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "click>=8.1",
#   "httpx>=0.27",
#   "websockets>=13",
#   "loguru>=0.7",
#   "cryptography>=42",
# ]
# ///
"""cdp.py - drive an already-running Chrome over the DevTools Protocol.

Connects to a Chrome started with --remote-debugging-port (see chrome-agent.sh).
Safe to run from many agents and sub-agents at once against ONE shared browser:

  * Each new tab opens in the BACKGROUND and returns a unique targetId. Operate
    on YOUR targetId (-t) so concurrent agents never clobber each other's tabs.
  * `--strict` (or CHROME_AGENT_STRICT=1) refuses the implicit "most recent tab"
    fallback, forcing explicit -t in shared setups.
  * For full isolation (separate cookies/storage), give each agent its own
    browser context: `ctx new` -> open --context <id> -> `ctx close <id>`.

Every invocation is logged with a trace id to <state>/cdp.log for triage.

Exit codes: 0 ok | 2 bad usage/target | 3 cannot reach Chrome
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import platform
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import click
import httpx
import websockets
from loguru import logger

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9222

# CDP results (DOM snapshots, big eval payloads) can exceed the websockets 1 MiB
# default frame cap and raise mid-read. These are short request/response calls,
# so lifting the cap avoids spurious failures.
WS_MAX_SIZE = None
# One CDP round-trip on loopback answers in milliseconds; this bounds hangs so a
# wedged browser surfaces a clear error instead of blocking forever.
CALL_TIMEOUT_S = 30.0
# The /json/* HTTP endpoints are instant when healthy; a shorter bound makes a
# wedged (alive-but-frozen) browser detectable quickly instead of after 30s.
HTTP_PROBE_TIMEOUT_S = 10.0
# Poll cadence when waiting for a navigation to reach readyState "complete".
READY_POLL_S = 0.25


def _state_dir() -> Path:
    env = os.environ.get("CHROME_AGENT_STATE")
    if env:
        return Path(env)
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "chrome-agent"


def _setup_logging(trace: str, verbose: bool) -> Any:
    logger.remove()
    fmt = "{time:YYYY-MM-DDTHH:mm:ss!UTC}Z [{level}] (pid {process}) trace={extra[trace]} {message}"
    try:
        d = _state_dir()
        d.mkdir(parents=True, exist_ok=True)
        logger.add(d / "cdp.log", rotation="5 MB", retention=5, level="DEBUG", format=fmt)
    except OSError:
        pass  # logging must never break the tool
    if verbose:
        logger.add(sys.stderr, level="DEBUG", format=fmt)
    return logger.bind(trace=trace)


def base_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


async def _get_json(url: str, log: Any) -> Any:
    try:
        async with httpx.AsyncClient(timeout=HTTP_PROBE_TIMEOUT_S) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        _die_unreachable(url, exc, log)
    except httpx.TimeoutException as exc:
        # Connected but no response in time: the browser is likely wedged.
        log.error(f"http timeout {url}: {exc!r}")
        click.echo("error: Chrome accepted the connection but did not respond "
                   "(likely wedged); run: chrome-agent.sh recover", err=True)
        raise SystemExit(3) from exc


def _die_unreachable(url: str, exc: Exception, log: Any) -> None:
    log.error(f"unreachable {url}: {exc!r}")
    click.echo(
        f"error: cannot reach Chrome at {url} ({exc.__class__.__name__}).\n"
        f"hint: chrome-agent.sh start   (or 'chrome-agent.sh health' to triage)",
        err=True,
    )
    raise SystemExit(3)


# CDP methods whose params carry secrets (cookie values) we must never write to
# the on-disk log: `seed` pushes decrypted real cookies through Storage.setCookies.
_SENSITIVE_METHODS = {"Storage.setCookies", "Network.setCookie", "Network.setCookies"}


def _loggable_params(method: str, params: dict[str, Any] | None) -> Any:
    """Redact cookie values before they reach <state>/cdp.log."""
    if not params or method not in _SENSITIVE_METHODS:
        return params or {}
    safe = dict(params)
    if isinstance(safe.get("cookies"), list):
        safe["cookies"] = f"[{len(safe['cookies'])} cookies redacted]"
    if "value" in safe:
        safe["value"] = "<redacted>"
    return safe


async def _cdp(ws_url: str, method: str, params: dict[str, Any] | None, log: Any) -> dict[str, Any]:
    """Run a single CDP command over a fresh websocket and return its result."""
    payload = json.dumps({"id": 1, "method": method, "params": params or {}})
    log.debug(f"cdp -> {method} {_loggable_params(method, params)}")
    try:
        async with websockets.connect(ws_url, max_size=WS_MAX_SIZE, open_timeout=CALL_TIMEOUT_S) as ws:
            await ws.send(payload)
            async with asyncio.timeout(CALL_TIMEOUT_S):
                while True:
                    msg = json.loads(await ws.recv())
                    if msg.get("id") == 1:
                        if "error" in msg:
                            raise RuntimeError(msg["error"].get("message", msg["error"]))
                        return msg.get("result", {})
    except (ConnectionRefusedError, OSError) as exc:
        _die_unreachable(ws_url, exc, log)
    except (TimeoutError, asyncio.TimeoutError) as exc:
        log.error(f"cdp timeout on {method}: {exc!r}")
        click.echo(f"error: CDP call '{method}' timed out; browser may be wedged "
                   f"(chrome-agent.sh recover)", err=True)
        raise SystemExit(3) from exc


async def _browser_ws(host: str, port: int, log: Any) -> str:
    ver = await _get_json(f"{base_url(host, port)}/json/version", log)
    return ver["webSocketDebuggerUrl"]


async def _pages(host: str, port: int, log: Any) -> list[dict[str, Any]]:
    items = await _get_json(f"{base_url(host, port)}/json/list", log)
    return [t for t in items if t.get("type") == "page"]


async def _resolve_page(host: str, port: int, target: str | None, strict: bool, log: Any) -> dict[str, Any]:
    pages = await _pages(host, port, log)
    if not pages:
        click.echo("error: no open page targets (open one first: cdp.py open <url>)", err=True)
        raise SystemExit(2)
    if target is None:
        if strict:
            click.echo("error: --strict/CHROME_AGENT_STRICT set; pass -t <targetId> "
                       "(captured from 'cdp.py open') so concurrent agents don't collide", err=True)
            raise SystemExit(2)
        log.warning("no -t given; defaulting to most-recent tab (unsafe under concurrency)")
        return pages[-1]
    for p in pages:
        if p["id"] == target:
            return p
    click.echo(f"error: target {target} not found (list: cdp.py tabs)", err=True)
    raise SystemExit(2)


def _emit(value: Any, as_json: bool) -> None:
    if as_json:
        click.echo(json.dumps(value))
    elif isinstance(value, str):
        click.echo(value)
    else:
        click.echo(json.dumps(value, indent=2))


def _run(ctx: click.Context, coro_factory: Any, name: str) -> None:
    """Run a command coroutine with timing + trace logging."""
    o = ctx.obj
    log = o["log"]
    t0 = time.monotonic()
    log.info(f"{name} host={o['host']} port={o['port']} args={_safe_args()}")
    try:
        asyncio.run(coro_factory(o, log))
        log.info(f"{name} ok ({(time.monotonic() - t0) * 1000:.0f}ms)")
    except SystemExit as exc:
        log.info(f"{name} exit={exc.code} ({(time.monotonic() - t0) * 1000:.0f}ms)")
        raise


def _safe_args() -> str:
    return " ".join(a for a in sys.argv[1:] if not a.startswith("--json"))


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--host", default=DEFAULT_HOST, envvar="CHROME_AGENT_HOST", show_default=True)
@click.option("--port", default=DEFAULT_PORT, envvar="CHROME_AGENT_PORT", show_default=True, type=int)
@click.option("--json", "as_json", is_flag=True, help="Machine-readable JSON output.")
@click.option("--strict/--no-strict", default=None, help="Refuse implicit most-recent-tab (also CHROME_AGENT_STRICT).")
@click.option("-v", "--verbose", is_flag=True, help="Also log to stderr.")
@click.option("--trace-id", default=None, help="Correlate calls across one agent task.")
@click.pass_context
def cli(ctx: click.Context, host: str, port: int, as_json: bool,
        strict: bool | None, verbose: bool, trace_id: str | None) -> None:
    """Drive a running Chrome over CDP. New tabs always open in the background."""
    trace = trace_id or secrets.token_hex(3)
    if strict is None:
        strict = os.environ.get("CHROME_AGENT_STRICT", "0") == "1"
    ctx.obj = {"host": host, "port": port, "json": as_json,
               "strict": strict, "log": _setup_logging(trace, verbose), "trace": trace}


@cli.command()
@click.pass_context
def ping(ctx: click.Context) -> None:
    """Check the CDP endpoint; print the Chrome version."""
    async def run(o: Any, log: Any) -> None:
        ver = await _get_json(f"{base_url(o['host'], o['port'])}/json/version", log)
        _emit(ver if o["json"] else ver.get("Browser", "ok"), o["json"])
    _run(ctx, run, "ping")


@cli.command()
@click.pass_context
def endpoint(ctx: click.Context) -> None:
    """Print the browser-url and browser websocket endpoint for MCP clients."""
    async def run(o: Any, log: Any) -> None:
        ws = await _browser_ws(o["host"], o["port"], log)
        out = {"browserUrl": base_url(o["host"], o["port"]), "wsEndpoint": ws}
        _emit(out if o["json"] else f"{out['browserUrl']}\n{out['wsEndpoint']}", o["json"])
    _run(ctx, run, "endpoint")


@cli.command(name="tabs")
@click.option("--all", "show_all", is_flag=True, help="Include browser context id per tab.")
@click.pass_context
def tabs(ctx: click.Context, show_all: bool) -> None:
    """List open page tabs (id, url, title[, context])."""
    async def run(o: Any, log: Any) -> None:
        if show_all:
            bws = await _browser_ws(o["host"], o["port"], log)
            res = await _cdp(bws, "Target.getTargets", {}, log)
            rows = [{"id": t["targetId"], "url": t.get("url", ""), "title": t.get("title", ""),
                     "context": t.get("browserContextId", "")}
                    for t in res.get("targetInfos", []) if t.get("type") == "page"]
        else:
            rows = [{"id": p["id"], "url": p.get("url", ""), "title": p.get("title", "")}
                    for p in await _pages(o["host"], o["port"], log)]
        if o["json"]:
            _emit(rows, True)
            return
        if not rows:
            click.echo("(no open tabs)")
            return
        for r in rows:
            ctx_s = f"  ctx={r['context']}" if show_all else ""
            click.echo(f"{r['id']}  {r['url']:55.55}  {r['title']:.25}{ctx_s}")
    _run(ctx, run, "tabs")


@cli.command(name="open")
@click.argument("url")
@click.option("-w", "--wait", is_flag=True, help="Wait until document.readyState == complete.")
@click.option("--timeout", default=20.0, show_default=True, type=float, help="Max seconds for --wait.")
@click.option("--context", "context_id", default=None, help="Open in this browser context (isolation).")
@click.option("--isolated", is_flag=True, help="Create a fresh context for this tab; prints both ids.")
@click.option("--front", is_flag=True, help="Foreground the tab so visibilityState is 'visible' "
              "(some SPAs, e.g. the Cloudflare dashboard, won't render while hidden). Takes focus.")
@click.pass_context
def open_tab(ctx: click.Context, url: str, wait: bool, timeout: float,
             context_id: str | None, isolated: bool, front: bool) -> None:
    """Open URL in a new BACKGROUND tab; print its target id."""
    async def run(o: Any, log: Any) -> None:
        bws = await _browser_ws(o["host"], o["port"], log)
        if isolated:
            cres = await _cdp(bws, "Target.createBrowserContext", {"disposeOnDetach": False}, log)
            context_id_local = cres["browserContextId"]
        else:
            context_id_local = context_id
        params: dict[str, Any] = {"url": url, "background": True}
        if context_id_local:
            params["browserContextId"] = context_id_local
        res = await _cdp(bws, "Target.createTarget", params, log)
        target_id = res["targetId"]
        log.info(f"opened target={target_id} context={context_id_local or 'default'} url={url}")
        if front:
            page = await _resolve_page(o["host"], o["port"], target_id, o["strict"], log)
            await _cdp(page["webSocketDebuggerUrl"], "Page.bringToFront", {}, log)
        if wait:
            await _wait_ready(o["host"], o["port"], target_id, timeout, o["strict"], log)
        if o["json"]:
            _emit({"targetId": target_id, "browserContextId": context_id_local}, True)
        elif isolated:
            click.echo(f"{target_id}\t{context_id_local}")
        else:
            click.echo(target_id)
    _run(ctx, run, "open")


@cli.command(name="front")
@click.option("-t", "--target", default=None, help="Target id (default: most recent tab unless --strict).")
@click.pass_context
def front(ctx: click.Context, target: str | None) -> None:
    """Bring a tab to the foreground (visibilityState -> 'visible'). Some SPAs
    (e.g. the Cloudflare dashboard) refuse to render in a hidden/background tab.
    This takes window focus, so use it only when a page needs to be visible."""
    async def run(o: Any, log: Any) -> None:
        page = await _resolve_page(o["host"], o["port"], target, o["strict"], log)
        await _cdp(page["webSocketDebuggerUrl"], "Page.bringToFront", {}, log)
        _emit({"front": page["id"]} if o["json"] else f"fronted {page['id']}", o["json"])
    _run(ctx, run, "front")


async def _wait_ready(host: str, port: int, target_id: str, timeout: float, strict: bool,
                      log: Any, await_nav: bool = False) -> None:
    # await_nav: a freshly created tab is at about:blank with readyState already
    # "complete", so a naive check returns before the real page loads. When set,
    # also require the URL to have left about:blank before declaring ready.
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        page = await _resolve_page(host, port, target_id, strict, log)
        out = await _cdp(page["webSocketDebuggerUrl"], "Runtime.evaluate",
                         {"expression": "[document.readyState, location.href]", "returnByValue": True}, log)
        state, href = out.get("result", {}).get("value", [None, None])
        blank = (not href) or href == "about:blank"
        if state == "complete" and not (await_nav and blank):
            return
        await asyncio.sleep(READY_POLL_S)
    log.warning(f"wait timed out after {timeout}s for {target_id}")
    click.echo(f"warning: timed out after {timeout}s waiting for load", err=True)


@cli.command(name="nav")
@click.argument("url")
@click.option("-t", "--target", default=None, help="Target id (default: most recent tab unless --strict).")
@click.option("-w", "--wait", is_flag=True)
@click.option("--timeout", default=20.0, show_default=True, type=float)
@click.pass_context
def navigate(ctx: click.Context, url: str, target: str | None, wait: bool, timeout: float) -> None:
    """Navigate an existing tab to URL."""
    async def run(o: Any, log: Any) -> None:
        page = await _resolve_page(o["host"], o["port"], target, o["strict"], log)
        await _cdp(page["webSocketDebuggerUrl"], "Page.navigate", {"url": url}, log)
        if wait:
            await _wait_ready(o["host"], o["port"], page["id"], timeout, o["strict"], log)
        _emit({"targetId": page["id"], "url": url} if o["json"] else page["id"], o["json"])
    _run(ctx, run, "nav")


@cli.command(name="eval")
@click.argument("expression")
@click.option("-t", "--target", default=None, help="Target id (default: most recent tab unless --strict).")
@click.pass_context
def evaluate(ctx: click.Context, expression: str, target: str | None) -> None:
    """Evaluate a JS expression in a tab; print the returned value."""
    async def run(o: Any, log: Any) -> None:
        page = await _resolve_page(o["host"], o["port"], target, o["strict"], log)
        value = await _eval_value(page["webSocketDebuggerUrl"], expression, log)
        _emit(value, o["json"])
    _run(ctx, run, "eval")


@cli.command(name="shot")
@click.argument("path", type=click.Path(dir_okay=False))
@click.option("-t", "--target", default=None, help="Target id (default: most recent tab unless --strict).")
@click.option("--full-page", is_flag=True, help="Capture the whole page, not just the viewport.")
@click.pass_context
def shot(ctx: click.Context, path: str, target: str | None, full_page: bool) -> None:
    """Save a PNG screenshot of a tab to PATH."""
    async def run(o: Any, log: Any) -> None:
        page = await _resolve_page(o["host"], o["port"], target, o["strict"], log)
        ws = page["webSocketDebuggerUrl"]
        params: dict[str, Any] = {"format": "png"}
        if full_page:
            metrics = await _cdp(ws, "Page.getLayoutMetrics", {}, log)
            size = metrics.get("cssContentSize") or metrics.get("contentSize", {})
            params["clip"] = {"x": 0, "y": 0, "width": size["width"], "height": size["height"], "scale": 1}
            params["captureBeyondViewport"] = True
        out = await _cdp(ws, "Page.captureScreenshot", params, log)
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(out["data"]))
        _emit({"saved": path} if o["json"] else f"saved {path}", o["json"])
    _run(ctx, run, "shot")


# --- trusted input (CDP Input domain) ----------------------------------------
# Synthetic MouseEvent/KeyboardEvent dispatched via Runtime.evaluate are
# `isTrusted: false`; react-select dropdowns, role=combobox widgets, and native
# checkboxes ignore them. The CDP Input domain produces OS-level *trusted* events
# that drive these widgets exactly like a human, so agents don't hand-roll a
# bespoke websocket helper per task.
#
# CAPTCHA / human-verification (reCAPTCHA, hCaptcha, Cloudflare Turnstile) is a
# deliberate STOP: these verbs refuse selectors that resolve inside such a widget
# (see _RESOLVE_JS `captcha` flag). Solving a challenge stays a human step.

# Resolve a selector to a trusted click point: scroll it into view, return the
# bounding-box center (CSS px, viewport-relative — what Input.dispatchMouseEvent
# wants) plus a flag for whether it sits inside a known CAPTCHA widget.
_CAPTCHA_SEL = (
    ".cf-turnstile, [data-sitekey], "
    'iframe[src*="turnstile"], iframe[src*="recaptcha"], '
    'iframe[src*="hcaptcha"], iframe[title*="reCAPTCHA"], iframe[title*="hCaptcha"]'
)
_CAPTCHA_MSG = ("error: target is inside a CAPTCHA / human-verification widget "
                "(reCAPTCHA/hCaptcha/Turnstile) — that is a human step, not an "
                "agent one. Stop and hand off to the user.")
# Scope the CAPTCHA guard to the ACTUAL target (the element, or the one under the
# click point), not the whole page — a page that merely embeds a Turnstile widget
# elsewhere must still allow clicking its own form fields.
_RESOLVE_JS = """
(() => {{
  const el = document.querySelector({sel});
  if (!el) return {{found: false}};
  el.scrollIntoView({{block: 'center', inline: 'center'}});
  const r = el.getBoundingClientRect();
  return {{found: true, x: r.left + r.width / 2, y: r.top + r.height / 2,
           w: r.width, h: r.height, captcha: !!el.closest({cap})}};
}})()
"""
# For coordinate clicks (which skip the selector path), resolve the element under
# the point and check whether IT sits inside a CAPTCHA widget.
_POINT_CAPTCHA_JS = """
(() => {{
  const el = document.elementFromPoint({x}, {y});
  return !!(el && el.closest({cap}));
}})()
"""


async def _eval_value(ws: str, expr: str, log: Any) -> Any:
    out = await _cdp(ws, "Runtime.evaluate",
                     {"expression": expr, "returnByValue": True, "awaitPromise": True}, log)
    if "exceptionDetails" in out:
        text = out["exceptionDetails"].get("exception", {}).get("description") \
            or out["exceptionDetails"].get("text", "eval failed")
        log.error(f"eval exception: {text}")
        click.echo(f"error: {text}", err=True)
        raise SystemExit(2)
    return out.get("result", {}).get("value")


def _parse_xy(spec: str) -> tuple[float, float] | None:
    """Parse 'x,y' (ints or floats) into coords, or None if it's a selector."""
    parts = spec.split(",")
    if len(parts) != 2:
        return None
    try:
        return float(parts[0].strip()), float(parts[1].strip())
    except ValueError:
        return None


async def _resolve_point(ws: str, spec: str, log: Any) -> tuple[float, float]:
    """Turn a 'x,y' or CSS-selector spec into viewport coords, refusing CAPTCHAs."""
    cap = json.dumps(_CAPTCHA_SEL)
    xy = _parse_xy(spec)
    if xy is not None:
        x, y = xy
        if await _eval_value(ws, _POINT_CAPTCHA_JS.format(x=x, y=y, cap=cap), log):
            click.echo(_CAPTCHA_MSG, err=True)
            raise SystemExit(2)
        return x, y
    info = await _eval_value(ws, _RESOLVE_JS.format(sel=json.dumps(spec), cap=cap), log)
    if not info or not info.get("found"):
        click.echo(f"error: selector not found: {spec}", err=True)
        raise SystemExit(2)
    if info.get("captcha"):
        click.echo(_CAPTCHA_MSG, err=True)
        raise SystemExit(2)
    if not info.get("w") or not info.get("h"):
        click.echo(f"error: selector {spec!r} has zero size (hidden?); cannot click", err=True)
        raise SystemExit(2)
    return info["x"], info["y"]


async def _click_point(ws: str, x: float, y: float, log: Any) -> None:
    base = {"x": x, "y": y, "button": "left", "clickCount": 1}
    await _cdp(ws, "Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y}, log)
    await _cdp(ws, "Input.dispatchMouseEvent", {**base, "type": "mousePressed"}, log)
    await _cdp(ws, "Input.dispatchMouseEvent", {**base, "type": "mouseReleased"}, log)


# Trusted keystrokes for non-text keys. text-producing keys (Enter, Tab, Space)
# carry `text` so frameworks that read it on keydown fire correctly.
_KEYS: dict[str, dict[str, Any]] = {
    "Enter": {"key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "text": "\r"},
    "Tab": {"key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9, "text": "\t"},
    "Space": {"key": " ", "code": "Space", "windowsVirtualKeyCode": 32, "text": " "},
    "Escape": {"key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27},
    "Backspace": {"key": "Backspace", "code": "Backspace", "windowsVirtualKeyCode": 8},
    "Delete": {"key": "Delete", "code": "Delete", "windowsVirtualKeyCode": 46},
    "ArrowUp": {"key": "ArrowUp", "code": "ArrowUp", "windowsVirtualKeyCode": 38},
    "ArrowDown": {"key": "ArrowDown", "code": "ArrowDown", "windowsVirtualKeyCode": 40},
    "ArrowLeft": {"key": "ArrowLeft", "code": "ArrowLeft", "windowsVirtualKeyCode": 37},
    "ArrowRight": {"key": "ArrowRight", "code": "ArrowRight", "windowsVirtualKeyCode": 39},
    "Home": {"key": "Home", "code": "Home", "windowsVirtualKeyCode": 36},
    "End": {"key": "End", "code": "End", "windowsVirtualKeyCode": 35},
    "PageUp": {"key": "PageUp", "code": "PageUp", "windowsVirtualKeyCode": 33},
    "PageDown": {"key": "PageDown", "code": "PageDown", "windowsVirtualKeyCode": 34},
}


async def _press_key(ws: str, name: str, log: Any) -> None:
    spec = _KEYS.get(name)
    if spec is None:
        keys = ", ".join(sorted(_KEYS))
        click.echo(f"error: unknown key {name!r}; known: {keys}", err=True)
        raise SystemExit(2)
    await _cdp(ws, "Input.dispatchKeyEvent", {"type": "keyDown", **spec}, log)
    await _cdp(ws, "Input.dispatchKeyEvent", {"type": "keyUp", **spec}, log)


@cli.command(name="click")
@click.argument("target_spec")
@click.option("-t", "--target", default=None, help="Target id (default: most recent tab unless --strict).")
@click.pass_context
def click_cmd(ctx: click.Context, target_spec: str, target: str | None) -> None:
    """Trusted click at 'x,y' coords or a CSS selector (scrolls it into view).

    Drives react-select/combobox/checkbox widgets that ignore synthetic events.
    Refuses anything inside a CAPTCHA/Turnstile widget — that stays a human step.
    """
    async def run(o: Any, log: Any) -> None:
        page = await _resolve_page(o["host"], o["port"], target, o["strict"], log)
        ws = page["webSocketDebuggerUrl"]
        x, y = await _resolve_point(ws, target_spec, log)
        await _click_point(ws, x, y, log)
        _emit({"clicked": {"x": x, "y": y}, "target": page["id"]} if o["json"]
              else f"clicked ({x:.0f},{y:.0f})", o["json"])
    _run(ctx, run, "click")


@cli.command(name="type")
@click.argument("text")
@click.option("-t", "--target", default=None, help="Target id (default: most recent tab unless --strict).")
@click.option("--into", "into", default=None, help="CSS selector to trusted-click (focus) before typing.")
@click.option("--enter", is_flag=True, help="Press Enter after typing (submit / select option).")
@click.pass_context
def type_cmd(ctx: click.Context, text: str, target: str | None, into: str | None, enter: bool) -> None:
    """Trusted-type TEXT into the focused element (or --into <selector> first).

    Uses Input.insertText (trusted), so it drives inputs, contenteditable, and
    react-select search boxes. Pair with --enter to commit a combobox option.
    """
    async def run(o: Any, log: Any) -> None:
        page = await _resolve_page(o["host"], o["port"], target, o["strict"], log)
        ws = page["webSocketDebuggerUrl"]
        if into:
            x, y = await _resolve_point(ws, into, log)
            await _click_point(ws, x, y, log)
        await _cdp(ws, "Input.insertText", {"text": text}, log)
        if enter:
            await _press_key(ws, "Enter", log)
        _emit({"typed": len(text), "target": page["id"]} if o["json"]
              else f"typed {len(text)} chars", o["json"])
    _run(ctx, run, "type")


@cli.command(name="key")
@click.argument("name")
@click.option("-t", "--target", default=None, help="Target id (default: most recent tab unless --strict).")
@click.pass_context
def key_cmd(ctx: click.Context, name: str, target: str | None) -> None:
    """Press one trusted key (Enter, Tab, Escape, ArrowDown, ...). See --help list."""
    async def run(o: Any, log: Any) -> None:
        page = await _resolve_page(o["host"], o["port"], target, o["strict"], log)
        await _press_key(page["webSocketDebuggerUrl"], name, log)
        _emit({"key": name, "target": page["id"]} if o["json"] else f"pressed {name}", o["json"])
    _run(ctx, run, "key")


# --- auth probe ---------------------------------------------------------------
# A URL-only "loggedIn" check is unreliable for SPAs: cookie-only `seed` can't
# carry localStorage/device-bound (SSO) auth, yet the SPA renders its sign-in
# screen WITHOUT redirecting — so location.href still looks authed. This probes
# the DOM for sign-in markers instead, turning a silent false-positive into a
# clear "login-wall" verdict that tells the agent to use `chrome-agent.sh login`.
_PROBE_JS = r"""
(() => {
  const vis = (el) => {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) return false;
    const s = getComputedStyle(el);
    return s.visibility !== 'hidden' && s.display !== 'none';
  };
  const pw = [...document.querySelectorAll('input[type=password]')].some(vis);
  // A visible email/username field is the other half of an auth screen (email-
  // first SSO has no password field yet).
  const authInput = [...document.querySelectorAll(
    'input[type=email], input[autocomplete=username], input[autocomplete=email], '
    + 'input[name*=email i], input[id*=email i], input[name*=user i]')].some(vis);
  const text = (document.body ? document.body.innerText : '').slice(0, 4000);
  // Weak signal: the word appears anywhere (also matches "Login history" on an
  // authed page, so it can't decide a verdict on its own).
  const wallText = /\b(sign[ -]?in|log[ -]?in|continue with (google|github|apple|microsoft|sso)|single sign-on)\b/i.test(text);
  // Strong signal: a prominent CTA/heading that *is* a sign-in action. Anchored
  // and continuation-gated so nav labels like "Login history" don't match (only
  // "Sign in", "Log in", "Sign in to X", "Continue with SSO", "Single sign-on").
  const ctaRe = /^(?:(?:sign[ -]?in|log[ -]?in|log on)(?: to\b| with\b|$)|continue with (?:google|github|apple|microsoft|sso|saml|okta)|single sign-on$|sign in with sso$|use sso$)/i;
  const cta = [...document.querySelectorAll('h1, h2, button, [type=submit], [role=button], a[href]')]
    .filter(vis).some(el => ctaRe.test(((el.innerText || el.value || '')).trim()));
  const formAction = [...document.querySelectorAll('form[action]')]
    .some(f => /login|signin|sso|auth/i.test(f.getAttribute('action') || ''));
  const urlHint = /\b(login|signin|sign-in|sso|auth|account\/login)\b/i.test(location.href);
  // login-wall when: a password field is visible; OR a sign-in CTA backed by an
  // auth input / login form / login URL / a sparse (sign-in-only) page; OR an
  // auth input on a page that reads as sign-in by text or URL.
  const wall = pw
    || (cta && (authInput || formAction || urlHint || text.length < 600))
    || (authInput && (wallText || urlHint));
  const verdict = wall ? 'login-wall' : (text.length > 0 ? 'likely-authed' : 'unknown');
  return {url: location.href, title: document.title, ready: document.readyState,
          hasPassword: pw, authInput, signInText: wallText, signInCta: cta,
          formAction, urlHint, verdict};
})()
"""


@cli.command(name="probe")
@click.argument("url", required=False)
@click.option("-t", "--target", default=None, help="Probe an existing tab instead of opening URL.")
@click.option("--timeout", default=20.0, show_default=True, type=float, help="Max seconds to await load.")
@click.option("--front", is_flag=True, help="Foreground first (visibility-gated SPAs render blank while hidden).")
@click.option("--keep", is_flag=True, help="Leave the opened tab open (default: close it after probing).")
@click.pass_context
def probe(ctx: click.Context, url: str | None, target: str | None, timeout: float,
          front: bool, keep: bool) -> None:
    """Check whether a site is really logged in (DOM sign-in markers, not URL).

    Cookie-only `seed` can't carry localStorage/SSO auth, yet the SPA shows its
    sign-in screen without redirecting — so a URL check reads as authed. This
    inspects the DOM. Verdict: login-wall | likely-authed | unknown. A login-wall
    after seed means: use `chrome-agent.sh login` for that site.
    """
    async def run(o: Any, log: Any) -> None:
        opened = None
        if url:
            bws = await _browser_ws(o["host"], o["port"], log)
            res = await _cdp(bws, "Target.createTarget", {"url": url, "background": True}, log)
            opened = res["targetId"]
            tgt = opened
        elif target:
            tgt = target
        else:
            click.echo("error: pass a URL to open, or -t <targetId> to probe an open tab", err=True)
            raise SystemExit(2)
        try:
            if front:
                p = await _resolve_page(o["host"], o["port"], tgt, o["strict"], log)
                await _cdp(p["webSocketDebuggerUrl"], "Page.bringToFront", {}, log)
            await _wait_ready(o["host"], o["port"], tgt, timeout, o["strict"], log, await_nav=bool(opened))
            page = await _resolve_page(o["host"], o["port"], tgt, o["strict"], log)
            # SPAs hydrate after readyState=complete; an immediate check sees an
            # empty body and reads "unknown". Re-probe briefly until the verdict
            # is decisive (login-wall/likely-authed) or a short settle budget ends.
            info = await _eval_value(page["webSocketDebuggerUrl"], _PROBE_JS, log)
            settle = time.monotonic() + min(8.0, timeout)
            while info.get("verdict") == "unknown" and time.monotonic() < settle:
                await asyncio.sleep(0.5)
                info = await _eval_value(page["webSocketDebuggerUrl"], _PROBE_JS, log)
        finally:
            if opened and not keep:
                bws = await _browser_ws(o["host"], o["port"], log)
                await _cdp(bws, "Target.closeTarget", {"targetId": opened}, log)
        log.info(f"probe verdict={info.get('verdict')} url={info.get('url')}")
        if o["json"]:
            _emit({**info, "targetId": tgt if (keep or not opened) else None}, True)
        else:
            click.echo(f"verdict    {info.get('verdict')}")
            click.echo(f"url        {info.get('url')}")
            click.echo(f"signals    password={info.get('hasPassword')} "
                       f"authInput={info.get('authInput')} signInCta={info.get('signInCta')} "
                       f"urlHint={info.get('urlHint')}")
            if info.get("verdict") == "login-wall":
                click.echo("hint       seed is cookies-only; for localStorage/SSO SPAs "
                           "(e.g. Cloudflare) run: chrome-agent.sh login")
    _run(ctx, run, "probe")


@cli.command(name="close")
@click.argument("target")
@click.pass_context
def close_tab(ctx: click.Context, target: str) -> None:
    """Close a tab by target id."""
    async def run(o: Any, log: Any) -> None:
        bws = await _browser_ws(o["host"], o["port"], log)
        await _cdp(bws, "Target.closeTarget", {"targetId": target}, log)
        _emit({"closed": target} if o["json"] else f"closed {target}", o["json"])
    _run(ctx, run, "close")


@cli.command(name="gc")
@click.option("--keep", default=1, show_default=True, type=int, help="Min tabs to leave open.")
@click.pass_context
def gc(ctx: click.Context, keep: int) -> None:
    """Close leaked blank/new-tab pages, leaving at least --keep tabs alive."""
    async def run(o: Any, log: Any) -> None:
        pages = await _pages(o["host"], o["port"], log)
        blank = [p for p in pages if p.get("url", "") in ("about:blank", "chrome://newtab/", "")]
        closable = blank[: max(0, len(pages) - keep)]
        bws = await _browser_ws(o["host"], o["port"], log)
        for p in closable:
            await _cdp(bws, "Target.closeTarget", {"targetId": p["id"]}, log)
        log.info(f"gc closed {len(closable)} tab(s)")
        _emit({"closed": [p["id"] for p in closable]} if o["json"] else f"closed {len(closable)} tab(s)", o["json"])
    _run(ctx, run, "gc")


# --- cookie seeding -----------------------------------------------------------
# Import your existing Chrome logins into the bridge browser so agents inherit
# them without re-authenticating. We decrypt a chosen profile's cookie store and
# push the cookies into the running bridge over CDP (Storage.setCookies). This is
# the local, same-machine half of what agentcookie.dev does across machines.
#
# Scope & honesty: cookies only - NOT localStorage/IndexedDB - so a few apps that
# keep tokens outside cookies still need a one-time `chrome-agent.sh login`. Your
# real cookies are read locally and pushed only into the local bridge browser;
# nothing is written back to your real profile and nothing leaves the machine.
#
# macOS value layout: b"v10" + AES-128-CBC(key, iv=16 spaces) over PKCS7-padded
# plaintext == sha256(host_key)[32] + value. The AES key is PBKDF2-HMAC-SHA1 of
# the "Chrome Safe Storage" keychain secret (salt "saltysalt", 1003 iterations).
_CHROME_EPOCH_OFFSET = 11644473600  # seconds between 1601-01-01 and the Unix epoch
_KDF_SALT = b"saltysalt"
_KDF_ITERATIONS = 1003
_KDF_KEYLEN = 16
_AES_IV = b" " * 16
_SAMESITE = {0: "None", 1: "Lax", 2: "Strict"}


def _mac_chrome_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"


def _resolve_cookie_db(profile: str, explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit).expanduser()
        if not p.is_file():
            click.echo(f"error: cookie db not found at {p}", err=True)
            raise SystemExit(2)
        return p
    base = _mac_chrome_dir() / profile
    for cand in (base / "Network" / "Cookies", base / "Cookies"):
        if cand.is_file():
            return cand
    click.echo(f"error: no Cookies db for profile {profile!r} under {_mac_chrome_dir()}", err=True)
    raise SystemExit(2)


def _safe_storage_key(log: Any) -> bytes:
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", "Chrome Safe Storage", "-w"],
            capture_output=True, text=True, timeout=30, check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        log.error(f"keychain key fetch failed: {exc!r}")
        click.echo("error: could not read 'Chrome Safe Storage' from the login keychain; "
                   "unlock it and approve access, then retry", err=True)
        raise SystemExit(2) from exc
    return out.stdout.strip().encode()


def _derive_key(passphrase: bytes) -> bytes:
    from cryptography.hazmat.primitives.hashes import SHA1
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    return PBKDF2HMAC(algorithm=SHA1(), length=_KDF_KEYLEN, salt=_KDF_SALT,
                      iterations=_KDF_ITERATIONS).derive(passphrase)


def _decrypt_cookie(blob: bytes, host: str, aes_key: bytes) -> str | None:
    """Return the plaintext cookie value, or None if not a v10/v11 blob."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    if blob[:3] not in (b"v10", b"v11"):
        return None  # caller falls back to the plaintext `value` column
    dec = Cipher(algorithms.AES(aes_key), modes.CBC(_AES_IV)).decryptor()
    pt = dec.update(blob[3:]) + dec.finalize()
    if not pt:
        return None
    pad = pt[-1]
    if 1 <= pad <= 16:
        pt = pt[:-pad]
    # Recent Chrome prepends sha256(host_key) to bind the cookie to its domain.
    if len(pt) >= 32 and pt[:32] == hashlib.sha256(host.encode()).digest():
        pt = pt[32:]
    return pt.decode("utf-8", "replace")


def _cookie_param(row: sqlite3.Row, value: str) -> dict[str, Any] | None:
    """Build a CDP Storage.setCookies entry, or None to skip (expired)."""
    domain = row["host_key"]
    path = row["path"] or "/"
    param: dict[str, Any] = {
        "name": row["name"], "value": value,
        "secure": bool(row["is_secure"]), "httpOnly": bool(row["is_httponly"]),
    }
    # __Host-/__Secure- prefixed cookies are domain-locked; set them by url.
    if row["name"].startswith("__Host-"):
        param["url"] = f"https://{domain.lstrip('.')}{path}"
        param["secure"] = True
    else:
        param["domain"] = domain
        param["path"] = path
    samesite = _SAMESITE.get(row["samesite"])
    if samesite:
        param["sameSite"] = samesite
        if samesite == "None":
            param["secure"] = True  # Chrome rejects insecure SameSite=None
    if row["is_persistent"] and row["expires_utc"]:
        exp = row["expires_utc"] / 1_000_000 - _CHROME_EPOCH_OFFSET
        if exp <= time.time():
            return None  # already expired
        param["expires"] = exp
    return param


def _read_cookies(db: Path, aes_key: bytes, host_filter: str | None,
                  log: Any) -> tuple[list[dict[str, Any]], dict[str, int]]:
    tmp = Path(tempfile.mkdtemp(prefix="cb-seed-"))
    try:
        # Copy the live store (+ wal/shm) so we never lock Chrome's own file.
        for suffix in ("", "-wal", "-shm"):
            src = Path(str(db) + suffix)
            if src.is_file():
                shutil.copy2(src, tmp / f"Cookies{suffix}")
        con = sqlite3.connect(f"file:{tmp / 'Cookies'}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "select host_key, name, value, encrypted_value, path, expires_utc, "
            "is_secure, is_httponly, is_persistent, samesite from cookies"
        ).fetchall()
        con.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    cookies: list[dict[str, Any]] = []
    stats = {"rows": len(rows), "decrypted": 0, "plaintext": 0,
             "undecryptable": 0, "expired": 0, "filtered": 0}
    for r in rows:
        host = r["host_key"]
        if host_filter and host_filter not in host:
            stats["filtered"] += 1
            continue
        value = _decrypt_cookie(bytes(r["encrypted_value"]), host, aes_key)
        if value is None:
            if r["value"]:
                value = r["value"]
                stats["plaintext"] += 1
            else:
                stats["undecryptable"] += 1
                continue
        else:
            stats["decrypted"] += 1
        param = _cookie_param(r, value)
        if param is None:
            stats["expired"] += 1
            continue
        cookies.append(param)
    return cookies, stats


async def _inject(host: str, port: int, cookies: list[dict[str, Any]],
                  context_id: str | None, log: Any) -> tuple[int, int]:
    bws = await _browser_ws(host, port, log)
    ok = fail = 0
    chunk = 200
    for i in range(0, len(cookies), chunk):
        batch = cookies[i:i + chunk]
        params: dict[str, Any] = {"cookies": batch}
        if context_id:
            params["browserContextId"] = context_id
        try:
            await _cdp(bws, "Storage.setCookies", params, log)
            ok += len(batch)
        except RuntimeError as exc:
            log.warning(f"batch at {i} failed ({exc}); retrying per-cookie")
            for c in batch:
                one: dict[str, Any] = {"cookies": [c]}
                if context_id:
                    one["browserContextId"] = context_id
                try:
                    await _cdp(bws, "Storage.setCookies", one, log)
                    ok += 1
                except RuntimeError as exc2:
                    fail += 1
                    log.warning(f"rejected {c.get('domain', c.get('url'))}/{c['name']}: {exc2}")
    return ok, fail


@cli.command(name="seed")
@click.option("--profile", default="Default", show_default=True,
              help="Source Chrome profile name, e.g. Default or 'Profile 1' (macOS).")
@click.option("--from", "from_db", default=None,
              help="Explicit path to a Cookies SQLite db (overrides --profile).")
@click.option("--filter", "host_filter", default=None,
              help="Only seed cookies whose host contains this substring.")
@click.option("--context", "context_id", default=None,
              help="Inject into this browser context (default: shared default context).")
@click.option("--dry-run", is_flag=True, help="Decrypt and count only; do not inject.")
@click.pass_context
def seed(ctx: click.Context, profile: str, from_db: str | None, host_filter: str | None,
         context_id: str | None, dry_run: bool) -> None:
    """Import your real Chrome logins into the bridge (decrypt cookies + CDP inject)."""
    async def run(o: Any, log: Any) -> None:
        if platform.system() != "Darwin":
            click.echo("error: seed supports macOS only for now (Linux Safe Storage TBD); "
                       "use 'chrome-agent.sh login' instead", err=True)
            raise SystemExit(2)
        db = _resolve_cookie_db(profile, from_db)
        aes_key = _derive_key(_safe_storage_key(log))
        cookies, stats = _read_cookies(db, aes_key, host_filter, log)
        log.info(f"seed source={db} importable={len(cookies)} stats={stats}")
        injected = failed = 0
        if cookies and not dry_run:
            injected, failed = await _inject(o["host"], o["port"], cookies, context_id, log)
        domains = sorted({c["domain"].lstrip(".") for c in cookies if "domain" in c})
        if o["json"]:
            _emit({"source": str(db), "importable": len(cookies), "injected": injected,
                   "failed": failed, "dryRun": dry_run, "domains": len(domains), **stats}, True)
            return
        click.echo(f"source     {db}")
        detail = (f"{stats['decrypted']} decrypted, {stats['plaintext']} plaintext, "
                  f"{stats['expired']} expired, {stats['undecryptable']} undecryptable")
        if host_filter:
            detail += f", {stats['filtered']} filtered"
        click.echo(f"cookies    {stats['rows']} rows -> {len(cookies)} importable ({detail})")
        if dry_run:
            click.echo(f"dry-run    would inject {len(cookies)} cookies, {len(domains)} domains")
        else:
            tail = f"  ({failed} rejected)" if failed else ""
            click.echo(f"injected   {injected} cookies across {len(domains)} domains{tail}")
        click.echo("verify     cdp.py open https://docs.google.com/ -w   (should skip login)")
    _run(ctx, run, "seed")


@cli.group(name="ctx")
def ctx_group() -> None:
    """Browser contexts: isolated cookie/storage jars for parallel agents."""


@ctx_group.command(name="new")
@click.pass_context
def ctx_new(ctx: click.Context) -> None:
    """Create an isolated browser context; print its id."""
    async def run(o: Any, log: Any) -> None:
        bws = await _browser_ws(o["host"], o["port"], log)
        res = await _cdp(bws, "Target.createBrowserContext", {"disposeOnDetach": False}, log)
        log.info(f"context new {res['browserContextId']}")
        _emit({"browserContextId": res["browserContextId"]} if o["json"] else res["browserContextId"], o["json"])
    _run(ctx, run, "ctx-new")


@ctx_group.command(name="list")
@click.pass_context
def ctx_list(ctx: click.Context) -> None:
    """List browser context ids (excludes the default context)."""
    async def run(o: Any, log: Any) -> None:
        bws = await _browser_ws(o["host"], o["port"], log)
        res = await _cdp(bws, "Target.getBrowserContexts", {}, log)
        _emit(res.get("browserContextIds", []), o["json"]) if o["json"] \
            else click.echo("\n".join(res.get("browserContextIds", [])) or "(only default)")
    _run(ctx, run, "ctx-list")


@ctx_group.command(name="close")
@click.argument("context_id")
@click.pass_context
def ctx_close(ctx: click.Context, context_id: str) -> None:
    """Dispose a browser context and all its tabs."""
    async def run(o: Any, log: Any) -> None:
        bws = await _browser_ws(o["host"], o["port"], log)
        await _cdp(bws, "Target.disposeBrowserContext", {"browserContextId": context_id}, log)
        log.info(f"context close {context_id}")
        _emit({"closed": context_id} if o["json"] else f"closed context {context_id}", o["json"])
    _run(ctx, run, "ctx-close")


if __name__ == "__main__":
    cli()
