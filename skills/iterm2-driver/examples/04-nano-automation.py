# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 4: Advanced - TUI Automation (Nano Editor)

This script demonstrates how to drive a full-screen terminal application (Nano).
It launches the editor, types text, and handles the save-and-quit keystroke sequence
(`Ctrl+X`, `y`, `Enter`).
Corresponds to Example 4 in SKILL.md.

Usage:
    uv run 04-nano-automation.py
"""

import iterm2
import asyncio

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window

    if window is not None:
        tab = await window.async_create_tab()
        session = tab.current_session

        # 1. Launch Nano with a specific file path
        # Use absolute path to be sure where the file ends up
        filepath = "/tmp/ai_generated_note.txt"
        await session.async_send_text(f"nano {filepath}\n")
        await asyncio.sleep(1.0) # Wait for TUI to load

        # 2. Type content
        await session.async_send_text("Hello from the iTerm2 API!\n")
        await session.async_send_text("This file was created by an AI agent.")
        await asyncio.sleep(0.5)

        # 3. Save and Quit Sequence
        # Ctrl+X is \x18
        await session.async_send_text("\x18")
        await asyncio.sleep(0.5)

        # Prompt: "Save modified buffer?" -> Send 'y'
        await session.async_send_text("y")
        await asyncio.sleep(0.5)

        # Prompt: "File Name to Write: ..." -> Send Enter (\r)
        # IMPORTANT: Use \r for Enter in TUI interactions often works better than \n
        await session.async_send_text("\r")
        await asyncio.sleep(0.5)

        print(f"File saved to {filepath}")

    else:
        print("No active window found")

if __name__ == "__main__":
    iterm2.run_until_complete(main)
