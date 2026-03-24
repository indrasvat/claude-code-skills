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

# API Compatibility Check

Detect breaking changes in API definitions. Read-only analysis, safe to re-run.

## 1. Prerequisites

Check for specialized tools via `command -v`: `buf` (protobuf), `oasdiff` (OpenAPI). Report availability. If missing, fall back to manual git-diff analysis and note which tool would improve accuracy.

## 2. Scope

If `$ARGUMENTS` names specific files, analyze only those. Otherwise, find API files changed since base branch using `git diff --name-only $(git merge-base HEAD main)`. Detect by pattern:

| Pattern | Type |
|---------|------|
| `*.proto` | Protobuf |
| `openapi.yaml`, `swagger.json`, `*.openapi.*`, `*.swagger.*` | OpenAPI |
| `*.graphql`, `*.gql` | GraphQL |
| `*.go` with exported types changed | Go exported API |

Stop with a clear message if no API files are found in scope.

## 3. Baseline

Compute and print the merge-base: `git merge-base HEAD main`. For each file in scope, diff working tree against that baseline using `git diff <merge-base> -- <file>`.

## 4. Analysis by Type

### Protobuf
If `buf` is available, run `buf breaking --against .git#ref=<merge-base>`. Otherwise, manually inspect diffs for:
- BREAKING: field number reuse, field removal, type change, adding required fields
- SAFE: new optional field, new enum value with no renumbering

### OpenAPI
If `oasdiff` is available, run `oasdiff breaking <base-file> <current-file>`. Otherwise, manually inspect diffs for:
- BREAKING: removed endpoint, changed HTTP method, removed parameter, new required parameter, response schema narrowing
- SAFE: new optional parameter, new endpoint, added response fields

### GraphQL
Manually inspect diffs for:
- BREAKING: removed type/field, changed return type, new required argument, removed enum value
- SAFE: new optional field/argument, new type, new enum value

### Go Exported API
Manually inspect diffs for:
- BREAKING: removed exported symbol, changed function signature, changed interface method set, changed struct field types
- SAFE: new exported symbol, new method on concrete type

## 5. Output

Print a summary line first: total changes found, how many breaking. Then print a compatibility report table:

```
| Change | File:Line | Type | Severity |
```

Severity values: BREAKING, WARN, SAFE. Use WARN when a change is technically non-breaking but likely to cause client issues (e.g., deprecating a widely-used field, adding an enum value to a closed enum).

## 6. Idempotency

Read-only. No files created, modified, or deleted. Safe to re-run at any time.

`$ARGUMENTS`
