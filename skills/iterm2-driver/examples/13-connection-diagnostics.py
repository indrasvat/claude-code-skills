# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "iterm2",
#   "pyobjc",
#   "pyobjc-framework-Quartz",
# ]
# ///

"""
Example 13: Connection Diagnostics — Pre-flight checks for iTerm2 automation

Run this FIRST when iTerm2 automation fails silently. Checks every prerequisite
and reports actionable fixes. Addresses the #1 CASS finding: scripts exit with
code 1 and no output when iTerm2 is misconfigured.

Tests:
    1. Socket Check: Is the Unix domain socket present?
    2. Socket Connectivity: Can we actually connect to the socket?
    3. iTerm2 Process: Is iTerm2 running?
    4. API Connection: Can we establish a WebSocket connection?
    5. Window Access: Can we enumerate windows?
    6. Session Creation: Can we create a new tab/session?
    7. Screen Read: Can we read screen contents?
    8. Screenshot: Can we capture a Quartz-targeted screenshot?
    9. Cleanup: Can we close the test session?

Verification Strategy:
    - Each check is independent and reports PASS/FAIL with actionable message
    - Checks run in dependency order — if socket is missing, skip API checks
    - Output is human-readable for troubleshooting

Usage:
    uv run 13-connection-diagnostics.py
"""

import os
import socket
import subprocess
import sys
import time

# ============================================================
# PRE-CONNECTION CHECKS (no iTerm2 import needed)
# ============================================================

SOCKET_PATH = os.path.expanduser(
    "~/Library/Application Support/iTerm2/private/socket"
)
results = {"passed": 0, "failed": 0, "tests": []}


def log_result(name: str, status: str, details: str = "", fix: str = ""):
    results["tests"].append({"name": name, "status": status})
    if status == "PASS":
        results["passed"] += 1
        print(f"  [+] PASS: {name}")
        if details:
            print(f"         {details}")
    else:
        results["failed"] += 1
        print(f"  [x] FAIL: {name}")
        if details:
            print(f"         {details}")
        if fix:
            print(f"         FIX: {fix}")


def print_summary() -> int:
    total = results["passed"] + results["failed"]
    print(f"\n{'=' * 60}")
    print(f"DIAGNOSTICS: {results['passed']}/{total} checks passed")
    print("=" * 60)
    if results["failed"] > 0:
        print("\nFailed checks:")
        for t in results["tests"]:
            if t["status"] == "FAIL":
                print(f"  x {t['name']}")
        print("\nFix the issues above, then re-run this diagnostic.")
        return 1
    print("\nAll checks passed — iTerm2 automation is ready!")
    return 0


def main_sync():
    """Run pre-connection checks that don't need the iTerm2 API."""
    print("\n" + "#" * 60)
    print("# iTerm2 CONNECTION DIAGNOSTICS")
    print("# Run this when automation scripts fail silently")
    print("#" * 60)

    # ============================================================
    # CHECK 1: Socket exists
    # ============================================================
    print(f"\n{'=' * 60}")
    print("CHECK 1: Unix Domain Socket")
    print("=" * 60)

    if os.path.exists(SOCKET_PATH):
        mtime = os.path.getmtime(SOCKET_PATH)
        age_s = time.time() - mtime
        log_result("Socket Exists", "PASS", f"Age: {age_s:.0f}s")
    else:
        log_result(
            "Socket Exists", "FAIL",
            f"Not found at: {SOCKET_PATH}",
            "Enable Python API: iTerm2 > Preferences > General > Magic > Enable Python API"
        )
        return print_summary()

    # ============================================================
    # CHECK 2: Socket connectivity
    # ============================================================
    print(f"\n{'=' * 60}")
    print("CHECK 2: Socket Connectivity")
    print("=" * 60)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(SOCKET_PATH)
        sock.close()
        log_result("Socket Connectable", "PASS")
    except ConnectionRefusedError:
        log_result(
            "Socket Connectable", "FAIL",
            "Connection refused — socket is stale",
            "Restart iTerm2: osascript -e 'tell application \"iTerm\" to quit' && sleep 2 && open -a iTerm"
        )
        # Check if removing stale socket helps
        return print_summary()
    except Exception as e:
        log_result("Socket Connectable", "FAIL", str(e))
        return print_summary()

    # ============================================================
    # CHECK 3: iTerm2 process
    # ============================================================
    print(f"\n{'=' * 60}")
    print("CHECK 3: iTerm2 Process")
    print("=" * 60)

    result = subprocess.run(["pgrep", "-x", "iTerm2"], capture_output=True)
    if result.returncode == 0:
        pid = result.stdout.decode().strip().split("\n")[0]
        log_result("iTerm2 Running", "PASS", f"PID: {pid}")
    else:
        log_result(
            "iTerm2 Running", "FAIL",
            "iTerm2 process not found",
            "Start iTerm2: open -a iTerm"
        )
        return print_summary()

    # ============================================================
    # CHECK 4-9: API checks (require iTerm2 connection)
    # ============================================================
    print("\n  Proceeding to API connection checks...")
    return None  # Signal to continue with async checks


