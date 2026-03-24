---
name: deslop
description: >
  Clean AI-generated slop from code — remove unnecessary comments, dead code,
  redundant logic, and rename for self-documentation. Use when the user says
  "clean this up", "deslop", "remove slop", "clean code", "remove unnecessary
  comments", "simplify", "code hygiene", "polish this", "remove noise", or
  after an agent has generated code that needs cleanup.
disable-model-invocation: true
allowed-tools: Read, Edit, Write, Glob, Grep
argument-hint: [file-or-directory]
---

# Deslop

Strip AI-generated noise. Make code speak for itself.

## 1. Scope

If `$ARGUMENTS` specifies files or directories, use those. Otherwise, target files changed since last commit:

```bash
git diff --name-only HEAD
```

If no uncommitted changes, use the last commit:

```bash
git diff --name-only HEAD~1
```

Read every in-scope file before making any edits.

## 2. Remove

- Comments restating what the code does ("what" comments, not "why" comments)
- Outdated comments that no longer match the code
- Comments masking unclear code -- fix the code instead of keeping the comment
- Commented-out code blocks
- Stale TODOs with no actionable context
- Unused imports, variables, functions, types
- Redundant type assertions the compiler already infers

## 3. Transform

- Rename variables/functions for self-documentation instead of adding comments
- Extract well-named functions instead of commenting code blocks
- Flatten nesting with early returns
- Make implicit behavior explicit

## 4. Preserve (DO NOT TOUCH)

- "Why" comments explaining non-obvious decisions
- External constraints, business rules, regulatory notes
- Edge case warnings
- Public API docs (godoc, JSDoc, docstrings)
- License headers

## 5. Language-specific

- **Go**: stale godoc restating the signature, `// handle error` noise, unjustified `// nolint` directives
- **Python**: `# type: ignore` without reason, stale docstrings that contradict the signature
- **JS/TS**: `// eslint-disable` without reason, `@ts-ignore` without reason
- **Rust**: `#[allow(dead_code)]` on items that are actually used

## 6. Idempotency

Running deslop on already-clean code produces zero edits. Do not reformat, reorder, or restructure code that has no slop.

## 7. Arguments

`$ARGUMENTS` -- files or directories to clean. Default: uncommitted changed files.
