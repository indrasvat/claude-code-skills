---
name: iterm2-driver
description: Drive iTerm2 programmatically using Python scripts to automate terminal tasks, run tests, or manage sessions.
---

# iTerm2 Driver Skill

This skill enables you to fully control the iTerm2 terminal emulator using its Python API. You can create windows, tabs, and splits, inject commands, read screen content, and interact with running applications (CLI/TUI/REPL).

## CRITICAL INSTRUCTION: Script Format

Every Python script you generate to drive iTerm2 **MUST** use `uv` for dependency management and execution.
You must always include the `uv` inline metadata header at the top of the script.

**Required Header Format:**
```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///
```

**Execution:**
Run the scripts using: `uv run script_name.py`

## Core Concepts

- **Connection**: Use `iterm2.run_until_complete(main)` for standalone scripts that perform a task and exit.
- **Hierarchy**: `App` -> `Window` -> `Tab` -> `Session`.
- **Interaction**:
    - `session.async_send_text("command\n")`: Send input.
    - `session.async_get_contents()` or `session.async_get_screen_contents()`: Read screen text.
    - `session.async_split_pane(vertical=True/False)`: Create splits.
    - `session.async_activate()`: Focus a session.

## Examples

### Example 1: Basic - Open a New Tab and Run a Command

This script gets the current window, creates a new tab, and runs `ls -la`.

```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window
    
    if window is not None:
        # Create a new tab
        tab = await window.async_create_tab()
        session = tab.current_session
        
        # Run a command
        await session.async_send_text("ls -la\n")
        print(f"Created tab {tab.tab_id} and sent command")
    else:
        print("No active window found")

if __name__ == "__main__":
    iterm2.run_until_complete(main)
```

### Example 2: Intermediate - Layout Orchestration for Dev Environment

This script demonstrates how to create a complex 4-pane grid layout for a development environment (Server, Worker, Database, Logs), setting titles for each pane.

```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

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
```

### Example 3: Advanced - Interactive REPL Driver

This script drives an interactive process (Python REPL). It sends code, waits for execution, and verifies the output by reading the screen content programmatically. This pattern is essential for testing TUIs or interactive CLIs.

```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

import iterm2
import asyncio

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window
    
    if window is not None:
        # Create a dedicated tab for this test
        tab = await window.async_create_tab()
        session = tab.current_session
        
        # 1. Start the interactive process (Python REPL)
        print("Starting REPL...")
        await session.async_send_text("python3\n")
        await asyncio.sleep(1) # Wait for prompt
        
        # 2. Define a function (send extra newline to ensure block closure)
        print("Defining function...")
        await session.async_send_text("def f(x): return x * 2\n\n")
        await asyncio.sleep(0.5)

        # 3. Send a calculation command
        print("Sending command...")
        # We print a unique marker string to look for
        cmd = "print(f'MARKER_RESULT: {f(10)}')"
        await session.async_send_text(f"{cmd}\n")
        
        # 4. Poll the screen until we see the result or timeout
        print("Waiting for result...")
        found = False
        for _ in range(10): # Try for 5 seconds (10 * 0.5s)
            await asyncio.sleep(0.5)
            screen_contents = await session.async_get_screen_contents()
            
            # Check all lines for our marker
            # Note: Use screen_contents.line(i).string to access text
            for i in range(screen_contents.number_of_lines):
                if "MARKER_RESULT: 20" in screen_contents.line(i).string:
                    found = True
                    break
            if found:
                break
        
        # 4. Report results
        if found:
            print("SUCCESS: Calculation verified correctly.")
        else:
            print("FAILURE: Could not find expected output on screen.")
            # Optional: Print screen dump for debugging
            # print("\n".join([l.string for l in screen_contents.lines]))

        # 5. Clean up (Exit REPL)
        await session.async_send_text("exit()\n")
            
    else:
        print("No active window found")

if __name__ == "__main__":
    iterm2.run_until_complete(main)
```

### Example 4: Advanced - TUI Automation (Nano Editor)

This script demonstrates how to drive a full-screen terminal application (Nano). It launches the editor, types text, and handles the save-and-quit keystroke sequence (`Ctrl+X`, `y`, `Enter`).

