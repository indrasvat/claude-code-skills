# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 2: Intermediate - Layout Orchestration for Dev Environment

This script demonstrates how to create a complex 4-pane grid layout for a development
environment (Server, Worker, Database, Logs), setting titles for each pane.
Corresponds to Example 2 in SKILL.md.

Usage:
    uv run 02-dev-layout.py
"""

import iterm2
import asyncio

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window

    if not window:
        print("No active window found")
        return

    # Create a new tab to hold our environment
    tab = await window.async_create_tab()

    # 1. Top Left: Server
    session_tl = tab.current_session
    await session_tl.async_set_name("Server")
    await session_tl.async_send_text("echo 'Starting Server...'\n")

    # 2. Top Right: Worker (Split Vertically)
    session_tr = await session_tl.async_split_pane(vertical=True)
    if session_tr:
        await session_tr.async_set_name("Worker")
        await session_tr.async_send_text("echo 'Starting Worker...'\n")

        # 3. Bottom Right: Logs (Split Top Right Horizontally)
        session_br = await session_tr.async_split_pane(vertical=False)
        if session_br:
            await session_br.async_set_name("Logs")
            await session_br.async_send_text("echo 'Tailing logs...'\n")

    # 4. Bottom Left: Database (Split Top Left Horizontally)
    session_bl = await session_tl.async_split_pane(vertical=False)
    if session_bl:
        await session_bl.async_set_name("Database")
        await session_bl.async_send_text("echo 'Starting DB...'\n")

    print("Dev environment layout created successfully")

if __name__ == "__main__":
    iterm2.run_until_complete(main)
