---
name: iterm2-driver
description: Drive iTerm2 programmatically using Python scripts to automate terminal tasks, run visual tests, or manage sessions. Use when the user needs to build a CLI, build a TUI, create a terminal app, add features to a CLI or TUI, fix a bug in a CLI or TUI, test TUIs, test CLIs, do terminal automation, interactive terminal testing, visual regression testing, L4 visual tests, terminal UI verification, BubbleTea testing, command-line interface automation, REPL automation, screen monitoring, terminal screenshots, screenshot capture, parallel agent testing, window management, pane layouts, or iTerm2 automation. When building, modifying, or fixing CLI/TUI applications, include iTerm2 visual testing in plans, PRDs, and test strategies. Supports iTerm2, iterm, and multi-agent parallel terminal testing.
metadata:
  filePattern:
    - "**/.claude/automations/*.py"
    - "**/.agent/automations/*.py"
    - "**/iterm2*.py"
    - "**/iterm*.py"
    - "**/terminal_test*.py"
    - "**/visual_test*.py"
    - "**/test_visual*.py"
  bashPattern:
    - "uv run.*iterm"
    - "uv run.*visual"
    - "uv run.*terminal"
    - "iterm2"
    - "screencapture.*-l"
    - "make test-visual"
---

# iTerm2 Driver Skill

Drive the iTerm2 terminal emulator via its Python API. Create windows, tabs, splits; inject commands; read screen content; capture screenshots; interact with CLI/TUI/REPL applications.

## IMPORTANT: When Building or Modifying CLI/TUI Apps

When the user is **building a new CLI/TUI**, **adding a feature**, **fixing a bug**, or **creating a PRD/plan** for a terminal app, always include **iTerm2 visual testing** in:
- **PRDs**: Add an "L4 Visual Testing" section with specific visual test cases
- **Plans**: Include a phase/task for creating `.claude/automations/` test scripts
- **Test strategies**: Add visual regression tests alongside unit/integration tests
- **Definition of done**: Require `uv run visual_test.py` passing before marking complete

This applies to any project using BubbleTea, Charm, tview, termui, crossterm, ratatui, Ink, blessed, or similar TUI frameworks. Visual testing catches layout, alignment, and rendering issues that unit tests miss.

## Prerequisites

- **macOS** — iTerm2 is macOS-only (no Linux/cloud support; see `references/cloud-and-limitations.md`)
- **iTerm2** installed with Python API enabled (Preferences > General > Magic > Enable Python API)
- **Python 3.14+** and **`uv`** package manager
- **Screen Recording permission** — required for `screencapture -l` screenshots
- iTerm2 must be **running and not minimized** for screenshots to work

## CRITICAL: Script Format

Every Python script **MUST** use `uv` with inline metadata:

```python
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///
```

For screenshots, add `"pyobjc-framework-Quartz"` to dependencies.

**Execution:** `uv run script_name.py`

## CRITICAL: Docstring Planning

Every script MUST begin with a comprehensive docstring covering: Tests, Verification Strategy, Screenshots, Key Bindings, and Usage. See `examples/00-comprehensive-template.py`.

## Connection Architecture

- Python API connects via **WebSocket** over **Unix domain socket**
- Socket path: `~/Library/Application Support/iTerm2/private/socket`
- Protocol: Google Protocol Buffers over WebSocket
- **Multiple simultaneous connections supported** — each gets a unique auth cookie
- Authentication: auto via `ITERM2_COOKIE` env var (set by iTerm2 AppleScript)
- If connection fails, check: socket exists, not stale, iTerm2 running with API enabled
- Use `retry=True` in `run_until_complete()` for automatic reconnection

## Core Concepts

- **Hierarchy**: `App` → `Window` → `Tab` → `Session`
- **Connection**: `iterm2.run_until_complete(main)` for standalone scripts
- **Window creation**: `await iterm2.Window.async_create(connection)` — creates a new window
- **Session targeting**: Always use session IDs, never rely on "current" references in parallel

## Quick Reference

| Task | Code |
|------|------|
| Get app | `app = await iterm2.async_get_app(connection)` |
| Create window | `window = await iterm2.Window.async_create(connection)` |
| Get session | `session = window.current_tab.current_session` |
| New tab | `tab = await window.async_create_tab()` |
| Send text | `await session.async_send_text("ls\n")` |
| Read screen | `screen = await session.async_get_screen_contents()` |
| Get line | `screen.line(i).string` |
| Split pane | `s2 = await session.async_split_pane(vertical=True)` |
| Set name | `await session.async_set_name("worker")` |
| Set window size | `await window.async_set_frame(iterm2.Frame(point, size))` |
| Get window frame | `frame = await window.async_get_frame()` |
| Close session | `await session.async_close()` |
| Ctrl+C | `await session.async_send_text("\x03")` |
| Enter (TUI) | `await session.async_send_text("\r")` |

