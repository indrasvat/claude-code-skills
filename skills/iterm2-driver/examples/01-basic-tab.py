# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 1: Basic - Open a New Tab and Run a Command

This script gets the current window, creates a new tab, and runs `ls -la`.
Corresponds to Example 1 in SKILL.md.

Usage:
    uv run 01-basic-tab.py
"""

import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window

    if window is not None:
        # Create a new tab
        tab = await window.async_create_tab()
        session = tab.current_session

        # Run a command
        await session.async_send_text("ls -la\n")
        print(f"Created tab {tab.tab_id} and sent command")
    else:
        print("No active window found")

if __name__ == "__main__":
    iterm2.run_until_complete(main)
