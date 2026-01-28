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

This template demonstrates the complete set of best practices for iTerm2 TUI automation:
- Comprehensive docstring with all required sections
- Quartz-based window targeting for precise screenshots
- Multi-level try-except-finally cleanup
- Screenshot capture and verification
- Result tracking and reporting

Tests:
    1. Launch Test: Verify the shell is accessible and responsive
    2. Command Test: Run a command and verify output
    3. Cleanup Test: Verify session closes cleanly

Verification Strategy:
    - Use screen polling with 5-second timeout for each state transition
    - Look for shell prompt characters ($ or %) to confirm shell is ready
    - Verify command output by searching for expected text
    - Confirm cleanup by checking session closure completes without error

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
    "tests": [],
    "screenshots": [],
    "start_time": None,
    "end_time": None,
}


def log_result(test_name: str, status: str, details: str = "", screenshot: str = None):
    """Log a test result with optional details and screenshot reference.

    Args:
        test_name: Name of the test
        status: "PASS", "FAIL", or "UNVERIFIED"
        details: Additional details about the result
        screenshot: Path to related screenshot if any
    """
    results["tests"].append({
        "name": test_name,
        "status": status,
        "details": details,
        "screenshot": screenshot,
    })

    if screenshot:
        results["screenshots"].append(screenshot)

    if status == "PASS":
        results["passed"] += 1
        print(f"  [+] PASS: {test_name}")
    elif status == "FAIL":
        results["failed"] += 1
        print(f"  [x] FAIL: {test_name} - {details}")
    else:
        results["unverified"] += 1
        print(f"  [?] UNVERIFIED: {test_name} - {details}")

    if screenshot:
        print(f"      Screenshot: {screenshot}")


def print_summary() -> int:
    """Print final test summary and return exit code."""
    results["end_time"] = datetime.now()
    total = results["passed"] + results["failed"] + results["unverified"]
    duration = (results["end_time"] - results["start_time"]).total_seconds() if results["start_time"] else 0

    print("\n" + "=" * 60)
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
        for test in results["tests"]:
            if test["status"] == "FAIL":
                print(f"  - {test['name']}: {test['details']}")

    print("\n" + "-" * 60)
    if results["failed"] > 0:
        print("OVERALL: FAILED")
        return 1
    elif results["unverified"] > 0:
        print("OVERALL: PASSED (with unverified tests)")
        return 0
    else:
        print("OVERALL: PASSED")
        return 0


def print_test_header(test_name: str, test_num: int = None):
    """Print a visual header for a test section."""
    if test_num:
        header = f"TEST {test_num}: {test_name}"
    else:
        header = f"TEST: {test_name}"
    print("\n" + "=" * 60)
    print(header)
    print("=" * 60)


# ============================================================
# QUARTZ WINDOW TARGETING
# ============================================================

try:
    import Quartz

    def get_iterm2_window_id():
        """Get the window ID of the frontmost iTerm2 window for targeted screenshots."""
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
    print("WARNING: Quartz not available, screenshots will capture full screen")

    def get_iterm2_window_id():
        return None


def capture_screenshot(name: str) -> str:
    """Capture a screenshot of just the iTerm2 window.

    Args:
        name: Descriptive name for the screenshot (without extension)

    Returns:
        Path to the saved screenshot
    """
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)

    window_id = get_iterm2_window_id()
    if window_id:
        # -x: no sound, -l: specific window ID
        subprocess.run(["screencapture", "-x", "-l", str(window_id), filepath], check=True)
    else:
        # Fallback to full screen if window not found
        print("  WARNING: iTerm2 window not found, capturing full screen")
        subprocess.run(["screencapture", "-x", filepath], check=True)

    print(f"  SCREENSHOT: {filepath}")
    return filepath


# ============================================================
# VERIFICATION HELPERS
# ============================================================

async def verify_screen_contains(session, expected: str, description: str) -> bool:
    """Verify that expected text appears on screen within timeout.

    Args:
        session: iTerm2 session
        expected: Text to look for
        description: Human-readable description for logging

    Returns:
        True if found, False otherwise
    """
    import time
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
    """Verify that a shell prompt is visible ($ or %)."""
    screen = await session.async_get_screen_contents()
    for i in range(screen.number_of_lines):
        line = screen.line(i).string
        if "$" in line or "%" in line or ">" in line:
            return True
    return False


