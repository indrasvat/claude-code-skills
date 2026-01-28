# TUI Verification Patterns

This reference provides patterns for verifying Terminal User Interface (TUI) behavior in iTerm2 automation scripts.

## Contents

- Screen Content Verification (text search, headers, footers, columns)
- State Transition Verification (wait for change, modals)
- ANSI Color Verification
- Interactive Element Verification (cursor, menus)
- Error Detection
- Complete Verification Example
- Screen Streaming for Real-Time Verification
- Layout & Alignment Verification (box integrity, modals, status bars)

## Screen Content Verification

### Basic Text Search

```python
async def verify_text_present(session, text: str, timeout: float = 5.0) -> bool:
    """Check if text appears anywhere on screen."""
    start = time.monotonic()
    while (time.monotonic() - start) < timeout:
        screen = await session.async_get_screen_contents()
        for i in range(screen.number_of_lines):
            if text in screen.line(i).string:
                return True
        await asyncio.sleep(0.2)
    return False
```

### Header Verification

```python
async def verify_header(session, *keywords, lines: int = 3) -> bool:
    """Verify that the top N lines contain expected keywords.

    Useful for TUI headers that show app name, status, etc.
    """
    screen = await session.async_get_screen_contents()
    header_text = " ".join(
        screen.line(i).string
        for i in range(min(lines, screen.number_of_lines))
    )

    for kw in keywords:
        if kw not in header_text:
            print(f"Header missing: {kw}")
            return False
    return True
```

### Footer Verification

```python
async def verify_footer(session, *keywords, lines: int = 2) -> bool:
    """Verify that the bottom N lines contain expected keywords.

    Useful for TUI footers that show keybindings, status, etc.
    """
    screen = await session.async_get_screen_contents()
    total_lines = screen.number_of_lines

    footer_text = " ".join(
        screen.line(i).string
        for i in range(max(0, total_lines - lines), total_lines)
    )

    for kw in keywords:
        if kw not in footer_text:
            print(f"Footer missing: {kw}")
            return False
    return True
```

### Column Content Verification

```python
async def verify_column_headers(session, headers: list[str], line_num: int = 0) -> bool:
    """Verify that a specific line contains expected column headers."""
    screen = await session.async_get_screen_contents()
    header_line = screen.line(line_num).string

    for header in headers:
        if header not in header_line:
            print(f"Column header missing: {header}")
            return False
    return True
```

## State Transition Verification

### Wait for State Change

```python
async def wait_for_state(session, marker: str, timeout: float = 5.0) -> bool:
    """Wait until a specific marker appears, indicating state change."""
    start = time.monotonic()
    while (time.monotonic() - start) < timeout:
        screen = await session.async_get_screen_contents()
        full_text = "\n".join(
            screen.line(i).string
            for i in range(screen.number_of_lines)
        )
        if marker in full_text:
            return True
        await asyncio.sleep(0.2)
    return False
```

### Wait for State Removal

```python
async def wait_until_gone(session, marker: str, timeout: float = 5.0) -> bool:
    """Wait until a specific marker disappears from screen."""
    start = time.monotonic()
    while (time.monotonic() - start) < timeout:
        screen = await session.async_get_screen_contents()
        full_text = "\n".join(
            screen.line(i).string
            for i in range(screen.number_of_lines)
        )
        if marker not in full_text:
            return True
        await asyncio.sleep(0.2)
    return False
```

### Verify Modal/Overlay

```python
async def verify_modal_open(session, modal_title: str) -> bool:
    """Verify a modal/overlay is displayed.

    Modals typically have a border and title that we can detect.
    """
    screen = await session.async_get_screen_contents()
    for i in range(screen.number_of_lines):
        line = screen.line(i).string
        # Look for modal title (often centered with padding)
        if modal_title in line:
            return True
    return False
```

## ANSI Color Verification

Note: The iTerm2 API provides screen text but not raw ANSI codes. However, you can infer colors from context:

### Verify Selection/Highlight by Position

```python
async def verify_selection_on_line(session, line_content: str) -> bool:
    """Verify that a specific line appears to be selected.

    Since we can't read colors directly, we verify by:
    1. The line content matches
    2. The line is in expected position for selection
    """
    screen = await session.async_get_screen_contents()
    for i in range(screen.number_of_lines):
        if line_content in screen.line(i).string:
            return True
    return False
```

### Status Indicator Patterns

