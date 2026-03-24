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

# Triage PR

Fetch, categorize, and address pull request review comments in priority order.

## Prerequisites

Fail immediately with an explicit error if any check fails: `gh` installed (`command -v gh`), authenticated (`gh auth status`), inside a git repo (`git rev-parse --is-inside-work-tree`).

## Step 1 -- Identify PR

Use `$ARGUMENTS` as the PR number if provided. Otherwise detect from the current branch via `gh pr view --json number --jq '.number'`. Stop if no PR is found, or if the PR state is CLOSED or MERGED.

## Step 2 -- Fetch

Get owner/repo: `gh repo view --json owner,name --jq '"\(.owner.login)/\(.name)"'`

Run all fetches in parallel:

- **PR metadata**: `gh pr view <num> --json title,body,baseRefName,headRefName,state,reviewDecision`
- **Inline comments**: `gh api repos/{owner}/{repo}/pulls/{num}/comments`
- **Top-level reviews**: `gh api repos/{owner}/{repo}/pulls/{num}/reviews`
- **Resolved status** (critical -- without this, resolved threads cannot be skipped):

```bash
gh api graphql -f query='
  query($owner:String!,$repo:String!,$num:Int!){
    repository(owner:$owner,name:$repo){
      pullRequest(number:$num){
        reviewThreads(first:100){nodes{id isResolved
          comments(first:10){nodes{id body author{login} path line createdAt}}
        }}
      }
    }
  }' -f owner=OWNER -f repo=REPO -F num=NUM
```

Discard all threads where `isResolved` is `true`. Only unresolved threads proceed.

## Step 3 -- Categorize

For each unresolved comment, record: reviewer, file:line, full text, category. Assign exactly one category (first match wins):

| Category | Signals |
|----------|---------|
| BLOCKER | Required change, bug, security issue, "must", "please fix", `CHANGES_REQUESTED` reviewer |
| QUESTION | Asks for clarification, "why", "can you explain", "what about", substantive `?` |
| SUGGESTION | Optional improvement, "consider", "maybe", "might be nice", "what if", "could we" |
| NITPICK | Minor style, starts with "nit:", "nitpick", "minor", formatting-only |

Default to SUGGESTION if no pattern matches.

## Step 4 -- Address in Order

Work through BLOCKERs, then QUESTIONs, then SUGGESTIONs, then NITPICKs.

- **BLOCKERs**: Read the file and lines. Show the planned fix. WAIT for user confirmation before editing.
- **QUESTIONs**: Draft reply text. Print it. Do NOT post via `gh` without user permission.
- **SUGGESTIONs/NITPICKs**: Apply if quick and correct. Otherwise mark SKIPPED with reason.

Track each comment as: FIXED, DRAFTED, SKIPPED, or PENDING.

## Step 5 -- Summary

```
| # | Category   | Reviewer | File:Line          | Status  |
|---|------------|----------|--------------------|---------|
| 1 | BLOCKER    | alice    | src/auth.ts:42     | FIXED   |
| 2 | QUESTION   | bob      | lib/utils.go:118   | DRAFTED |
| 3 | SUGGESTION | alice    | src/auth.ts:55     | SKIPPED |
| 4 | NITPICK    | carol    | README.md:12       | FIXED   |
```

## Idempotency

Safe to re-run. Fetches fresh state each time. Resolved threads are automatically skipped via the GraphQL `isResolved` check.

## Arguments

`$ARGUMENTS` -- PR number. If omitted, detected from the current branch.
