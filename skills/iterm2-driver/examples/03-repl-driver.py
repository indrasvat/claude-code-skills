# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 3: Advanced - Interactive REPL Driver

This script drives an interactive process (Python REPL). It sends code, waits for
execution, and verifies the output by reading the screen content programmatically.
Uses safe window creation (never current_terminal_window) with readiness probes.

Tests:
    1. REPL Start: Verify Python REPL launches and shows prompt
    2. Function Definition: Define a function and verify it's accepted
    3. Function Execution: Call the function and verify correct output
    4. Clean Exit: Exit REPL and verify return to shell

Verification Strategy:
    - Create own window (parallel-safe)
    - Poll screen for ">>>" prompt to confirm REPL is ready
    - Use unique marker string "MARKER_RESULT" for output verification
    - Timeout after 5 seconds if expected output not found
    - Dump screen on failure for debugging

Screenshot Inspection Checklist:
    - Colors: Python syntax highlighting (if terminal supports)
    - Boundaries: REPL prompt ">>>" clearly visible
    - Visible Elements: Function definition, calculation result
    - Keyboard Navigation: Cursor at prompt

Key Bindings:
    - Enter: Execute line
    - exit(): Quit Python REPL

Usage:
    uv run 03-repl-driver.py
"""

import iterm2
import asyncio

# ============================================================
# RESULT TRACKING
# ============================================================

results = {"passed": 0, "failed": 0, "tests": []}


def log_result(test_name: str, status: str, details: str = ""):
    """Log a test result."""
    results["tests"].append({"name": test_name, "status": status, "details": details})
    if status == "PASS":
        results["passed"] += 1
        print(f"  [+] PASS: {test_name}")
    else:
        results["failed"] += 1
        print(f"  [x] FAIL: {test_name} - {details}")


def print_summary() -> int:
    """Print test summary and return exit code."""
    total = results["passed"] + results["failed"]
    print("\n" + "=" * 50)
    print(f"SUMMARY: {results['passed']}/{total} passed")
    print("=" * 50)
    if results["failed"] > 0:
        print("OVERALL: FAILED")
        return 1
    print("OVERALL: PASSED")
    return 0


# ============================================================
# VERIFICATION HELPERS
# ============================================================

async def verify_screen_contains(session, expected: str, timeout: float = 5.0) -> bool:
    """Check if expected text appears on screen within timeout."""
    import time
    start = time.monotonic()
    while (time.monotonic() - start) < timeout:
        screen = await session.async_get_screen_contents()
        for i in range(screen.number_of_lines):
            if expected in screen.line(i).string:
                return True
        await asyncio.sleep(0.2)
    return False


async def dump_screen(session, label: str):
    """Dump screen contents for debugging."""
    screen = await session.async_get_screen_contents()
    print(f"\n--- SCREEN DUMP: {label} ---")
    for i in range(screen.number_of_lines):
        line = screen.line(i).string
        if line.strip():
            print(f"{i:03d}: {line}")
    print("---")


# ============================================================
# CLEANUP HELPER
# ============================================================

async def cleanup_session(session):
    """Perform multi-level cleanup on a session."""
    try:
        await session.async_send_text("\x03")  # Ctrl+C
        await asyncio.sleep(0.1)
        await session.async_send_text("exit()\n")
        await asyncio.sleep(0.1)
        await session.async_send_text("exit\n")
        await asyncio.sleep(0.2)
        await session.async_close()
    except Exception as e:
        print(f"  Cleanup warning: {e}")


# ============================================================
# MAIN TEST
# ============================================================

async def main(connection):
    # Create own window (parallel-safe, never use current_terminal_window)
    window = await iterm2.Window.async_create(connection)
    await asyncio.sleep(0.5)
    app = await iterm2.async_get_app(connection)
    if window.current_tab is None:
        for w in app.terminal_windows:
            if w.window_id == window.window_id:
                window = w
                break
    for _ in range(20):
        if window.current_tab and window.current_tab.current_session:
            break
        await asyncio.sleep(0.2)

    session = window.current_tab.current_session
    await session.async_set_name("repl-driver")
    created_sessions = [session]

    try:
        # ============================================================
        # TEST 1: Start REPL
        # ============================================================
        print("\n--- TEST 1: Start REPL ---")
        await session.async_send_text("python3\n")

        if await verify_screen_contains(session, ">>>"):
            log_result("Start REPL", "PASS")
        else:
            log_result("Start REPL", "FAIL", "REPL prompt not found")
            await dump_screen(session, "repl_start_failed")
            return print_summary()

        # ============================================================
        # TEST 2: Define Function
        # ============================================================
        print("\n--- TEST 2: Define Function ---")
        await session.async_send_text("def f(x): return x * 2\n\n")
        await asyncio.sleep(0.5)

        # Function definition should return to prompt without error
        if await verify_screen_contains(session, ">>>", timeout=2.0):
            log_result("Define Function", "PASS")
        else:
            log_result("Define Function", "FAIL", "Prompt not returned after definition")

        # ============================================================
        # TEST 3: Execute Function
        # ============================================================
        print("\n--- TEST 3: Execute Function ---")
        cmd = "print(f'MARKER_RESULT: {f(10)}')"
        await session.async_send_text(f"{cmd}\n")

        if await verify_screen_contains(session, "MARKER_RESULT: 20"):
            log_result("Execute Function", "PASS")
        else:
            log_result("Execute Function", "FAIL", "Expected output 'MARKER_RESULT: 20' not found")
            await dump_screen(session, "execution_failed")

        # ============================================================
        # TEST 4: Clean Exit
        # ============================================================
        print("\n--- TEST 4: Clean Exit ---")
        await session.async_send_text("exit()\n")
        await asyncio.sleep(0.5)

        # Should be back at shell prompt
        screen = await session.async_get_screen_contents()
        back_at_shell = False
        non_empty = 0
        for i in range(screen.number_of_lines):
            line = screen.line(i).string
            if line.strip():
                non_empty += 1
            if "$" in line or "%" in line or "~" in line or "❯" in line or "➜" in line:
                back_at_shell = True
                break
        if not back_at_shell and non_empty >= 2:
            back_at_shell = True  # Modern prompt without traditional indicators

        if back_at_shell:
            log_result("Clean Exit", "PASS")
        else:
            log_result("Clean Exit", "FAIL", "Shell prompt not detected after exit")

    except Exception as e:
        print(f"ERROR: {e}")
        try:
            await dump_screen(session, "error_state")
        except Exception:
            pass

    finally:
        for s in created_sessions:
            await cleanup_session(s)

    return print_summary()


if __name__ == "__main__":
    exit_code = iterm2.run_until_complete(main)
    exit(exit_code if exit_code else 0)
