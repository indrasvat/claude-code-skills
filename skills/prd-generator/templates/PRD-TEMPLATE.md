# Product Requirements Document: {PROJECT_NAME}

## Metadata

| Field | Value |
|-------|-------|
| **Created** | {TIMESTAMP} |
| **Last Updated** | {TIMESTAMP} |
| **Status** | draft / in-progress / implemented |
| **Version** | 1.0 |
| **Author** | Claude + {USER} |

---

## 1. Executive Summary

{2-3 sentences describing the problem and proposed solution. This should be understandable by anyone in 30 seconds.}

---

## 2. Problem Statement

### Pain Points

- {Specific pain point 1 - who experiences it, how often, impact}
- {Specific pain point 2}
- {Specific pain point 3}

### Current State

{How do users currently solve this problem? What workarounds exist? Why are they insufficient?}

### Why Now?

{What makes this problem worth solving now? Market timing, user demand, technical feasibility changes?}

---

## 3. Success Metrics & Kill Criteria

### Success Metrics (SMART)

How we'll know this project succeeded:

- [ ] **{Metric 1}**: {Specific, Measurable target} by {timeframe}
- [ ] **{Metric 2}**: {Specific, Measurable target} by {timeframe}
- [ ] **{Metric 3}**: {Specific, Measurable target} by {timeframe}

### Kill Criteria

When to roll back or pivot (be honest upfront):

- If {metric X} is not met by {date}, we will {action}
- If {condition}, we stop and reassess

---

## 4. User Stories / Jobs to Be Done

### Primary Persona: {PERSONA_NAME}

> {Brief description: role, technical level, key characteristics}

### Jobs to Be Done (JTBD)

*Frame requirements around what job users are "hiring" this product to do:*

> **When** {situation/trigger}, **I want to** {motivation/goal}, **so I can** {expected outcome}.

- **Job 1**: When {situation}, I want to {action}, so I can {outcome}
- **Job 2**: When {situation}, I want to {action}, so I can {outcome}

### Core User Stories

- [ ] **US-001**: As a {user type}, I want {goal} so that {benefit}
  - **Acceptance Criteria**:
    - [ ] {Testable criterion 1}
    - [ ] {Testable criterion 2}
  - **Priority**: P0

- [ ] **US-002**: As a {user type}, I want {goal} so that {benefit}
  - **Acceptance Criteria**:
    - [ ] {Testable criterion 1}
    - [ ] {Testable criterion 2}
  - **Priority**: P1

- [ ] **US-003**: As a {user type}, I want {goal} so that {benefit}
  - **Acceptance Criteria**:
    - [ ] {Testable criterion 1}
  - **Priority**: P1

{Add more user stories as needed}

---

## 5. Functional Requirements

### Core Features

- [ ] **FR-001**: {Feature description}
  - Priority: P0
  - Dependencies: {None / FR-XXX}
  - Notes: {Implementation considerations}

- [ ] **FR-002**: {Feature description}
  - Priority: P0
  - Dependencies: {None / FR-XXX}

- [ ] **FR-003**: {Feature description}
  - Priority: P1
  - Dependencies: {FR-001}

{Add more requirements as needed}

### Out of Scope (Explicit)

These items are explicitly NOT part of this project:

- {Feature/capability 1} — Reason: {why excluded}
- {Feature/capability 2} — Reason: {why excluded}
- {Feature/capability 3} — Future phase consideration

---

## 6. Technical Specifications

### Tech Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| Frontend | {e.g., React, Vue} | {version, key libs} |
| Backend | {e.g., Node.js, Python} | {framework} |
| Database | {e.g., PostgreSQL, MongoDB} | {hosted where} |
| Deployment | {e.g., Vercel, AWS} | {environment} |

### Architecture Overview

{High-level architecture description. Include diagram if complex.}

```
{ASCII diagram or reference to architecture diagram}
```

### Data Models

```
{Key entity definitions}

Example:
User {
  id: UUID (PK)
  email: string (unique)
  name: string
  created_at: timestamp
}
```

### API Contracts (if applicable)

```
{Key endpoint definitions}

Example:
POST /api/users
  Request: { email: string, name: string }
  Response: { id: string, email: string, name: string }
  Errors: 400 (validation), 409 (duplicate)
```

---

## 7. Implementation Phases

*Each task should be completable in 1-4 hours (roughly one PR/commit). If a task is bigger, break it down.*

### Phase 1: Walking Skeleton (Foundation)

**Goal**: Basic end-to-end flow working, even if ugly. Proves the architecture.

- [ ] **Task 1.1**: {Setup - e.g., "Initialize repo with boilerplate and CI/CD"}
- [ ] **Task 1.2**: {Infrastructure - e.g., "Set up database and basic schema"}
- [ ] **Task 1.3**: {Deployment - e.g., "Deploy 'Hello World' to staging"}
- [ ] **Task 1.4**: {Integration - e.g., "Connect frontend to backend with one real endpoint"}

