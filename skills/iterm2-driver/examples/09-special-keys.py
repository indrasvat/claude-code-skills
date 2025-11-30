# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 9: Special Keys Reference

When driving TUIs (like htop, mc, or vim), you often need to send special keys.
This example demonstrates how to use special key codes.
Corresponds to Example 9 in SKILL.md.

Special Keys Reference:
    Enter:        \r (Use this instead of \n)
    Esc:          \x1b
    Up Arrow:     \x1b[A
    Down Arrow:   \x1b[B
    Right Arrow:  \x1b[C
    Left Arrow:   \x1b[D
    Ctrl+C:       \x03
    Ctrl+X:       \x18
    Ctrl+Z:       \x1a
    F1:           \x1bOP

Usage:
    uv run 09-special-keys.py
"""

import iterm2
import asyncio

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window

    if window is not None:
        tab = await window.async_create_tab()
        session = tab.current_session

        # Demonstrate special keys by navigating in bash history
        await session.async_send_text("# First command\n")
        await asyncio.sleep(0.3)
        await session.async_send_text("# Second command\n")
        await asyncio.sleep(0.3)
        await session.async_send_text("# Third command\n")
        await asyncio.sleep(0.3)

        print("Navigating command history with arrow keys...")

        # Up arrow to go back in history
        await session.async_send_text("\x1b[A")
        await asyncio.sleep(0.5)

        # Up arrow again
        await session.async_send_text("\x1b[A")
        await asyncio.sleep(0.5)

        # Down arrow to go forward
        await session.async_send_text("\x1b[B")
        await asyncio.sleep(0.5)

        # Clear the line with Ctrl+C
        await session.async_send_text("\x03")

        print("Special keys demo complete")

    else:
        print("No active window found")

if __name__ == "__main__":
    iterm2.run_until_complete(main)
