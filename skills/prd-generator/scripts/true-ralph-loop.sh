#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════════
#  TRUE RALPH LOOP - Fresh Session Implementation
#  Based on Geoffrey Huntley's original vision: https://ghuntley.com/ralph/
#
#  Unlike Anthropic's Ralph plugin (same-session Stop hook), this spawns
#  FRESH Claude sessions for each iteration, preventing context rot.
#═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ┌─────────────────────────────────────────────────────────────────────────────┐
# │                              CONFIGURATION                                  │
# └─────────────────────────────────────────────────────────────────────────────┘

VERSION="1.0.0"
SCRIPT_NAME="True Ralph Loop"

# Colors & Formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

# File paths
PRD_FILE="docs/PRD.md"
PROGRESS_FILE="docs/PROGRESS.md"
RALPH_DIR=".ralph"
PROMPT_FILE="$RALPH_DIR/PROMPT.md"
LOG_DIR="$RALPH_DIR/logs"

# Defaults
DEFAULT_MAX_ITERATIONS=10
DEFAULT_PAUSE_SECONDS=3

# ┌─────────────────────────────────────────────────────────────────────────────┐
# │                              DISPLAY FUNCTIONS                              │
# └─────────────────────────────────────────────────────────────────────────────┘

print_banner() {
    echo -e "${CYAN}"
    cat << 'BANNER'

  +=====================================================================+
  |                                                                     |
  |   _____  ____   _   _  _____     ____    _    _     ____   _   _    |
  |  |_   _||  _ \ | | | || ____|   |  _ \  / \  | |   |  _ \ | | | |   |
  |    | |  | |_) || | | ||  _|     | |_) |/ _ \ | |   | |_) || |_| |   |
  |    | |  |  _ < | |_| || |___    |  _ </ ___ \| |___|  __/ |  _  |   |
  |    |_|  |_| \_\ \___/ |_____|   |_| \_\_/  \_\_____|_|    |_| |_|   |
  |                                                                     |
  |              Fresh Sessions  *  No Context Pollution                |
  |              Based on Geoffrey Huntley's Vision                     |
  |                                                                     |
  +=====================================================================+

BANNER
    echo -e "${NC}"
}

print_box() {
    local title="$1"
    local width=72

    echo -e "${BLUE}╔$(printf '═%.0s' $(seq 1 $width))╗${NC}"
    echo -e "${BLUE}║${NC} ${BOLD}${WHITE}$title${NC}$(printf ' %.0s' $(seq 1 $((width - ${#title} - 1))))${BLUE}║${NC}"
    echo -e "${BLUE}╠$(printf '═%.0s' $(seq 1 $width))╣${NC}"

    # Read content from stdin
    while IFS= read -r line || [[ -n "$line" ]]; do
        printf '%b║%b %-72s%b║%b\n' "${BLUE}" "${NC}" "$line" "${BLUE}" "${NC}"
    done

    echo -e "${BLUE}╚$(printf '═%.0s' $(seq 1 $width))╝${NC}"
}

print_progress_bar() {
    local current=$1
    local total=$2
    local width=50

    if [ "$total" -eq 0 ]; then
        echo -e "  ${DIM}No tasks found${NC}"
        return
    fi

    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))

    printf '  %b▐' "${GREEN}"
    for ((i=0; i<filled; i++)); do printf "█"; done
    printf '%b' "${DIM}"
    for ((i=0; i<empty; i++)); do printf "░"; done
    printf '%b%b▌%b' "${NC}" "${GREEN}" "${NC}"
    printf " %3d%% (%d/%d)\n" "$percentage" "$current" "$total"
}

log_info() {
    echo -e "  ${BLUE}ℹ${NC}  $1"
}

log_success() {
    echo -e "  ${GREEN}✓${NC}  $1"
}

log_warning() {
    echo -e "  ${YELLOW}⚠${NC}  $1"
}

log_error() {
    echo -e "  ${RED}✗${NC}  $1"
}

timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

format_duration() {
    local seconds=$1
    if [ "$seconds" -lt 60 ]; then
        echo "${seconds}s"
    elif [ "$seconds" -lt 3600 ]; then
        echo "$((seconds / 60))m $((seconds % 60))s"
    else
        echo "$((seconds / 3600))h $((seconds % 3600 / 60))m"
    fi
}

# ┌─────────────────────────────────────────────────────────────────────────────┐
# │                              VALIDATION                                     │
# └─────────────────────────────────────────────────────────────────────────────┘