def main_async_wrapper():
    """Run the async API checks."""
    import iterm2
    import asyncio

    async def api_checks(connection):
        # ============================================================
        # CHECK 4: API connection
        # ============================================================
        print(f"\n{'=' * 60}")
        print("CHECK 4: API Connection")
        print("=" * 60)
        log_result("API Connection", "PASS", "WebSocket connected")

        # ============================================================
        # CHECK 5: Window access
        # ============================================================
        print(f"\n{'=' * 60}")
        print("CHECK 5: Window Access")
        print("=" * 60)

        app = await iterm2.async_get_app(connection)
        windows = app.terminal_windows
        log_result("Window Access", "PASS", f"{len(windows)} window(s) found")

        # ============================================================
        # CHECK 6: Session creation
        # ============================================================
        print(f"\n{'=' * 60}")
        print("CHECK 6: Session Creation")
        print("=" * 60)

        test_session = None
        test_window = None
        try:
            test_window = await iterm2.Window.async_create(connection)
            # Readiness probe
            for _ in range(20):
                if test_window and test_window.current_tab and test_window.current_tab.current_session:
                    break
                await asyncio.sleep(0.2)

            if test_window and test_window.current_tab:
                test_session = test_window.current_tab.current_session
                await test_session.async_set_name("diagnostics-test")
                log_result("Session Creation", "PASS", f"Session: {test_session.session_id}")
            else:
                log_result("Session Creation", "FAIL", "Window created but tab/session not ready")
        except Exception as e:
            log_result("Session Creation", "FAIL", str(e))

        if not test_session:
            return print_summary()

        # ============================================================
        # CHECK 7: Screen read
        # ============================================================
        print(f"\n{'=' * 60}")
        print("CHECK 7: Screen Read")
        print("=" * 60)

        try:
            marker = "DIAG_TEST_42"
            await test_session.async_send_text(f"echo '{marker}'\n")
            await asyncio.sleep(0.5)
            screen = await test_session.async_get_screen_contents()
            found = False
            for i in range(screen.number_of_lines):
                if marker in screen.line(i).string:
                    found = True
                    break
            if found:
                log_result("Screen Read", "PASS", f"Marker '{marker}' found on screen")
            else:
                log_result("Screen Read", "FAIL", "Sent text but could not read it back")
        except Exception as e:
            log_result("Screen Read", "FAIL", str(e))

        # ============================================================
        # CHECK 8: Screenshot
        # ============================================================
        print(f"\n{'=' * 60}")
        print("CHECK 8: Screenshot Capture")
        print("=" * 60)

        try:
            import Quartz
            frame = await test_window.async_get_frame()
            window_list = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly
                | Quartz.kCGWindowListExcludeDesktopElements,
                Quartz.kCGNullWindowID,
            )
            iterm_windows = [
                w for w in window_list
                if "iTerm" in w.get("kCGWindowOwnerName", "")
            ]
            if iterm_windows:
                qid = iterm_windows[0].get("kCGWindowNumber")
                path = "/tmp/iterm2_diag_screenshot.png"
                subprocess.run(["screencapture", "-x", "-l", str(qid), path], check=True)
                if os.path.exists(path) and os.path.getsize(path) > 1000:
                    log_result("Screenshot", "PASS", f"{os.path.getsize(path)} bytes")
                    os.unlink(path)
                else:
                    log_result("Screenshot", "FAIL", "File too small or missing")
            else:
                log_result("Screenshot", "FAIL",
                           "No iTerm2 windows in Quartz",
                           "Ensure iTerm2 is not minimized and Screen Recording permission is granted")
        except ImportError:
            log_result("Screenshot", "FAIL",
                       "Quartz not available",
                       "Add pyobjc-framework-Quartz to dependencies")
        except Exception as e:
            log_result("Screenshot", "FAIL", str(e))

        # ============================================================
        # CHECK 9: Cleanup
        # ============================================================
        print(f"\n{'=' * 60}")
        print("CHECK 9: Cleanup")
        print("=" * 60)

        try:
            await test_session.async_send_text("exit\n")
            await asyncio.sleep(0.5)
            try:
                await test_session.async_close()
            except Exception:
                pass  # Session may auto-close after exit
            log_result("Cleanup", "PASS")
        except Exception as e:
            log_result("Cleanup", "FAIL", str(e),
                       "Session may have already been closed")

        return print_summary()

    try:
        exit_code = iterm2.run_until_complete(api_checks)
        return exit_code if exit_code else 0
    except Exception as e:
        log_result("API Connection", "FAIL", str(e),
                   "Is iTerm2 running with Python API enabled?")
        return print_summary()


if __name__ == "__main__":
    sync_result = main_sync()
    if sync_result is not None:
        exit(sync_result)
    exit_code = main_async_wrapper()
    exit(exit_code if exit_code else 0)