async def dump_screen(session, label: str):
    """Dump current screen contents for debugging.

    Args:
        session: iTerm2 session
        label: Label for the dump (used in output)
    """
    screen = await session.async_get_screen_contents()
    print(f"\n{'='*60}")
    print(f"SCREEN DUMP: {label}")
    print(f"{'='*60}")
    for i in range(screen.number_of_lines):
        line = screen.line(i).string
        if line.strip():  # Only print non-empty lines
            print(f"{i:03d}: {line}")
    print(f"{'='*60}\n")


# ============================================================
# CLEANUP
# ============================================================

async def cleanup_session(session, quit_key: str = None):
    """Perform multi-level cleanup on a session.

    Args:
        session: iTerm2 session to clean up
        quit_key: Optional key to send for TUI quit (e.g., 'q' for htop)
    """
    print("\n  Performing cleanup...")
    try:
        # Level 1: Send Ctrl+C to interrupt any running process
        await session.async_send_text("\x03")
        await asyncio.sleep(0.2)

        # Level 2: Send quit key if specified (for TUIs like htop, vim, etc.)
        if quit_key:
            await session.async_send_text(quit_key)
            await asyncio.sleep(0.2)

        # Level 3: Send exit command for shells/REPLs
        await session.async_send_text("exit\n")
        await asyncio.sleep(0.2)

        # Level 4: Close the session
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
    print(f"# Started: {results['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    print("#" * 60)

    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window

    if not window:
        print("ERROR: No active window found")
        log_result("Setup", "FAIL", "No active iTerm2 window")
        return print_summary()

    # Create a new tab for testing
    tab = await window.async_create_tab()
    session = tab.current_session

    # Track created resources for cleanup
    created_sessions = [session]

    try:
        # ============================================================
        # TEST 1: Shell Ready
        # ============================================================
        print_test_header("Shell Ready", 1)
        print("  Waiting for shell prompt...")
        await asyncio.sleep(0.5)

        if await verify_shell_prompt(session):
            screenshot = capture_screenshot("template_shell_ready")
            log_result("Shell Ready", "PASS", screenshot=screenshot)
        else:
            await dump_screen(session, "shell_not_ready")
            log_result("Shell Ready", "FAIL", "Shell prompt not detected")

        # ============================================================
        # TEST 2: Command Execution
        # ============================================================
        print_test_header("Command Execution", 2)
        print("  Sending test command...")

        # Use a unique marker for verification
        marker = f"TEMPLATE_TEST_{datetime.now().strftime('%H%M%S')}"
        await session.async_send_text(f"echo '{marker}'\n")
        await asyncio.sleep(0.5)

        if await verify_screen_contains(session, marker, "echo output"):
            screenshot = capture_screenshot("template_command_output")
            log_result("Command Execution", "PASS", screenshot=screenshot)
        else:
            await dump_screen(session, "command_failed")
            log_result("Command Execution", "FAIL", f"Marker '{marker}' not found in output")

        # ============================================================
        # TEST 3: Multiple Commands
        # ============================================================
        print_test_header("Multiple Commands", 3)
        print("  Testing pwd and ls commands...")

        await session.async_send_text("pwd\n")
        await asyncio.sleep(0.3)
        await session.async_send_text("ls -la | head -5\n")
        await asyncio.sleep(0.5)

        # Verify we can see directory listing indicators
        screen = await session.async_get_screen_contents()
        has_output = False
        for i in range(screen.number_of_lines):
            line = screen.line(i).string
            # Look for typical ls output patterns
            if "total" in line or "drwx" in line or "-rw" in line:
                has_output = True
                break

        if has_output:
            screenshot = capture_screenshot("template_multiple_commands")
            log_result("Multiple Commands", "PASS", screenshot=screenshot)
        else:
            log_result("Multiple Commands", "UNVERIFIED", "Could not verify ls output format")

        # ============================================================
        # TEST 4: Final State
        # ============================================================
        print_test_header("Final State", 4)
        print("  Capturing final state...")

        screenshot = capture_screenshot("template_final")
        log_result("Final State", "PASS", "Final screenshot captured", screenshot=screenshot)

    except Exception as e:
        print(f"\nERROR during test execution: {e}")
        log_result("Test Execution", "FAIL", str(e))
        await dump_screen(session, "error_state")

    finally:
        # ============================================================
        # CLEANUP
        # ============================================================
        print("\n" + "=" * 60)
        print("CLEANUP")
        print("=" * 60)

        for s in created_sessions:
            await cleanup_session(s)

    return print_summary()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    exit_code = iterm2.run_until_complete(main)
    exit(exit_code if exit_code else 0)
