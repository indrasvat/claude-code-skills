# iTerm2 Automation Script Templates

This reference provides complete, copy-paste-ready templates for iTerm2 automation scripts.

## Contents

- Complete Test Script Template
- Simple Automation Template (No Tests)
- Layout Template (Multi-Pane)

## Complete Test Script Template

```python
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "iterm2",
#   "pyobjc",
#   "pyobjc-framework-Quartz",
# ]
# ///

"""
<Application> TUI Test: Automated testing of <application> terminal interface

Tests:
    1. Launch Test: Verify <application> starts and displays expected UI
    2. Navigation Test: Test keyboard navigation through interface
    3. Feature Test: Test specific feature functionality
    4. Quit Test: Verify clean exit

Verification Strategy:
    - Use screen polling with 5-second timeout for each state transition
    - Look for specific text markers in screen content
    - Verify state changes by checking for expected elements
    - Confirm exit by checking shell prompt returns

Screenshots:
    - <app>_launch.png: Initial screen showing main interface
    - <app>_feature.png: Screen after activating feature
    - <app>_exit.png: Clean shell prompt after quit

Screenshot Inspection Checklist:
    - Colors: <Describe expected status colors, highlights>
    - Boundaries: <Describe headers, footers, borders>
    - Buttons/Controls: <Describe visible controls>
    - Mouse Support: <N/A or describe click targets>
    - Visible Elements: <Describe key text/elements>
    - Keyboard Navigation: <Describe selection indicators>

Key Bindings:
    - q: Quit
    - ?: Help
    - <other bindings>

Usage:
    uv run test_<app>.py
"""

import iterm2
import asyncio
import subprocess
import os
from datetime import datetime

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
    "tests": []
}


def log_result(test_name: str, status: str, details: str = ""):
    """Log a test result."""
    results["tests"].append({
        "name": test_name,
        "status": status,
        "details": details
    })

    if status == "PASS":
        results["passed"] += 1
        print(f"  PASS: {test_name}")
    elif status == "FAIL":
        results["failed"] += 1
        print(f"  FAIL: {test_name} - {details}")
    else:
        results["unverified"] += 1
        print(f"  UNVERIFIED: {test_name} - {details}")


def print_summary():
    """Print final test summary."""
    total = results["passed"] + results["failed"] + results["unverified"]

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total:      {total}")
    print(f"Passed:     {results['passed']}")
    print(f"Failed:     {results['failed']}")
    print(f"Unverified: {results['unverified']}")
    print("=" * 60)

    if results["failed"] > 0:
        print("\nFailed tests:")
        for test in results["tests"]:
            if test["status"] == "FAIL":
                print(f"  - {test['name']}: {test['details']}")

    if results["failed"] > 0:
        print("\nOVERALL: FAILED")
        return 1
    elif results["unverified"] > 0:
        print("\nOVERALL: PASSED (with unverified tests)")
        return 0
    else:
        print("\nOVERALL: PASSED")
        return 0


def print_test_header(test_name: str):
    """Print a visual header for a test section."""
    print("\n" + "-" * 60)
    print(f"TEST: {test_name}")
    print("-" * 60)


# ============================================================
# QUARTZ WINDOW TARGETING
# ============================================================

try:
    import Quartz

    def get_iterm2_window_id():
        """Get the window ID of the frontmost iTerm2 window."""
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID
        )
        for window in window_list:
            owner = window.get('kCGWindowOwnerName', '')
            if 'iTerm' in owner:
                return window.get('kCGWindowNumber')
        return None
except ImportError:
    def get_iterm2_window_id():
        return None


def capture_screenshot(name: str) -> str:
    """Capture a screenshot of the iTerm2 window."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)

    window_id = get_iterm2_window_id()
    if window_id:
        subprocess.run(["screencapture", "-x", "-l", str(window_id), filepath], check=True)
    else:
        subprocess.run(["screencapture", "-x", filepath], check=True)

    print(f"  SCREENSHOT: {filepath}")
    return filepath


# ============================================================
# VERIFICATION HELPERS
# ============================================================

async def verify_screen_contains(session, expected: str, description: str) -> bool:
    """Verify that expected text appears on screen within timeout."""
    start = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start) < TIMEOUT_SECONDS:
        screen = await session.async_get_screen_contents()
        for i in range(screen.number_of_lines):
            if expected in screen.line(i).string:
                return True
        await asyncio.sleep(0.2)
    return False


async def dump_screen(session, label: str):
    """Dump current screen contents for debugging."""
    screen = await session.async_get_screen_contents()
    print(f"\n{'='*60}")
    print(f"SCREEN DUMP: {label}")
    print(f"{'='*60}")
    for i in range(screen.number_of_lines):
        line = screen.line(i).string
        if line.strip():
            print(f"{i:03d}: {line}")
    print(f"{'='*60}\n")


# ============================================================
# CLEANUP
# ============================================================

async def cleanup_session(session, quit_key: str = "q"):
    """Perform multi-level cleanup on a session."""
    try:
        await session.async_send_text("\x03")  # Ctrl+C
        await asyncio.sleep(0.2)
        await session.async_send_text(quit_key)
        await asyncio.sleep(0.2)
        await session.async_send_text("exit\n")
        await asyncio.sleep(0.2)
        await session.async_close()
    except Exception as e:
        print(f"  Cleanup warning: {e}")


# ============================================================
# MAIN TEST FUNCTION
# ============================================================

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window

    if not window:
        print("ERROR: No active window found")
        return 1

    tab = await window.async_create_tab()
    session = tab.current_session

    try:
        # ============================================================
        # TEST 1: Launch application
        # ============================================================
        print_test_header("Launch application")
        await session.async_send_text("<command>\n")
        await asyncio.sleep(1.0)

        if await verify_screen_contains(session, "<expected>", "Expected element visible"):
            log_result("Launch application", "PASS")
            capture_screenshot("launch")
        else:
            log_result("Launch application", "FAIL", "Expected element not visible")
            await dump_screen(session, "launch_failure")

        # ============================================================
        # TEST 2: Feature test
        # ============================================================
        print_test_header("Feature test")
        await session.async_send_text("<key>")
        await asyncio.sleep(0.5)

        if await verify_screen_contains(session, "<expected>", "Feature activated"):
            log_result("Feature test", "PASS")
            capture_screenshot("feature")
        else:
            log_result("Feature test", "FAIL", "Feature not activated")

        # ============================================================
        # TEST 3: Exit test
        # ============================================================
        print_test_header("Exit test")
        await session.async_send_text("q")
        await asyncio.sleep(0.5)

        # Verify we're back at shell prompt
        screen = await session.async_get_screen_contents()
        # Check for shell prompt indicator ($ or %)
        back_at_shell = False
        for i in range(screen.number_of_lines):
            line = screen.line(i).string
            if "$" in line or "%" in line:
                back_at_shell = True
                break

        if back_at_shell:
            log_result("Exit test", "PASS")
            capture_screenshot("exit")
        else:
            log_result("Exit test", "FAIL", "Not back at shell prompt")

    except Exception as e:
        log_result("Script execution", "FAIL", str(e))
        raise

    finally:
        await cleanup_session(session)
        return print_summary()


if __name__ == "__main__":
    exit_code = iterm2.run_until_complete(main)
    exit(exit_code if exit_code else 0)
```

