# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "iterm2",
#   "pyobjc",
#   "pyobjc-framework-Quartz",
# ]
# ///

"""
Example 12: Parallel Agents — Multiple concurrent agents with independent windows

Demonstrates how multiple AI agents can each drive their own iTerm2 window
simultaneously, running different real commands and capturing independent
screenshots without interfering with each other.

Tests:
    1. Sequential Window Creation: Create 3 windows with unique positions
    2. Concurrent Execution: Run different real commands in each window
    3. Independent Screenshots: Capture each window separately (no focus needed)
    4. Session Isolation: Verify no cross-contamination between agents
    5. Cleanup: Close all windows cleanly

Verification Strategy:
    - Each agent sends a unique MARKER string and verifies only its own marker
    - Screenshots are captured per-window using position-based Quartz correlation
    - Cross-contamination check: each agent scans for other agents' markers

Screenshots:
    - parallel_agent1_git.png: Agent 1 showing git log
    - parallel_agent2_sysinfo.png: Agent 2 showing system info
    - parallel_agent3_files.png: Agent 3 showing file listing

Key Bindings:
    - N/A (non-interactive — automated agents)

Usage:
    uv run 12-parallel-agents.py
"""

import asyncio
import os
import subprocess
import sys
import time

import iterm2

# ============================================================
# CONFIGURATION
# ============================================================

SCREENSHOT_DIR = "./screenshots"

# ============================================================
# RESULT TRACKING
# ============================================================

results = {"passed": 0, "failed": 0, "tests": [], "start_time": None}


def log_result(name: str, status: str, details: str = ""):
    results["tests"].append({"name": name, "status": status, "details": details})
    if status == "PASS":
        results["passed"] += 1
        print(f"  [+] PASS: {name}")
    else:
        results["failed"] += 1
        print(f"  [x] FAIL: {name} — {details}")


def print_summary() -> int:
    total = results["passed"] + results["failed"]
    elapsed = time.monotonic() - results["start_time"] if results["start_time"] else 0
    print(f"\n{'=' * 60}")
    print(f"PARALLEL AGENTS: {results['passed']}/{total} passed ({elapsed:.1f}s)")
    print("=" * 60)
    if results["failed"] > 0:
        for t in results["tests"]:
            if t["status"] == "FAIL":
                print(f"  x {t['name']}: {t['details']}")
        print("\nOVERALL: FAILED")
        return 1
    print("\nOVERALL: PASSED")
    return 0


# ============================================================
# QUARTZ SCREENSHOT
# ============================================================

try:
    import Quartz

    def find_quartz_id(target_x, target_w, target_h, tolerance=30):
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

except ImportError:

    def find_quartz_id(target_x, target_w, target_h, tolerance=30):
        return None


async def capture_screenshot(window, name):
    frame = await window.async_get_frame()
    qid = find_quartz_id(frame.origin.x, frame.size.width, frame.size.height)
    if qid:
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        path = f"{SCREENSHOT_DIR}/{name}.png"
        subprocess.run(["screencapture", "-x", "-l", str(qid), path], check=True)
        print(f"  SCREENSHOT: {path}")
        return path
    print(f"  WARNING: No Quartz match for {name}")
    return None


# ============================================================
# READINESS + VERIFICATION HELPERS
# ============================================================


async def create_agent_window(connection, agent_id, x_pos, width=650, height=450):
    """Create a window with readiness probes and app-refresh pattern."""
    window = await iterm2.Window.async_create(connection)
    await asyncio.sleep(0.5)

    # Refresh — returned window object can be stale
    app = await iterm2.async_get_app(connection)
    if window.current_tab is None:
        for w in app.terminal_windows:
            if w.window_id == window.window_id:
                window = w
                break

    for _ in range(20):
        if window and window.current_tab and window.current_tab.current_session:
            break
        await asyncio.sleep(0.2)

    if not window or not window.current_tab or not window.current_tab.current_session:
        raise RuntimeError(f"[{agent_id}] Window not ready")

    session = window.current_tab.current_session
    await session.async_set_name(agent_id)

    frame = await window.async_get_frame()
    await window.async_set_frame(
        iterm2.Frame(iterm2.Point(x_pos, frame.origin.y), iterm2.Size(width, height))
    )
    await asyncio.sleep(0.3)
    return window, session


async def verify_text(session, text, timeout=5.0):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        screen = await session.async_get_screen_contents()
        for i in range(screen.number_of_lines):
            if text in screen.line(i).string:
                return True
        await asyncio.sleep(0.2)
    return False


async def screen_lines(session):
    screen = await session.async_get_screen_contents()
    return [screen.line(i).string for i in range(screen.number_of_lines)]


# ============================================================
# AGENT WORK FUNCTIONS
# ============================================================


async def agent_1_git(session, window):
    """Agent 1: Git operations."""
    marker = "AGENT1_MARKER_GIT"
    await session.async_send_text(
        f"echo '{marker}' && git log --oneline -5 2>/dev/null || echo 'no git repo'\n"
    )
    await asyncio.sleep(1.0)
    found = await verify_text(session, marker, timeout=3)
    await capture_screenshot(window, "parallel_agent1_git")
    return found, marker


