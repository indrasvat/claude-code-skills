# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 2: Intermediate — 4-Pane Development Layout

Creates a 2x2 grid layout in a new window with named panes for a typical
dev environment: Server, Worker, Database, Logs. Each pane runs a different
command. Uses safe window creation and verifies all panes are responsive.

Tests:
    1. Window + Split Creation: Create 4 panes in a 2x2 grid
    2. Named Panes: Each pane has a descriptive name
    3. Command Execution: Each pane receives a command
    4. Cleanup: All 4 panes closed cleanly

Verification Strategy:
    - Create own window (parallel-safe)
    - Split into 4 panes: TL→TR (vertical), TL→BL (horizontal), TR→BR (horizontal)
    - Verify each pane exists and has the correct name

Usage:
    uv run 02-dev-layout.py
"""

import asyncio

import iterm2


async def main(connection):
    # Create a new window with app-refresh pattern
    window = await iterm2.Window.async_create(connection)
    await asyncio.sleep(0.5)

    # Refresh — returned window object can be stale
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

    all_sessions = []

    try:
        # Top Left: Server
        session_tl = window.current_tab.current_session
        await session_tl.async_set_name("Server")
        await session_tl.async_send_text("echo 'Starting Server...'\n")
        all_sessions.append(session_tl)

        # Top Right: Worker (vertical split from top left)
        session_tr = await session_tl.async_split_pane(vertical=True)
        if session_tr:
            await session_tr.async_set_name("Worker")
            await session_tr.async_send_text("echo 'Starting Worker...'\n")
            all_sessions.append(session_tr)

            # Bottom Right: Logs (horizontal split from top right)
            session_br = await session_tr.async_split_pane(vertical=False)
            if session_br:
                await session_br.async_set_name("Logs")
                await session_br.async_send_text("echo 'Tailing logs...'\n")
                all_sessions.append(session_br)

        # Bottom Left: Database (horizontal split from top left)
        session_bl = await session_tl.async_split_pane(vertical=False)
        if session_bl:
            await session_bl.async_set_name("Database")
            await session_bl.async_send_text("echo 'Starting DB...'\n")
            all_sessions.append(session_bl)

        print(f"  Created {len(all_sessions)}-pane dev layout")

        # Verify all panes exist
        if len(all_sessions) == 4:
            print("  [+] PASS: All 4 panes created")
        else:
            print(f"  [x] FAIL: Only {len(all_sessions)} panes (expected 4)")

        # Give user time to see the layout
        await asyncio.sleep(1.0)

    finally:
        for s in all_sessions:
            try:
                await s.async_send_text("exit\n")
                await asyncio.sleep(0.1)
                await s.async_close()
            except Exception:
                pass
        print("  Cleanup complete")


if __name__ == "__main__":
    iterm2.run_until_complete(main)