## Simple Automation Template (No Tests)

For scripts that perform automation without testing:

```python
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
<Script Name>: <Brief description>

Purpose:
    <What this script does>

Usage:
    uv run <script_name>.py
"""

import iterm2
import asyncio


async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window

    if not window:
        print("No active window found")
        return

    tab = await window.async_create_tab()
    session = tab.current_session

    try:
        # === AUTOMATION LOGIC ===
        await session.async_send_text("<command>\n")
        await asyncio.sleep(1.0)

        # ... additional logic ...

        print("Automation complete")

    except Exception as e:
        print(f"ERROR: {e}")
        raise

    finally:
        # Cleanup if needed
        pass


if __name__ == "__main__":
    iterm2.run_until_complete(main)
```

## Layout Template (Multi-Pane)

```python
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
<Layout Name>: Create a <N>-pane development layout

Panes:
    - Top Left: <Purpose>
    - Top Right: <Purpose>
    - Bottom Left: <Purpose>
    - Bottom Right: <Purpose>

Usage:
    uv run layout_<name>.py
"""

import iterm2
import asyncio


async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window

    if not window:
        print("No active window found")
        return

    # Create a new tab for the layout
    tab = await window.async_create_tab()

    # Top Left
    session_tl = tab.current_session
    await session_tl.async_set_name("<Name>")
    await session_tl.async_send_text("<command>\n")

    # Top Right (vertical split from top left)
    session_tr = await session_tl.async_split_pane(vertical=True)
    if session_tr:
        await session_tr.async_set_name("<Name>")
        await session_tr.async_send_text("<command>\n")

        # Bottom Right (horizontal split from top right)
        session_br = await session_tr.async_split_pane(vertical=False)
        if session_br:
            await session_br.async_set_name("<Name>")
            await session_br.async_send_text("<command>\n")

    # Bottom Left (horizontal split from top left)
    session_bl = await session_tl.async_split_pane(vertical=False)
    if session_bl:
        await session_bl.async_set_name("<Name>")
        await session_bl.async_send_text("<command>\n")

    print("Layout created successfully")


if __name__ == "__main__":
    iterm2.run_until_complete(main)
```
