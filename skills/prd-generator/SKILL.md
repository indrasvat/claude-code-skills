---
name: prd-generator
description: Generate comprehensive Product Requirements Documents with interactive discovery, progress tracking, and True Ralph Loop support for autonomous implementation. Use when user wants to (1) create a PRD for a new project/feature, (2) implement a PRD autonomously with fresh Claude sessions, (3) track implementation progress, (4) recover context after session loss. Creates docs/PRD.md and docs/PROGRESS.md.
---

# PRD Generator with True Ralph Loop

Generate production-quality PRDs through interactive discovery, then implement autonomously using fresh Claude sessions (True Ralph Loop).

## When to Use

- User says: "create PRD", "generate PRD", "new project", "write requirements", "plan feature"
- User wants to implement a PRD autonomously: "implement PRD", "start ralph loop", "autonomous mode"
- User needs to check progress: "PRD status", "what's left", "implementation progress"
- User returns after break/crash: "where was I", "resume", "continue from last session"

## Phase 1: Discovery (Interactive Q&A)

Before generating a PRD, gather comprehensive requirements through adaptive questioning.

### Question Flow

Ask questions ONE AT A TIME. Adapt based on answers. Minimum 8 questions before PRD generation.

**Problem Space (Start Here)**

1. **What problem are you solving?**
   - Ask about pain points, current workarounds, why existing solutions don't work
   - Follow-up: "Who experiences this problem most acutely?"

2. **Who is the target user?**
   - Technical level, frequency of use, environment (mobile/desktop/CLI)
   - Follow-up: "What's their current workflow without this solution?"

3. **What does success look like?**
   - Measurable outcomes, KPIs, "how will you know this worked?"
   - Follow-up: "What would make users choose this over alternatives?"

**Technical Context (Adapt Based on Problem)**

4. **What's the tech stack?**
   - Languages, frameworks, databases, deployment target
   - If existing codebase: "Can you point me to the repo or key files?"

5. **Any existing codebase to integrate with?**
   - If yes: Explore architecture, patterns, conventions
   - Ask Claude to read key files to understand context

6. **Scale and performance requirements?**
   - Expected users, requests/sec, data volume
   - "Any hard latency or uptime requirements?"

**Scope & Constraints**

7. **What's explicitly OUT of scope?**
   - MVP boundaries, "what are we NOT building?"
   - Future phases vs current scope

8. **Non-functional requirements?**
   - Security (auth, encryption, compliance)
   - Accessibility, i18n, offline support
   - "Any regulatory requirements?"

9. **External dependencies?**
   - APIs, auth providers, third-party services
   - "Any rate limits or costs to consider?"

**Verification**

10. **How will we test this?**
    - Unit, integration, e2e strategies
    - "Any specific test frameworks in use?"

11. **What does 'done' look like?**
    - Acceptance criteria for launch
    - "What would block a release?"

12. **Known edge cases or error scenarios?**
    - Failure modes, error handling expectations
    - "What happens when X fails?"

### Completeness Check

Before generating PRD, verify each section has sufficient detail:

| Section | Required Info |
|---------|--------------|
| Problem | Clear pain points, user impact |
| Users | Persona, technical level, workflow |
| Success | Measurable metrics |
| Tech | Stack, architecture decisions |
| Scope | In/out of scope explicit |
| Testing | Strategy defined |
| Done | Acceptance criteria clear |

If any section is sparse, ask targeted follow-ups.

## Phase 2: PRD Generation

Once discovery is complete, generate `docs/PRD.md`:

```bash
mkdir -p docs
```

Use the template in [`templates/PRD-TEMPLATE.md`](templates/PRD-TEMPLATE.md).

**Critical PRD Requirements:**
- Every task must have a checkbox: `- [ ] Task description`
- Group tasks into numbered phases (Phase 1, Phase 2, etc.)
- Each task ID format: `Task X.Y` (e.g., Task 1.1, Task 2.3)
- Include testable acceptance criteria for each user story
- Explicit "Out of Scope" section to prevent scope creep

## Phase 3: PROGRESS.md Creation

Immediately after PRD, create `docs/PROGRESS.md`:

Use the template in [`templates/PROGRESS-TEMPLATE.md`](templates/PROGRESS-TEMPLATE.md).

**Critical PROGRESS.md Requirements:**
- "Quick Context" section at top for instant orientation
- Current task clearly identified
- Recovery instructions for context loss scenarios
- Session history log for debugging

## Phase 4: True Ralph Loop (Autonomous Implementation)

### Why "True Ralph"?

The official Anthropic Ralph plugin uses a Stop hook that keeps Claude in the SAME session. This causes:
- Context rot from compaction over time
- "Ralph Wiggum state" - confusion from accumulated noise
- Degraded output quality after many iterations

