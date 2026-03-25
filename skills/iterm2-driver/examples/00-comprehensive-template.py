# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "iterm2",
#   "pyobjc",
#   "pyobjc-framework-Quartz",
# ]
# ///

"""
Comprehensive Template: Canonical example demonstrating ALL iTerm2 automation patterns

This is the copy-paste starting point for new automation scripts. It demonstrates:
- Safe window creation with readiness probes (never uses current_terminal_window)
- Position-based Quartz screenshot targeting (works without focus)
- Multi-level try-except-finally cleanup with resource tracking
- Result tracking with pass/fail/unverified and summary report
- Screen verification with timeout-based polling
- Connection diagnostics on failure

Tests:
    1. Shell Ready: Verify the shell is accessible and responsive
    2. Command Execution: Run a command and verify output via unique marker
    3. Multiple Commands: Run sequential commands and verify output
    4. Final State: Capture final screenshot

Verification Strategy:
    - Create a dedicated window (not current_terminal_window) for isolation
    - Use readiness probes to confirm window/tab/session initialization
    - Use unique timestamp-based markers for output verification
    - Poll screen with 5-second timeout for each state transition
    - Dump full screen contents on any failure for debugging

Screenshots:
    - template_shell_ready.png: Shell prompt visible and ready
    - template_command_output.png: Output after running test command
    - template_final.png: Final state before cleanup

Screenshot Inspection Checklist:
    - Colors: Shell prompt colors (if customized), command output
    - Boundaries: Terminal window bounds captured correctly
    - Buttons/Controls: N/A (basic shell)
    - Mouse Support: N/A (keyboard-only)
    - Visible Elements: Shell prompt, command output, working directory
    - Keyboard Navigation: Cursor visible at prompt

Key Bindings:
    - Enter: Execute command
    - Ctrl+C: Interrupt running command
    - exit: Close shell

Usage:
    uv run 00-comprehensive-template.py
"""

import asyncio
import os
import subprocess
import sys
import time
from datetime import datetime

import iterm2

# ============================================================
# CONFIGURATION
# ============================================================

SCREENSHOT_DIR = "./screenshots"
TIMEOUT_SECONDS = 5.0

# ============================================================
# RESULT TRACKING
# ============================================================

results = {
    "passed": 0,
    "failed": 0,
    "unverified": 0,
    "tests": [],
    "screenshots": [],
    "start_time": None,
    "end_time": None,
}


def log_result(
    test_name: str, status: str, details: str = "", screenshot: str | None = None
):
    """Log a test result."""
    results["tests"].append(
        {
            "name": test_name,
            "status": status,
            "details": details,
            "screenshot": screenshot,
        }
    )
    if screenshot:
        results["screenshots"].append(screenshot)

    symbol = {"PASS": "+", "FAIL": "x", "UNVERIFIED": "?"}.get(status, "?")
    results[{"PASS": "passed", "FAIL": "failed"}.get(status, "unverified")] += 1
    print(f"  [{symbol}] {status}: {test_name}")
    if details:
        print(f"      {details}")
    if screenshot:
        print(f"      Screenshot: {screenshot}")


def print_summary() -> int:
    """Print final test summary and return exit code."""
    results["end_time"] = datetime.now()
    total = results["passed"] + results["failed"] + results["unverified"]
    duration = (
        (results["end_time"] - results["start_time"]).total_seconds()
        if results["start_time"]
        else 0
    )

    print(f"\n{'=' * 60}")
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Duration:   {duration:.1f}s")
    print(f"Total:      {total}")
    print(f"Passed:     {results['passed']}")
    print(f"Failed:     {results['failed']}")
    print(f"Unverified: {results['unverified']}")
    if results["screenshots"]:
        print(f"Screenshots: {len(results['screenshots'])}")
    print("=" * 60)

    if results["failed"] > 0:
        print("\nFailed tests:")
        for t in results["tests"]:
            if t["status"] == "FAIL":
                print(f"  - {t['name']}: {t['details']}")
        print("\nOVERALL: FAILED")
        return 1
    print("\nOVERALL: PASSED")
    return 0