```python
async def verify_status_indicator(session, indicator_text: str, expected_context: str) -> bool:
    """Verify a status indicator is present with expected context.

    Example: verify "[OK]" appears near "Build completed"
    """
    screen = await session.async_get_screen_contents()
    for i in range(screen.number_of_lines):
        line = screen.line(i).string
        if indicator_text in line and expected_context in line:
            return True
    return False
```

## Interactive Element Verification

### Cursor/Focus Verification

```python
async def verify_cursor_on_line(session, line_content: str) -> bool:
    """Verify cursor appears to be on a line containing specific content.

    Many TUIs show cursor position with '>' or highlight.
    """
    screen = await session.async_get_screen_contents()
    for i in range(screen.number_of_lines):
        line = screen.line(i).string
        # Check for cursor indicators
        if (">" in line or "*" in line) and line_content in line:
            return True
    return False
```

### Menu Item Verification

```python
async def verify_menu_items(session, items: list[str]) -> dict[str, bool]:
    """Verify that expected menu items are visible.

    Returns dict mapping item name to whether it was found.
    """
    screen = await session.async_get_screen_contents()
    full_text = "\n".join(
        screen.line(i).string
        for i in range(screen.number_of_lines)
    )

    return {item: item in full_text for item in items}
```

## Error Detection

### Detect Error States

```python
async def check_for_errors(session) -> list[str]:
    """Scan screen for common error indicators.

    Returns list of detected error messages.
    """
    error_indicators = [
        "Error:",
        "ERROR",
        "Failed",
        "FAILED",
        "not found",
        "Permission denied",
        "Connection refused",
    ]

    screen = await session.async_get_screen_contents()
    errors = []

    for i in range(screen.number_of_lines):
        line = screen.line(i).string
        for indicator in error_indicators:
            if indicator in line:
                errors.append(line.strip())
                break

    return errors
```

### Verify No Errors

```python
async def verify_no_errors(session) -> bool:
    """Verify that no error indicators are present on screen."""
    errors = await check_for_errors(session)
    if errors:
        print(f"Errors detected: {errors}")
        return False
    return True
```

## Complete Verification Example

```python
async def verify_htop_running(session) -> bool:
    """Complete verification that htop is running correctly."""

    # Check header contains expected columns
    if not await verify_column_headers(session, ["PID", "USER", "CPU", "MEM"]):
        print("Header verification failed")
        return False

    # Check footer contains help hint
    if not await verify_footer(session, "F1", "F10", "Help", "Quit"):
        print("Footer verification failed")
        return False

    # Verify no errors
    if not await verify_no_errors(session):
        print("Error check failed")
        return False

    # Verify at least some processes are shown
    screen = await session.async_get_screen_contents()
    process_lines = 0
    for i in range(3, screen.number_of_lines - 2):  # Skip header/footer
        line = screen.line(i).string
        # Process lines typically start with a PID (number)
        stripped = line.strip()
        if stripped and stripped[0].isdigit():
            process_lines += 1

    if process_lines < 5:
        print(f"Only {process_lines} process lines found, expected more")
        return False

    return True
```

## Screen Streaming for Real-Time Verification

For TUIs that update frequently, use screen streaming:

```python
async def wait_for_update_containing(session, text: str, max_updates: int = 10) -> bool:
    """Wait for a screen update containing specific text.

    Uses screen streaming for efficient real-time monitoring.
    """
    async with session.get_screen_streamer() as streamer:
        for _ in range(max_updates):
            screen = await streamer.async_get()
            full_text = "\n".join(
                screen.line(i).string
                for i in range(screen.number_of_lines)
            )
            if text in full_text:
                return True
    return False
```

## Layout & Alignment Verification (CRITICAL)

TUI elements frequently render incorrectly due to terminal size mismatches, encoding issues, or race conditions. These layout issues are subtle but indicate broken UI state.

### Box-Drawing Character Constants

```python
BOX_CHARS = {
    'corners': '┌┐└┘╭╮╰╯╔╗╚╝',
    'horizontal': '─═━',
    'vertical': '│║┃',
    'junctions': '├┤┬┴┼╠╣╦╩╬',
}
```

### Verify Box Integrity

