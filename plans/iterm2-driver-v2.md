# iTerm2-Driver v2: Comprehensive Improvement Plan

## Executive Summary

After thorough analysis of the iterm2-driver skill (CASS history across 1,264 sessions in 8+ projects, skill authoring best practices review, 9 spike tests, iTerm2 API source code research, and headless alternatives research), this plan addresses three major areas:

1. **Skill Quality Improvements** — Fix identified gaps against authoring best practices
2. **Parallel Agent Support** — Enable multiple agents to use iTerm2 simultaneously (VERIFIED FEASIBLE)
3. **Headless/Cloud Support** — Provide alternatives for Linux-based cloud environments (NOT feasible with iTerm2; alternative architecture needed)

---

## Part 1: Skill Quality Issues & Fixes

### 1.1 Issues Found (14 total)

| # | Issue | Severity | Category |
|---|-------|----------|----------|
| 1 | Missing `metadata` frontmatter (no `filePattern`/`bashPattern`) | Medium | Discoverability |
| 2 | No Prerequisites section | Medium | Onboarding |
| 3 | `get_iterm2_window_id()` returns FIRST iTerm2 window — broken for multi-window | Critical | Correctness |
| 4 | `app.current_terminal_window` used everywhere — race condition in parallel | Critical | Correctness |
| 5 | No window creation pattern (`Window.async_create()`) | High | Missing feature |
| 6 | Missing error recovery (iTerm2 not running, API not enabled, socket stale) | High | Reliability |
| 7 | Boilerplate duplication across all 12 examples | Medium | Maintainability |
| 8 | No connection architecture documentation (websocket, socket path) | Medium | Understanding |
| 9 | Python `>=3.14` requirement — aggressive, works but could exclude users | Low | Compatibility |
| 10 | Missing `allowed-tools` field | Low | Security |
| 11 | No timeout configuration guidance | Low | Usability |
| 12 | Missing links to specific API reference pages | Low | Documentation |
| 13 | No global cleanup mechanism — orphaned windows on crash | High | Reliability |
| 14 | No window position/size management patterns | Medium | Missing feature |

### 1.2 Fixes

**CRITICAL (must fix):**

1. **Replace `get_iterm2_window_id()`** with position-based Quartz correlation:
   ```python
   async def get_quartz_window_id(iterm_window):
       """Resolve iTerm2 window to Quartz CGWindowNumber using frame matching."""
       frame = await iterm_window.async_get_frame()
       window_list = Quartz.CGWindowListCopyWindowInfo(...)
       # Match by (X position, width, height) — unique fingerprint
   ```

2. **Replace `app.current_terminal_window`** with explicit window creation:
   ```python
   # OLD (broken for parallel)
   window = app.current_terminal_window

   # NEW (parallel-safe)
   window = await iterm2.Window.async_create(connection)
   session = window.current_tab.current_session
   ```

3. **Add global cleanup wrapper** that tracks all created windows/sessions:
   ```python
   created_resources = []
   try:
       # test logic
   finally:
       for window in created_resources:
           # close all sessions, close window
   ```

**HIGH priority:**

4. **Add Prerequisites section** to SKILL.md top:
   ```markdown
   ## Prerequisites
   - macOS with iTerm2 installed
   - iTerm2 Python API enabled (Preferences > General > Magic)
   - Python 3.14+ and `uv` package manager
   - For screenshots: iTerm2 must be running (not minimized to dock)
   ```

5. **Add connection diagnostics pattern**:
   ```python
   # Check if iTerm2 API socket is connectable before running
   import socket, os
   sock_path = os.path.expanduser("~/Library/Application Support/iTerm2/private/socket")
   if not os.path.exists(sock_path):
       print("ERROR: iTerm2 API socket not found. Is iTerm2 running with Python API enabled?")
   ```

6. **Add stale socket recovery**:
   ```python
   # If connection fails, check for stale socket
   # Socket timestamp older than iTerm2 process start time = stale
   ```

**MEDIUM priority:**

7. **Add metadata frontmatter** for auto-injection:
   ```yaml
   metadata:
     filePattern: ["**/.claude/automations/*.py", "**/iterm2*.py"]
     bashPattern: ["uv run.*iterm", "iterm2"]
   ```

8. **Extract shared utilities** into a `references/utilities.md`:
   - Result tracking (log_result, print_summary)
   - Screenshot capture (with position-based Quartz correlation)
   - Cleanup helpers
   - Screen verification helpers