```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

import iterm2
import asyncio

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window
    
    if window is not None:
        tab = await window.async_create_tab()
        session = tab.current_session
        
        # 1. Launch Nano with a specific file path
        # Use absolute path to be sure where the file ends up
        filepath = "/tmp/ai_generated_note.txt"
        await session.async_send_text(f"nano {filepath}\n")
        await asyncio.sleep(1.0) # Wait for TUI to load

        # 2. Type content
        await session.async_send_text("Hello from the iTerm2 API!\n")
        await session.async_send_text("This file was created by an AI agent.")
        await asyncio.sleep(0.5)

        # 3. Save and Quit Sequence
        # Ctrl+X is \x18
        await session.async_send_text("\x18")
        await asyncio.sleep(0.5)
        
        # Prompt: "Save modified buffer?" -> Send 'y'
        await session.async_send_text("y")
        await asyncio.sleep(0.5)
        
        # Prompt: "File Name to Write: ..." -> Send Enter (\r)
        # IMPORTANT: Use \r for Enter in TUI interactions often works better than \n
        await session.async_send_text("\r")
        await asyncio.sleep(0.5)
        
        print(f"File saved to {filepath}")
            
    else:
        print("No active window found")

if __name__ == "__main__":
    iterm2.run_until_complete(main)
```

### Example 5: Advanced - Screen Streaming (Real-Time Monitoring)

This demonstrates how to use `ScreenStreamer` to "watch" the screen for updates. This is much more reliable than using `sleep()` because it reacts to actual screen paints. This is ideal for an agent to "see" what is happening in a TUI or long-running process.

```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

import iterm2
import asyncio

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window
    
    if window is not None:
        tab = await window.async_create_tab()
        session = tab.current_session
        
        # Start a process that outputs continually (e.g., ping)
        print("Starting ping...")
        await session.async_send_text("ping 127.0.0.1\n")

        # Use ScreenStreamer to monitor updates
        print("Monitoring screen (capturing 5 updates)...")
        async with session.get_screen_streamer() as streamer:
            for i in range(5):
                # Blocks until the screen changes
                screen_contents = await streamer.async_get()
                
                print(f"\n--- Screen Update {i+1} ---")
                # Print the non-empty lines
                for j in range(screen_contents.number_of_lines):
                    line = screen_contents.line(j).string
                    if line.strip():
                        print(f"Line {j}: {line}")

        # Stop the process
        await session.async_send_text("\x03") # Ctrl+C
        print("\nStopped process.")
            
    else:
        print("No active window found")

if __name__ == "__main__":
    iterm2.run_until_complete(main)
```

### Example 6: Environment Propagation (Ensuring Tools Work Correctly)

By default, new iTerm2 tabs launch as **Login Shells**. They load your `~/.zshrc` or `~/.bash_profile`. This means tools like `kubectl`, `nvim`, or `node` should work if they are in your standard PATH.

However, if you have **exported variables in your current session** (like `KUBECONFIG=/tmp/k8s.yaml`) that are *not* in your rc files, you must manually propagate them to the new tab if you want the tool to see them.

```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

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
```

## Guidelines

1.  **Always use `uv run`**: Never suggest running python directly.
2.  **Dependencies**: Always include `iterm2` and `pyobjc` in the inline `dependencies` list.
3.  **Async/Await**: The iTerm2 API is asynchronous. Use `await` for most operations.
4.  **Error Handling**: Always check if `app.current_terminal_window` is not None before proceeding.
5.  **Splitting Panes**: `async_split_pane(vertical=True)` creates a side-by-side split. `vertical=False` creates a top-bottom split.
6.  **Screen Reading**: 
    *   Use `async_get_screen_contents()` for one-off snapshots.
    *   Use `async with session.get_screen_streamer() as streamer` for continuous monitoring.
7.  **TUI Keys**:
    *   Enter: `\r` is often safer than `\n` for confirming prompts in TUIs.
    *   Control Keys: Use hex codes (e.g., Ctrl+C = `\x03`, Ctrl+X = `\x18`, Esc = `\x1b`).
8.  **Environment**: New tabs load user profiles (zshrc/bashrc). Only inject `os.environ` variables explicitly if they are transient (not in rc files).
9.  **Tool Config**: To run tools like `nvim` with user config, simply call them by name (`nvim`). Only use flags like `-u NONE` if you explicitly want a vanilla environment for testing.

## Script Storage Strategy

Do not create scripts in `/tmp` unless explicitly requested. Instead, persist them so they can be reused or audited.

1.  **Determine the Scope**:
    *   **Project-Specific**: If the script relates to the current project (e.g., runs specific tests, builds, or watches local logs), store it in:
        `./.claude/automations/{script_name}.py`
    *   **General Utility**: If the script is a general tool (e.g., system monitoring, generic window layouts, TUI drivers for standard tools), store it in:
        `~/.claude/automations/{script_name}.py`

2.  **Naming Convention**:
    *   Use descriptive, action-oriented filenames: `watch_build_logs.py`, `drive_k9s_debug.py`, `layout_dev_env.py`.
    *   Avoid generic names like `test.py` or `script.py`.

3.  **Implementation**:
    *   Always use `os.makedirs(os.path.dirname(path), exist_ok=True)` or equivalent logic in your thinking process to ensure the directory exists before creating the file.

## Debugging & Troubleshooting

If your automation fails to find expected text or behaves unexpectedly, your script **MUST** dump the screen contents to stdout before exiting. This allows you (the agent) to "see" what went wrong.

