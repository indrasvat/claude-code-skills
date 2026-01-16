# Progress: {PROJECT_NAME}

## Quick Context (Read This First!)

| Field | Value |
|-------|-------|
| **Current Phase** | Phase {N} - {phase name} |
| **Current Task** | Task {X.Y} - {task description} |
| **Blocker** | None / {description} |
| **Last Action** | {what was just completed} |
| **Last Updated** | {timestamp} |

---

## Environment

| Field | Value |
|-------|-------|
| **Working Directory** | {absolute path} |
| **Git Branch** | {branch name} |
| **Last Commit** | {short hash} - {message} |

---

## Progress Tracker

### Completed

{Tasks move here when done, with commit hash}

- [x] **Task 1.1**: {description} — `{commit hash}`
- [x] **Task 1.2**: {description} — `{commit hash}`

### In Progress

{Only ONE task should be here at a time}

- [ ] **Task {X.Y}**: {description}
  - **Started**: {timestamp}
  - **Status**: {current progress details}
  - **Files Modified**: {list of files}
  - **Notes**: {any important context}

### Pending

{Tasks waiting to be started}

- [ ] **Task {X.Y}**: {description}
- [ ] **Task {X.Y}**: {description}
- [ ] **Task {X.Y}**: {description}

---

## Critical Context (Preserve Across Sessions!)

### Architecture Decisions Made

{Decisions that affect future implementation - don't repeat research}

- **{Decision 1}**: {rationale}
- **{Decision 2}**: {rationale}

### Known Issues / Workarounds

{Problems encountered and how they were solved}

- **{Issue}**: {workaround applied}

### Important File Locations

{Quick reference to key files}

| Purpose | Path |
|---------|------|
| Main entry | `{path}` |
| Config | `{path}` |
| Tests | `{path}` |
| Types/Models | `{path}` |

### Dependencies Added

{Track what was installed}

- `{package}` - {purpose}

---

## Blockers

{Tasks that couldn't be completed - document for human intervention}

| Task | Blocker | Attempts | Last Tried |
|------|---------|----------|------------|
| {task} | {description} | {N} | {timestamp} |

---

## Recovery Instructions

**If resuming after a crash, context loss, or new session:**

1. **Read this file first** - Quick Context section has current state
2. **Read PRD**: `cat docs/PRD.md` - understand full requirements
3. **Check git log**: `git log --oneline -10` - see recent commits
4. **Check git status**: `git status` - see uncommitted changes
5. **Current task is**: Task {X.Y} - {description}
6. **Next action should be**: {specific next step}

**Important Context to Remember:**
- {Key context 1 that would be lost without this note}
- {Key context 2}

---

## Session History

{Log of what happened in each session}

| Timestamp | Event | Details |
|-----------|-------|---------|
| {YYYY-MM-DD HH:MM} | Session Start | Initial PRD creation |
| {YYYY-MM-DD HH:MM} | Task Complete | Task 1.1 - {description} |
| {YYYY-MM-DD HH:MM} | Commit | `{hash}` - {message} |
| {YYYY-MM-DD HH:MM} | Blocker | Task 2.3 - {issue} |
| {YYYY-MM-DD HH:MM} | Context Loss | Recovered via PROGRESS.md |

---

## Notes

{Freeform notes that don't fit elsewhere}

- {Note 1}
- {Note 2}