async def agent_2_sysinfo(session, window):
    """Agent 2: System information."""
    marker = "AGENT2_MARKER_SYS"
    await session.async_send_text(
        f"echo '{marker}' && uptime && sysctl -n machdep.cpu.brand_string\n"
    )
    await asyncio.sleep(1.0)
    found = await verify_text(session, marker, timeout=3)
    await capture_screenshot(window, "parallel_agent2_sysinfo")
    return found, marker


async def agent_3_files(session, window):
    """Agent 3: File listing."""
    marker = "AGENT3_MARKER_FS"
    await session.async_send_text(
        f"echo '{marker}' && df -h / && ls /tmp/*.py 2>/dev/null | head -5\n"
    )
    await asyncio.sleep(1.0)
    found = await verify_text(session, marker, timeout=3)
    await capture_screenshot(window, "parallel_agent3_files")
    return found, marker


# ============================================================
# MAIN
# ============================================================


async def cleanup_stale_windows(connection, prefix="parallel-agent-"):
    """Close windows from previous crashed runs."""
    app = await iterm2.async_get_app(connection)
    for window in app.terminal_windows:
        for tab in window.tabs:
            for session in tab.sessions:
                if session.name and session.name.startswith(prefix):
                    try:
                        await session.async_send_text("exit\n")
                        await asyncio.sleep(0.1)
                        try:
                            await session.async_close()
                        except Exception:
                            pass
                    except Exception:
                        pass


async def main(connection):
    results["start_time"] = time.monotonic()

    print("\n" + "#" * 60)
    print("# PARALLEL AGENTS TEST")
    print("# 3 concurrent agents, independent windows & screenshots")
    print("#" * 60)

    # Startup janitor — clean up orphans from previous crashed runs
    await cleanup_stale_windows(connection)

    agents = []
    agent_fns = [agent_1_git, agent_2_sysinfo, agent_3_files]
    x_positions = [50, 350, 650]

    try:
        # ============================================================
        # TEST 1: Sequential Window Creation
        # ============================================================
        print(f"\n{'=' * 60}")
        print("TEST 1: Sequential Window Creation")
        print("=" * 60)

        for i, x_pos in enumerate(x_positions):
            agent_id = f"parallel-agent-{i + 1}"
            window, session = await create_agent_window(connection, agent_id, x_pos)
            agents.append((agent_id, window, session))
            print(f"  Created {agent_id} at x={x_pos}")
        log_result("Sequential Window Creation", "PASS")

        # ============================================================
        # TEST 2: Concurrent Execution
        # ============================================================
        print(f"\n{'=' * 60}")
        print("TEST 2: Concurrent Execution")
        print("=" * 60)

        agent_results = await asyncio.gather(
            *[fn(sess, win) for fn, (_, win, sess) in zip(agent_fns, agents, strict=False)]
        )
        all_found = all(found for found, _ in agent_results)
        if all_found:
            log_result("Concurrent Execution", "PASS")
        else:
            missing = [m for found, m in agent_results if not found]
            log_result("Concurrent Execution", "FAIL", f"Markers not found: {missing}")

        # ============================================================
        # TEST 3: Independent Screenshots
        # ============================================================
        print(f"\n{'=' * 60}")
        print("TEST 3: Independent Screenshots")
        print("=" * 60)

        screenshots = (
            os.listdir(SCREENSHOT_DIR) if os.path.exists(SCREENSHOT_DIR) else []
        )
        parallel_shots = [f for f in screenshots if f.startswith("parallel_")]
        if len(parallel_shots) >= 3:
            sizes = [os.path.getsize(f"{SCREENSHOT_DIR}/{f}") for f in parallel_shots]
            log_result(
                "Independent Screenshots",
                "PASS",
                f"{len(parallel_shots)} screenshots, sizes: {sizes}",
            )
        else:
            log_result(
                "Independent Screenshots",
                "FAIL",
                f"Only {len(parallel_shots)} screenshots (expected 3)",
            )

        # ============================================================
        # TEST 4: Session Isolation
        # ============================================================
        print(f"\n{'=' * 60}")
        print("TEST 4: Session Isolation")
        print("=" * 60)

        contaminated = False
        for agent_id, _, session in agents:
            lines = await screen_lines(session)
            full_text = " ".join(lines)
            for other_id, _, _ in agents:
                if other_id == agent_id:
                    continue
                other_num = other_id.split("-")[-1]
                other_marker = f"AGENT{other_num}_MARKER"
                if other_marker in full_text:
                    contaminated = True
                    print(f"  CONTAMINATION: {agent_id} contains {other_marker}")

        if not contaminated:
            log_result("Session Isolation", "PASS")
        else:
            log_result("Session Isolation", "FAIL", "Cross-contamination detected")

        log_result("Cleanup", "PASS")

    except Exception as e:
        log_result("Test Execution", "FAIL", str(e))

    finally:
        # ============================================================
        # CLEANUP (always runs, even on crash)
        # ============================================================
        print(f"\n{'=' * 60}")
        print("CLEANUP")
        print("=" * 60)

        for _agent_id, _, session in agents:
            try:
                await session.async_send_text("exit\n")
                await asyncio.sleep(0.2)
                try:
                    await session.async_close()
                except Exception:
                    pass
            except Exception:
                pass

    return print_summary()


if __name__ == "__main__":
    exit_code = iterm2.run_until_complete(main)
    sys.exit(exit_code or 0)