**Phase 1 Verification**: {e.g., "App deploys to staging, one user flow works end-to-end"}

---

### Phase 2: Core MVP (Primary Value)

**Goal**: The main user value delivered. Users can actually use it.

- [ ] **Task 2.1**: {Core feature 1 - e.g., "Implement user authentication"}
- [ ] **Task 2.2**: {Core feature 2 - e.g., "Build main dashboard view"}
- [ ] **Task 2.3**: {Core feature 3 - e.g., "Add data creation/editing flow"}
- [ ] **Task 2.4**: {Core feature 4 - e.g., "Implement basic error handling"}
- [ ] **Task 2.5**: {Integration - e.g., "Connect all features into coherent flow"}

**Phase 2 Verification**: {e.g., "User can complete primary job-to-be-done end-to-end"}

---

### Phase 3: Polish & Harden (Production Ready)

**Goal**: Production-quality release. Handle edge cases, improve UX.

- [ ] **Task 3.1**: {UX polish - e.g., "Add loading states and error messages"}
- [ ] **Task 3.2**: {Edge cases - e.g., "Handle offline/network failure gracefully"}
- [ ] **Task 3.3**: {Documentation - e.g., "Write user-facing docs and API reference"}
- [ ] **Task 3.4**: {Monitoring - e.g., "Add logging, metrics, and alerting"}

**Phase 3 Verification**: {e.g., "All acceptance criteria met, tests pass, docs complete"}

---

## 8. Testing Strategy

### Unit Tests

- [ ] {Component/Module}: {What to test}
- [ ] {Component/Module}: {What to test}

### Integration Tests

- [ ] {Flow/Feature}: {What to test}
- [ ] {Flow/Feature}: {What to test}

### E2E Tests

- [ ] {User scenario}: {What to test}
- [ ] {User scenario}: {What to test}

### Test Commands

```bash
# Run all tests
{test command}

# Run specific test suite
{test command}

# Run with coverage
{test command}
```

---

## 9. Non-Functional Requirements

### Performance

- Response time: {target, e.g., < 200ms for API calls}
- Throughput: {target, e.g., 1000 req/sec}
- Concurrent users: {target}

### Security

- [ ] {Security requirement 1, e.g., HTTPS only}
- [ ] {Security requirement 2, e.g., Input validation}
- [ ] {Security requirement 3, e.g., Auth mechanism}

### Other

- Accessibility: {requirements, e.g., WCAG 2.1 AA}
- Browser support: {targets}
- Mobile support: {requirements}

---

## 10. Risk Assessment & Pre-Mortem

### Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| {Risk 1} | High/Med/Low | High/Med/Low | {Mitigation strategy} |
| {Risk 2} | High/Med/Low | High/Med/Low | {Mitigation strategy} |
| {Risk 3} | High/Med/Low | High/Med/Low | {Mitigation strategy} |

### Pre-Mortem: Why This Project Failed

*Write this section as if the project already failed. What went wrong?*

> It's 6 months from now and this project was a failure. Here's what happened:

- {Reason 1 - e.g., "We underestimated the complexity of X"}
- {Reason 2 - e.g., "Users didn't actually want Y, they wanted Z"}
- {Reason 3 - e.g., "We couldn't get buy-in from stakeholder A"}

*Use these to inform mitigation strategies above.*

---

## 11. Open Questions & Assumptions

### Open Questions

*Unknowns to be resolved during development (it's okay not to have all answers):*

- [ ] {Question 1 - e.g., "How will we handle edge case X?"}
- [ ] {Question 2 - e.g., "What's the expected data volume?"}
- [ ] {Question 3 - e.g., "Do we need admin approval workflow?"}

### Assumptions

*What we're assuming to be true (document so we can revisit):*

- {Assumption 1 - e.g., "Users have GitHub accounts"}
- {Assumption 2 - e.g., "API rate limits won't be hit at expected scale"}
- {Assumption 3 - e.g., "Existing auth system can be extended"}

---

## 12. Dependencies

### External Dependencies

- {External service/API 1}: {What we need from it}
- {External service/API 2}: {What we need from it}

### Task Dependencies

```mermaid
graph TD
    A[Task 1.1] --> B[Task 1.2]
    B --> C[Task 2.1]
    C --> D[Task 2.2]
    D --> E[Task 3.1]
```

---

## Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| {DATE} | 1.0 | Initial PRD | Claude |

---

## Appendix

### Glossary

- **{Term 1}**: {Definition}
- **{Term 2}**: {Definition}

### References

- {Link to design docs}
- {Link to related PRDs}
- {Link to external resources}
