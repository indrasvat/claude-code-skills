# Project Conventions

A Claude Code marketplace: skills under `skills/<name>/SKILL.md` plus the
`dootdashaa` statusline plugin. Keep changes small and well-scoped.

## Branch first

`main` only takes merged PRs — never commit to it directly. Before the first
edit, cut a branch: `feat/…`, `fix/…`, `chore/…`, or `refactor/…`.

## Commits

- Brief, one-liner conventional commits: `type: short description`.
- Examples: `feat: add plugin manifest`, `fix: correct typo in README`.

## Quality gates (before every push)

- `make check` runs everything CI runs: `lint` (shellcheck, severity=warning),
  `validate-skills` (SKILL.md frontmatter parse), `test-browsing` (offline tests).
  A red `make check` locally is a red CI — fix it before pushing.
- Shell scripts must be shellcheck-clean.

## Skills

- One skill per `skills/<name>/`, entry point `SKILL.md` with YAML frontmatter:
  `name` (lowercase/hyphens, must equal the directory) + `description`.
- Progressive disclosure: keep `SKILL.md` lean; push detail into `references/`.

## feat / fix protocol (every change)

1. Branch (`feat/…` or `fix/…`), implement, add or extend tests where the logic
   warrants it.
2. `make check` green locally.
3. Commit (one-liner), push, open the PR.
4. **gh-ghent discipline — as soon as the PR exists, not later:** run
   `gh ghent status --pr <N> --logs --format json --no-tui`. Fix every CI failure
   and reply-and-resolve every review thread with
   `gh ghent reply --pr <N> --thread <id> --body "…" --resolve` (a body is
   required) — never a top-level PR comment. Re-run after each fix push. The PR
   is **not done** until gh-ghent
   reports checks pass and 0 unresolved threads.
