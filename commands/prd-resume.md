---
description: Recover context and resume PRD implementation after crash or new session
---

# PRD Resume - Context Recovery

Recover context from filesystem and resume PRD implementation.

## Instructions

This command recovers state after:
- Session crash or timeout
- Context compaction (`/clear`)
- Starting a new day/session
- Any context loss event

## Recovery Steps

1. **Read PROGRESS.md** for current state:

```bash
if [ -f docs/PROGRESS.md ]; then
    echo "=== PROGRESS.md Found ==="
    cat docs/PROGRESS.md
else
    echo "ERROR: docs/PROGRESS.md not found"
    echo "Cannot recover without progress file."
    exit 1
fi
```

2. **Read PRD.md** for full requirements:

```bash
if [ -f docs/PRD.md ]; then
    echo "=== PRD.md Found ==="
    cat docs/PRD.md
else
    echo "ERROR: docs/PRD.md not found"
    exit 1
fi
```

3. **Check git history** for recent commits:

```bash
echo "=== Recent Git Activity ==="
git log --oneline -10 2>/dev/null || echo "Not a git repository"

echo ""
echo "=== Uncommitted Changes ==="
git status --short 2>/dev/null || echo "Not a git repository"
```

## After Recovery

Once you've read the files, summarize:

1. **Project name** from PRD header
2. **Current phase** from PROGRESS.md Quick Context
3. **Current task** that was in progress
4. **Last completed action**
5. **Any blockers** documented
6. **Next action** to take

Then ask the user if they want to:
- Continue with the current task manually
- Start `/prd-ralph` for autonomous implementation
- Review/modify the PRD first

## Key Principle

**Files are the ONLY source of truth.** Do not hallucinate requirements or progress. Everything must come from:
- `docs/PRD.md`
- `docs/PROGRESS.md`
- Git history