validate_environment() {
    local errors=0

    echo ""
    echo -e "  ${BOLD}Validating environment...${NC}"
    echo ""

    # Check for claude CLI
    if command -v claude &> /dev/null; then
        log_success "Claude CLI found: $(which claude)"
    else
        log_error "Claude CLI not found"
        log_info "Install: npm install -g @anthropic-ai/claude-code"
        errors=$((errors + 1))
    fi

    # Check for PRD file
    if [ -f "$PRD_FILE" ]; then
        local task_total
        local task_done
        task_total=$(grep -c '^\- \[' "$PRD_FILE" 2>/dev/null || echo "0")
        task_done=$(grep -c '^\- \[x\]' "$PRD_FILE" 2>/dev/null || echo "0")
        local task_pending=$((task_total - task_done))
        log_success "PRD found: $PRD_FILE"
        log_info "  Tasks: $task_done done, $task_pending pending"
    else
        log_error "PRD not found at $PRD_FILE"
        log_info "Run the PRD generator skill first to create a PRD"
        errors=$((errors + 1))
    fi

    # Check for PROGRESS file
    if [ -f "$PROGRESS_FILE" ]; then
        log_success "Progress file found: $PROGRESS_FILE"
    else
        log_warning "Progress file not found - will be created"
    fi

    # Check for git repo
    if git rev-parse --is-inside-work-tree &> /dev/null; then
        local branch
        local status
        branch=$(git branch --show-current 2>/dev/null || echo "unknown")
        status=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
        log_success "Git repository: branch '$branch'"
        if [ "$status" != "0" ]; then
            log_warning "  $status uncommitted changes"
        fi
    else
        log_warning "Not a git repository - commits will be skipped"
    fi

    if [ $errors -gt 0 ]; then
        echo ""
        echo -e "  ${RED}${BOLD}Cannot start: $errors error(s) found${NC}"
        echo ""
        exit 1
    fi

    echo ""
    echo -e "  ${GREEN}${BOLD}Environment validated!${NC}"
}

# ┌─────────────────────────────────────────────────────────────────────────────┐
# │                              CORE FUNCTIONS                                 │
# └─────────────────────────────────────────────────────────────────────────────┘

generate_prompt() {
    cat << 'PROMPT_EOF'
# True Ralph Loop - Iteration Task

You are in a True Ralph Loop iteration. Each iteration runs in a FRESH Claude session.
Your memory is ONLY what's in the filesystem - PRD.md, PROGRESS.md, and git history.

## Step 1: Understand Current State (REQUIRED)

Read these files to understand where we are:
```bash
cat docs/PROGRESS.md
cat docs/PRD.md
git log --oneline -5 2>/dev/null || echo "Not a git repo"
git status -s 2>/dev/null || echo "Not a git repo"
```

## Step 2: Execute ONE Task

1. Find the current "In Progress" task in PROGRESS.md
2. If none, pick the first unchecked task from PRD.md
3. Implement it COMPLETELY:
   - NO placeholders or TODOs
   - NO "implement later" comments
   - Full, working implementation
4. Write tests if the PRD specifies testing requirements

## Step 3: Update Files (REQUIRED)

After completing the task:

1. **Update PRD.md**: Mark the task as done with `[x]`
2. **Update PROGRESS.md**:
   - Move completed task to "Completed" section with commit hash
   - Move next pending task to "In Progress"
   - Update "Quick Context" section at top
   - Add entry to "Session History" table

## Step 4: Commit Changes

If this is a git repository:
```bash
git add -A
git commit -m "feat: [brief description of what was implemented]"
```

## Step 5: Exit

When done with ONE task, simply finish your response.
A fresh session will handle the next task.

## Completion Signal

If ALL tasks in PRD.md are marked with `[x]`:
Output exactly this text: <promise>PRD_COMPLETE</promise>

## If Stuck

- Document the blocker in PROGRESS.md under "Known Issues / Workarounds"
- Try an alternative approach
- After 3 attempts on the same task, add to "Blockers" and move to next task
- Do NOT output false completion promises

## CRITICAL RULES

1. Do ONE task only - not more, not less
2. Update BOTH PRD.md AND PROGRESS.md
3. Full implementations - no shortcuts
4. Commit your changes
5. Be honest about completion status

BEGIN: Read PROGRESS.md first to understand current state.
PROMPT_EOF
}

