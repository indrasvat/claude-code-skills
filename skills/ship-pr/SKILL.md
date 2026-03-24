---
name: ship-pr
description: >
  Create a pull request with a standards compliance review gate. Reviews the diff
  against CLAUDE.md and repo conventions before creating the PR, stopping on
  discrepancies. Supports tiered PR templates (small, standard, complex). Use when
  the user says "create PR", "open PR", "ship it", "ship PR", "make a pull request",
  "push and PR", "ready for review", "send for review", "create a pull request",
  or wants to create a GitHub pull request from the current branch.
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
argument-hint: [base-branch]
---

# Ship PR

Create a pull request. Enforce project standards before anything leaves the branch.

## Prerequisites

Fail immediately with an explicit error if any check fails.

1. `gh` installed: `command -v gh`
2. `gh` authenticated: `gh auth status`
3. Inside a git repo: `git rev-parse --is-inside-work-tree`

## Step 1 -- Inspect

Run in parallel:

- `git status`, `git diff --staged`, `git diff` -- working tree state
- `git log --oneline -10` -- recent history
- `git rev-parse --abbrev-ref HEAD` -- current branch
- `git rev-parse --abbrev-ref @{upstream} 2>/dev/null || echo "no-upstream"` -- tracking

Base branch: use `$ARGUMENTS` if provided, else `main`. Verify with `git rev-parse --verify origin/<base>`. Compute full diff: `git diff origin/<base>...HEAD`.

## Step 2 -- Standards Review (BLOCKING GATE)

This step is mandatory. It cannot be skipped silently.

Read every applicable conventions file:

- `~/.claude/CLAUDE.md` (user global)
- `CLAUDE.md` in repo root (project)
- `.claude/CLAUDE.md` in repo root (alternate location)
- `AGENTS.md` in repo root (if present)

Extract all actionable conventions. Review the full diff against every convention.

**If discrepancies are found**: STOP. Present a findings table:

```
| File | Standard | Issue | Fix |
|------|----------|-------|-----|
| src/foo.ts | Commit msg format | Missing conventional prefix | Amend to "feat: ..." |
| lib/bar.go | No fmt errors | gofmt diff detected | Run gofmt -w lib/bar.go |
```

Offer exactly these options:

1. **Fix all** -- apply every fix, re-run review
2. **Fix some** -- user picks which fixes to apply
3. **Proceed anyway** -- create PR with known discrepancies
4. **Discuss** -- explain findings before deciding

Do NOT proceed until the user confirms a path forward.

**If no discrepancies**: report "Standards review: all clear" and continue.

## Step 3 -- Branch

If on `main` or `master`: do NOT commit to the default branch. Ask user for a branch name with conventional prefix (`feat/`, `fix/`, `chore/`, `refactor/`, `docs/`, `test/`). Create with `git checkout -b <prefix>/<name>`.

If already on a feature branch, continue on it.

## Step 4 -- Stage and Commit

Stage files using explicit paths. Never use `git add -A` or `git add .`.

If nothing to commit, skip this step.

Write a conventional commit via HEREDOC:

```bash
git commit -m "$(cat <<'EOF'
type: short description
EOF
)"
```

Follow commit conventions from CLAUDE.md. Default: `type: short description`.

## Step 5 -- Push

```bash
git push -u origin <branch>
```

If remote is already current, skip and report.

## Step 6 -- Create PR

Read `references/templates.md`. Select the smallest tier that fits:

- **Small**: docs-only, config tweaks, single-file low-risk
- **Standard**: behavior changes, multi-file, new features
- **Complex**: schema migrations, auth changes, breaking changes

Create with `gh pr create` and HEREDOC body:

```bash
gh pr create --base <base> --title "<title>" --body "$(cat <<'EOF'
<filled template>
EOF
)"
```

Title under 70 characters. Detail goes in the body.

## Step 7 -- Report

Print the PR URL. Nothing else.

## Idempotency

Before creating, check for an existing PR:

```bash
gh pr list --head <branch> --json url --jq '.[0].url'
```

If a PR exists: push new commits to update, report existing URL. Do not create a duplicate.

## Arguments

`$ARGUMENTS` -- base branch for the PR. Default: `main`.
