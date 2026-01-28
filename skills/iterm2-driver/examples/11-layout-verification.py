# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "iterm2",
#   "pyobjc",
#   "pyobjc-framework-Quartz",
# ]
# ///

"""
Example 11: TUI Layout & Alignment Verification

This script demonstrates how to detect misaligned TUI elements like:
- Broken box-drawing characters (rounded rects, borders)
- Misaligned help modals that overflow or get cut off
- Status bars with gaps or incorrect width
- Column alignment issues in tables

This is CRITICAL for TUI testing because visual misalignment is a common
failure mode that basic text verification misses.

Tests:
    1. Box Integrity: Verify box-drawing characters connect properly
    2. Modal Boundaries: Check help modal has symmetric boundaries
    3. Status Bar: Verify footer spans expected width
    4. Column Alignment: Check table headers align with data

Verification Strategy:
    - Parse screen for Unicode box-drawing characters (─│┌┐└┘╭╮╰╯)
    - Check that corners connect to edges (no orphaned corners)
    - Verify modal top/bottom borders are same width
    - Check status bar for suspicious gaps

Screenshot Inspection Checklist:
    - Colors: N/A (focusing on structure, not color)
    - Boundaries: Box corners must connect to edges
    - Buttons/Controls: Verify function key labels intact
    - Mouse Support: N/A
    - Visible Elements: All UI chrome should be complete
    - Keyboard Navigation: Focus indicators should be properly boxed

Key Bindings:
    - q: Quit
    - ?: Help (opens modal to test)

Usage:
    uv run 11-layout-verification.py

Note: This example uses 'htop' as a test subject. Replace with your TUI app.
"""

import iterm2
import asyncio
import subprocess
import os
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

SCREENSHOT_DIR = "./screenshots"
TARGET_APP = "htop"  # Change to your TUI app

# Box-drawing character sets
BOX_CHARS = {
    'corners': '┌┐└┘╭╮╰╯╔╗╚╝',
    'horizontal': '─═━',
    'vertical': '│║┃',
    'junctions': '├┤┬┴┼╠╣╦╩╬',
}

# ============================================================
# RESULT TRACKING
# ============================================================

results = {"passed": 0, "failed": 0, "tests": []}


def log_result(test_name: str, status: str, details: str = ""):
    """Log a test result."""
    results["tests"].append({"name": test_name, "status": status, "details": details})
    if status == "PASS":
        results["passed"] += 1
        print(f"  [+] PASS: {test_name}")
    else:
        results["failed"] += 1
        print(f"  [x] FAIL: {test_name}")
        if details:
            print(f"      {details}")


def print_summary() -> int:
    """Print test summary."""
    total = results["passed"] + results["failed"]
    print("\n" + "=" * 60)
    print(f"LAYOUT VERIFICATION SUMMARY: {results['passed']}/{total} passed")
    print("=" * 60)

    if results["failed"] > 0:
        print("\nFailed checks:")
        for test in results["tests"]:
            if test["status"] == "FAIL":
                print(f"  - {test['name']}: {test['details']}")
        print("\nOVERALL: LAYOUT ISSUES DETECTED")
        return 1

    print("\nOVERALL: LAYOUT VERIFIED OK")
    return 0


# ============================================================
# SCREENSHOT HELPERS
# ============================================================

try:
    import Quartz

    def get_iterm2_window_id():
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID
        )
        for window in window_list:
            if 'iTerm' in window.get('kCGWindowOwnerName', ''):
                return window.get('kCGWindowNumber')
        return None
except ImportError:
    def get_iterm2_window_id():
        return None


