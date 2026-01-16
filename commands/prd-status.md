---
description: Show current PRD implementation status and progress
---

# PRD Status Check

Check the current status of PRD implementation.

## Instructions

1. Check if `docs/PRD.md` exists
2. Check if `docs/PROGRESS.md` exists
3. Count completed vs pending tasks in PRD.md
4. Show current task from PROGRESS.md
5. Display a summary

## Implementation

```bash
echo "=== PRD Status ==="
echo ""

if [ -f docs/PRD.md ]; then
    completed=$(grep -c '^\- \[x\]' docs/PRD.md 2>/dev/null || echo "0")
    pending=$(grep -c '^\- \[ \]' docs/PRD.md 2>/dev/null || echo "0")
    total=$((completed + pending))

    echo "PRD File: docs/PRD.md"
    echo "  Completed: $completed tasks"
    echo "  Pending:   $pending tasks"
    echo "  Total:     $total tasks"

    if [ $total -gt 0 ]; then
        pct=$((completed * 100 / total))
        echo "  Progress:  ${pct}%"
    fi
else
    echo "PRD File: Not found"
    echo "  Run /prd to generate a PRD"
fi

echo ""
echo "=== Current State ==="
echo ""

if [ -f docs/PROGRESS.md ]; then
    echo "Progress File: docs/PROGRESS.md"
    echo ""
    # Show Quick Context section
    sed -n '/## Quick Context/,/^---/p' docs/PROGRESS.md | head -15
else
    echo "Progress File: Not found"
fi

echo ""
echo "=== Recent Git Activity ==="
git log --oneline -5 2>/dev/null || echo "Not a git repository"
```

Run this script and present the results in a formatted summary.
