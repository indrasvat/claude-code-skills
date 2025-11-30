# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 8: Visual Status (Badges)

Use badges to indicate the status of a long-running task (e.g., "Building",
"Testing", "Success"). Since the API doesn't have a direct helper, use the iTerm2
escape sequence `OSC 1337`.
Corresponds to Example 8 in SKILL.md.

Usage:
    uv run 08-badge-control.py
"""

import iterm2
import asyncio
import base64

async def set_badge(session, text):
    """Set the badge text for a session using iTerm2 escape sequences."""
    # OSC 1337 ; SetBadgeFormat=Base64 ST
    data = base64.b64encode(text.encode('utf-8')).decode('utf-8')
    cmd = f"\x1b]1337;SetBadgeFormat={data}\x07"
    await session.async_send_text(cmd)

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window

    if window is not None:
        tab = await window.async_create_tab()
        session = tab.current_session

        # Demonstrate badge updates
        await set_badge(session, "Compiling...")
        print("Set badge to 'Compiling...'")
        await asyncio.sleep(2)

        await set_badge(session, "Testing...")
        print("Set badge to 'Testing...'")
        await asyncio.sleep(2)

        await set_badge(session, "✓ Success")
        print("Set badge to '✓ Success'")
        await asyncio.sleep(2)

        # Clear badge
        await set_badge(session, "")
        print("Cleared badge")

    else:
        print("No active window found")

if __name__ == "__main__":
    iterm2.run_until_complete(main)
