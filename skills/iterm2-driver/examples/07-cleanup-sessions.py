# /// script
# requires-python = ">=3.14"
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

Uses safe window creation (never current_terminal_window) with readiness probes.
Creates a dedicated window, demonstrates tab creation and cleanup, then closes
the window itself.

Usage:
    uv run 07-cleanup-sessions.py
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
    await session.async_set_name("cleanup-demo")
    created_sessions = [session]

    try:
        # Create a few extra tabs to demonstrate cleanup
        print("Creating extra tabs for cleanup demonstration...")
        for _i in range(3):
            tab = await window.async_create_tab()
            created_sessions.append(tab.current_session)
            await asyncio.sleep(0.1)

        tabs = window.tabs
        print(f"Window now has {len(tabs)} tabs")

        if len(tabs) <= 1:
            print("Cleanup not needed.")
            return

        print(f"Closing {len(tabs) - 1} extra tabs...")

        # Iterate backwards to avoid index shifting issues
        # Keep index 0 (the first tab) open
        for i in range(len(tabs) - 1, 0, -1):
            tab = tabs[i]
            # Close all sessions in the tab to ensure it closes
            for s in tab.sessions:
                try:
                    await s.async_close()
                except Exception as e:
                    print(f"  Warning closing session: {e}")
            await asyncio.sleep(0.1)  # Brief pause for UI stability

        print("Cleanup complete.")

    except Exception as e:
        print(f"\nERROR: {e}")
        try:
            await dump_screen(session, "error_state")
        except Exception:
            pass

    finally:
        # Close remaining sessions (the first tab's session)
        for s in created_sessions:
            try:
                await s.async_send_text("exit\n")
                await asyncio.sleep(0.1)
                await s.async_close()
            except Exception:
                pass


if __name__ == "__main__":
    iterm2.run_until_complete(main)
