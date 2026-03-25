# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 9: Special Keys Reference

When driving TUIs (like htop, mc, or vim), you often need to send special keys.
This example demonstrates how to use special key codes. Uses safe window creation
(never current_terminal_window) with readiness probes.

Special Keys Reference:
    Enter:        \\r (Use this instead of \\n)
    Esc:          \\x1b
    Up Arrow:     \\x1b[A
    Down Arrow:   \\x1b[B
    Right Arrow:  \\x1b[C
    Left Arrow:   \\x1b[D
    Ctrl+C:       \\x03
    Ctrl+X:       \\x18
    Ctrl+Z:       \\x1a
    F1:           \\x1bOP

Usage:
    uv run 09-special-keys.py
"""

import iterm2
import asyncio


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
    await session.async_set_name("special-keys")
    created_sessions = [session]

    try:
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
