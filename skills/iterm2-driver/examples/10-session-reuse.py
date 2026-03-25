# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 10: Session Reuse (Get-or-Create Pattern)

Avoid clutter by reusing a named session if it exists. This pattern is useful
for long-running services or repeated tasks where you want to reconnect to the
same session rather than creating duplicates. Uses safe window creation
(never current_terminal_window) with readiness probes.

Usage:
    uv run 10-session-reuse.py
"""

import asyncio

import iterm2


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
    app = await iterm2.async_get_app(connection)

    # Define target name
    target_name = "MyWorker"
    target_session = None
    created_sessions = []

    # 1. Search existing sessions across all windows
    for w in app.terminal_windows:
        for tab in w.tabs:
            for session in tab.sessions:
                if session.name == target_name:
                    target_session = session
                    print(f"Found existing session: {target_name}")
                    break
            if target_session:
                break
        if target_session:
            break

    # 2. Create if not found — use safe window creation
    if not target_session:
        window = await iterm2.Window.async_create(connection)

        # Readiness probe
        for _ in range(20):
            if window and window.current_tab and window.current_tab.current_session:
                break
            await asyncio.sleep(0.2)

        target_session = window.current_tab.current_session
        await target_session.async_set_name(target_name)
        created_sessions.append(target_session)
        print(f"Created new session: {target_name}")

    try:
        if target_session:
            await target_session.async_activate()
            await target_session.async_send_text("echo 'Ready'\n")
            print(f"Activated and sent command to: {target_name}")
        else:
            print("Failed to get or create session")

    except Exception as e:
        print(f"\nERROR: {e}")
        try:
            if target_session:
                await dump_screen(target_session, "error_state")
        except Exception:
            pass

    finally:
        for s in created_sessions:
            await cleanup_session(s)


if __name__ == "__main__":
    iterm2.run_until_complete(main)
