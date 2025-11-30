# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 10: Session Reuse (Get-or-Create Pattern)

Avoid clutter by reusing a named session if it exists. This pattern is useful
for long-running services or repeated tasks where you want to reconnect to the
same session rather than creating duplicates.
Corresponds to Example 10 in SKILL.md.

Usage:
    uv run 10-session-reuse.py
"""

import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)

    # Define target name
    target_name = "MyWorker"
    target_session = None

    # 1. Search existing
    if app.current_terminal_window:
        for tab in app.current_terminal_window.tabs:
            for session in tab.sessions:
                if session.name == target_name:
                    target_session = session
                    print(f"Found existing session: {target_name}")
                    break
            if target_session:
                break

    # 2. Create if not found
    if not target_session:
        if app.current_terminal_window:
            tab = await app.current_terminal_window.async_create_tab()
            target_session = tab.current_session
            await target_session.async_set_name(target_name)
            print(f"Created new session: {target_name}")

    if target_session:
        await target_session.async_activate()
        await target_session.async_send_text("echo 'Ready'\n")
        print(f"Activated and sent command to: {target_name}")
    else:
        print("Failed to get or create session")

if __name__ == "__main__":
    iterm2.run_until_complete(main)
