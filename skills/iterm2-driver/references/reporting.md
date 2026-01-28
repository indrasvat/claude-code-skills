# Test Reporting Patterns

This reference provides patterns for structured test reporting in iTerm2 automation scripts.

## Contents

- Basic Result Tracking (result dictionary, log functions)
- Visual Output Formatting (headers, suite headers)
- Summary Report (basic, detailed)
- JSON Report Export
- CI/CD Integration (exit codes, JUnit XML)
- Complete Reporting Example

## Basic Result Tracking

### Result Dictionary

```python
# Initialize at script start
results = {
    "passed": 0,
    "failed": 0,
    "unverified": 0,
    "skipped": 0,
    "tests": [],
    "screenshots": [],
    "start_time": None,
    "end_time": None,
}
```

### Log Result Function

```python
from datetime import datetime

def log_result(test_name: str, status: str, details: str = "", screenshot: str = None):
    """Log a test result with optional details and screenshot reference.

    Args:
        test_name: Name of the test
        status: "PASS", "FAIL", "UNVERIFIED", or "SKIP"
        details: Additional details about the result
        screenshot: Path to related screenshot if any
    """
    timestamp = datetime.now().isoformat()

    test_record = {
        "name": test_name,
        "status": status,
        "details": details,
        "timestamp": timestamp,
        "screenshot": screenshot,
    }
    results["tests"].append(test_record)

    if screenshot:
        results["screenshots"].append(screenshot)

    # Update counts
    if status == "PASS":
        results["passed"] += 1
        symbol = "+"
    elif status == "FAIL":
        results["failed"] += 1
        symbol = "x"
    elif status == "SKIP":
        results["skipped"] += 1
        symbol = "-"
    else:
        results["unverified"] += 1
        symbol = "?"

    # Print to console
    print(f"  [{symbol}] {status}: {test_name}")
    if details:
        print(f"      {details}")
    if screenshot:
        print(f"      Screenshot: {screenshot}")
```

## Visual Output Formatting

### Test Section Headers

```python
def print_test_header(test_name: str, test_num: int = None):
    """Print a visual header for a test section."""
    if test_num:
        header = f"TEST {test_num}: {test_name}"
    else:
        header = f"TEST: {test_name}"

    print("\n" + "=" * 60)
    print(header)
    print("=" * 60)


def print_subsection(name: str):
    """Print a subsection header within a test."""
    print(f"\n  --- {name} ---")
```

### Test Suite Header

```python
def print_suite_header(suite_name: str, description: str = ""):
    """Print header for entire test suite."""
    print("\n" + "#" * 60)
    print(f"# TEST SUITE: {suite_name}")
    if description:
        print(f"# {description}")
    print("#" * 60)
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#" * 60 + "\n")

    results["start_time"] = datetime.now()
```

## Summary Report

### Basic Summary

```python
def print_summary() -> int:
    """Print final test summary and return exit code."""
    results["end_time"] = datetime.now()

    total = results["passed"] + results["failed"] + results["unverified"] + results["skipped"]
    duration = (results["end_time"] - results["start_time"]).total_seconds() if results["start_time"] else 0

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Duration:   {duration:.1f}s")
    print(f"Total:      {total}")
    print(f"Passed:     {results['passed']}")
    print(f"Failed:     {results['failed']}")
    print(f"Unverified: {results['unverified']}")
    print(f"Skipped:    {results['skipped']}")

    if results["screenshots"]:
        print(f"Screenshots: {len(results['screenshots'])}")

    print("=" * 60)

    # List failures
    if results["failed"] > 0:
        print("\nFAILED TESTS:")
        for test in results["tests"]:
            if test["status"] == "FAIL":
                print(f"  x {test['name']}")
                if test["details"]:
                    print(f"    Reason: {test['details']}")
                if test["screenshot"]:
                    print(f"    Screenshot: {test['screenshot']}")

    # List unverified
    if results["unverified"] > 0:
        print("\nUNVERIFIED TESTS:")
        for test in results["tests"]:
            if test["status"] == "UNVERIFIED":
                print(f"  ? {test['name']}: {test['details']}")

    # Overall status
    print("\n" + "-" * 60)
    if results["failed"] > 0:
        print("OVERALL: FAILED")
        return 1
    elif results["unverified"] > 0:
        print("OVERALL: PASSED (with unverified)")
        return 0
    else:
        print("OVERALL: PASSED")
        return 0
```

### Detailed Report