def capture_screenshot(name: str) -> str:
    """Capture screenshot of iTerm2 window."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(SCREENSHOT_DIR, f"{name}_{timestamp}.png")

    window_id = get_iterm2_window_id()
    if window_id:
        subprocess.run(["screencapture", "-x", "-l", str(window_id), filepath], check=True)
    else:
        subprocess.run(["screencapture", "-x", filepath], check=True)

    print(f"  SCREENSHOT: {filepath}")
    return filepath


# ============================================================
# LAYOUT VERIFICATION FUNCTIONS
# ============================================================

async def verify_box_integrity(session, description: str = "UI") -> dict:
    """Check that box-drawing characters form complete, connected boxes."""
    screen = await session.async_get_screen_contents()
    issues = []
    box_lines = []

    all_box_chars = (BOX_CHARS['corners'] + BOX_CHARS['horizontal'] +
                     BOX_CHARS['vertical'] + BOX_CHARS['junctions'])

    for i in range(screen.number_of_lines):
        line = screen.line(i).string
        has_box = any(c in line for c in all_box_chars)
        if has_box:
            box_lines.append((i, line))

    # Check corner connectivity
    for line_num, line in box_lines:
        for j, char in enumerate(line):
            # Top-left corners should connect right
            if char in '┌╭╔':
                if j + 1 < len(line):
                    next_char = line[j + 1]
                    if next_char not in BOX_CHARS['horizontal'] + BOX_CHARS['junctions'] + BOX_CHARS['corners']:
                        issues.append(f"Line {line_num}, col {j}: '{char}' not connected to horizontal edge (found '{next_char}')")

            # Top-right corners should connect left
            elif char in '┐╮╗':
                if j > 0:
                    prev_char = line[j - 1]
                    if prev_char not in BOX_CHARS['horizontal'] + BOX_CHARS['junctions'] + BOX_CHARS['corners']:
                        issues.append(f"Line {line_num}, col {j}: '{char}' not connected to horizontal edge (found '{prev_char}')")

            # Bottom corners similar checks
            elif char in '└╰╚':
                if j + 1 < len(line):
                    next_char = line[j + 1]
                    if next_char not in BOX_CHARS['horizontal'] + BOX_CHARS['junctions'] + BOX_CHARS['corners'] + ' ':
                        issues.append(f"Line {line_num}, col {j}: '{char}' not connected properly")

            elif char in '┘╯╝':
                if j > 0:
                    prev_char = line[j - 1]
                    if prev_char not in BOX_CHARS['horizontal'] + BOX_CHARS['junctions'] + BOX_CHARS['corners'] + ' ':
                        issues.append(f"Line {line_num}, col {j}: '{char}' not connected properly")

    return {
        'valid': len(issues) == 0,
        'issues': issues[:10],  # Limit to first 10
        'box_lines_found': len(box_lines),
    }


async def verify_modal_boundaries(session) -> dict:
    """Verify modal/dialog has symmetric boundaries."""
    screen = await session.async_get_screen_contents()
    issues = []

    top_corners = []
    bottom_corners = []

    for i in range(screen.number_of_lines):
        line = screen.line(i).string
        for j, char in enumerate(line):
            if char in '┌╭╔':
                top_corners.append((i, j, char))
            elif char in '└╰╚':
                bottom_corners.append((i, j, char))

    # Check for matching corners
    if len(top_corners) == 0:
        issues.append("No modal top-left corner found")
    elif len(bottom_corners) == 0:
        issues.append("No modal bottom-left corner found (modal may be cut off)")
    else:
        # Check alignment of innermost modal (last top corner should match last bottom corner)
        if top_corners and bottom_corners:
            top_line, top_col, _ = top_corners[-1]
            bottom_line, bottom_col, _ = bottom_corners[-1]

            if top_col != bottom_col:
                issues.append(f"Modal corners misaligned: top at col {top_col}, bottom at col {bottom_col}")

            # Check modal height is reasonable
            height = bottom_line - top_line
            if height < 2:
                issues.append(f"Modal too short: only {height} lines")

    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'top_corners': len(top_corners),
        'bottom_corners': len(bottom_corners),
    }


async def verify_status_bar(session, position: str = "bottom") -> dict:
    """Verify status bar is intact without gaps."""
    screen = await session.async_get_screen_contents()
    issues = []

    # Find status bar line
    if position == "bottom":
        for i in range(screen.number_of_lines - 1, -1, -1):
            line = screen.line(i).string
            if line.strip():
                status_line = line
                status_line_num = i
                break
    else:
        for i in range(screen.number_of_lines):
            line = screen.line(i).string
            if line.strip():
                status_line = line
                status_line_num = i
                break

    # Check for large gaps (more than 10 consecutive spaces in middle)
    in_content = False
    space_run = 0
    for char in status_line:
        if char != ' ':
            in_content = True
            if space_run > 10 and in_content:
                issues.append(f"Large gap ({space_run} spaces) in status bar")
            space_run = 0
        else:
            space_run += 1

    # Check line has reasonable content
    content_len = len(status_line.strip())
    if content_len < 10:
        issues.append(f"Status bar too short: only {content_len} chars of content")

    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'line': status_line_num,
        'content_length': content_len,
    }


async def verify_column_alignment(session, header_line: int = 0) -> dict:
    """Verify table columns are aligned."""
    screen = await session.async_get_screen_contents()
    issues = []

    header = screen.line(header_line).string

    # Find where content blocks start/end in header
    content_positions = []
    in_content = False
    start = 0

    for i, char in enumerate(header):
        if char != ' ' and not in_content:
            in_content = True
            start = i
        elif char == ' ' and in_content:
            in_content = False
            content_positions.append((start, i))

    # Check a few data lines
    misalignments = 0
    for line_num in range(header_line + 1, min(header_line + 6, screen.number_of_lines)):
        data_line = screen.line(line_num).string
        if not data_line.strip():
            continue

        # Very basic check: do content blocks start at similar positions?
        data_starts = []
        in_content = False
        for i, char in enumerate(data_line):
            if char != ' ' and not in_content:
                in_content = True
                data_starts.append(i)
            elif char == ' ':
                in_content = False

        # Compare first few column starts
        header_starts = [pos[0] for pos in content_positions[:5]]
        for h_start in header_starts:
            # Check if any data start is within 3 chars
            if not any(abs(d - h_start) <= 3 for d in data_starts[:5]):
                misalignments += 1

    if misalignments > 3:
        issues.append(f"Multiple column misalignments detected ({misalignments})")

    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'header_columns': len(content_positions),
    }


async def dump_layout_debug(session, label: str):
    """Dump screen with box characters highlighted for debugging."""
    screen = await session.async_get_screen_contents()
    all_box = (BOX_CHARS['corners'] + BOX_CHARS['horizontal'] +
               BOX_CHARS['vertical'] + BOX_CHARS['junctions'])

    print(f"\n{'='*70}")
    print(f"LAYOUT DEBUG: {label}")
    print(f"{'='*70}")
    print("     " + "0         1         2         3         4         5         6         7")
    print("     " + "0123456789" * 7)
    print()

    for i in range(screen.number_of_lines):
        line = screen.line(i).string
        if line.strip():
            # Mark box chars
            marked = ""
            for c in line[:70]:
                if c in all_box:
                    marked += f"\033[91m{c}\033[0m"  # Red for box chars
                else:
                    marked += c
            print(f"{i:03d}: {line[:70]}")

    print(f"{'='*70}\n")


# ============================================================
# CLEANUP
# ============================================================

async def cleanup_session(session, quit_key: str = "q"):
    """Multi-level cleanup."""
    try:
        await session.async_send_text("\x03")  # Ctrl+C
        await asyncio.sleep(0.2)
        await session.async_send_text(quit_key)
        await asyncio.sleep(0.2)
        await session.async_send_text("exit\n")
        await asyncio.sleep(0.2)
        await session.async_close()
    except Exception as e:
        print(f"  Cleanup warning: {e}")


# ============================================================
# MAIN TEST
# ============================================================

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window

    if not window:
        print("ERROR: No active window")
        return 1

    tab = await window.async_create_tab()
    session = tab.current_session

    print("\n" + "#" * 60)
    print("# TUI LAYOUT VERIFICATION TEST")
    print(f"# Target: {TARGET_APP}")
    print("#" * 60)

    try:
        # ============================================================
        # Launch TUI
        # ============================================================
        print(f"\nLaunching {TARGET_APP}...")
        await session.async_send_text(f"{TARGET_APP}\n")
        await asyncio.sleep(1.5)  # Wait for TUI to render

        # ============================================================
        # TEST 1: Box Integrity
        # ============================================================
        print("\n" + "=" * 60)
        print("TEST 1: Box Drawing Integrity")
        print("=" * 60)

        box_result = await verify_box_integrity(session, "main UI boxes")

        if box_result['valid']:
            log_result("Box Integrity", "PASS")
        else:
            log_result("Box Integrity", "FAIL",
                      f"{len(box_result['issues'])} issues: {box_result['issues'][0] if box_result['issues'] else 'unknown'}")
            capture_screenshot("box_integrity_fail")

        print(f"  Found {box_result['box_lines_found']} lines with box-drawing chars")

        # ============================================================
        # TEST 2: Status Bar
        # ============================================================
        print("\n" + "=" * 60)
        print("TEST 2: Status Bar Integrity")
        print("=" * 60)

        status_result = await verify_status_bar(session, "bottom")

        if status_result['valid']:
            log_result("Status Bar", "PASS")
        else:
            log_result("Status Bar", "FAIL",
                      status_result['issues'][0] if status_result['issues'] else "unknown issue")

        print(f"  Status bar at line {status_result.get('line', 'N/A')}, "
              f"content length: {status_result.get('content_length', 'N/A')}")

        # ============================================================
        # TEST 3: Column Alignment
        # ============================================================
        print("\n" + "=" * 60)
        print("TEST 3: Column Alignment")
        print("=" * 60)

        # htop header is typically at line 0-2 depending on meters
        col_result = await verify_column_alignment(session, header_line=1)

        if col_result['valid']:
            log_result("Column Alignment", "PASS")
        else:
            log_result("Column Alignment", "FAIL",
                      col_result['issues'][0] if col_result['issues'] else "unknown")

        print(f"  Detected {col_result['header_columns']} column boundaries")

        # ============================================================
        # TEST 4: Help Modal (if applicable)
        # ============================================================
        print("\n" + "=" * 60)
        print("TEST 4: Help Modal Boundaries")
        print("=" * 60)

        # Open help
        await session.async_send_text("?")
        await asyncio.sleep(0.5)

        modal_result = await verify_modal_boundaries(session)

        if modal_result['valid']:
            log_result("Modal Boundaries", "PASS")
            capture_screenshot("modal_ok")
        else:
            log_result("Modal Boundaries", "FAIL",
                      modal_result['issues'][0] if modal_result['issues'] else "unknown")
            capture_screenshot("modal_fail")
            await dump_layout_debug(session, "modal_failure")

        print(f"  Found {modal_result['top_corners']} top corners, "
              f"{modal_result['bottom_corners']} bottom corners")

        # Close help
        await session.async_send_text("q")
        await asyncio.sleep(0.3)

        # ============================================================
        # Capture final state
        # ============================================================
        capture_screenshot("layout_final")

    except Exception as e:
        print(f"\nERROR: {e}")
        log_result("Execution", "FAIL", str(e))
        await dump_layout_debug(session, "error_state")

    finally:
        await cleanup_session(session, "q")

    return print_summary()


if __name__ == "__main__":
    exit_code = iterm2.run_until_complete(main)
    exit(exit_code if exit_code else 0)
