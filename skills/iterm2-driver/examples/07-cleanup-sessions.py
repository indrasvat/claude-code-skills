# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 7: Global Cleanup (Close All Tabs Except First)

This is useful for resetting the environment after a heavy testing session.
When running multiple automated tasks, iTerm2 tabs can pile up. You should generally
clean up tabs created during a session unless the user explicitly wants them left
open for inspection.
Corresponds to Example 7 in SKILL.md.

Usage:
    uv run 07-cleanup-sessions.py
"""

import iterm2
import asyncio

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window
    if not window:
        return

    tabs = window.tabs
    if len(tabs) <= 1:
        print("Cleanup not needed.")
        return

    print(f"Closing {len(tabs) - 1} extra tabs...")

    # Iterate backwards to avoid index shifting issues
    # Keep index 0 (the first tab) open
    for i in range(len(tabs) - 1, 0, -1):
        tab = tabs[i]
        # Close all sessions in the tab to ensure it closes
        for session in tab.sessions:
            await session.async_close()
        await asyncio.sleep(0.1) # Brief pause for UI stability

    print("Cleanup complete.")

if __name__ == "__main__":
    iterm2.run_until_complete(main)
