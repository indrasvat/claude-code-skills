---
name: exec-plan
description: >
  Create a self-contained execution plan (ExecPlan) for a feature, refactor,
  migration, or complex task. Produces a living markdown document any agent or
  developer can follow end-to-end without prior context. Use when the user says
  "create a plan", "write an exec plan", "plan this feature", "design this",
  "write a spec", "implementation plan", "how should we build this", "break this
  down", "plan the work", "write up the approach", or when a task is complex
  enough to warrant planning before implementation.
disable-model-invocation: true
argument-hint: <task-description>
effort: high
---

# ExecPlan

An ExecPlan is a self-contained living document. A fresh, stateless agent reads only this file and succeeds at every step without external context. There are no "as discussed" references, no assumed knowledge, no implicit dependencies. Every term of art is defined inline where it first appears. Every file path is repo-relative. Every validation step includes the exact command and its expected output.

Living document means the plan is updated as work proceeds: checkboxes get ticked, discoveries are logged, decisions are recorded with rationale, and open questions migrate to the Decision Log once resolved.

## Process

Four phases, executed in order. Implementation is out of scope for this skill.

```
Discovery --> Draft --> Resolve Questions --> Approval Gate
```

## Phase 1: Discovery

Map the repository. Read key files, directory structure, build configs, and existing conventions. Identify:

- **Scope**: What exactly is being built, changed, or migrated. Name the boundaries.
- **Unknowns**: Technical risks, ambiguous requirements, missing information.
- **Existing patterns**: Conventions already in the codebase that the plan must follow.
- **Dependencies**: Libraries, services, APIs, or other teams involved.

Ask focused questions using the conversational interface extensively. Do not guess when you can ask. Prefer narrow, specific questions over broad ones. Each question should target a single unknown.

## Phase 2: Draft

Read the template at `references/template.md`. Fill in every section. Leave nothing as placeholder text. If a section genuinely does not apply, write "Not applicable -- [reason]" so the reader knows it was considered.

Requirements for the draft:

- All file paths are repo-relative (e.g., `src/lib/auth.ts`, not `/Users/dev/project/src/lib/auth.ts`).
- Every milestone has acceptance criteria with exact commands and expected output.
- Steps are ordered so each can be executed independently and idempotently.
- Spike milestones are inserted before any milestone that depends on an unresolved unknown.

## Phase 3: Resolve Questions

Present all open questions from the draft to the user. Update the plan as answers arrive:

- Answered questions move to the Decision Log with the decision, rationale, and date.
- New questions discovered during resolution get added to Open Questions.
- Milestones affected by decisions are updated immediately.

Continue until Open Questions is empty or all remaining questions are explicitly deferred with a rationale.

## Phase 4: Approval Gate

Present the complete plan to the user. Summarize:

- Total milestones and estimated scope.
- Key decisions made during planning.
- Any deferred questions and their risk.

DO NOT begin implementation until the user explicitly approves the plan.

## Plan Location

If the project already has a `plans/` directory, write the plan there. Otherwise, create one:

```
plans/<YYYYMMDD-HHmm>-<name>.md
```

Use the current date-time and a short kebab-case name derived from the task (e.g., `plans/20260323-1400-auth-migration.md`).

## Non-Negotiable Rules

1. **Self-contained.** A reader with zero prior context understands every sentence.
2. **Living document.** Updated at every stopping point with current progress and discoveries.
3. **Observable outcomes.** Every milestone ends with a verification step: exact command, expected output.
4. **Idempotent steps.** Running a step twice produces the same result as running it once.
5. **Spike milestones for unknowns.** Never commit to an approach for something unvalidated. Insert a time-boxed spike first.

## Lifecycle

- Active plans live in `plans/`.
- On PR merge (plan complete), move to `plans/done/`.
- On deprioritization (plan abandoned), move to `plans/abandoned/`.

$ARGUMENTS
