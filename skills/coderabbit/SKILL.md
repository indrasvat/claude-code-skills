---
name: coderabbit
description: Local AI code reviews via CodeRabbit CLI. ONLY use when (1) user explicitly requests "coderabbit"/"cr review", OR (2) code changes are high-risk (security, concurrency, complex logic). Rate-limited to 1 review/hour—be highly selective.
---

# CodeRabbit CLI

AI code reviews locally. **Rate limit: 1 review/hour.** Use sparingly.

## When to Use (Be Selective)

**USE CodeRabbit for:**
- User explicitly requests it
- Security-sensitive code (auth, crypto, input validation, secrets)
- Concurrency/async (race conditions, deadlocks, shared state)
- Memory management (leaks, resource cleanup)
- Complex business logic with non-obvious edge cases
- Database migrations or schema changes
- Public API contract changes

**SKIP CodeRabbit for:**
- Simple refactors, renames, moves
- Documentation or comment changes
- Test additions (unless testing complex logic)
- Config/env changes
- Obvious bug fixes
- Formatting/style cleanup

When uncertain, ask user: "This looks like it could benefit from a CodeRabbit review (1/hour limit). Want me to run one?"

## Setup (First Use)

```bash
# Check if installed
command -v cr &>/dev/null || {
  echo "Installing CodeRabbit CLI..."
  curl -fsSL https://cli.coderabbit.ai/install.sh | sh
  source ~/.zshrc  # or ~/.bashrc
}

# Check auth status, login if needed
cr auth status || cr auth login
```

If CLI missing, prompt user: "CodeRabbit CLI not installed. Install it now?" Then run install + auth.

## Execution (Always Background)

**ALWAYS run in background with monitoring:**

```bash
# Start review in background, capture output
cr review --prompt-only --type uncommitted > /tmp/cr-review.txt 2>&1 &
CR_PID=$!

# Monitor completion (reviews take 7-30 min)
while kill -0 $CR_PID 2>/dev/null; do sleep 30; done

# Read results
cat /tmp/cr-review.txt
```

**Flags:**
- `--prompt-only` — Always use. AI-optimized, token-efficient output
- `--type uncommitted` — Faster, reviews only unstaged/staged changes
- `--type committed` — Only committed changes vs base
- `--base <branch>` — Compare against specific branch (default: main)

## Workflow

1. **Run background review** (command above)
2. **Continue other work** while waiting
3. **Parse findings** when complete — prioritize: critical > major > minor (ignore nits)
4. **Fix critical/major only** — don't chase diminishing returns
5. **NO verification re-run** unless user requests (preserve rate limit)

## Troubleshooting

- **No findings:** Check `git status`, verify `--base` branch
- **Stalled:** Reviews can take 30+ min for large diffs — be patient
- **Auth issues:** Re-run `cr auth login`