def print_test_header(test_name: str, test_num: int | None = None):
    header = f"TEST {test_num}: {test_name}" if test_num else f"TEST: {test_name}"
    print(f"\n{'=' * 60}")
    print(header)
    print("=" * 60)


# ============================================================
# QUARTZ WINDOW TARGETING (position-based, parallel-safe)
# ============================================================

try:
    import Quartz

    def find_quartz_window_id(target_x, target_w, target_h, tolerance=30):
        """Find Quartz CGWindowNumber by matching iTerm2 window frame geometry."""
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
    print("WARNING: Quartz not available, screenshots will capture full screen")

    def find_quartz_window_id(target_x, target_w, target_h, tolerance=30):
        return None


async def capture_screenshot(window, name: str) -> str:
    """Capture a screenshot of a specific iTerm2 window (no focus required)."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)

    frame = await window.async_get_frame()
    qid = find_quartz_window_id(frame.origin.x, frame.size.width, frame.size.height)

    if qid:
        subprocess.run(["screencapture", "-x", "-l", str(qid), filepath], check=True)
    else:
        print("  WARNING: Quartz window not found, capturing full screen")
        subprocess.run(["screencapture", "-x", filepath], check=True)

    print(f"  SCREENSHOT: {filepath}")
    return filepath


# ============================================================
# VERIFICATION HELPERS
# ============================================================


async def verify_screen_contains(session, expected: str, description: str) -> bool:
    """Wait for expected text to appear on screen within timeout."""
    start = time.monotonic()
    while (time.monotonic() - start) < TIMEOUT_SECONDS:
        screen = await session.async_get_screen_contents()
        for i in range(screen.number_of_lines):
            if expected in screen.line(i).string:
                print(f"  Found: '{expected}' ({description})")
                return True
        await asyncio.sleep(0.2)
    print(f"  Not found: '{expected}' after {TIMEOUT_SECONDS}s ({description})")
    return False


async def verify_shell_prompt(session) -> bool:
    """Verify that a shell prompt is visible.

    Handles traditional ($, %, >) and modern prompts (Starship, Powerlevel10k)
    by checking for username, ~, or any non-empty content after login.
    """
    screen = await session.async_get_screen_contents()
    non_empty = 0
    for i in range(screen.number_of_lines):
        line = screen.line(i).string.strip()
        if line:
            non_empty += 1
        # Traditional prompts
        if "$" in line or "%" in line or ">" in line:
            return True
        # Modern prompts (Starship, Powerlevel10k, Oh-My-Zsh)
        if "~" in line or "❯" in line or "➜" in line or "λ" in line:
            return True
    # If we see at least 2 non-empty lines, the shell likely rendered
    return non_empty >= 2


async def dump_screen(session, label: str):
    """Dump current screen contents for debugging."""
    screen = await session.async_get_screen_contents()
    print(f"\n{'=' * 60}")
    print(f"SCREEN DUMP: {label}")
    print(f"{'=' * 60}")
    for i in range(screen.number_of_lines):
        line = screen.line(i).string
        if line.strip():
            print(f"{i:03d}: {line}")
    print(f"{'=' * 60}\n")


# ============================================================
# WINDOW CREATION WITH READINESS PROBES
# ============================================================


async def create_test_window(connection, name="test", x_pos=100):
    """Create an isolated test window with full readiness verification.

    Never uses app.current_terminal_window — always creates a new window.
    """
    window = await iterm2.Window.async_create(connection)
    if window is None:
        raise RuntimeError("Window.async_create() returned None")

    await asyncio.sleep(0.5)  # Let iTerm2 fully initialize

    # Refresh app state — returned window object can be stale
    app = await iterm2.async_get_app(connection)
    if window.current_tab is None:
        for w in app.terminal_windows:
            if w.window_id == window.window_id:
                window = w
                break

    # Readiness probe: wait for tab and session
    for _ in range(20):
        if window.current_tab and window.current_tab.current_session:
            break
        await asyncio.sleep(0.2)

    if not window.current_tab or not window.current_tab.current_session:
        raise RuntimeError("Window tab/session not ready after timeout")

    session = window.current_tab.current_session
    await session.async_set_name(name)

    # Position window (enables Quartz screenshot targeting)
    frame = await window.async_get_frame()
    await window.async_set_frame(
        iterm2.Frame(
            iterm2.Point(x_pos, frame.origin.y),
            iterm2.Size(frame.size.width, frame.size.height),
        )
    )
    await asyncio.sleep(0.3)

    # Verify screen is readable
    screen = await session.async_get_screen_contents()
    if screen is None:
        raise RuntimeError("Screen not readable after window creation")

    return window, session


# ============================================================
# CLEANUP
# ============================================================


async def cleanup_session(session, quit_key: str | None = None):
    """Perform multi-level cleanup on a session."""
    print("\n  Performing cleanup...")
    try:
        await session.async_send_text("\x03")  # Ctrl+C
        await asyncio.sleep(0.1)
        if quit_key:
            await session.async_send_text(quit_key)
            await asyncio.sleep(0.1)
        await session.async_send_text("exit\n")
        await asyncio.sleep(0.2)
        await session.async_close()
        print("  Cleanup complete")
    except Exception as e:
        print(f"  Cleanup warning: {e}")


# ============================================================
# MAIN TEST FUNCTION
# ============================================================


async def main(connection):
    """Main test function demonstrating all patterns."""
    results["start_time"] = datetime.now()

    print("\n" + "#" * 60)
    print("# COMPREHENSIVE TEMPLATE TEST")
    print("# Demonstrates all iTerm2 automation patterns")
    print("#" * 60)

    # Create isolated test window (NOT current_terminal_window)
    window, session = await create_test_window(connection, "template-test")
    created_sessions = [session]

    try:
        # ============================================================
        # TEST 1: Shell Ready
        # ============================================================
        print_test_header("Shell Ready", 1)
        await asyncio.sleep(0.5)

        if await verify_shell_prompt(session):
            screenshot = await capture_screenshot(window, "template_shell_ready")
            log_result("Shell Ready", "PASS", screenshot=screenshot)
        else:
            await dump_screen(session, "shell_not_ready")
            log_result("Shell Ready", "FAIL", "Shell prompt not detected")

        # ============================================================
        # TEST 2: Command Execution
        # ============================================================
        print_test_header("Command Execution", 2)

        marker = f"TEMPLATE_TEST_{datetime.now().strftime('%H%M%S')}"
        await session.async_send_text(f"echo '{marker}'\n")
        await asyncio.sleep(0.5)

        if await verify_screen_contains(session, marker, "echo output"):
            screenshot = await capture_screenshot(window, "template_command_output")
            log_result("Command Execution", "PASS", screenshot=screenshot)
        else:
            await dump_screen(session, "command_failed")
            log_result("Command Execution", "FAIL", f"Marker '{marker}' not found")

        # ============================================================
        # TEST 3: Multiple Commands
        # ============================================================
        print_test_header("Multiple Commands", 3)

        await session.async_send_text("pwd\n")
        await asyncio.sleep(0.3)
        await session.async_send_text("ls -la | head -5\n")
        await asyncio.sleep(0.5)

        screen = await session.async_get_screen_contents()
        has_output = any(
            "total" in screen.line(i).string or "drwx" in screen.line(i).string
            for i in range(screen.number_of_lines)
        )

        if has_output:
            log_result("Multiple Commands", "PASS")
        else:
            log_result("Multiple Commands", "UNVERIFIED", "Could not verify ls output")

        # ============================================================
        # TEST 4: Final State
        # ============================================================
        print_test_header("Final State", 4)
        screenshot = await capture_screenshot(window, "template_final")
        log_result(
            "Final State", "PASS", "Final screenshot captured", screenshot=screenshot
        )

    except Exception as e:
        print(f"\nERROR during test execution: {e}")
        log_result("Test Execution", "FAIL", str(e))
        await dump_screen(session, "error_state")

    finally:
        for s in created_sessions:
            await cleanup_session(s)

    return print_summary()


if __name__ == "__main__":
    exit_code = iterm2.run_until_complete(main)
    sys.exit(exit_code or 0)
