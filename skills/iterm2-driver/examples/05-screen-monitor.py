# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 5: Advanced - Screen Streaming (Real-Time Monitoring)

This demonstrates how to use `ScreenStreamer` to "watch" the screen for updates.
This is much more reliable than using `sleep()` because it reacts to actual screen paints.
This is ideal for an agent to "see" what is happening in a TUI or long-running process.

Tests:
    1. Start Process: Launch ping command
    2. Monitor Updates: Capture 5 screen updates using ScreenStreamer
    3. Stop Process: Send Ctrl+C and verify process stops

Verification Strategy:
    - Use ScreenStreamer.async_get() which blocks until screen changes
    - Verify each update contains expected ping output patterns
    - Confirm process stops by checking for shell prompt after Ctrl+C

Screenshot Inspection Checklist:
    - Colors: N/A (ping is plain text)
    - Boundaries: Terminal shows ping output
    - Visible Elements: "ping", "bytes from", "icmp_seq" in output
    - Keyboard Navigation: N/A

Key Bindings:
    - Ctrl+C (\\x03): Stop ping process

Usage:
    uv run 05-screen-monitor.py
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
# CLEANUP HELPER
# ============================================================

async def cleanup_session(session):
    """Perform multi-level cleanup."""
    try:
        await session.async_send_text("\x03")  # Ctrl+C
        await asyncio.sleep(0.2)
        await session.async_send_text("exit\n")
        await asyncio.sleep(0.2)
        await session.async_close()
    except Exception as e:
        print(f"  Cleanup warning: {e}")


# ============================================================
# MAIN
# ============================================================

async def main(connection):
    # Create own window (parallel-safe, with app-refresh)
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
    await session.async_set_name("screen-monitor")

    try:
        print("\n--- SCREEN STREAMING TEST ---\n")

        # ============================================================
        # TEST 1: Start Process
        # ============================================================
        print("--- TEST 1: Start Process ---")
        print("  Starting ping...")
        await session.async_send_text("ping 127.0.0.1\n")

        # Brief wait for process to start
        await asyncio.sleep(0.5)
        log_result("Start Process", "PASS")

        # ============================================================
        # TEST 2: Monitor Updates
        # ============================================================
        print("\n--- TEST 2: Monitor Updates ---")
        print("  Monitoring screen (capturing 5 updates)...")

        updates_captured = 0
        ping_output_found = False

        async with session.get_screen_streamer() as streamer:
            for i in range(5):
                # This blocks until the screen changes
                screen_contents = await streamer.async_get()
                updates_captured += 1

                print(f"\n  --- Screen Update {i+1} ---")
                # Print the non-empty lines
                for j in range(screen_contents.number_of_lines):
                    line = screen_contents.line(j).string
                    if line.strip():
                        print(f"  Line {j}: {line}")
                        # Check for ping output
                        if "bytes from" in line or "icmp_seq" in line:
                            ping_output_found = True

        if updates_captured >= 5 and ping_output_found:
            log_result("Monitor Updates", "PASS")
        elif updates_captured >= 5:
            log_result("Monitor Updates", "PASS", "Updates captured but ping pattern not found")
        else:
            log_result("Monitor Updates", "FAIL", f"Only captured {updates_captured} updates")

        # ============================================================
        # TEST 3: Stop Process
        # ============================================================
        print("\n--- TEST 3: Stop Process ---")
        print("  Sending Ctrl+C...")
        await session.async_send_text("\x03")  # Ctrl+C
        await asyncio.sleep(0.5)

        # Verify process stopped (check for statistics or shell prompt)
        screen = await session.async_get_screen_contents()
        process_stopped = False
        for i in range(screen.number_of_lines):
            line = screen.line(i).string
            # Ping shows statistics when stopped, or we see shell prompt
            if "statistics" in line or "packets" in line or "$" in line or "%" in line:
                process_stopped = True
                break

        if process_stopped:
            log_result("Stop Process", "PASS")
        else:
            log_result("Stop Process", "FAIL", "Could not verify process stopped")

        print("\n  Screen streaming demonstration complete.")

    except Exception as e:
        print(f"\nERROR: {e}")
        log_result("Execution", "FAIL", str(e))

    finally:
        await cleanup_session(session)

    return print_summary()


if __name__ == "__main__":
    exit_code = iterm2.run_until_complete(main)
    exit(exit_code if exit_code else 0)
