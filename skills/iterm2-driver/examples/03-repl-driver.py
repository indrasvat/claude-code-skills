# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 3: Advanced - Interactive REPL Driver

This script drives an interactive process (Python REPL). It sends code, waits for
execution, and verifies the output by reading the screen content programmatically.
This pattern is essential for testing TUIs or interactive CLIs.
Corresponds to Example 3 in SKILL.md.

Usage:
    uv run 03-repl-driver.py
"""

import iterm2
import asyncio

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window

    if window is not None:
        # Create a dedicated tab for this test
        tab = await window.async_create_tab()
        session = tab.current_session

        # 1. Start the interactive process (Python REPL)
        print("Starting REPL...")
        await session.async_send_text("python3\n")
        await asyncio.sleep(1) # Wait for prompt

        # 2. Define a function (send extra newline to ensure block closure)
        print("Defining function...")
        await session.async_send_text("def f(x): return x * 2\n\n")
        await asyncio.sleep(0.5)

        # 3. Send a calculation command
        print("Sending command...")
        # We print a unique marker string to look for
        cmd = "print(f'MARKER_RESULT: {f(10)}')"
        await session.async_send_text(f"{cmd}\n")

        # 4. Poll the screen until we see the result or timeout
        print("Waiting for result...")
        found = False
        for _ in range(10): # Try for 5 seconds (10 * 0.5s)
            await asyncio.sleep(0.5)
            screen_contents = await session.async_get_screen_contents()

            # Check all lines for our marker
            # Note: Use screen_contents.line(i).string to access text
            for i in range(screen_contents.number_of_lines):
                if "MARKER_RESULT: 20" in screen_contents.line(i).string:
                    found = True
                    break
            if found:
                break

        # 4. Report results
        if found:
            print("SUCCESS: Calculation verified correctly.")
        else:
            print("FAILURE: Could not find expected output on screen.")
            # Optional: Print screen dump for debugging
            # print("\n".join([l.string for l in screen_contents.lines]))

        # 5. Clean up (Exit REPL)
        await session.async_send_text("exit()\n")

    else:
        print("No active window found")

if __name__ == "__main__":
    iterm2.run_until_complete(main)