get_current_task() {
    local task
    if [ -f "$PROGRESS_FILE" ]; then
        # Try to extract current task from "In Progress" section
        task=$(grep -A2 "### In Progress" "$PROGRESS_FILE" 2>/dev/null | grep '^\- \[ \]' | head -1 | sed 's/^- \[ \] //')
        if [ -n "$task" ]; then
            echo "$task"
            return
        fi
    fi

    # Fall back to first unchecked task in PRD
    if [ -f "$PRD_FILE" ]; then
        task=$(grep '^\- \[ \]' "$PRD_FILE" 2>/dev/null | head -1 | sed 's/^- \[ \] //')
        if [ -n "$task" ]; then
            echo "$task"
            return
        fi
    fi

    echo "Unknown"
}

get_task_counts() {
    if [ -f "$PRD_FILE" ]; then
        local total
        local completed
        total=$(grep -c '^\- \[' "$PRD_FILE" 2>/dev/null || echo "0")
        completed=$(grep -c '^\- \[x\]' "$PRD_FILE" 2>/dev/null || echo "0")
        echo "$completed $total"
    else
        echo "0 0"
    fi
}

run_iteration() {
    local iteration=$1
    local max=$2
    local log_file
    log_file="$LOG_DIR/iteration-$(printf '%03d' "$iteration")-$(date +%Y%m%d-%H%M%S).log"

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${BOLD}ITERATION $iteration of $max${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Show current state
    local current_task
    local counts
    local completed
    local total
    current_task=$(get_current_task)
    counts=$(get_task_counts)
    completed=$(echo "$counts" | cut -d' ' -f1)
    total=$(echo "$counts" | cut -d' ' -f2)

    echo -e "  ${DIM}Current Task:${NC}  ${WHITE}$current_task${NC}"
    echo -e "  ${DIM}Progress:${NC}"
    print_progress_bar "$completed" "$total"
    echo -e "  ${DIM}Log File:${NC}      $log_file"
    echo -e "  ${DIM}Started:${NC}       $(timestamp)"
    echo ""

    # Generate fresh prompt
    generate_prompt > "$PROMPT_FILE"

    # Run Claude with fresh session
    local start_time
    start_time=$(date +%s)

    echo -e "  ${YELLOW}▶${NC}  Running Claude (fresh session)..."
    echo ""

    # Execute and capture output
    # Using --print for non-interactive mode
    if cat "$PROMPT_FILE" | claude --print 2>&1 | tee "$log_file"; then
        local end_time
        local duration
        end_time=$(date +%s)
        duration=$((end_time - start_time))

        echo ""
        echo -e "  ${DIM}Duration:${NC}      $(format_duration "$duration")"

        # Check for completion
        if grep -q "<promise>PRD_COMPLETE</promise>" "$log_file"; then
            return 0  # Complete!
        fi

        # Show latest commit if available
        if git rev-parse --is-inside-work-tree &> /dev/null; then
            local last_commit
            last_commit=$(git log --oneline -1 2>/dev/null || echo "none")
            echo -e "  ${DIM}Last Commit:${NC}   $last_commit"
        fi

        # Update counts
        local new_counts
        local new_done
        new_counts=$(get_task_counts)
        new_done=$(echo "$new_counts" | cut -d' ' -f1)

        if [ "$new_done" -gt "$completed" ]; then
            log_success "Task completed! ($new_done/$total done)"
        else
            log_warning "Task may not have been marked complete"
        fi

        return 1  # Continue
    else
        local exit_code=$?
        log_error "Claude exited with code $exit_code"
        return 2  # Error
    fi
}

# ┌─────────────────────────────────────────────────────────────────────────────┐
# │                              HELP & MAIN                                    │
# └─────────────────────────────────────────────────────────────────────────────┘

show_help() {
    cat << HELP
${BOLD}$SCRIPT_NAME${NC} v$VERSION

${BOLD}USAGE${NC}
    $(basename "$0") [OPTIONS]

${BOLD}OPTIONS${NC}
    -n, --max-iterations N    Maximum iterations (default: $DEFAULT_MAX_ITERATIONS)
    -p, --pause N             Pause between iterations in seconds (default: $DEFAULT_PAUSE_SECONDS)
    -h, --help                Show this help message
    -v, --version             Show version

${BOLD}EXAMPLES${NC}
    $(basename "$0")                      # Run with defaults (10 iterations)
    $(basename "$0") -n 20                # Run up to 20 iterations
    $(basename "$0") -n 15 -p 5           # 15 iterations, 5s pause

${BOLD}REQUIREMENTS${NC}
    - docs/PRD.md must exist (run the PRD generator skill first)
    - Claude CLI must be installed (npm install -g @anthropic-ai/claude-code)
    - Recommended: git repository for version control

${BOLD}HOW IT WORKS${NC}
    Unlike Anthropic's Ralph plugin which uses a Stop hook in the SAME session,
    True Ralph spawns a FRESH Claude session for each iteration.

    This prevents context rot and ensures each iteration has full context
    capacity. State is preserved through:
      - docs/PRD.md       → Requirements with checkboxes
      - docs/PROGRESS.md  → Current task and progress
      - Git commits       → Code history

${BOLD}STOPPING${NC}
    - Press Ctrl+C to stop gracefully
    - Loop stops when all PRD tasks are complete
    - Loop stops when max iterations reached

${BOLD}MONITORING${NC}
    - Watch terminal output for real-time progress
    - Check docs/PROGRESS.md for detailed state
    - View logs in .ralph/logs/

HELP
}

main() {
    local max_iterations=$DEFAULT_MAX_ITERATIONS
    local pause_seconds=$DEFAULT_PAUSE_SECONDS

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -n|--max-iterations)
                if [[ -z "${2:-}" ]] || [[ ! "$2" =~ ^[0-9]+$ ]]; then
                    log_error "--max-iterations requires a positive integer"
                    exit 1
                fi
                max_iterations="$2"
                shift 2
                ;;
            -p|--pause)
                if [[ -z "${2:-}" ]] || [[ ! "$2" =~ ^[0-9]+$ ]]; then
                    log_error "--pause requires a positive integer"
                    exit 1
                fi
                pause_seconds="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--version)
                echo "$SCRIPT_NAME v$VERSION"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    # Setup
    mkdir -p "$LOG_DIR"

    # Show banner
    print_banner

    # Validate environment
    validate_environment

    # Show configuration
    echo ""
    cat << EOF | print_box "CONFIGURATION"
