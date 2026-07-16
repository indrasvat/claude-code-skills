# This collection's conventions

Apply when adding a skill to indrasvat/claude-code-skills.

## Frontmatter policy
- Required on every skill: `name` (equals the directory), `description` (folded
  `>` block), `allowed-tools`, `argument-hint`.
- `disable-model-invocation: true` on mutation skills (edit files, create PRs,
  run destructive commands). Omit on read-only / guidance skills so they
  auto-load. skillwright itself omits it: its whole value is being model-invoked
  during authoring.
- `allowed-tools`: read-only gets `Bash, Read, Grep, Glob`; mutation adds
  `Edit, Write`.
- Not used here: `agent`, `user-invocable`, `hooks`. `effort` / `context` optional.
- A plain (unquoted) `description` containing `": "` is invalid YAML and makes the
  skill silently undiscoverable; the folded `>` block avoids it.

## Layout
- One skill per `skills/<name>/`, entry point `SKILL.md`.
- Detail in `references/` (plural). Runnable code in `scripts/` or `examples/`.

## Gates
- Branch first (`feat/…`, `fix/…`), never commit to `main`.
- `make check` green before push: shellcheck (severity=warning), validate-skills
  (frontmatter parse), test-browsing.
- Conventional one-line commits. No emoji. No AI attribution in commits or files.
- After the PR exists, run gh-ghent: fix every check, reply-and-resolve every
  thread; the PR is not done until checks pass and 0 threads remain.

## Register (Go / K8s house style)
- Direct, zero-fluff; lead with summary tables; show commands + expected output.
- Prerequisite checks first: `command -v <tool>` before use, fail fast.
- Go 1.26+ idioms; Python 3.14+ / uv / ruff; bash `set -euo pipefail`.
- State idempotency (what happens on re-run).
