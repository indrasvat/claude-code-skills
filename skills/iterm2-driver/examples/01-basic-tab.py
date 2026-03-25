# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 1: Basic — Create a window, run a command, verify output

The simplest possible iTerm2 automation: create a new window, send a command,
and verify the output appeared. Uses safe window creation (never current_terminal_window).

Tests:
    1. Window Creation: Create a new window with readiness probe
    2. Command Execution: Run `ls -la` and verify output
    3. Cleanup: Close the session cleanly

Verification Strategy:
    - Create own window (parallel-safe)
    - Send `ls -la` and check for typical output patterns (total, drwx, -rw)
    - Dump screen on failure for debugging

Usage:
    uv run 01-basic-tab.py
"""

import asyncio
import time

import iterm2


async def main(connection):
    # Create a new window (never use app.current_terminal_window)
    window = await iterm2.Window.async_create(connection)
    await asyncio.sleep(0.5)  # Let window initialize

    # Readiness probe — refresh app state if needed
    app = await iterm2.async_get_app(connection)
    if window.current_tab is None:
        # Window object may be stale — find it via app
        for w in app.terminal_windows:
            if w.window_id == window.window_id:
                window = w
                break

    for _ in range(20):
        if window.current_tab and window.current_tab.current_session:
            break
        await asyncio.sleep(0.2)

    session = window.current_tab.current_session
    await session.async_set_name("basic-test")

    try:
        # Run a command
        await session.async_send_text("ls -la\n")
        print("  Created window, sent 'ls -la'")

        # Verify output appeared
        start = time.monotonic()
        found = False
        while time.monotonic() - start < 5.0:
            screen = await session.async_get_screen_contents()
            for i in range(screen.number_of_lines):
                line = screen.line(i).string
                if "total" in line or "drwx" in line or "-rw" in line:
                    found = True
                    break
            if found:
                break
            await asyncio.sleep(0.2)

        if found:
            print("  [+] PASS: ls output verified")
        else:
            print("  [x] FAIL: ls output not found, dumping screen:")
            screen = await session.async_get_screen_contents()
            for i in range(screen.number_of_lines):
                line = screen.line(i).string
                if line.strip():
                    print(f"  {i:03d}: {line}")

    finally:
        await session.async_send_text("exit\n")
        await asyncio.sleep(0.2)
        try:
            await session.async_close()
        except Exception:
            pass
        print("  Cleanup complete")


if __name__ == "__main__":
    iterm2.run_until_complete(main)
