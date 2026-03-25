# Parallel Agent Patterns

Patterns for running multiple AI agents concurrently, each with independent iTerm2 windows, sessions, and screenshots.

## Architecture

```
┌──────────────── iTerm2 (single instance) ────────────────┐
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ Window 1  │  │ Window 2  │  │ Window 3  │             │
│  │ Agent A   │  │ Agent B   │  │ Agent C   │             │
│  │ QID: 4201 │  │ QID: 4202 │  │ QID: 4203 │            │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘              │
│        │              │              │                    │
│   WebSocket 1    WebSocket 2    WebSocket 3               │
│        └──────────────┼──────────────┘                    │
│              Unix Domain Socket                           │
└──────────────────────────────────────────────────────────┘
```

Multiple WebSocket connections are fully supported. The iTerm2 API server maintains a connection dictionary — each agent gets its own cookie+key pair for authentication.

## Key Rules

1. **Each agent creates its OWN window** — not a tab in a shared window
2. **Window creation must be sequential** — concurrent `Window.async_create()` causes race conditions
3. **All operations target explicit session IDs** — never use `current_terminal_window`
4. **Use `suppress_broadcast=True`** with `async_send_text()` to prevent text leaking
5. **Position windows uniquely** — enables Quartz ID correlation for screenshots

## Window Creation with Readiness Probes

```python
async def create_agent_window(
    connection,
    agent_id: str,
    x_pos: int,
    width: int = 700,
    height: int = 500,
    timeout: float = 5.0,
) -> tuple:
    """Create an isolated window with full readiness verification.

    Args:
        connection: iTerm2 connection
        agent_id: Unique identifier for this agent (used as session name)
        x_pos: X position in pixels (must be unique per concurrent agent)
        width: Window width in pixels
        height: Window height in pixels
        timeout: Maximum seconds to wait for readiness

    Returns:
        (window, session) tuple

    Raises:
        RuntimeError: If window fails readiness checks
    """
    import time

    window = await iterm2.Window.async_create(connection)
    if window is None:
        raise RuntimeError(f"[{agent_id}] Window creation returned None")

    await asyncio.sleep(0.5)  # Let iTerm2 fully initialize

    # Refresh app state — returned window object can be stale
    app = await iterm2.async_get_app(connection)
    if window.current_tab is None:
        for w in app.terminal_windows:
            if w.window_id == window.window_id:
                window = w
                break

    # Readiness probe: wait for tab + session
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if window.current_tab and window.current_tab.current_session:
            break
        await asyncio.sleep(0.2)
    else:
        raise RuntimeError(f"[{agent_id}] Tab/session not ready after {timeout}s")

    session = window.current_tab.current_session
    await session.async_set_name(agent_id)

    # Position window uniquely for Quartz correlation
    frame = await window.async_get_frame()
    await window.async_set_frame(iterm2.Frame(
        iterm2.Point(x_pos, frame.origin.y),
        iterm2.Size(width, height),
    ))
    await asyncio.sleep(0.3)

    # Verify position settled
    frame = await window.async_get_frame()
    if abs(frame.origin.x - x_pos) > 20:
        print(f"  [{agent_id}] WARNING: Window at x={frame.origin.x}, expected {x_pos}")

    # Verify screen is readable
    screen = await session.async_get_screen_contents()
    if screen is None:
        raise RuntimeError(f"[{agent_id}] Screen not readable after creation")

    return window, session
```

## Parallel Orchestrator Pattern

```python
async def main(connection):
    """Run multiple agents concurrently."""
    # Step 1: Create windows SEQUENTIALLY (avoid race conditions)
    agents = []
    x_positions = [50, 250, 450, 650, 850]  # 200px apart

    for i, x_pos in enumerate(x_positions):
        agent_id = f"agent-{i+1}"
        window, session = await create_agent_window(connection, agent_id, x_pos)
        agents.append((agent_id, window, session))
        print(f"  Created {agent_id} at x={x_pos}")

    # Step 2: Run agent work CONCURRENTLY
    async def agent_work(agent_id, window, session):
        try:
            await session.async_send_text("echo 'Hello from " + agent_id + "'\n")
            await asyncio.sleep(0.5)
            # ... agent-specific work ...
            return True
        except Exception as e:
            print(f"  [{agent_id}] ERROR: {e}")
            return False

    results = await asyncio.gather(
        *[agent_work(aid, win, sess) for aid, win, sess in agents]
    )

    # Step 3: Cleanup ALL windows
    for agent_id, window, session in agents:
        try:
            await session.async_send_text("exit\n")
            await asyncio.sleep(0.1)
            await session.async_close()
        except Exception:
            pass

    return all(results)
```