```python
def print_detailed_report():
    """Print detailed report with all test information."""
    print("\n" + "=" * 60)
    print("DETAILED TEST REPORT")
    print("=" * 60)

    for i, test in enumerate(results["tests"], 1):
        status_symbol = {
            "PASS": "+",
            "FAIL": "x",
            "UNVERIFIED": "?",
            "SKIP": "-"
        }.get(test["status"], "?")

        print(f"\n{i}. [{status_symbol}] {test['name']}")
        print(f"   Status: {test['status']}")
        print(f"   Time: {test['timestamp']}")
        if test["details"]:
            print(f"   Details: {test['details']}")
        if test["screenshot"]:
            print(f"   Screenshot: {test['screenshot']}")
```

## JSON Report Export

```python
import json

def export_json_report(filepath: str):
    """Export test results as JSON for CI/CD integration."""
    report = {
        "suite": "iTerm2 TUI Test",
        "start_time": results["start_time"].isoformat() if results["start_time"] else None,
        "end_time": results["end_time"].isoformat() if results["end_time"] else None,
        "summary": {
            "total": results["passed"] + results["failed"] + results["unverified"] + results["skipped"],
            "passed": results["passed"],
            "failed": results["failed"],
            "unverified": results["unverified"],
            "skipped": results["skipped"],
        },
        "tests": results["tests"],
        "screenshots": results["screenshots"],
    }

    with open(filepath, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nJSON report exported to: {filepath}")
```

## CI/CD Integration

### Exit Code Handling

```python
def get_exit_code() -> int:
    """Get appropriate exit code for CI/CD.

    Returns:
        0: All tests passed (or passed with unverified)
        1: One or more tests failed
    """
    if results["failed"] > 0:
        return 1
    return 0
```

### JUnit XML Export (for CI systems)

```python
def export_junit_xml(filepath: str):
    """Export test results as JUnit XML for CI systems."""
    from xml.etree.ElementTree import Element, SubElement, tostring
    from xml.dom import minidom

    testsuite = Element("testsuite")
    testsuite.set("name", "iTerm2 TUI Test")
    testsuite.set("tests", str(len(results["tests"])))
    testsuite.set("failures", str(results["failed"]))
    testsuite.set("errors", "0")
    testsuite.set("skipped", str(results["skipped"]))

    for test in results["tests"]:
        testcase = SubElement(testsuite, "testcase")
        testcase.set("name", test["name"])
        testcase.set("classname", "iTerm2Test")

        if test["status"] == "FAIL":
            failure = SubElement(testcase, "failure")
            failure.set("message", test["details"] or "Test failed")
            failure.text = test["details"]
        elif test["status"] == "SKIP":
            skipped = SubElement(testcase, "skipped")
            if test["details"]:
                skipped.set("message", test["details"])

    xml_str = minidom.parseString(tostring(testsuite)).toprettyxml(indent="  ")
    with open(filepath, "w") as f:
        f.write(xml_str)

    print(f"\nJUnit XML report exported to: {filepath}")
```

## Complete Reporting Example

```python
async def main(connection):
    # Initialize
    print_suite_header("htop TUI Test", "Automated testing of htop interface")

    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window
    if not window:
        log_result("Setup", "FAIL", "No active window")
        return print_summary()

    tab = await window.async_create_tab()
    session = tab.current_session

    try:
        # Test 1
        print_test_header("Launch htop", 1)
        await session.async_send_text("htop\n")
        await asyncio.sleep(1.0)

        if await verify_screen_contains(session, "CPU", "CPU visible"):
            screenshot = capture_screenshot("htop_launch")
            log_result("Launch htop", "PASS", screenshot=screenshot)
        else:
            screenshot = capture_screenshot("htop_launch_fail")
            log_result("Launch htop", "FAIL", "CPU column not visible", screenshot=screenshot)

        # Test 2
        print_test_header("Help screen", 2)
        await session.async_send_text("?")
        await asyncio.sleep(0.5)

        if await verify_screen_contains(session, "Help", "Help visible"):
            log_result("Help screen", "PASS")
        else:
            log_result("Help screen", "FAIL", "Help not displayed")

        await session.async_send_text("q")  # Close help

        # Test 3
        print_test_header("Quit htop", 3)
        await session.async_send_text("q")
        await asyncio.sleep(0.5)
        log_result("Quit htop", "PASS")

    except Exception as e:
        log_result("Execution", "FAIL", str(e))

    finally:
        await cleanup_session(session)

        # Generate reports
        exit_code = print_summary()
        print_detailed_report()
        export_json_report("./test-results.json")

        return exit_code


if __name__ == "__main__":
    exit_code = iterm2.run_until_complete(main)
    exit(exit_code if exit_code else 0)
```
