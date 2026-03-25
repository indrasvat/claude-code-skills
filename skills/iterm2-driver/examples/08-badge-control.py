# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 8: Visual Status (Badges)

Use badges to indicate the status of a long-running task (e.g., "Building",
"Testing", "Success"). Since the API doesn't have a direct helper, use the iTerm2
escape sequence `OSC 1337`. Uses safe window creation (never current_terminal_window)
with readiness probes.

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


async def dump_screen(session, label: str):
    """Dump screen contents for debugging."""
    try:
        screen = await session.async_get_screen_contents()
        print(f"\n--- SCREEN DUMP: {label} ---")
        for i in range(screen.number_of_lines):
            line = screen.line(i).string
            if line.strip():
                print(f"{i:03d}: {line}")
        print("---")
    except Exception:
        pass


async def cleanup_session(session):
    """Perform multi-level cleanup on a session."""
    try:
        await session.async_send_text("\x03")  # Ctrl+C
        await asyncio.sleep(0.1)
        await session.async_send_text("exit\n")
        await asyncio.sleep(0.2)
        await session.async_close()
    except Exception as e:
        print(f"  Cleanup warning: {e}")


async def main(connection):
    # Create own window (parallel-safe, never use current_terminal_window)
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
    await session.async_set_name("badge-control")
    created_sessions = [session]

    try:
        # Demonstrate badge updates
        await set_badge(session, "Compiling...")
        print("Set badge to 'Compiling...'")
        await asyncio.sleep(2)

        await set_badge(session, "Testing...")
        print("Set badge to 'Testing...'")
        await asyncio.sleep(2)

        await set_badge(session, "Success")
        print("Set badge to 'Success'")
        await asyncio.sleep(2)

        # Clear badge
        await set_badge(session, "")
        print("Cleared badge")

    except Exception as e:
        print(f"\nERROR: {e}")
        try:
            await dump_screen(session, "error_state")
        except Exception:
            pass

    finally:
        for s in created_sessions:
            await cleanup_session(s)


if __name__ == "__main__":
    iterm2.run_until_complete(main)