## Position-Based Screenshot Capture

Window names change when commands run, so use frame geometry for Quartz ID correlation:

```python
try:
    import Quartz
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False


def find_quartz_window_id(target_x, target_w, target_h, tolerance=30):
    """Find Quartz CGWindowNumber by matching frame geometry.

    Uses (X * 2 + W + H) scoring — X weighted higher since it is the
    primary discriminator when windows have the same size.
    """
    if not HAS_QUARTZ:
        return None
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
        score = (
            abs(float(b.get("X", 0)) - target_x) * 2
            + abs(float(b.get("Width", 0)) - target_w)
            + abs(float(b.get("Height", 0)) - target_h)
        )
        if score < best_score:
            best_score, best_id = score, w.get("kCGWindowNumber")
    return best_id if best_score < tolerance else None


async def capture_agent_screenshot(window, output_path):
    """Capture screenshot of a specific agent's window.

    Does NOT require the window to be frontmost.
    Minimized windows cannot be captured.
    """
    frame = await window.async_get_frame()
    qid = find_quartz_window_id(frame.origin.x, frame.size.width, frame.size.height)
    if qid is None:
        print(f"  WARNING: No matching Quartz window found for screenshot")
        return None
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    subprocess.run(["screencapture", "-x", "-l", str(qid), output_path], check=True)
    return output_path
```

## Global Cleanup (Crash-Safe)

Individual `finally` blocks fail when the parent process is killed. Add a startup janitor:

```python
async def cleanup_stale_windows(connection, run_token_prefix="agent-"):
    """Find and close windows from previous crashed runs.

    Call this at the START of each orchestrator run to clean up orphans.
    """
    app = await iterm2.async_get_app(connection)
    closed = 0
    for window in app.terminal_windows:
        for tab in window.tabs:
            for session in tab.sessions:
                if session.name and session.name.startswith(run_token_prefix):
                    try:
                        await session.async_send_text("\x03")
                        await asyncio.sleep(0.1)
                        await session.async_send_text("exit\n")
                        await asyncio.sleep(0.1)
                        await session.async_close()
                        closed += 1
                    except Exception:
                        pass
    if closed:
        print(f"  Cleaned up {closed} stale sessions from previous run")
```

## Screen Verification (Parallel-Safe)

```python
async def verify_text(session, text, timeout=5.0):
    """Wait for text to appear on screen. Works with any session ID."""
    import time
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        screen = await session.async_get_screen_contents()
        for i in range(screen.number_of_lines):
            if text in screen.line(i).string:
                return True
        await asyncio.sleep(0.2)
    return False


async def get_screen_text(session):
    """Get all non-empty lines from screen."""
    screen = await session.async_get_screen_contents()
    return [
        screen.line(i).string
        for i in range(screen.number_of_lines)
        if screen.line(i).string.strip()
    ]
```

## Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| Single iTerm2 instance only | All agents share one app | Multiple windows in one instance is sufficient |
| Window creation must be sequential | Slight startup delay | Create windows first, run work concurrently |
| ~10-15 windows practical max | Scale limit | Enough for typical agent workflows |
| Tabs share Quartz window ID | Cannot screenshot individual tabs | Use split panes for visual isolation |
| Transaction blocking | One agent's Transaction queues others | Avoid Transactions; use individual atomic ops |
| WebSocket stability (long sessions) | Connections may drop after hours | Use `retry=True` or add reconnection logic |
| Minimized windows not capturable | Screenshot returns nothing | Ensure windows are not minimized |
| Focus may shift during window creation | Brief visual disruption | Non-issue for automated agents |
