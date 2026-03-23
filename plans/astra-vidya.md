# astra-vidya — Forging a Portable Agent Skills Arsenal

ExecPlan for creating 10 agent skills in [indrasvat/claude-code-skills](https://github.com/indrasvat/claude-code-skills).

References:
[Superset commands](https://github.com/superset-sh/superset/tree/main/.agents/commands) |
[Claude Code Skills docs](https://code.claude.com/docs/en/slash-commands) |
[Codex Skills](https://developers.openai.com/codex/skills) |
[Agent Skills standard](https://agentskills.io) |
[npx skills CLI](https://github.com/vercel-labs/skills)

Multi-agent reviewed: Codex (gpt-5.3-codex), Claude (sonnet-4-6), Gemini (gemini-3-flash-preview).


## Purpose

Create 10 production-grade skills (5 universal, 5 Go/K8s) in the `indrasvat/claude-code-skills`
repo, installable via:

    npx skills add indrasvat/claude-code-skills --skill ci-gate -g -a claude-code
    # or
    /plugin install indrasvat-skills

After implementation, users get: `/ci-gate`, `/exec-plan`, `/ship-pr`, `/deslop`,
`/triage-pr`, `/k8s-diff`, `/migration-guard`, `/api-compat`, `/rollout-check`, `/crd-impact`.


## Architecture

### Repository layout

All new skills go under `skills/` in the existing repo alongside cf-edge, coderabbit,
iterm2-driver, prd-generator:

    skills/
    ├── ci-gate/SKILL.md
    ├── exec-plan/
    │   ├── SKILL.md
    │   └── references/template.md
    ├── ship-pr/
    │   ├── SKILL.md
    │   └── references/templates.md
    ├── deslop/SKILL.md
    ├── triage-pr/SKILL.md
    ├── k8s-diff/SKILL.md
    ├── migration-guard/SKILL.md
    ├── api-compat/SKILL.md
    ├── rollout-check/SKILL.md
    └── crd-impact/SKILL.md

### Design constraints (apply to ALL skills)

These are non-negotiable. Derived from Claude Code docs, Codex docs, Agent Skills
standard, multi-agent review, and user CLAUDE.md:

1. **Progressive disclosure**: SKILL.md under 100 lines. Heavy content in `references/`.
   Description always in context; full skill loads only on invoke.
2. **`disable-model-invocation: true`** on every mutation skill (anything that edits
   files, creates PRs, runs destructive commands). Only user triggers these.
3. **Prerequisite checks first**: Every skill that calls external tools (`gh`, `kubectl`,
   `golangci-lint`) must verify tool existence with `command -v` before proceeding.
   Fail fast and explicit — no silent fallbacks.
4. **Idempotency stated**: Every skill documents what happens on re-run.
5. **`allowed-tools` restricted**: Read-only skills get `Bash, Read, Grep, Glob`.
   Mutation skills add `Edit, Write`. No skill gets unrestricted access.
6. **Trigger-rich descriptions**: Include the exact phrases users say (natural language
   triggers) plus the formal capability description. This is how Claude decides when
   to load the skill. Be generous with trigger phrases.
7. **`argument-hint`** on every skill for autocomplete discoverability.
8. **Output style**: Direct, zero-fluff. Lead with summary tables. Show commands and
   expected output. No hedging or preambles.
9. **Language**: Go is primary. Go-specific guidance should reference Go 1.26+ idioms
   (range-over-func, slog, etc.). Python refs use 3.14+/uv/ruff.
10. **No emoji in skill content** unless explicitly requested.
11. **Structured output**: Skills should produce parseable tables/lists, not prose, to
    support agent-to-agent handoff.

### Frontmatter reference

All fields from Claude Code docs ([source](https://code.claude.com/docs/en/slash-commands)):

    ---
    name: skill-name                       # /slash-command name. lowercase+hyphens, max 64 chars.
    description: >                         # CRITICAL for auto-triggering. Include natural-language
      What the skill does. Trigger phrases.  trigger phrases. Claude uses this to decide when to load.
    disable-model-invocation: true         # Only user can invoke. USE ON ALL MUTATION SKILLS.
    allowed-tools: Bash, Read, Grep, Glob  # Tool restrictions during execution.
    argument-hint: [args-description]      # Shown in autocomplete. Always include.
    effort: high                           # Override reasoning effort. Use on complex skills.
    context: fork                          # Run in isolated subagent. Use for heavy/noisy skills.
    agent: Explore                         # Subagent type (Explore, Plan, general-purpose).
    user-invocable: false                  # Hide from / menu. For background knowledge only.
    hooks: ...                             # Lifecycle hooks (pre/post).
    ---

String substitutions available in skill body:
- `$ARGUMENTS` — all args passed when invoking
- `$ARGUMENTS[N]` or `$N` — positional arg by index
- `${CLAUDE_SESSION_ID}` — current session ID
- `${CLAUDE_SKILL_DIR}` — directory containing SKILL.md
- `` !`command` `` — dynamic context injection (runs before skill loads)


## Progress

- [ ] Milestone 1: Implement skills (ALL 10 IN PARALLEL — see skill specs below)
- [ ] Milestone 2: Update repo README.md to document new skills
- [ ] Milestone 3: Validate (invoke each, check /context, verify no collisions)

**Parallelization**: Each skill spec below is self-contained. An implementing agent
should create all 10 skills in parallel since they have zero dependencies on each other.
After all 10 are written, run validation.


## Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| Personal skills in shared repo, not project-level | Cross-project reuse across personal + SpectroCloud repos | 2026-03-23 |
| Action verbs for names (ci-gate, ship-pr, not ci-check, create-pr) | Signal intent, avoid collision with Superset names | 2026-03-23 |
| `disable-model-invocation: true` on all mutation skills | Multi-agent consensus: auto-invocable mutations are dangerous | 2026-03-23 |
| SKILL.md under 100 lines; references/ for large content | Progressive disclosure + context budget optimization | 2026-03-23 |
| Prerequisite checks in every tool-calling skill | Codex review flagged late failures as anti-pattern | 2026-03-23 |
| Read-only K8s skills (no Edit/Write) | Infra inspection should report, not mutate | 2026-03-23 |


---
---


## Skill Specs

Each spec below is independently implementable. They can ALL be worked on in parallel.


---


### SKILL 1: ci-gate
<a id="ci-gate"></a>

**File**: `skills/ci-gate/SKILL.md`

**Origin**: [Superset ci-check.md](https://github.com/superset-sh/superset/blob/main/.agents/commands/ci-check.md) — adapted to be polyglot, read-only by default.

**Key design choice**: Unlike Superset's ci-check which auto-fixes, this is READ-ONLY
by default. Pass `--fix` to opt into mutations. Separates "report" from "mutate"
(Codex review anti-pattern flag).

#### Frontmatter

```yaml
---
name: ci-gate
description: >
  Run all CI checks locally before pushing — linters, type checks, tests, and
  vulnerability scans in parallel with a pass/fail summary table. Use when the
  user says "run CI", "check before push", "run all tests", "lint check", "pre-push
  checks", "validate before PR", "CI gate", "does it pass CI", "is it clean",
  "run checks", or wants to verify the project builds and passes before pushing.
disable-model-invocation: true
allowed-tools: Bash, Read, Glob
argument-hint: [--fix to also auto-fix]
---
```

#### Body specification

1. **Prerequisites**: `command -v` check for detected tools. Report missing, stop if critical.
2. **Detection**: Check working directory for marker files:
   - `go.mod` → Go: `go vet ./...`, `golangci-lint run ./...`, `go test -race -count=1 ./...`, `govulncheck ./...`
   - `package.json` → JS/TS: detect pm (bun.lockb→bun, pnpm-lock→pnpm, yarn.lock→yarn, else npm), run lint, typecheck, test. If turbo.json, use turbo.
   - `Cargo.toml` → Rust: `cargo clippy -- -D warnings`, `cargo test`, `cargo audit`
   - `pyproject.toml` → Python: `ruff check .`, `ruff format --check .`, `python -m pytest`
   - Multiple markers → run checks for ALL detected types.
3. **Execution**: Run all checks for detected type(s) in parallel.
4. **Output**: Summary table: `| Check | Status | Duration |`. Show error output for failures.
5. **`--fix` mode**: If `$ARGUMENTS` contains `--fix`, also run auto-fix variants and re-check.
6. **Idempotency**: Without `--fix`, changes nothing. With `--fix`, changes visible via `git diff`.

Keep under 80 lines.


---


### SKILL 2: exec-plan
<a id="exec-plan"></a>

**Files**: `skills/exec-plan/SKILL.md` + `skills/exec-plan/references/template.md`

**Origin**: [Superset create-plan.md](https://github.com/superset-sh/superset/blob/main/.agents/commands/create-plan.md) — the most sophisticated command, distilled to be project-agnostic.

**Key design choice**: SKILL.md is the concise process guide (~90 lines). The full
ExecPlan template skeleton lives in `references/template.md` — agent reads it
on-demand during plan creation. This is textbook progressive disclosure.

#### Frontmatter

```yaml
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
```

#### SKILL.md body specification

Cover these sections in ~90 lines:

1. **What an ExecPlan is**: Self-contained living doc. A fresh stateless agent reads only
   this file and succeeds. No "as discussed" references. Define every term of art inline.
2. **Process** (5 phases): Discovery → Draft → Resolve Questions → Approval Gate → (Implementation is out of scope for this skill — that's the agent's job after approval).
3. **Phase 1 Discovery**: Map repo, name scope, enumerate unknowns, ask focused questions
   using AskUserQuestion extensively (per user CLAUDE.md preference).
4. **Phase 2 Draft**: Read the template at `[references/template.md](references/template.md)`,
   fill in every section. Full repo-relative paths. Expected command output for every validation.
5. **Phase 3 Resolve**: Present open questions. Update plan as answers arrive. Move resolved
   items to Decision Log with rationale.
6. **Phase 4 Approval Gate**: Present complete plan. DO NOT implement until user approves.
7. **Plan location**: Project's `plans/` dir if it exists, else create `plans/<YYYYMMDD-HHmm>-<name>.md`.
8. **Non-negotiable rules** (one-liners): Self-contained. Living document. Observable outcomes.
   Idempotent steps. Spike milestones for unknowns.
9. **Lifecycle**: active → `plans/done/` on PR merge, active → `plans/abandoned/` on deprioritize.
10. `$ARGUMENTS`

#### references/template.md specification

The full ExecPlan skeleton (~120 lines). Sections:

- `# <Title>` + living doc notice
- `## Purpose / Big Picture` — user-visible behavior enabled
- `## Assumptions` — temporary, must be confirmed or removed
- `## Open Questions` — acceptance-oriented, link to Decision Log
- `## Progress` — checkbox list with timestamps. Mandatory at every stopping point.
- `## Surprises & Discoveries` — observation + evidence format
- `## Decision Log` — decision + rationale + date format
- `## Outcomes & Retrospective` — fill at completion
- `## Context and Orientation` — current repo state, key files, define terms
- `## Plan of Work` with `### Milestone N:` subsections (scope, steps, acceptance, verify-before-proceeding)
- `### Spike: <Name>` template (goal, approach, time box, success criteria, outcome)
- `## Validation and Acceptance` — exact commands + expected output
- `## Idempotence and Recovery` — retry/rollback paths
- `## Interfaces and Dependencies` — libraries, types, signatures


---


### SKILL 3: ship-pr
<a id="ship-pr"></a>

**Files**: `skills/ship-pr/SKILL.md` + `skills/ship-pr/references/templates.md`

**Origin**: [Superset create-pr.md](https://github.com/superset-sh/superset/blob/main/.agents/commands/create-pr.md) — the standards-gate pattern is the killer feature.

**Key design choice**: Step 2 (standards review) is a BLOCKING GATE. The agent
stops and presents findings to the user before proceeding. This prevents agents
from submitting non-compliant code.

#### Frontmatter

```yaml
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
```

#### SKILL.md body specification (~90 lines)

Workflow steps:

1. **Prerequisites**: `gh` installed + authenticated. Current dir is git repo.
2. **Step 1 — Inspect**: (parallel) `git status`, `git diff --staged`, `git diff`,
   `git log --oneline -10`, check remote tracking status.
3. **Step 2 — Standards Review (BLOCKING GATE)**: Read project CLAUDE.md (all levels)
   and AGENTS.md if present. Review diff against every convention. If discrepancies:
   STOP, present findings with file/standard/issue/fix per item, offer options
   (fix all / fix some / proceed anyway / discuss). Only proceed after user confirms.
4. **Step 3 — Branch**: If on main/master, create feature branch. Conventional prefix:
   feat/, fix/, chore/, refactor/, docs/, test/.
5. **Step 4 — Stage and Commit**: Explicit file paths (no `git add -A`). Conventional
   commit message. HEREDOC format.
6. **Step 5 — Push**: `git push -u origin <branch>`.
7. **Step 6 — Create PR**: Select template tier from `references/templates.md`. Use
   smallest that fits. Create with `gh pr create` + HEREDOC body.
8. **Step 7 — Report**: Print PR URL.
9. **Idempotency**: If PR exists for branch, update branch, report existing URL.
10. `$ARGUMENTS`

#### references/templates.md specification (~150 lines)

Three tiers:

**Small** (low risk, docs-only):
- Summary (1-3 bullets)
- Testing (commands run)
- Notes (optional)

**Standard** (behavior changes, multi-file):
- Links (optional: ExecPlan, issue)
- Summary
- Why / Context
- How It Works
- Manual QA Checklist
- Testing (typecheck, lint, test)
- Design Decisions (optional)
- Known Limitations (optional)
- Follow-ups (optional)
- Risks / Rollout (omit if low-risk)

**Complex** (schema migrations, auth changes, multi-feature):
- All of Standard, plus:
- Part headers (Part 1: Feature A, Part 2: Feature B)
- Decision tables (Decision | Choice | Rationale)
- Compatibility Matrix
- Deployment / Rollout plan
- Rollback plan
- Files Changed (New + Modified)


---


### SKILL 4: deslop
<a id="deslop"></a>

**File**: `skills/deslop/SKILL.md`

**Origin**: [Superset deslop.md](https://github.com/superset-sh/superset/blob/main/.agents/commands/deslop.md) — universalized with language-specific rules.

#### Frontmatter

```yaml
---
name: deslop
description: >
  Clean AI-generated slop from code — remove unnecessary comments, dead code,
  redundant logic, and rename for self-documentation. Use when the user says
  "clean this up", "deslop", "remove slop", "clean code", "remove unnecessary
  comments", "simplify", "code hygiene", "polish this", "remove noise", or
  after an agent has generated code that needs cleanup.
allowed-tools: Read, Edit, Write, Glob, Grep
argument-hint: [file-or-directory]
---
```

#### Body specification (~50 lines)

1. **Scope**: If `$ARGUMENTS` specifies files/dirs, use those. Else, files changed since
   last commit. If no uncommitted changes, files from last commit.
2. **Remove**: Comments restating code, "what" not "why" comments, outdated comments,
   comments masking unclear code (fix code instead), commented-out blocks, stale TODOs,
   unused imports/vars/functions/types, redundant type assertions.
3. **Transform**: Rename for self-documentation over commenting, extract well-named
   functions over commenting blocks, early returns over nesting, explicit over implicit.
4. **Preserve**: "Why" comments, external constraints/business rules, edge case warnings,
   public API docs (godoc, JSDoc, docstrings), license headers.
5. **Language-specific**:
   - Go: stale godoc restating signature, `// handle error` noise, unjustified `// nolint`
   - Python: `# type: ignore` without reason, stale docstrings
   - JS/TS: `// eslint-disable` without reason, `@ts-ignore` without reason
   - Rust: `#[allow(dead_code)]` on used items
6. `$ARGUMENTS`


---


### SKILL 5: triage-pr
<a id="triage-pr"></a>

**File**: `skills/triage-pr/SKILL.md`

**Origin**: [Superset respond-to-pr-comments.md](https://github.com/superset-sh/superset/blob/main/.agents/commands/respond-to-pr-comments.md)

#### Frontmatter

```yaml
---
name: triage-pr
description: >
  Fetch, categorize, and address PR review comments in priority order. Classifies
  each comment as BLOCKER, QUESTION, SUGGESTION, or NITPICK and works through
  blockers first. Use when the user says "address PR comments", "fix review
  feedback", "respond to PR", "handle review comments", "triage PR", "what does
  the reviewer want", "address feedback", "PR comments", "review feedback",
  or needs to work through pull request review comments systematically.
disable-model-invocation: true
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
argument-hint: [PR-number]
---
```

#### Body specification (~65 lines)

1. **Prerequisites**: `gh` installed + authed.
2. **Step 1 — Identify PR**: Use `$ARGUMENTS` PR number, or detect from branch via `gh pr view`.
   Stop if no PR or closed/merged.
3. **Step 2 — Fetch**: (parallel) PR info, inline comments (`gh api .../comments`), reviews.
4. **Step 3 — Categorize**: Each comment gets: reviewer, file:line, full text, category.
   - BLOCKER: required change, bug, security issue
   - QUESTION: asks for clarification
   - SUGGESTION: optional improvement
   - NITPICK: minor style preference
5. **Step 4 — Address in order**: BLOCKERs → QUESTIONs → SUGGESTIONs → NITPICKs.
   For BLOCKERs: show planned change, wait for user confirmation before editing.
   For QUESTIONs: draft reply text (do not post without permission).
   For SUGGESTIONs/NITPICKs: apply if quick+correct, else note for user.
6. **Step 5 — Summary table**: `| # | Category | Reviewer | File:Line | Status |`
7. **Idempotency**: Safe to re-run. Fetches fresh state. Resolved threads skipped.
8. `$ARGUMENTS`


---


### SKILL 6: k8s-diff
<a id="k8s-diff"></a>

**File**: `skills/k8s-diff/SKILL.md`

**Origin**: Codex + Gemini recommendations from multi-agent review. Gemini specifically
suggested `cluster-state-diff` for Helm/Kustomize comparison against live clusters.

#### Frontmatter

```yaml
---
name: k8s-diff
description: >
  Render Kubernetes manifests (Helm, Kustomize, raw YAML) and diff against a live
  cluster or previous render, flagging risky changes. Use when the user says "k8s
  diff", "manifest diff", "helm diff", "kustomize diff", "what changed in k8s",
  "compare manifests", "show k8s changes", "what will deploy", "dry run deploy",
  "preview deploy", "cluster drift", or wants to see Kubernetes resource changes
  before applying.
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
argument-hint: <path-to-manifests> [--context <k8s-context>]
---
```

#### Body specification (~75 lines)

1. **Prerequisites**: `kubectl` required. `helm`/`kustomize` optional (detected from input).
   Verify cluster access: `kubectl cluster-info`. Report current context.
2. **Detection**: Chart.yaml→Helm, kustomization.yaml→Kustomize, .yaml/.yml→raw.
3. **Render**: Render to temp file (helm template / kubectl kustomize / cat).
4. **Diff**: If `--context` in args, diff rendered vs live (`kubectl get -o yaml` per resource,
   ignoring managed fields + last-applied annotation). Else diff vs git-committed version.
5. **Risk flags**: Scan diff for patterns:
   - CRITICAL: namespace deletion, PV/PVC removal, RBAC escalation
   - HIGH: resource limit reduction >50%, replicas→0, image tag→`latest`
   - MEDIUM: new CRD version, service port change, configmap key removal
   - LOW: label/annotation changes, resource request adjustments
6. **Output**: Summary (N added, M modified, K removed) → Risk table → Full diff.
7. `$ARGUMENTS`


---


### SKILL 7: migration-guard
<a id="migration-guard"></a>

**File**: `skills/migration-guard/SKILL.md`

**Origin**: Codex recommended `migration-check`. Adapted for Go migration tools (goose,
golang-migrate, atlas) + general SQL analysis.

#### Frontmatter

```yaml
---
name: migration-guard
description: >
  Analyze database schema migrations for safety — lock risk, backward compatibility,
  rollback path, and data preservation. Use when the user says "check migration",
  "migration safe", "migration review", "schema change review", "will this lock",
  "migration guard", "review schema changes", "database migration check", "is this
  migration safe", or when a migration file has been created or modified.
allowed-tools: Bash, Read, Grep, Glob
argument-hint: [migration-file-or-directory]
---
```

#### Body specification (~65 lines)

1. **Prerequisites**: Detect migration framework from project (go.mod→goose/golang-migrate/atlas,
   drizzle.config→Drizzle, alembic.ini→Alembic, knexfile→Knex, raw .sql).
2. **Scope**: `$ARGUMENTS` files, or changed migration files since last commit.
3. **Analysis checklist**:
   - Lock risk: ALTER TABLE on large tables, ADD/DROP INDEX (concurrent?), column rename
   - Backward compatibility: old app still works after migration? NOT NULL with DEFAULT?
   - Rollback path: down migration exists? data-safe rollback? forward-only documented?
   - Data preservation: safe type changes? ENUM additions vs removals?
4. **Output**: Safety report table (`| Check | Status | Detail |`) + specific recommendations.
5. `$ARGUMENTS`


---


### SKILL 8: api-compat
<a id="api-compat"></a>

**File**: `skills/api-compat/SKILL.md`

**Origin**: Codex recommended `api-compat-check`. Covers protobuf, OpenAPI, GraphQL, Go exported API.

#### Frontmatter

```yaml
---
name: api-compat
description: >
  Detect breaking changes in APIs — protobuf, OpenAPI/Swagger, GraphQL schemas,
  or Go exported interfaces. Use when the user says "API compat", "breaking changes",
  "check API compatibility", "proto breaking", "schema breaking", "is this breaking",
  "backward compatible", "API diff", "contract check", or when API definition files
  have been modified.
allowed-tools: Bash, Read, Grep, Glob
argument-hint: [api-definition-file]
---
```

#### Body specification (~70 lines)

1. **Prerequisites**: Detect API type from changed files. Check for specialized tools
   (`buf` for proto, `oasdiff` for OpenAPI). Fall back to manual analysis if missing.
2. **Scope**: `$ARGUMENTS` files, or API files changed since base branch.
3. **Analysis by type**:
   - Protobuf: field number reuse, removal, type change, required addition (all BREAKING).
     New optional field, new enum value (SAFE). Use `buf breaking` if available.
   - OpenAPI: removed endpoints, changed method, removed params, new required params,
     response narrowing (BREAKING). Use `oasdiff` if available.
   - Go exported API: removed symbol, changed signature, changed interface method set (BREAKING).
4. **Output**: Compatibility report table (`| Change | File | Type | Severity |`).
5. `$ARGUMENTS`


---


### SKILL 9: rollout-check
<a id="rollout-check"></a>

**File**: `skills/rollout-check/SKILL.md`

**Origin**: Codex + Gemini recommendations. Gemini specifically suggested envtest/vcluster
provisioning; kept this as a lighter-weight live cluster check instead.

#### Frontmatter

```yaml
---
name: rollout-check
description: >
  Verify Kubernetes deployment health — pod status, rollout progress, events,
  readiness, HPA state, and recent errors. Use when the user says "check rollout",
  "is deploy healthy", "rollout status", "deployment health", "pod status",
  "check pods", "why is deploy failing", "k8s health", "verify deployment",
  "are pods ready", "check deployment", or wants to verify a Kubernetes
  deployment is healthy after a rollout.
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
argument-hint: <deployment-name> [-n namespace] [--context ctx]
---
```

#### Body specification (~65 lines)

1. **Prerequisites**: `kubectl` required. Verify cluster access. If `--context`, use it.
   Report current context.
2. **Input**: Parse deployment name (required), `--namespace`/`-n` (optional), `--context` (optional).
3. **Checks** (parallel):
   - Rollout status: `kubectl rollout status` (progressing/complete/failed)
   - Pod status: `kubectl get pods -l app=<name>` (ready/not-ready/pending/crashloop/evicted)
   - Recent events: `kubectl get events` for the deployment (warnings, errors, back-off)
   - Resource usage: `kubectl top pods` if metrics-server available (near-limit flags)
   - HPA status: `kubectl get hpa` matching deployment (current/target replicas)
   - Container logs: for unhealthy pods only, `--tail=20` (plus `--previous` if crashlooping)
4. **Output**: Health dashboard table (`| Check | Status | Detail |`). Non-OK items get
   log/event excerpts below the table.
5. `$ARGUMENTS`


---


### SKILL 10: crd-impact
<a id="crd-impact"></a>

**File**: `skills/crd-impact/SKILL.md`

**Origin**: Gemini recommended `crd-impact-analysis` — find all controllers, webhooks,
RBAC, manifests, and tests affected by a CRD change.

#### Frontmatter

```yaml
---
name: crd-impact
description: >
  Analyze the impact of CRD (Custom Resource Definition) changes — find all
  controllers, operators, webhooks, RBAC rules, and manifests that reference the
  CRD and need updates. Use when the user says "CRD impact", "what breaks if I
  change this CRD", "CRD change analysis", "custom resource impact", "who uses
  this CRD", "CRD consumers", "operator impact", "CRD dependencies", or when
  a CRD definition file has been modified.
allowed-tools: Bash, Read, Grep, Glob
argument-hint: <crd-file-or-group/version/kind>
---
```

#### Body specification (~65 lines)

1. **Input**: Parse `$ARGUMENTS` for file path (read to extract group/version/kind/fields)
   or group/version/kind identifier directly.
2. **Analysis** (5 searches):
   - Controllers: Go files importing CRD's API group, `Reconcile` functions, `SetupWithManager`
   - Webhooks: validating/mutating configs, `//+kubebuilder:webhook` markers
   - RBAC: `//+kubebuilder:rbac` markers, ClusterRole/Role YAML, `config/rbac/`
   - Manifests: sample CR YAML, test fixtures, Helm values/templates generating CRs
   - Client usage: generated clients, informers, listers, direct API calls, E2E tests
3. **Impact assessment**: For each changed field (added/removed/type changed), list every
   file referencing it, classify as MUST UPDATE / SHOULD UPDATE / INFORMATIONAL.
4. **Output**: Changes detected → Impact map table (`| File | Type | Impact | Reason |`).
5. `$ARGUMENTS`


---
---


## Validation (Milestone 3)

After all 10 skills are written:

1. **Visibility**: `ls skills/*/SKILL.md` — expect 14 entries (4 existing + 10 new).
2. **Frontmatter valid**: Each SKILL.md starts with `---`, has `name:` and `description:`.
3. **Context budget**: Total description text across all skills under 16,000 chars. Estimate
   ~4,500 chars for new skills + ~3,000 for existing = well within budget.
4. **No name collisions**: No overlap with existing skills (cf-edge, coderabbit, iterm2-driver,
   prd-generator) or built-in commands (help, clear, compact, init, context, batch, etc.).
5. **Dry-run each**: Invoke briefly to confirm skill loads and prerequisites section runs.


## Installation (post-merge)

After the PR merges to `indrasvat/claude-code-skills`:

    # Install all new skills globally for Claude Code
    npx skills add indrasvat/claude-code-skills -g -a claude-code --skill ci-gate --skill exec-plan --skill ship-pr --skill deslop --skill triage-pr --skill k8s-diff --skill migration-guard --skill api-compat --skill rollout-check --skill crd-impact

    # Or install everything at once
    npx skills add indrasvat/claude-code-skills -g -a claude-code --all

    # Or via plugin system
    /plugin install indrasvat-skills

    # Verify
    # Type / in Claude Code and confirm all 10 appear in autocomplete


## Revision Log

- 2026-03-23: Initial plan created from Superset analysis + multi-agent review.
- 2026-03-23: Restructured for parallel skill implementation. Each skill spec is
  self-contained and independently implementable. Added distribution strategy
  for indrasvat/claude-code-skills repo + npx skills CLI. Incorporated Claude Code
  Skills best practices (progressive disclosure, disable-model-invocation, context:fork,
  effort, argument-hint, dynamic context injection, supporting files). Tailored to
  user CLAUDE.md preferences (Go-first, fail loud, zero-fluff, AskUserQuestion).