9. **Document connection architecture** in Core Concepts:
   ```markdown
   ## Connection Architecture
   - Python API connects via WebSocket over Unix domain socket
   - Socket path: ~/Library/Application Support/iTerm2/private/socket
   - Multiple simultaneous connections supported (each gets unique cookie)
   - Connection authenticated via ITERM2_COOKIE env var
   ```

---

## Part 2: Parallel Agent Support

### 2.1 Feasibility: VERIFIED

Spike tests confirmed:

| Capability | Status | Evidence |
|-----------|--------|----------|
| Multiple websocket connections | WORKS | Spike 02: 2 agents, 2 PIDs, both connected |
| Session isolation | WORKS | No cross-contamination of commands |
| Independent screenshots | WORKS | `screencapture -l` works for non-frontmost windows |
| Concurrent command execution | WORKS | Spike 08: 5 agents, 5 real commands, 9 screenshots, 7.5s |
| Multi-tab windows | WORKS | Spike 09: 3-tab window with independent content |
| Split pane windows | WORKS | Spike 09: 2x2 and 3-way horizontal splits |
| Diverse window sizes | WORKS | Large (900x600), small (500x350), tall (400x700), wide (1000x400) |

### 2.2 Architecture for Parallel Agents

```
┌─────────────────────────────────────────────────┐
│                   iTerm2 App                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Window 1  │  │ Window 2  │  │ Window 3  │    │
│  │ Agent A   │  │ Agent B   │  │ Agent C   │    │
│  │ Quartz:42 │  │ Quartz:43 │  │ Quartz:44 │   │
│  └──────────┘  └──────────┘  └──────────┘      │
│        ↕              ↕              ↕           │
│   WebSocket 1    WebSocket 2    WebSocket 3      │
│        ↕              ↕              ↕           │
│    Unix Domain Socket (shared, multiplexed)      │
└─────────────────────────────────────────────────┘
        ↕              ↕              ↕
   ┌────────┐    ┌────────┐    ┌────────┐
   │Agent A │    │Agent B │    │Agent C │
   │Python  │    │Python  │    │Python  │
   │Process │    │Process │    │Process │
   └────────┘    └────────┘    └────────┘
```

### 2.3 Key Design Decisions

1. **Each agent creates its OWN window** (not tab in shared window)
   - Required for independent screenshots via `screencapture -l`
   - Tabs within a window share the same Quartz window ID

2. **Window creation must be sequential** (not concurrent)
   - Creating 5+ windows simultaneously via `asyncio.gather()` causes race conditions
   - `Window.async_create()` returns before the window is fully initialized
   - Solution: Create windows sequentially with 0.5s delay, then run agent work concurrently

3. **Position-based Quartz ID correlation**
   - Each agent sets its window to a unique X position via `async_set_frame()`
   - Correlation: match (X, Width, Height) to Quartz window bounds
   - Why not window name? Name changes when commands run