```python
# Debug Pattern: Dump screen on failure
if not found:
    print("FAILURE: Expected pattern not found.")
    print("--- SCREEN DUMP ---")
    screen = await session.async_get_screen_contents()
    for i in range(screen.number_of_lines):
        print(f"{i:03d}: {screen.line(i).string}")
    print("-------------------")
```

## Session Discovery (Context Awareness)

You don't always need to create a new tab. You can interact with the currently active session or find a specific existing session.

```python
# Get the currently active session (where the user is looking)
session = app.current_terminal_window.current_tab.current_session

# Find a specific session by name
target_session = None
for tab in app.current_terminal_window.tabs:
    for s in tab.sessions:
        if s.name == "MyServer":
            target_session = s
            break
```

## User Confirmation

For destructive actions, use iTerm2's native alert system to ask for permission.

```python
# Ask for confirmation
alert = iterm2.Alert("Delete Database?", "This action cannot be undone.")
alert.add_button("Cancel")
alert.add_button("Proceed")
selection = await alert.async_run(connection)
if selection == 1: # Buttons are 0-indexed? No, usually 1000+ or based on add order.
    # Check API docs or specific return values.
    pass
```

## References

- [iTerm2 Python API Documentation](https://iterm2.com/python-api/)
- [iTerm2 Scripting Tutorial](https://iterm2.com/python-api/tutorial/index.html)
- [iTerm2 Example Scripts](https://iterm2.com/python-api/examples/index.html)
- [UV Documentation](https://github.com/astral-sh/uv)

### Example 8: Visual Status (Badges)

Use badges to indicate the status of a long-running task (e.g., "Building", "Testing", "Success"). Since the API doesn't have a direct helper, use the iTerm2 escape sequence `OSC 1337`.

```python
import base64

async def set_badge(session, text):
    # OSC 1337 ; SetBadgeFormat=Base64 ST
    data = base64.b64encode(text.encode('utf-8')).decode('utf-8')
    cmd = f"\x1b]1337;SetBadgeFormat={data}\x07"
    await session.async_send_text(cmd)

# Usage
await set_badge(session, "Compiling...")
```

### Example 9: Special Keys Reference

When driving TUIs (like htop, mc, or vim), you often need to send special keys. Use these hex codes:

| Key | Code |
| :--- | :--- |
| **Enter** | `\r` (Use this instead of `\n`) |
| **Esc** | `\x1b` |
| **Up Arrow** | `\x1b[A` |
| **Down Arrow** | `\x1b[B` |
| **Right Arrow** | `\x1b[C` |
| **Left Arrow** | `\x1b[D` |
| **Ctrl+C** | `\x03` |
| **Ctrl+X** | `\x18` |
| **Ctrl+Z** | `\x1a` |
| **F1** | `\x1bOP` |

### Example 10: Session Reuse (Get-or-Create Pattern)

Avoid clutter by reusing a named session if it exists.

```python
# Define target name
target_name = "MyWorker"
target_session = None

# 1. Search existing
if app.current_terminal_window:
    for tab in app.current_terminal_window.tabs:
        for session in tab.sessions:
            if session.name == target_name:
                target_session = session
                break
        if target_session: break

# 2. Create if not found
if not target_session:
    if app.current_terminal_window:
        tab = await app.current_terminal_window.async_create_tab()
        target_session = tab.current_session
        await target_session.async_set_name(target_name)

if target_session:
    await target_session.async_activate()
    await target_session.async_send_text("echo 'Ready'\n")
```

## Cleanup Strategy

When running multiple automated tasks, iTerm2 tabs can pile up. You should generally clean up tabs created during a session unless the user explicitly wants them left open for inspection.

To close a tab, close its active session:

```python
# Cleanup: Close the session (and the tab if it's the only session)
await session.async_close()
```

If you have created a complex layout with multiple splits, ensure you close the `Tab` object or all its sessions.

### Example 7: Global Cleanup (Close All Tabs Except First)

This is useful for resetting the environment after a heavy testing session.

```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
#   "pyobjc",
# ]
# ///

import iterm2
import asyncio

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window
    if not window:
        return

    tabs = window.tabs
    if len(tabs) <= 1:
        print("Cleanup not needed.")
        return

    print(f"Closing {len(tabs) - 1} extra tabs...")
    
    # Iterate backwards to avoid index shifting issues
    # Keep index 0 (the first tab) open
    for i in range(len(tabs) - 1, 0, -1):
        tab = tabs[i]
        # Close all sessions in the tab to ensure it closes
        for session in tab.sessions:
            await session.async_close()
        await asyncio.sleep(0.1) # Brief pause for UI stability

    print("Cleanup complete.")

if __name__ == "__main__":
    iterm2.run_until_complete(main)
```