**True Ralph** (Geoffrey Huntley's original vision) spawns FRESH Claude sessions:
- Each iteration has full context capacity
- No accumulated noise from previous attempts
- State persists only through files (PRD.md, PROGRESS.md, git)

### Mode 1: External Script (Recommended)

When user wants to start Ralph loop, explain clearly:

```
True Ralph requires fresh Claude sessions OUTSIDE of this conversation.
This cannot run from within Claude - you need to run it from your terminal.

1. Open a NEW terminal window

2. Navigate to your project:
   cd [PROJECT_PATH]

3. Run the True Ralph Loop:
   ~/.claude/plugins/indrasvat-skills/skills/prd-generator/scripts/true-ralph-loop.sh -n [ITERATIONS]

4. Monitor progress:
   - Watch terminal output
   - Check docs/PROGRESS.md
   - View logs in .ralph/logs/

5. Stop gracefully: Ctrl+C
```

Before handing off:
1. Validate docs/PRD.md exists and has tasks
2. Ensure docs/PROGRESS.md exists
3. Verify git repo if applicable
4. Output the exact command to run

### Mode 2: tmux Detach

If user prefers tmux and it's available:

```bash
# Check tmux availability
command -v tmux &>/dev/null || { echo "tmux not installed"; exit 1; }

# Get project name for session naming
PROJECT_NAME=$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')

# Spawn detached session
tmux new-session -d -s "ralph-${PROJECT_NAME}" \
  "~/.claude/plugins/indrasvat-skills/skills/prd-generator/scripts/true-ralph-loop.sh -n [ITERATIONS]"

echo "Ralph loop started in tmux session: ralph-${PROJECT_NAME}"
echo "Attach: tmux attach -t ralph-${PROJECT_NAME}"
echo "Kill:   tmux kill-session -t ralph-${PROJECT_NAME}"
```

## Phase 5: Status Check

When user asks about progress:

```bash
echo "=== PRD Status ==="
if [ -f docs/PRD.md ]; then
    TOTAL=$(grep -c '^\- \[' docs/PRD.md 2>/dev/null || echo "0")
    DONE=$(grep -c '^\- \[x\]' docs/PRD.md 2>/dev/null || echo "0")
    PENDING=$(grep -c '^\- \[ \]' docs/PRD.md 2>/dev/null || echo "0")
    echo "Total tasks:     $TOTAL"
    echo "Completed:       $DONE"
    echo "Pending:         $PENDING"
    if [ "$TOTAL" -gt 0 ]; then
        PCT=$((DONE * 100 / TOTAL))
        echo "Progress:        $PCT%"
    fi
else
    echo "No PRD found at docs/PRD.md"
fi

echo ""
echo "=== Current State ==="
if [ -f docs/PROGRESS.md ]; then
    head -25 docs/PROGRESS.md
else
    echo "No PROGRESS.md found"
fi
```

## Phase 6: Context Recovery

When user returns after a break, crash, or context loss:

1. **Read PROGRESS.md first** - contains quick context and current task
2. **Read PRD.md** - understand full requirements
3. **Check git log** - see recent commits
4. **Check git status** - see uncommitted changes

```bash
echo "=== Recovering Context ==="
echo ""
if [ -f docs/PROGRESS.md ]; then
    echo "Quick context from PROGRESS.md:"
    head -20 docs/PROGRESS.md
fi

echo ""
echo "Recent git activity:"
git log --oneline -5 2>/dev/null || echo "Not a git repo"

echo ""
echo "Uncommitted changes:"
git status -s 2>/dev/null || echo "Not a git repo"
```

Then summarize:
- Current phase and task
- What was last completed
- What should be done next

## Best Practices

### PRD Writing
- Use checkboxes (`- [ ]`) for ALL actionable items
- Group tasks logically into phases
- Each phase should be independently deployable
- Include "Out of Scope" to prevent creep
- Make acceptance criteria testable

### PROGRESS.md Updates
- Update after EVERY task completion
- Move next pending task to "In Progress"
- Log blockers immediately
- Include relevant file paths and commit hashes

### Ralph Loop Success
- Set realistic `--max-iterations` (start with 10-15)
- Ensure PRD tasks are granular (1-2 hour chunks)
- Each task should be independently verifiable
- Include test commands in PRD when applicable

## Troubleshooting

### "Claude keeps doing the same thing"
- Check PROGRESS.md - is the current task clearly marked?
- Regenerate PROGRESS.md with explicit task state
- Verify PRD tasks are actually checkboxed

### "Ralph loop stops unexpectedly"
- Check `.ralph/logs/` for the last iteration log
- Verify `claude` CLI is working: `claude --version`
- Check for syntax errors in PROGRESS.md

### "Lost context after compaction"
- This is normal - use PROGRESS.md for recovery
- Run context recovery steps above
- The whole point of True Ralph is to handle this gracefully

## See Also

- [`templates/PRD-TEMPLATE.md`](templates/PRD-TEMPLATE.md) - Full PRD template
- [`templates/PROGRESS-TEMPLATE.md`](templates/PROGRESS-TEMPLATE.md) - Full progress template
- [`scripts/true-ralph-loop.sh`](scripts/true-ralph-loop.sh) - The True Ralph Loop script
- [`references/discovery-questions.md`](references/discovery-questions.md) - Extended question bank