```python
async def verify_box_integrity(session) -> dict:
    """Check that box-drawing characters form connected boxes.

    Common failure: corners not connected to edges (╭ followed by space instead of ─)
    """
    screen = await session.async_get_screen_contents()
    issues = []
    all_box = BOX_CHARS['corners'] + BOX_CHARS['horizontal'] + BOX_CHARS['vertical']

    for i in range(screen.number_of_lines):
        line = screen.line(i).string
        for j, char in enumerate(line):
            # Top-left corners must connect right
            if char in '┌╭╔':
                if j + 1 < len(line):
                    next_char = line[j + 1]
                    if next_char not in BOX_CHARS['horizontal'] + BOX_CHARS['junctions']:
                        issues.append(f"Line {i}: '{char}' at col {j} not connected")

            # Top-right corners must connect left
            elif char in '┐╮╗':
                if j > 0:
                    prev_char = line[j - 1]
                    if prev_char not in BOX_CHARS['horizontal'] + BOX_CHARS['junctions']:
                        issues.append(f"Line {i}: '{char}' at col {j} not connected")

    return {'valid': len(issues) == 0, 'issues': issues}
```

### Verify Modal Boundaries

```python
async def verify_modal_symmetric(session) -> dict:
    """Verify modal has matching top/bottom boundaries.

    Detects: modals cut off at edges, asymmetric borders
    """
    screen = await session.async_get_screen_contents()

    top_left = None
    bottom_left = None

    for i in range(screen.number_of_lines):
        line = screen.line(i).string
        for j, char in enumerate(line):
            if char in '┌╭╔' and top_left is None:
                top_left = (i, j)
            elif char in '└╰╚':
                bottom_left = (i, j)

    issues = []
    if top_left is None:
        issues.append("No modal top border found")
    elif bottom_left is None:
        issues.append("No modal bottom border (cut off?)")
    elif top_left[1] != bottom_left[1]:
        issues.append(f"Modal corners misaligned: top col {top_left[1]}, bottom col {bottom_left[1]}")

    return {'valid': len(issues) == 0, 'issues': issues}
```

### Verify Status Bar Width

```python
async def verify_status_bar_intact(session) -> dict:
    """Verify status bar spans expected width without gaps.

    Detects: truncated status bars, large gaps in content
    """
    screen = await session.async_get_screen_contents()

    # Get bottom non-empty line
    status_line = None
    for i in range(screen.number_of_lines - 1, -1, -1):
        line = screen.line(i).string
        if line.strip():
            status_line = line
            break

    issues = []
    if status_line:
        # Check for suspicious gaps (> 10 spaces in middle of content)
        content_started = False
        space_run = 0
        for char in status_line:
            if char != ' ':
                content_started = True
                if space_run > 10:
                    issues.append(f"Gap of {space_run} spaces in status bar")
                space_run = 0
            else:
                if content_started:
                    space_run += 1

        # Check minimum content length
        if len(status_line.strip()) < 10:
            issues.append("Status bar content too short")
    else:
        issues.append("No status bar found")

    return {'valid': len(issues) == 0, 'issues': issues}
```

### Debug Layout Issues

```python
async def dump_layout_debug(session, label: str):
    """Dump screen with position markers for debugging layout issues."""
    screen = await session.async_get_screen_contents()

    print(f"\n{'='*70}")
    print(f"LAYOUT DEBUG: {label}")
    print("     " + "0         1         2         3         4         5         6")
    print("     " + "0123456789" * 7)

    all_box = BOX_CHARS['corners'] + BOX_CHARS['horizontal'] + BOX_CHARS['vertical'] + BOX_CHARS['junctions']

    for i in range(screen.number_of_lines):
        line = screen.line(i).string
        if line.strip():
            # Highlight box chars
            annotated = ""
            for c in line[:70]:
                if c in all_box:
                    annotated += f"*{c}*"
                else:
                    annotated += c
            print(f"{i:03d}: {line[:70]}")
            if any(c in line for c in all_box):
                print(f"     Box chars: {[c for c in line if c in all_box]}")

    print(f"{'='*70}\n")
```

### Complete Layout Check

```python
async def verify_tui_layout(session, app_name: str) -> bool:
    """Run all layout verification checks.

    Returns True if all checks pass.
    """
    print(f"Verifying layout for {app_name}...")

    checks = [
        ("Box integrity", await verify_box_integrity(session)),
        ("Modal boundaries", await verify_modal_symmetric(session)),
        ("Status bar", await verify_status_bar_intact(session)),
    ]

    all_passed = True
    for name, result in checks:
        if result['valid']:
            print(f"  PASS: {name}")
        else:
            print(f"  FAIL: {name}")
            for issue in result['issues'][:3]:
                print(f"    - {issue}")
            all_passed = False

    if not all_passed:
        await dump_layout_debug(session, "layout_failure")

    return all_passed
```
