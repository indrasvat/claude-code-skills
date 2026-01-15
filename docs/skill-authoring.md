# Skill Authoring Guide

A comprehensive guide to creating high-quality Claude Code skills.

## Table of Contents

- [Quick Start](#quick-start)
- [Skill Structure](#skill-structure)
- [YAML Frontmatter](#yaml-frontmatter)
- [Content Guidelines](#content-guidelines)
- [Examples and Patterns](#examples-and-patterns)
- [Script Management](#script-management)
- [Testing](#testing)
- [Best Practices](#best-practices)

## Quick Start

### 1. Create Skill Directory

```bash
mkdir -p skills/my-skill-name
cd skills/my-skill-name
```

### 2. Create SKILL.md with Frontmatter

```markdown
---
name: my-skill-name
description: Brief description of what this skill does and when to use it.
---

# My Skill Name

Detailed instructions for Claude on how to use this skill...

## Core Concepts

- Key concept 1
- Key concept 2

## Examples

### Example 1: Basic Usage

\`\`\`python
# Example code here
\`\`\`
```

### 3. Test Your Skill

Test the plugin locally:

```bash
claude --plugin-dir /path/to/claude-code-skills
```

Then ask Claude questions that should trigger the skill.

## Skill Structure

### Minimal Structure (Single File)

```
my-skill-name/
└── SKILL.md
```

Use this for focused skills that can fit in <500 lines.

### Modular Structure (Multiple Files)

```
my-skill-name/
├── SKILL.md           # Core instructions and overview
├── examples.md        # Extended examples
├── reference.md       # API reference, tables, specs
└── examples/          # Runnable scripts
    ├── 01-basic.py
    └── 02-advanced.py
```

Use this for complex skills with extensive documentation.

## YAML Frontmatter

Every SKILL.md must start with YAML frontmatter:

```yaml
---
name: skill-name
description: What it does and when to use it.
---
```

### Required Fields

#### `name`
- **Format**: lowercase, hyphens only, no spaces
- **Max length**: 64 characters
- **Pattern**: `^[a-z0-9-]+$`
- **Examples**:
  - ✅ `iterm2-driver`
  - ✅ `pdf-processor`
  - ✅ `api-client-generator`
  - ❌ `iTerm2Driver` (uppercase)
  - ❌ `pdf_processor` (underscore)
  - ❌ `api client` (space)

#### `description`
- **Max length**: 1024 characters
- **Voice**: Third person
- **Must include**:
  - WHAT the skill does
  - WHEN to use it
- **Examples**:
  - ✅ "Drive iTerm2 programmatically using Python scripts to automate terminal tasks, run tests, or manage sessions."
  - ✅ "Extract text and tables from PDF files. Use when working with PDFs or document extraction."
  - ❌ "A helpful utility" (too vague)
  - ❌ "Use this to work with PDFs" (missing WHAT)

### Optional Fields

#### `allowed-tools`
Restrict which tools the skill can use:

```yaml
---
name: read-only-analyzer
description: Analyze code without making changes.
allowed-tools:
  - Read
  - Grep
  - Glob
---
```

## Content Guidelines

### Keep It Under 500 Lines

For optimal performance, keep SKILL.md under 500 lines. If you have more content:

1. **Move examples to `examples.md`**
2. **Move reference material to `reference.md`**
3. **Create domain-specific files** (e.g., `reference/finance.md`, `reference/sales.md`)

### Progressive Disclosure

Structure content from general to specific:

```markdown
# Skill Name

High-level overview and key capabilities.

## Core Concepts

Essential concepts Claude needs to understand.

## Basic Patterns

Simple examples showing fundamental usage.

## Advanced Patterns

Complex examples for sophisticated use cases.

## Reference

Link to detailed reference material if needed.
```

### Use Concrete Examples

Claude learns best from concrete examples. Include:

- **Full code samples** (not pseudocode)
- **Real-world scenarios** (not abstract patterns)
- **Expected outputs** (show what success looks like)
- **Common pitfalls** (show what to avoid)

### Example Structure

```markdown
### Example 1: Create a Simple Layout

This example creates a 2-pane vertical split.

\`\`\`python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "iterm2",
# ]
# ///

import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_terminal_window

    if window:
        tab = await window.async_create_tab()
        session = tab.current_session
        await session.async_split_pane(vertical=True)

if __name__ == "__main__":
    iterm2.run_until_complete(main)
\`\`\`

**Expected Result**: A new tab with two side-by-side panes.
```

## Examples and Patterns

### Number Your Examples

Use sequential numbering for easy reference:

```markdown
### Example 1: Basic Usage
### Example 2: Intermediate Pattern
### Example 3: Advanced Workflow
```

This allows users to say "run example 2" and makes the skill more navigable.

### Include Runnable Scripts

Place standalone scripts in `examples/` directory:

```
examples/
├── 01-basic.py
├── 02-intermediate.py
└── 03-advanced.py
```

Each script should:
- Include uv metadata for dependencies
- Have a descriptive docstring
- Be runnable with `uv run`
- Correspond to examples in SKILL.md

### Pattern Templates

For common patterns, include reusable templates:

```markdown
## Cleanup Pattern

Always clean up resources when done:

\`\`\`python
try:
    # Do work
    result = await do_something()
finally:
    # Cleanup
    await cleanup_resources()
\`\`\`
```

## Script Management

### Use Inline Dependency Management

For Python scripts, use uv metadata:

```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "requests",
#   "rich",
# ]
# ///

import requests
from rich.console import Console

# Script code here...
```

### Script Storage Guidance

Provide clear guidance on where to store generated scripts:

```markdown
## Script Storage

### Project-Specific Scripts
Store in `./.claude/automations/{script_name}.py` for:
- Project builds
- Local tests
- Project-specific automation

### General Utilities
Store in `~/.claude/automations/{script_name}.py` for:
- System monitoring
- Generic layouts
- Reusable tools
```

### Execution Instructions

Always specify how to run scripts:

```markdown
## Running Scripts

All scripts use uv for dependency management:

\`\`\`bash
uv run script_name.py
\`\`\`

Never use `python script_name.py` directly.
```

## Testing

### Test Your Skill

Before committing, test that:

1. **Claude can find it**: Ask questions that should trigger the skill
2. **Examples work**: Run all example scripts to verify they execute
3. **Instructions are clear**: Ask Claude to perform tasks using the skill
4. **Error handling works**: Try edge cases and verify graceful failures

### Test Queries

Create a list of test queries that should trigger your skill:

```markdown
<!-- Test Queries (not shown to Claude) -->
<!--
- "Create a 3-pane layout in iTerm2"
- "Drive the Python REPL in iTerm2"
- "Automate nano editor"
-->
```

### Validation Checklist

- [ ] YAML frontmatter is valid
- [ ] `name` follows lowercase-hyphen convention
- [ ] `description` includes WHAT and WHEN
- [ ] Content is under 500 lines (or split appropriately)
- [ ] Examples are concrete and runnable
- [ ] All example scripts execute successfully
- [ ] Error handling is included
- [ ] File paths use forward slashes (Unix-style)

## Best Practices

### 1. Be Specific

❌ **Vague**: "Use this for automation"
✅ **Specific**: "Drive iTerm2 programmatically to automate terminal tasks, run tests in specific layouts, or manage long-running sessions"

### 2. Show, Don't Tell

❌ **Abstract**: "You can create layouts"
✅ **Concrete**:
```python
# Create 4-pane dev layout
session_tl = tab.current_session
session_tr = await session_tl.async_split_pane(vertical=True)
```

### 3. Include Error Handling

Always show how to handle common errors:

```python
if window is None:
    print("No active window found")
    return

if not session:
    print("Failed to create session")
    return
```

### 4. Use Forward Slashes

Always use Unix-style paths (works cross-platform):

✅ `~/.claude/automations/script.py`
❌ `~\.claude\automations\script.py`

### 5. Keep References Shallow

Only one level of file references:

✅ SKILL.md → examples.md (one level)
❌ SKILL.md → examples.md → advanced.md (two levels)

### 6. Assume Intelligence

Claude is smart. Don't over-explain basic concepts:

❌ "Functions are reusable blocks of code..."
✅ "Use this function to parse JSON responses:"

### 7. Include Markers

Use unique markers for verification:

```python
# Print a unique marker to verify execution
print(f"MARKER_SUCCESS: {result}")

# Then check for it
if "MARKER_SUCCESS" in screen_contents:
    print("Verified!")
```

### 8. Provide Debugging Patterns

Include patterns for troubleshooting:

```python
# Debug: Dump screen contents
if not found:
    screen = await session.async_get_screen_contents()
    for i in range(screen.number_of_lines):
        print(f"{i:03d}: {screen.line(i).string}")
```

### 9. Use Gerund Naming

Prefer gerund form for action-oriented skills:

✅ `processing-pdfs`, `analyzing-logs`, `monitoring-systems`
❌ `pdf-tool`, `log-helper`, `system-utils`

### 10. Document Tool Dependencies

If your skill requires specific tools:

```markdown
## Prerequisites

This skill requires:
- iTerm2 installed on macOS
- Python 3.13+
- `uv` package manager

To install uv:
\`\`\`bash
curl -LsSf https://astral.sh/uv/install.sh | sh
\`\`\`
```

## Example: Complete Skill Template

```markdown
---
name: my-automation-skill
description: Automate specific tasks using X tool. Use when you need to perform Y operations.
---

# My Automation Skill

This skill enables you to [main capability].

## Prerequisites

- Tool X version Y+
- Dependency Z

## Core Concepts

- **Concept 1**: Brief explanation
- **Concept 2**: Brief explanation

## Basic Usage

### Example 1: Simple Task

[Concrete, runnable example]

### Example 2: Common Pattern

[Another concrete example]

## Advanced Patterns

### Example 3: Complex Workflow

[Advanced example showing sophisticated usage]

## Guidelines

1. Always do X before Y
2. Never do Z without checking A
3. Use B for C scenarios

## Debugging

If things don't work:

\`\`\`python
# Debug pattern here
\`\`\`

## References

- [External Documentation](https://example.com)
- [API Reference](https://api.example.com)
```

## Next Steps

1. Create your skill following this guide
2. Test locally with `claude --plugin-dir /path/to/plugin`
3. Iterate based on real usage
4. Commit and push to share via `/plugin install`

---

For more guidance, see:
- [Best Practices](best-practices.md)
- [Troubleshooting](troubleshooting.md)
- [Agent Skills Overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