Max Iterations:  $max_iterations
Pause Between:   ${pause_seconds}s
PRD File:        $PRD_FILE
Progress File:   $PROGRESS_FILE
Log Directory:   $LOG_DIR
EOF

    echo ""
    log_info "Starting True Ralph Loop..."
    log_info "Press Ctrl+C to stop gracefully"
    echo ""

    # Trap for graceful shutdown
    trap 'echo ""; log_warning "Interrupted by user"; echo ""; log_info "Progress saved in $PROGRESS_FILE"; exit 130' INT

    # Main loop
    local iteration=0
    local start_time
    start_time=$(date +%s)

    while [ "$iteration" -lt "$max_iterations" ]; do
        iteration=$((iteration + 1))

        run_iteration "$iteration" "$max_iterations"
        local result=$?

        if [ $result -eq 0 ]; then
            # PRD Complete!
            echo ""
            echo -e "${GREEN}"
            cat << 'COMPLETE'

  +=====================================================================+
  |                                                                     |
  |    ____  ___  __  __ ____  _     _____ _____ _____   _              |
  |   / ___|/ _ \|  \/  |  _ \| |   | ____|_   _| ____| | |             |
  |  | |   | | | | |\/| | |_) | |   |  _|   | | |  _|   | |             |
  |  | |___| |_| | |  | |  __/| |___| |___  | | | |___  |_|             |
  |   \____|\___/|_|  |_|_|   |_____|_____| |_| |_____| (_)             |
  |                                                                     |
  |                   All PRD Tasks Implemented!                        |
  |                                                                     |
  +=====================================================================+

COMPLETE
            echo -e "${NC}"

            local end_time
            local total_duration
            end_time=$(date +%s)
            total_duration=$((end_time - start_time))

            echo ""
            log_success "Completed in $iteration iteration(s)"
            log_success "Total time: $(format_duration "$total_duration")"
            log_success "Logs: $LOG_DIR"
            echo ""

            exit 0
        fi

        # Pause between iterations
        if [ "$iteration" -lt "$max_iterations" ]; then
            echo ""
            echo -e "  ${DIM}Pausing ${pause_seconds}s before next iteration...${NC}"
            sleep "$pause_seconds"
        fi
    done

    # Max iterations reached
    echo ""
    echo -e "${YELLOW}"
    cat << 'MAXED'

  +=====================================================================+
  |                     MAX ITERATIONS REACHED                          |
  +=====================================================================+

MAXED
    echo -e "${NC}"

    local end_time
    local total_duration
    end_time=$(date +%s)
    total_duration=$((end_time - start_time))

    log_warning "Reached maximum iterations ($max_iterations)"
    log_info "Total time: $(format_duration "$total_duration")"
    log_info "Check docs/PROGRESS.md for current state"
    log_info "Run again to continue: $(basename "$0") -n $max_iterations"
    echo ""

    exit 0
}

main "$@"