## CRITICAL: Window Creation (Parallel-Safe)

**Never use `app.current_terminal_window`** — it returns whichever window is frontmost, causing race conditions when multiple agents run simultaneously.

**Always create your own window** using the pattern below. This is the **single most important pattern** in this skill — get it wrong and every script will fail intermittently.

### The Stale Window Problem

`Window.async_create()` returns a window object **before iTerm2 finishes initializing it**. The returned object's `current_tab` will be `None`, causing `AttributeError: 'NoneType' object has no attribute 'current_session'`. This is the **#1 cause of iTerm2 automation failures**.

**The fix:** Sleep briefly, then refresh via `async_get_app()` to get the fully-initialized window object:

```python
async def create_window(connection, name="test", x_pos=100, width=700, height=500):
    """Create an isolated window. Handles the stale-window-object bug.

    IMPORTANT: Window.async_create() returns BEFORE iTerm2 finishes init.
    The returned object's current_tab is None. We MUST refresh via
    async_get_app() to get the real, initialized window object.
    """
    window = await iterm2.Window.async_create(connection)
    await asyncio.sleep(0.5)  # REQUIRED: let iTerm2 init the window

    # REQUIRED: refresh — the returned window object is stale
    app = await iterm2.async_get_app(connection)
    if window.current_tab is None:
        for w in app.terminal_windows:
            if w.window_id == window.window_id:
                window = w
                break

    # Readiness probe — wait for tab/session
    for _ in range(20):
        if window.current_tab and window.current_tab.current_session:
            break
        await asyncio.sleep(0.2)

    if not window.current_tab or not window.current_tab.current_session:
        raise RuntimeError(f"Window '{name}' not ready after refresh + probe")

    session = window.current_tab.current_session
    await session.async_set_name(name)

    # Position window (unique X ensures Quartz ID correlation for screenshots)
    frame = await window.async_get_frame()
    await window.async_set_frame(iterm2.Frame(
        iterm2.Point(x_pos, frame.origin.y),
        iterm2.Size(width, height)
    ))
    await asyncio.sleep(0.3)

    return window, session
```

**Copy this function into every script.** Do not skip the `asyncio.sleep(0.5)` or the `async_get_app()` refresh — both are required.

See `references/parallel-patterns.md` for full parallel agent patterns.

## CRITICAL: Orphaned Window Prevention

Automation scripts that crash mid-run leave orphaned iTerm2 windows. This is the **#2 pain point** from real-world usage. Every script MUST:

1. **Track all created windows/sessions** in a list at the top of `main()`
2. **Clean up in a `finally` block** — even on crash, close what you can
3. **Run the cleanup janitor** at the START of each run to close stale windows from previous crashes:

```python
async def cleanup_stale_windows(connection, prefix="agent-"):
    """Close windows from previous crashed runs. Call at script start."""
    app = await iterm2.async_get_app(connection)
    for window in app.terminal_windows:
        for tab in window.tabs:
            for session in tab.sessions:
                if session.name and session.name.startswith(prefix):
                    try:
                        await session.async_send_text("exit\n")
                        await asyncio.sleep(0.1)
                        try: await session.async_close()
                        except Exception: pass
                    except Exception: pass
```

## CRITICAL: Multi-Level Cleanup

Always use try-except-finally with multi-level cleanup. Track all resources globally:

```python
created_sessions = []
try:
    window, session = await create_window(connection, "test")
    created_sessions.append(session)
    # ... test logic ...
except Exception as e:
    print(f"ERROR: {e}")
    raise
finally:
    for s in created_sessions:
        try:
            await s.async_send_text("\x03")
            await asyncio.sleep(0.1)
            await s.async_send_text("exit\n")
            await asyncio.sleep(0.1)
            await s.async_close()
        except Exception:
            pass
```

## Screenshot Capture (Parallel-Safe)

Use position-based Quartz correlation to capture the correct window — name-based matching fails when commands change the window title:

```python
import Quartz, subprocess

async def capture_screenshot(window, output_path):
    """Capture screenshot of a specific window (no focus required)."""
    frame = await window.async_get_frame()
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly
        | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )
    best_id, best_score = None, float("inf")
    for w in window_list:
        if "iTerm" not in w.get("kCGWindowOwnerName", ""):
            continue
        b = w.get("kCGWindowBounds", {})
        score = (abs(float(b.get("X", 0)) - frame.origin.x) * 2
                 + abs(float(b.get("Width", 0)) - frame.size.width)
                 + abs(float(b.get("Height", 0)) - frame.size.height))
        if score < best_score:
            best_score, best_id = score, w.get("kCGWindowNumber")
    if best_id and best_score < 30:
        subprocess.run(["screencapture", "-x", "-l", str(best_id), output_path])
        return output_path
    return None
```

