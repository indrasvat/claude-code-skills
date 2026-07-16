---
name: skillwright
description: >
  Author a new Agent Skill (a SKILL.md plus optional references, scripts, and
  hooks) for any task or domain. Use when the user says "write a skill", "create
  a skill", "author a skill", "scaffold a skill", "new SKILL.md", "make a Claude
  Code skill", "turn this into a skill", "build an agent skill", or wants to
  design, review, or improve a skill. Covers the frontmatter trigger contract,
  degree-of-freedom calibration, progressive disclosure, converting prose into
  machinery (references/hardening.md), this collection's conventions
  (references/conventions.md), and the ship checklist (references/checklist.md).
allowed-tools: Bash, Read, Grep, Glob
argument-hint: [skill-name | "what it should do"]
---

# Skillwright

Build a skill as a harness extension, not a prompt.

`prompting < harness engineering`. Prose the model *may* honor is the first half;
machinery the harness *runs* (script, router, hook, exit code, sub-agent gate)
forces the rest. Write minimal prose, harden only instructions that measurably
fail. Most skills ship instruction-only and need no machinery — add it only when
you can name the ignored instruction; it costs cache misses, portability, and a
format contract.

## Workflow

```
- [ ] 1. Baseline: run 2-3 real tasks with no skill; save failures verbatim
- [ ] 2. Trigger:  write name + description to fire on those tasks (below)
- [ ] 3. Freedom:  rate each instruction high / medium / low (below)
- [ ] 4. Draft:    minimal prose SKILL.md, just enough to beat baseline
- [ ] 5. Harden:   convert still-failing instructions to machinery -> references/hardening.md
- [ ] 6. Disclose: split over-limit content into one-level-deep references (below)
- [ ] 7. Verify:   references/conventions.md, then `make check`; lint + run every script
- [ ] 8. Ship:     references/checklist.md
```

## Trigger (name + description)

Only name + description load at startup; the description decides firing. If a
skill never triggers, the description is wrong, not the body.

- `name`: lowercase `[a-z0-9-]`, max 64 chars, must equal the directory; no
  `claude` / `anthropic`; never `helper` / `utils` / `tools`.
- `description`: third person, folded `>` block, max 1024 chars. State what it
  does AND when to fire; embed the literal phrases the user types. Be pushy,
  models under-trigger. Never a raw `": "` in a plain scalar (breaks discovery).

## Degree of freedom

Same dial as hardening: high = prose, low = an exact script. Match to fragility.

| Level | When | Form |
|---|---|---|
| High | many valid paths; context decides | numbered prose steps |
| Medium | preferred pattern, some variance ok | parameterized script |
| Low | fragile, order-critical | one exact command, "do not modify" |

Over-constrain an open task and you strangle the model; under-constrain a fragile
one and it walks off the cliff.

## Progressive disclosure

Context is a shared budget. Assume the model knows general concepts; add only what
it lacks.

- SKILL.md under 100 lines (this collection's bar). Over that, split.
- References one level deep; nested refs get partially read.
- Table of contents atop any reference over 100 lines. Split by domain.
- Scripts are executed (only stdout costs tokens): say "run X" vs "see X".
- Descriptive filenames; forward slashes only.

## Anti-patterns

Body before description. Machinery before a prose instruction has failed.
Explaining what the model knows. Nested refs, option menus, Windows paths, magic
constants. Assuming one harness's behavior is universal. Shipping without a
re-runnable baseline or a green `make check`.
