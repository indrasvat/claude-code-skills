# [Plan Title]

> Living document. Updated as work proceeds. Last updated: YYYY-MM-DD HH:MM.
> A fresh, stateless agent reads only this file and succeeds at every step.

---

## Purpose / Big Picture

What user-visible behavior does this plan enable? Write one to three sentences that a non-technical stakeholder would understand. Do not describe implementation details here.

---

## Assumptions

Temporary beliefs held during planning. Each must be confirmed or removed before the relevant milestone begins. An assumption that survives to implementation is a defect in the plan.

- [ ] **A1**: [Assumption text]. Confirmed by: [how to verify]. Status: unconfirmed.
- [ ] **A2**: [Assumption text]. Confirmed by: [how to verify]. Status: unconfirmed.

---

## Open Questions

Questions that must be answered before or during implementation. Each question is acceptance-oriented: answering it changes what gets built or how.

When a question is resolved, move it to the Decision Log with the decision and rationale. Do not delete questions.

| ID | Question | Blocks milestone | Status |
|----|----------|-----------------|--------|
| Q1 | [Question text] | Milestone N | Open |
| Q2 | [Question text] | Milestone N | Open |

---

## Progress

Checkbox list updated at every stopping point. Include timestamps so a reader can reconstruct the timeline.

- [ ] Plan drafted -- YYYY-MM-DD HH:MM
- [ ] All open questions resolved -- YYYY-MM-DD HH:MM
- [ ] Plan approved by user -- YYYY-MM-DD HH:MM
- [ ] Milestone 1 complete -- YYYY-MM-DD HH:MM
- [ ] Milestone 2 complete -- YYYY-MM-DD HH:MM
- [ ] All milestones complete -- YYYY-MM-DD HH:MM
- [ ] Retrospective written -- YYYY-MM-DD HH:MM

---

## Surprises and Discoveries

Log anything unexpected encountered during execution. Format: observation followed by evidence.

| Date | Observation | Evidence |
|------|------------|----------|
| YYYY-MM-DD | [What was unexpected] | [File path, command output, or link] |

---

## Decision Log

Decisions made during planning and execution. Never delete entries. Append only.

| ID | Decision | Rationale | Date |
|----|----------|-----------|------|
| D1 | [What was decided] | [Why this option over alternatives] | YYYY-MM-DD |

---

## Outcomes and Retrospective

Fill this section when the plan is complete (all milestones done) or abandoned.

**Outcome**: [Completed / Abandoned / Superseded by plan X]

**What went well**:
-

**What was harder than expected**:
-

**What would change next time**:
-

---

## Context and Orientation

Current state of the repository relevant to this plan. A reader who has never seen the codebase starts here.

### Repository structure (relevant subset)

```
repo-root/
  [directory and file listing relevant to this plan]
```

### Key files

| File | Role in this plan |
|------|-------------------|
| `path/to/file` | [What it does and why it matters] |

### Terms

Define every term of art, acronym, or project-specific concept used in this plan.

- **Term**: Definition.

---

## Plan of Work

### Milestone 1: [Name]

**Scope**: What this milestone delivers. One sentence.

**Steps**:

1. [Concrete action with repo-relative file paths].
2. [Next action].
3. [Continue until milestone is complete].

**Acceptance criteria**:
- [Observable outcome 1].
- [Observable outcome 2].

**Verify before proceeding**:

```bash
# Exact command to run
[command]
# Expected output (or pattern to match)
[expected output]
```

---

### Milestone 2: [Name]

**Scope**: [Description].

**Steps**:

1. [Action].
2. [Action].

**Acceptance criteria**:
- [Outcome].

**Verify before proceeding**:

```bash
[command]
[expected output]
```

---

### Spike: [Name]

Use a spike when a milestone depends on an unvalidated assumption or unknown technology.

**Goal**: The specific question this spike answers. One sentence.

**Approach**: How to investigate. Bullet list of concrete steps.

- [Step 1].
- [Step 2].

**Time box**: [Duration, e.g., 2 hours]. If the time box expires without an answer, escalate to the user.

**Success criteria**: What constitutes a sufficient answer. Be specific.

- [Criterion].

**Outcome**: [Fill after spike completes. State the answer, link to any prototype code or evidence.]

---

## Validation and Acceptance

Final validation after all milestones are complete. Each entry is an exact command and its expected output.

```bash
# Test suite passes
[test command]
# Expected: all tests pass, exit code 0

# Build succeeds
[build command]
# Expected: clean build, no warnings

# Feature works end-to-end
[e2e command or manual verification steps]
# Expected: [describe observable result]
```

---

## Idempotence and Recovery

How to retry or roll back if something fails mid-execution.

**Retry**: [Describe how to re-run a failed milestone safely. Explain why running it twice is harmless.]

**Rollback**: [Describe how to undo changes from a partially completed milestone. Include exact commands.]

**Known failure modes**:

| Failure | Symptom | Recovery |
|---------|---------|----------|
| [What can go wrong] | [How to detect it] | [How to fix it] |

---

## Interfaces and Dependencies

External libraries, services, APIs, types, and function signatures this plan depends on or introduces.

### External dependencies

| Dependency | Version | Purpose |
|-----------|---------|---------|
| [library/service] | [version or range] | [Why it is needed] |

### Interfaces introduced or modified

```
[Language-appropriate type signatures, API contracts, or schema definitions]
```

### Cross-team or cross-service dependencies

| Dependency | Owner | Status |
|-----------|-------|--------|
| [What is needed] | [Who provides it] | [Available / Requested / Blocked] |
