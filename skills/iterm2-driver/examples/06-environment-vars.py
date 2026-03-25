# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 6: Environment Propagation (Ensuring Tools Work Correctly)

By default, new iTerm2 windows launch as **Login Shells**. They load your `~/.zshrc`
or `~/.bash_profile`. This means tools like `kubectl`, `nvim`, or `node` should work
if they are in your standard PATH.

However, if you have **exported variables in your current session** (like
`KUBECONFIG=/tmp/k8s.yaml`) that are *not* in your rc files, you must manually
propagate them to the new window if you want the tool to see them.
Uses safe window creation (never current_terminal_window) with readiness probes.

Usage:
    uv run 06-environment-vars.py
"""

import asyncio
import os
import shlex

import iterm2


async def dump_screen(session, label: str):
    """Dump screen contents for debugging."""
    screen = await session.async_get_screen_contents()
    print(f"\n--- SCREEN DUMP: {label} ---")
    for i in range(screen.number_of_lines):
        line = screen.line(i).string
        if line.strip():
            print(f"{i:03d}: {line}")
    print("---")


async def cleanup_session(session):
    """Perform multi-level cleanup on a session."""
    try:
        await session.async_send_text("\x03")  # Ctrl+C
        await asyncio.sleep(0.1)
        await session.async_send_text("\x1b")  # Esc (in case in TUI)
        await asyncio.sleep(0.1)
        await session.async_send_text(":q!\n")  # quit vim/nvim if open
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
    await session.async_set_name("Tool with Env")
    created_sessions = [session]

    try:
        # 1. Inject specific critical environment variables
        # (Injecting *all* of os.environ is possible but slow/noisy)
        vars_to_propagate = ["KUBECONFIG", "AWS_PROFILE", "MY_PROJECT_ROOT"]

        for var in vars_to_propagate:
            val = os.environ.get(var)
            if val:
                # Use shlex.quote to safely handle spaces/special chars
                cmd = f"export {var}={shlex.quote(val)}\n"
                await session.async_send_text(cmd)

        # Clear screen to keep it clean
        await session.async_send_text("clear\n")

        # 2. Launch a complex tool
        # Note: We run 'nvim' WITHOUT '-u NONE' so it loads user plugins/config.
        # Ideally, check if the tool exists first or assume it does via .zshrc
        await session.async_send_text("nvim\n")

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
    # Simulate a custom env var for testing
    os.environ["MY_PROJECT_ROOT"] = "/Users/me/code/project"
    iterm2.run_until_complete(main)
