---
description: Start True Ralph Loop to implement PRD with fresh Claude sessions
argument-hint: "[--max-iterations N] [--external|-e] [--tmux|-t]"
---

# True Ralph Loop

Start autonomous PRD implementation using fresh Claude sessions.

## Why "True Ralph"?

Unlike Anthropic's Ralph plugin (which uses a Stop hook in the SAME session, causing context rot), True Ralph spawns **FRESH Claude sessions** for each iteration. This prevents context pollution and ensures each iteration has full context capacity.

State persists ONLY through filesystem artifacts:
- `docs/PRD.md` - Requirements with checkboxes
- `docs/PROGRESS.md` - Current task and progress
- Git commits - Code history

## Prerequisites

Before starting, verify:
1. `docs/PRD.md` exists (run `/prd` first)
2. `docs/PROGRESS.md` exists
3. Git repository is initialized
4. Claude CLI is installed

## Modes

### Mode 1: External Script (Default, Recommended)

This is the purest approach - you run the script from a separate terminal.

```bash
# Validate PRD exists
if [ ! -f docs/PRD.md ]; then
    echo "ERROR: docs/PRD.md not found. Run /prd first."
    exit 1
fi

# Show instructions
cat << 'EOF'

TRUE RALPH LOOP - EXTERNAL MODE

IMPORTANT: True Ralph requires running a script OUTSIDE of this Claude session.
Each iteration needs a FRESH Claude session with full context capacity.

INSTRUCTIONS:

1. Open a NEW terminal window

2. Navigate to your project:
   cd $(pwd)

3. Run the True Ralph Loop:
   ${CLAUDE_PLUGIN_ROOT}/skills/prd-generator/scripts/true-ralph-loop.sh -n 10

4. Monitor progress:
   - Watch the terminal output
   - Check docs/PROGRESS.md for current state
   - View logs in .ralph/logs/

5. To stop gracefully: Press Ctrl+C

EOF
```

### Mode 2: tmux Detach

Spawns a detached tmux session so this session can continue.

```bash
# Check tmux
if ! command -v tmux &> /dev/null; then
    echo "ERROR: tmux not installed. Install with: brew install tmux"
    exit 1
fi

# Get project name for session
PROJECT_NAME=$(basename "$(pwd)" | tr '.' '-')
SESSION_NAME="ralph-${PROJECT_NAME}"

# Check if session already exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Session '$SESSION_NAME' already running."
    echo "Attach with: tmux attach -t $SESSION_NAME"
    echo "Kill with:   tmux kill-session -t $SESSION_NAME"
    exit 1
fi

# Start detached session
tmux new-session -d -s "$SESSION_NAME" \
    "${CLAUDE_PLUGIN_ROOT}/skills/prd-generator/scripts/true-ralph-loop.sh -n ${1:-10}"

echo "Started tmux session: $SESSION_NAME"
echo ""
echo "Commands:"
echo "  Attach:  tmux attach -t $SESSION_NAME"
echo "  Detach:  Ctrl+B, then D (while attached)"
echo "  Status:  cat docs/PROGRESS.md"
echo "  Kill:    tmux kill-session -t $SESSION_NAME"
```

## Usage

Present both options to the user and help them choose:

1. **External Script** (recommended for pure Huntley approach)
   - User runs script in separate terminal
   - This session exits to free resources

2. **tmux Detach** (convenient for background execution)
   - Script runs in detached tmux session
   - This session continues normally

Ask which mode the user prefers, then provide the appropriate instructions or run the tmux command.