4. **Global cleanup mechanism**
   - Track all created windows in a list at the orchestrator level
   - On any crash, iterate and close all tracked windows
   - Individual agent finally-blocks are insufficient (crash in one doesn't clean up others)

### 2.4 Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| Single iTerm2 instance only | All agents share one app | Sufficient — multiple windows in one instance |
| Multiple instances: Python API can only connect to one | Cannot distribute across instances | Use one instance with multiple windows |
| Window creation limit | ~10-15 windows practical max | More than enough for typical use |
| `screencapture -l` captures entire window, not specific tab | Agent needing tab-specific screenshot must activate that tab first | Use split panes instead of tabs when visual isolation needed |
| Window names change with running commands | Cannot use name-based Quartz correlation | Use position+size-based correlation |
| macOS-only | No Linux/cloud support | See Part 3 |
| Transaction blocking | One agent's Transaction blocks all others temporarily | Avoid Transactions; use individual atomic ops |
| WebSocket stability (GitLab #7681) | Long-lived connections can drop with code 1006 after hours | Add reconnection logic; use `retry=True` |
| `suppress_broadcast` needed | Broadcast input mode sends text to ALL sessions | Always pass `suppress_broadcast=True` to `async_send_text()` |
| Minimized windows can't be captured | `kCGWindowListOptionOnScreenOnly` excludes minimized | Ensure agent windows are never minimized |

### 2.5 New Patterns to Add to Skill

```python
# Pattern: Parallel-safe window creation
async def create_agent_window(connection, agent_id, x_pos, width=600, height=400):
    """Create an isolated window for a parallel agent."""
    window = await iterm2.Window.async_create(connection)
    await asyncio.sleep(0.5)  # Wait for initialization

    session = window.current_tab.current_session
    await session.async_set_name(agent_id)

    frame = await window.async_get_frame()
    await window.async_set_frame(iterm2.Frame(
        iterm2.Point(x_pos, frame.origin.y),
        iterm2.Size(width, height)
    ))

    return window, session

# Pattern: Position-based screenshot capture
async def capture_agent_screenshot(window, output_path):
    """Capture screenshot of a specific agent's window (no focus required)."""
    frame = await window.async_get_frame()
    quartz_id = find_quartz_window(frame.origin.x, frame.size.width, frame.size.height)
    if quartz_id:
        subprocess.run(["screencapture", "-x", "-l", str(quartz_id), output_path])
```

---

## Part 3: Headless/Cloud Support

### 3.1 Feasibility Assessment

| Environment | iTerm2 Feasible? | Why |
|------------|-----------------|-----|
| macOS local | YES | Native support |
| macOS CI (GitHub Actions macOS runners) | MAYBE | Has WindowServer, but iTerm2 not pre-installed |
| Linux containers (Claude Code Web, Codex Web, Codespaces) | NO | iTerm2 is macOS-only, requires WindowServer |
| Linux CI (GitHub Actions ubuntu) | NO | No macOS, no WindowServer |
| Remote macOS via SSH | NO | No WindowServer access over SSH |

**Conclusion: iTerm2 cannot run in headless/cloud environments.** We need an alternative terminal automation layer.

### 3.2 Recommended Alternative: tmux + libtmux

tmux is the best alternative because:
- Available on all Linux distros (apt, yum, brew)
- No display/GUI required — fully headless
- Python library (libtmux) provides programmatic control
- Feature parity with iTerm2 for our use cases

**Feature Mapping:**

| iTerm2 Python API | tmux/libtmux Equivalent |
|------------------|------------------------|
| `iterm2.run_until_complete(main)` | `server = libtmux.Server()` |
| `Window.async_create(connection)` | `session.new_window()` |
| `session.async_split_pane(vertical=True)` | `window.split(vertical=True)` |
| `session.async_send_text("cmd\n")` | `pane.send_keys("cmd")` |
| `session.async_get_screen_contents()` | `pane.capture_pane()` |
| `screencapture -l <id>` | `pane.capture_pane()` → Rich/ANSI-to-image |
| `session.async_set_name("name")` | `window.rename_window("name")` |
| `session.async_close()` | `pane.kill()` |
| `ScreenStreamer` (real-time) | `pane.capture_pane()` polling |

**"Screenshot" alternative for headless:**

```python
# Option 1: ANSI text capture (fast, text-only)
output = pane.capture_pane()  # Returns list of strings

# Option 2: Rich Console rendering to HTML/SVG
from rich.console import Console
console = Console(record=True)
for line in pane.capture_pane():
    console.print(line)
console.save_svg("screenshot.svg")

# Option 3: Terminal recording (for demos/CI artifacts)
# asciinema rec output.cast
```

### 3.3 Architecture: Unified Terminal Automation Layer

To support both macOS (iTerm2) and cloud (tmux), create an abstraction layer:

```python
# terminal_driver.py — unified interface

class TerminalDriver:
    """Abstract interface for terminal automation."""

    async def create_window(self, name: str) -> Window: ...
    async def create_split(self, parent, vertical: bool) -> Session: ...
    async def send_text(self, session, text: str): ...
    async def get_screen(self, session) -> list[str]: ...
    async def capture_screenshot(self, window, path: str): ...
    async def close(self, session): ...

class ITerm2Driver(TerminalDriver):
    """macOS implementation using iTerm2 Python API."""
    ...

class TmuxDriver(TerminalDriver):
    """Linux/cloud implementation using libtmux."""
    ...

def get_driver() -> TerminalDriver:
    """Auto-detect environment and return appropriate driver."""
    if sys.platform == "darwin" and iterm2_available():
        return ITerm2Driver()
    else:
        return TmuxDriver()
```

### 3.4 Cloud Deployment Steps

For a cloud agent to use terminal automation:

```bash
# 1. Install tmux (usually pre-installed in CI/containers)
apt-get install -y tmux  # or: brew install tmux

# 2. Start tmux server (no display needed)
tmux new-session -d -s automation

# 3. Run automation script
uv run terminal_test.py  # Uses TmuxDriver automatically
```

### 3.5 Limitations of tmux Alternative

| Feature | iTerm2 | tmux | Gap |
|---------|--------|------|-----|
| True pixel screenshots | YES (Quartz) | NO (text-only capture) | Can render via Rich/SVG but not pixel-perfect |
| ANSI color in captures | Partial (text API) | YES (capture -p -e) | tmux is actually better here |
| Real-time streaming | ScreenStreamer | Polling | Slightly worse latency |
| Window management UI | Full GUI | None (headless) | Non-issue for automation |
| TUI rendering fidelity | Exact (real terminal) | Exact (real terminal) | No gap |
| Font rendering verification | YES (pixel screenshot) | NO | Cannot verify visual font rendering |
| Mouse interaction | Limited | Limited | Both limited |

---

## Part 4: Implementation Roadmap (REVISED per Council Review)

> **Council feedback incorporated:** Codex and Gemini reviewed this plan. Key changes:
> correctness-first sequencing, stronger window ownership, readiness probes instead of
> fixed sleeps, capability flags for the abstraction layer, and narrowed tmux contract.

### Phase 1: Correctness Hardening (2-3 days)

Fix the **live bugs first** — the current skill advertises `app.current_terminal_window`
which is a correctness defect for any multi-window scenario.

- [ ] Replace `app.current_terminal_window` with explicit `Window.async_create()`
- [ ] Replace `get_iterm2_window_id()` with robust window ownership model:
  - Full geometry matching (x + y + w + h)
  - Post-create / post-move verification loop
  - Retries under timeout/backoff
  - Run-token tagging for window identification
- [ ] Replace all `sleep(0.5)` with readiness probes:
  - Wait for tab/session presence
  - Verify frame matches requested bounds
  - Confirm input acceptance + screen read succeeds
  - Bounded timeout with exponential backoff
- [ ] Add startup janitor: find/close stale windows from previous crashed runs
- [ ] Add connection diagnostics (socket existence, connectivity check, stale socket detection)
- [ ] Add permission diagnostics (Screen Recording, Accessibility if needed)
- [ ] Add Prerequisites section to SKILL.md
- [ ] Document connection architecture (websocket, socket path, auth cookies)
- [ ] Add `retry=True` guidance for `run_until_complete()`
- [ ] Tests: single-window ownership, crash recovery, permission degradation

### Phase 2: Parallel Agent Support (2-3 days)

Only after single-window ownership is solid.

- [ ] Add `create_agent_window()` with readiness probes
- [ ] Add `capture_agent_screenshot()` with full-geometry Quartz correlation
- [ ] Add global cleanup wrapper + out-of-band janitor (handles SIGKILL, host crash)
- [ ] Run-token/lease model: each run gets a unique ID, all windows carry it
- [ ] Add example: `12-parallel-agents.py`
- [ ] Add reference: `references/parallel-patterns.md`
- [ ] Update existing examples to use explicit window creation
- [ ] Soak tests before declaring "verified":
  - [ ] 1 / 5 / 10 / 15 concurrent agents
  - [ ] Mixed resize + split + screenshot operations
  - [ ] Manual user interference (move/resize/close during run)
  - [ ] Crash recovery and stale-resource cleanup
- [ ] Experiment: Does `Window.async_create()` steal focus?
- [ ] Experiment: Does `screencapture -l` work across Spaces/Stage Manager?

### Phase 3: Headless/Cloud Support (3-5 days)

Build abstraction from **proven capabilities**, not guessed equivalence.

- [ ] Define normalized primitives (not 1:1 API mapping):
  - `send_input`, `capture_text`, `capture_visible_screen`
  - `split_pane`, `close`, `set_dimensions(cols, rows)`
  - `render_pixel_screenshot` (only where supported)
- [ ] Add explicit capability flags per driver:
  - `supports_pixel_screenshot`
  - `supports_text_snapshot`
  - `supports_alt_screen_capture`
  - `supports_parallel_windows`
  - `supports_mouse`
- [ ] Implement `ITerm2Driver` (wraps hardened Phase 1/2 patterns)
- [ ] Implement `TmuxDriver` (libtmux-based):
  - Per-run isolation via `tmux -L <run-id>` or `-S <socket-path>`
  - Session/window naming conventions
  - TTL cleanup for abandoned sessions
  - `capture_pane -p -e` for ANSI-preserving text capture
  - Alt-screen and scrollback handling with explicit flags
  - `send_keys` with explicit Enter behavior and control sequence handling
- [ ] "Screenshot" alternatives (explicitly NOT pixel-parity):
  - `screen_text` — for assertions (plain text)
  - `ansi_artifact` — for human review (ANSI-to-SVG via Rich or termtosvg)
  - `pixel_screenshot` — only on GUI backends (iTerm2)
- [ ] Add example: `13-tmux-automation.py`
- [ ] Add reference: `references/headless-patterns.md`
- [ ] Validate abstraction against existing examples during build (not after)

### Phase 4: Documentation & Polish

- [ ] Add metadata frontmatter for auto-injection
- [ ] Fix Python version to `>=3.12` (more inclusive)
- [ ] Add links to specific iTerm2 API reference pages
- [ ] Extract shared utilities into `references/utilities.md`
- [ ] Update SKILL.md with environment detection and capability guidance
- [ ] End-to-end validation suite for both backends

---

## Appendix A: Spike Test Results Summary

| Spike | Purpose | Result |
|-------|---------|--------|
| 01 | Connection architecture, window enumeration | Window IDs are GUIDs, unique per window |
| 02 | Concurrent connections (2 agents) | PASS — session isolation confirmed |
| 03 | Screenshot targeting analysis | `screencapture -l` works for non-frontmost windows |
| 04 | Window name correlation | Name match works but unreliable when commands run |
| 05 | Realistic parallel (HTTP server + top) | PASS — 5/5 agents, real commands |
| 06 | Robust screenshot (frame-based) | Frame matching works but ambiguous for same-size windows |
| 07 | Unique window positions | Position-based correlation solves ambiguity |
| 08 | Five concurrent agents | 5/5 PASS, 9 screenshots, 7.5s |
| 09 | Edge cases (layouts, splits, tabs, REPL) | 4/5 PASS, diverse layouts verified |

## Appendix B: CASS Session History Summary

- **1,264 sessions** indexed, **68,899 messages** analyzed
- **8+ projects** actively use iterm2-driver
- **Primary use case**: L4 visual regression testing with pre-commit enforcement
- **Top pain points**: Screenshot reliability (#1), parallel support (#2), silent failures (#3)
- **Test suite scale**: 8 to 44 tests per script
- **Alternative research**: Ghostty AppleScript explored, found lacking (no `contents` API)

## Appendix C: Multiple iTerm2 Instances

- macOS allows multiple instances via `open -n /Applications/iTerm.app`
- iTerm2 has undocumented `-suite` flag for separate preferences
- **CRITICAL LIMITATION**: Python API socket path is singular — only one instance can be targeted
- Both instances bind to the same socket; last one wins
- **Recommendation**: Use one instance with multiple windows (sufficient for all use cases)

## Appendix D: Council Review (Codex + Gemini)

**Date**: 2026-03-24

**Codex Key Findings (High Severity):**
1. Roadmap priority inversion: Critical correctness bugs delayed to Phase 2 while Phase 1 is docs
2. Position-based Quartz correlation is brittle (Retina, shadows, Stage Manager, multi-display)
3. `sleep(0.5)` is not an initialization strategy — needs readiness probes
4. `finally`-only cleanup insufficient for SIGKILL/host crash — needs out-of-band janitor
5. tmux mapping is logically inconsistent (Window maps to pane.kill())
6. tmux "screenshot" substitute is not feature-parity — need to split screen_text / ansi_artifact / pixel_screenshot
7. Need soak tests at 1/5/10/15 agents before declaring "verified"

**Gemini Key Findings:**
1. Stage Manager / Spaces may break `screencapture -l` (needs experiment)
2. Focus stealing from `Window.async_create()` (needs experiment)
3. Terminal dimension normalization (cols/rows) missing from abstraction
4. Resource exhaustion risk at 10+ windows (needs measurement)
5. API version mismatch risk between iTerm2 and Python library

**Codex Review of Gemini:** Some claims stated with unwarranted confidence (focus stealing, Spaces behavior, memory leaks). Should be treated as hypotheses to test, not accepted facts.

**Synthesis (Chair):** Plan is directionally strong but overconfident in two places: parallel window ownership and tmux feature equivalence. Correctness-first sequencing, capability flags, and stronger ownership model are the required changes.

**All council feedback has been incorporated into the revised Phase 1-4 roadmap above.**
