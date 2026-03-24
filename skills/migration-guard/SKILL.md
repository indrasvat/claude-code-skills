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

# Migration Guard

Read-only structural analysis. CAVEAT: Lock risk predictions require live table size, row counts, and engine metadata which this skill cannot access. Treat lock assessments as directional, not definitive.

## 1. Detect framework

Check project root: `go.mod` with goose/golang-migrate/atlas (Go), `drizzle.config.*` (Drizzle), `alembic.ini` or `alembic/` (Alembic), `knexfile.*` (Knex), raw `.sql` files (generic SQL). Report detected framework. If none match, analyze as raw SQL.

## 2. Scope

`$ARGUMENTS` files, or changed migration files since last commit:
```bash
git diff --name-only HEAD | grep -iE '(migrat|schema|\.sql)'
```
Fallback to `HEAD~1` with same filter. Read every in-scope file before analysis.

## 3. Analysis checklist

**Lock risk:**
- ALTER TABLE on large tables (ADD/DROP/RENAME COLUMN, ADD/DROP INDEX)
- ADD COLUMN with DEFAULT on existing rows (Postgres <11 rewrites table)
- CREATE INDEX without CONCURRENTLY
- Column type changes forcing table rewrite

**Backward compatibility:**
- NOT NULL without DEFAULT (breaks old app inserts)
- Column/table DROP without deprecation period
- Column rename (old queries break immediately)
- New constraints rejecting data the old app still writes

**Rollback path:**
- Down/rollback migration exists?
- Rollback is data-safe (up's DROP doesn't lose data irrecoverably)?
- Forward-only justified in a comment?

**Data preservation:**
- Type widening safe (INT->BIGINT); narrowing dangerous (VARCHAR(255)->VARCHAR(50))
- ENUM additions safe; removals may orphan rows
- DROP COLUMN loses data permanently -- flag unless prior migration copies it

## 4. Output

Print summary table first:
```
| Check                  | Status | Detail                                    |
|------------------------|--------|-------------------------------------------|
| Lock risk              | WARN   | ADD INDEX without CONCURRENTLY on "orders" |
| Backward compatibility | PASS   |                                           |
| Rollback path          | FAIL   | No down migration found                   |
| Data preservation      | PASS   |                                           |
```
For each WARN/FAIL, print a recommendation below the table: the risk and a concrete remediation.

## 5. Idempotency

Read-only. No files created or modified. Safe to re-run.

`$ARGUMENTS`
