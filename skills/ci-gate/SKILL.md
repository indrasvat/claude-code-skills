---
name: ci-gate
description: >
  Run all CI checks locally before pushing — linters, type checks, tests, and
  vulnerability scans in parallel with a pass/fail summary table. Use when the
  user says "run CI", "check before push", "run all tests", "lint check", "pre-push
  checks", "validate before PR", "CI gate", "does it pass CI", "is it clean",
  "run checks", or wants to verify the project builds and passes before pushing.
disable-model-invocation: true
allowed-tools: Bash, Read, Edit, Write, Glob
argument-hint: [--fix to also auto-fix]
---

# CI Gate

Run every CI check locally. Fail fast, report everything.

## 1. Detect project types

Look for marker files in the working directory:

| Marker | Stack | Checks |
|--------|-------|--------|
| `go.mod` | Go | `go vet ./...`, `golangci-lint run ./...`, `go test -race -count=1 ./...`, `govulncheck ./...` |
| `package.json` | JS/TS | lint, typecheck, test (detect pm: `bun.lockb`->bun, `pnpm-lock.yaml`->pnpm, `yarn.lock`->yarn, else npm). If `turbo.json` exists, use `turbo run lint typecheck test` instead. |
| `Cargo.toml` | Rust | `cargo clippy -- -D warnings`, `cargo test`, `cargo audit` |
| `pyproject.toml` | Python | `ruff check .`, `ruff format --check .`, `python -m pytest` |

If multiple markers exist, run checks for ALL detected stacks.

## 2. Prerequisites

Before running, `command -v` check every tool needed for the detected stack(s). Collect ALL missing tools into a single list and report them together. If a critical tool is missing (go, cargo, node, python), stop and tell the user. If only optional tools are missing (golangci-lint, govulncheck, cargo-audit, turbo), warn but continue without those checks.

## 3. Execution

Run all checks for all detected stacks in parallel using background jobs in a single Bash call. Capture each check's exit code, wall-clock duration (via `SECONDS`), and stderr/stdout.

## 4. Output

Print a summary table FIRST:

```
| Check                      | Status | Duration |
|----------------------------|--------|----------|
| go vet ./...               | PASS   | 2.1s     |
| cargo clippy -- -D warnings| FAIL   | 5.4s     |
```

For any FAIL row, print its full error output below the table. Exit with code 1 if any check failed, 0 if all passed.

## 5. --fix mode

If `$ARGUMENTS` contains `--fix`, run auto-fix variants BEFORE the regular checks:
- Go: `golangci-lint run --fix ./...`
- JS/TS: `<pm> run lint --fix` or `turbo run lint -- --fix`
- Rust: `cargo clippy --fix --allow-dirty -- -D warnings`
- Python: `ruff check --fix .`, `ruff format .`

Then re-run all checks to verify fixes. Without `--fix`, change nothing.

## 6. Idempotency

Without `--fix`: read-only, no side effects. With `--fix`: changes are visible via `git diff`.

Check `$ARGUMENTS` for flags.
