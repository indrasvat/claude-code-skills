# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

"""
Example 6: Environment Propagation (Ensuring Tools Work Correctly)

By default, new iTerm2 tabs launch as **Login Shells**. They load your `~/.zshrc`
or `~/.bash_profile`. This means tools like `kubectl`, `nvim`, or `node` should work
if they are in your standard PATH.

However, if you have **exported variables in your current session** (like
`KUBECONFIG=/tmp/k8s.yaml`) that are *not* in your rc files, you must manually
propagate them to the new tab if you want the tool to see them.
Corresponds to Example 6 in SKILL.md.

Usage:
    uv run 06-environment-vars.py
"""

import iterm2
import asyncio
import os
import shlex

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window
    if not window:
        return

    tab = await window.async_create_tab()
    session = tab.current_session
    await session.async_set_name("Tool with Env")

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

if __name__ == "__main__":
    # Simulate a custom env var for testing
    os.environ["MY_PROJECT_ROOT"] = "/Users/me/code/project"
    iterm2.run_until_complete(main)