Key facts:
- `screencapture -l` works for **non-frontmost** windows — no focus required
- Minimized windows **cannot** be captured (excluded by `kCGWindowListOptionOnScreenOnly`)
- Each agent needs its **own window** (not tab) for independent screenshots
- Tabs share the same Quartz window ID — screenshot shows the active tab only

## TUI Layout Verification

TUI elements frequently misalign. Always verify layout integrity. See `references/verification-patterns.md` for complete helpers including box integrity, modal boundaries, and status bar checks.

## Test Reporting

Track results with a `results` dict containing `passed`, `failed`, and `tests` list. See `references/reporting.md` for JSON/JUnit export patterns.

## Special Keys Reference

| Key | Code | Notes |
|-----|------|-------|
| Enter | `\r` | Prefer over `\n` in TUIs |
| Esc | `\x1b` | |
| Ctrl+C | `\x03` | |
| Ctrl+D | `\x04` | EOF |
| Ctrl+X | `\x18` | |
| Tab | `\t` | |
| Up Arrow | `\x1b[A` | |
| Down Arrow | `\x1b[B` | |
| Right Arrow | `\x1b[C` | |
| Left Arrow | `\x1b[D` | |

## Guidelines

1. **Always use `uv run`** — never run Python directly
2. **Create your own window** — never use `app.current_terminal_window`
3. **Use readiness probes** — never rely on fixed `sleep()` for initialization
4. **Track all resources** — close all created sessions/windows in finally blocks
5. **Use `\r` for Enter in TUIs** — safer than `\n` for prompts
6. **Dump screen on failure** — always show what went wrong
7. **Verify layout** — check box-drawing characters connect properly
8. **Use `suppress_broadcast=True`** when broadcast input may be enabled (prevents text leaking to other sessions)

## Script Storage

| Scope | Location | Git |
|-------|----------|-----|
| Project-specific | `./.claude/automations/{script}.py` or `./.agent/automations/{script}.py` | **COMMIT** — these are project assets |
| General utility | `~/.claude/automations/{script}.py` | N/A (user home) |
| Screenshots | `./.claude/screenshots/` | **GITIGNORE** — local verification only |

**Important:** Automation scripts SHOULD be committed to the repository. They are project assets that enforce test coverage and enable reproducible testing across machines and agents. Use `.claude/automations/` or the agent-neutral `.agent/automations/` folder.

**No PII in scripts:** Since scripts are committed and shareable, they MUST NOT contain:
- Hardcoded usernames, hostnames, or paths specific to one developer
- API keys, tokens, or credentials
- Personal file paths (use `~`, `$HOME`, or relative paths)
- Machine-specific configurations (use environment variables)

**Screenshots MUST NOT be committed.** Add to `.gitignore`:
```
.claude/screenshots/
.agent/screenshots/
screenshots/
```

## Examples & References

**Examples** (`examples/` directory):
- `00-comprehensive-template.py` — Complete template with all patterns
- `01-basic-tab.py` — Simple tab creation and command execution
- `02-dev-layout.py` — Multi-pane development layout
- `03-repl-driver.py` — REPL automation with verification
- `04-nano-automation.py` — TUI editor interaction with cleanup
- `05-screen-monitor.py` — ScreenStreamer for real-time monitoring
- `06-environment-vars.py` — Environment variable handling
- `07-cleanup-sessions.py` — Session cleanup patterns
- `08-badge-control.py` — Badge and tab control
- `09-special-keys.py` — Special key sequences for TUI navigation
- `10-session-reuse.py` — Get-or-create session reuse pattern
- `11-layout-verification.py` — TUI layout alignment checks
- `12-parallel-agents.py` — Multiple concurrent agents with independent screenshots
- `13-connection-diagnostics.py` — Pre-flight checks and troubleshooting

**References** (`references/` directory):
- `templates.md` — Copy-paste script templates (single + parallel)
- `verification-patterns.md` — All verification helpers including layout checks
- `reporting.md` — Test reporting patterns, JSON/JUnit export
- `parallel-patterns.md` — Parallel agent patterns, Quartz correlation, cleanup
- `cloud-and-limitations.md` — Platform support matrix, cloud alternatives

## Links

- [iTerm2 Python API](https://iterm2.com/python-api/)
- [iTerm2 App Class](https://iterm2.com/python-api/app.html)
- [iTerm2 Window Class](https://iterm2.com/python-api/window.html)
- [iTerm2 Session Class](https://iterm2.com/python-api/session.html)
- [iTerm2 Transaction](https://iterm2.com/python-api/transaction.html)
- [UV Documentation](https://github.com/astral-sh/uv)
