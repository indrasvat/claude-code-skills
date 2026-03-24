# PR Templates

Three tiers. Use the smallest that fits.

## Tier Selection

| Tier | Use when | Examples |
|------|----------|----------|
| Small | Low risk, narrow scope, docs-only | README fix, dep bump, typo, single-file config change |
| Standard | Behavior changes, multi-file | New endpoint, UI component, bug fix with test |
| Complex | Schema migrations, auth, breaking changes | DB migration, auth rewrite, multi-service deploy |

---

## Small

```markdown
## Summary

- [1-3 bullets: what changed and why]

## Testing

- [Commands run to verify]

## Notes

[Optional. Omit if nothing to add.]
```

---

## Standard

```markdown
## Links

- ExecPlan: [path or N/A]
- Issue: [link or N/A]

## Summary

- [What changed, scoped to user-visible or developer-visible impact]

## Why / Context

[1-2 paragraphs. Problem, previous state, why now.]

## How It Works

[Technical approach. Reference specific files and functions.]

## Manual QA Checklist

- [ ] [Step-by-step verification for reviewer]
- [ ] [Happy path and at least one edge case]

## Testing

- Typecheck: `[command and result]`
- Lint: `[command and result]`
- Tests: `[command and result]`

## Design Decisions

[Optional. "Decision: X. Alternatives: Y, Z. Rationale: ..."]

## Known Limitations

[Optional. What this does NOT do. Edge cases deferred.]

## Follow-ups

[Optional. Work this PR enables or defers.]

## Risks / Rollout

[Omit for low-risk changes. Include only when deployment considerations exist.]

- Risk: [description]
- Mitigation: [description]
- Rollback: [description]
```

---

## Complex

Everything from Standard, plus the sections below. Use Part headers when the change spans multiple logical units.

```markdown
## Links

- ExecPlan: [path or N/A]
- Issue: [link or N/A]
- Design doc: [link or N/A]
- Related PRs: [links or N/A]

## Summary

### Part 1: [Name]
- [Changes in this unit]

### Part 2: [Name]
- [Changes in this unit]

## Why / Context

[Full scope. Explain why this is one PR instead of multiple.]

## How It Works

### Part 1: [Name]
[Technical explanation.]

### Part 2: [Name]
[Technical explanation.]

## Decision Table

| Decision | Options Considered | Chosen | Rationale |
|----------|--------------------|--------|-----------|
| [What] | [A, B, C] | [B] | [Why] |

## Compatibility Matrix

| Component | Before | After | Migration Required |
|-----------|--------|-------|--------------------|
| [API/schema/config] | [old] | [new] | [yes/no + details] |

## Manual QA Checklist

- [ ] [Organized by Part if applicable]
- [ ] [Happy path, edge cases, error cases, rollback verification]

## Testing

- Typecheck: `[command and result]`
- Lint: `[command and result]`
- Unit tests: `[command and result]`
- Integration tests: `[command and result]`
- E2E tests: `[command and result, or N/A with justification]`

## Deployment / Rollout Plan

1. [Ordered steps for safe deployment]
2. [Feature flags, migration commands, verification]
3. [Ordering constraints between services]

## Rollback Plan

1. [Exact revert steps]
2. [Database rollback commands if applicable]
3. [Data recovery steps if destructive]

## Design Decisions

[Required for Complex tier.]

## Known Limitations

[Required for Complex tier.]

## Follow-ups

[Required for Complex tier.]

## Risks / Rollout

- Risk: [description]
- Likelihood: [low/medium/high]
- Impact: [low/medium/high]
- Mitigation: [description]
- Rollback: [description]

## Files Changed

### New Files

| File | Purpose |
|------|---------|
| `path/to/file` | [What it does] |

### Modified Files

| File | Change |
|------|--------|
| `path/to/file` | [What changed and why] |
```
