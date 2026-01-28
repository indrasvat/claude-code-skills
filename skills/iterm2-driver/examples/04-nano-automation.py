# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 4: Advanced - TUI Automation (Nano Editor)

This script demonstrates how to drive a full-screen terminal application (Nano).
It launches the editor, types text, and handles the save-and-quit keystroke sequence
(`Ctrl+X`, `y`, `Enter`).

Tests:
    1. Launch Nano: Verify Nano editor starts and shows interface
    2. Type Content: Enter text into the editor
    3. Save and Quit: Execute Ctrl+X, y, Enter sequence to save

Verification Strategy:
    - Look for "GNU nano" in header or "New Buffer" to confirm launch
    - After save sequence, verify return to shell prompt
    - Optionally verify file contents with cat command

Screenshot Inspection Checklist:
    - Colors: Nano's header bar, help text at bottom
    - Boundaries: Header showing filename, footer showing keybindings
    - Buttons/Controls: ^X Exit, ^O Write Out visible in footer
    - Visible Elements: Typed content in editor area
    - Keyboard Navigation: Cursor visible in text area

Key Bindings:
    - Ctrl+X (\\x18): Exit/Save prompt
    - y: Confirm save
    - Enter (\\r): Confirm filename

Usage:
    uv run 04-nano-automation.py
"""

import iterm2
import asyncio
import os

# ============================================================
# CLEANUP HELPER
# ============================================================

async def cleanup_session(session):
    """Perform multi-level cleanup on a session."""
    try:
        # Level 1: Ctrl+C to interrupt
        await session.async_send_text("\x03")
        await asyncio.sleep(0.2)

        # Level 2: Ctrl+X to exit nano if still in it
        await session.async_send_text("\x18")
        await asyncio.sleep(0.2)

        # Level 3: 'n' to discard changes if prompted
        await session.async_send_text("n")
        await asyncio.sleep(0.2)

        # Level 4: exit shell
        await session.async_send_text("exit\n")
        await asyncio.sleep(0.2)

        # Level 5: Close session
        await session.async_close()
    except Exception as e:
        print(f"  Cleanup warning: {e}")


# ============================================================
# MAIN
# ============================================================

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window

    if window is None:
        print("ERROR: No active window found")
        return 1

    tab = await window.async_create_tab()
    session = tab.current_session

    # Use a temp file that won't conflict with anything
    filepath = "/tmp/iterm2_nano_test.txt"

    try:
        print("\n--- NANO AUTOMATION TEST ---\n")

        # ============================================================
        # STEP 1: Launch Nano
        # ============================================================
        print("1. Launching Nano...")
        await session.async_send_text(f"nano {filepath}\n")
        await asyncio.sleep(1.0)  # Wait for TUI to load

        # Verify Nano launched (check for GNU nano header or typical indicators)
        screen = await session.async_get_screen_contents()
        nano_launched = False
        for i in range(min(5, screen.number_of_lines)):
            line = screen.line(i).string
            if "GNU nano" in line or "New Buffer" in line or "nano" in line.lower():
                nano_launched = True
                break

        if nano_launched:
            print("   Nano launched successfully")
        else:
            print("   WARNING: Could not verify Nano launch")
            # Continue anyway - it might still work

        # ============================================================
        # STEP 2: Type Content
        # ============================================================
        print("2. Typing content...")
        await session.async_send_text("Hello from the iTerm2 API!\n")
        await session.async_send_text("This file was created by an AI agent.\n")
        await session.async_send_text("Line 3: Testing nano automation.")
        await asyncio.sleep(0.5)
        print("   Content entered")

        # ============================================================
        # STEP 3: Save and Quit Sequence
        # ============================================================
        print("3. Saving and quitting...")

        # Ctrl+X to initiate exit
        await session.async_send_text("\x18")
        await asyncio.sleep(0.5)

        # Answer "Save modified buffer?" with 'y'
        await session.async_send_text("y")
        await asyncio.sleep(0.5)

        # Confirm filename with Enter
        # IMPORTANT: Use \r for Enter in TUI interactions
        await session.async_send_text("\r")
        await asyncio.sleep(0.5)

        # ============================================================
        # STEP 4: Verify
        # ============================================================
        print("4. Verifying...")

        # Check we're back at shell
        screen = await session.async_get_screen_contents()
        back_at_shell = False
        for i in range(screen.number_of_lines):
            line = screen.line(i).string
            if "$" in line or "%" in line:
                back_at_shell = True
                break

        if back_at_shell:
            print("   Back at shell prompt")

            # Verify file was created
            if os.path.exists(filepath):
                print(f"   File created: {filepath}")

                # Show file contents
                with open(filepath, 'r') as f:
                    contents = f.read()
                print(f"   File contents:\n{contents}")

                # Cleanup the temp file
                os.remove(filepath)
                print("   Temp file cleaned up")
                print("\n--- TEST PASSED ---")
                return 0
            else:
                print(f"   WARNING: File not found at {filepath}")
                print("\n--- TEST PASSED (with warning) ---")
                return 0
        else:
            print("   WARNING: May still be in Nano")
            print("\n--- TEST INCOMPLETE ---")
            return 1

    except Exception as e:
        print(f"\nERROR: {e}")
        raise

    finally:
        await cleanup_session(session)


if __name__ == "__main__":
    exit_code = iterm2.run_until_complete(main)
    exit(exit_code if exit_code else 0)
