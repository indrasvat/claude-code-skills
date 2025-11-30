# /// script
# requires-python = ">=3.13"
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
Corresponds to Example 5 in SKILL.md.

Usage:
    uv run 05-screen-monitor.py
"""

import iterm2
import asyncio

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window

    if window is not None:
        tab = await window.async_create_tab()
        session = tab.current_session

        # Start a process that outputs continually (e.g., ping)
        print("Starting ping...")
        await session.async_send_text("ping 127.0.0.1\n")

        # Use ScreenStreamer to monitor updates
        print("Monitoring screen (capturing 5 updates)...")
        async with session.get_screen_streamer() as streamer:
            for i in range(5):
                # Blocks until the screen changes
                screen_contents = await streamer.async_get()

                print(f"\n--- Screen Update {i+1} ---")
                # Print the non-empty lines
                for j in range(screen_contents.number_of_lines):
                    line = screen_contents.line(j).string
                    if line.strip():
                        print(f"Line {j}: {line}")

        # Stop the process
        await session.async_send_text("\x03") # Ctrl+C
        print("\nStopped process.")

    else:
        print("No active window found")

if __name__ == "__main__":
    iterm2.run_until_complete(main)
