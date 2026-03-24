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

# CRD Impact Analysis

Read-only analysis of CRD change blast radius across controllers, webhooks, RBAC, manifests, and clients.

## 1. Prerequisites
Standard tools (`grep`, `find`) always available. Check `command -v kubectl` and report availability (optional; used only to fetch live CRD schemas).

## 2. Input
Parse `$ARGUMENTS` for one of:
- **File path** -- Read the file, extract `spec.group`, `spec.versions[].name`, `spec.names.kind`, and field names from `openAPIV3Schema`.
- **group/version/kind** (e.g. `apps.example.com/v1alpha1/MyResource`) -- Split on `/`. Search repo for matching CRD YAML.
Derive: `GROUP`, `VERSION`, `KIND`, `PLURAL`, `SHORT_NAMES`, and a flat list of spec/status field paths.

## 3. Baseline
Diff CRD file against `git merge-base HEAD main`:
```bash
git diff $(git merge-base HEAD main) -- <crd-file>
```
Parse added/removed/changed fields. If no git history or new file, do full impact scan without field-level classification.

## 4. Analysis
Run five searches in parallel:

**Controllers** -- Go files importing the API group package, `Reconcile` functions, `SetupWithManager`, `ctrl.NewControllerManagedBy`, `For(&<kind>{})`.

**Webhooks** -- `//+kubebuilder:webhook` markers, ValidatingWebhookConfiguration/MutatingWebhookConfiguration YAML with matching `apiGroups`/`resources`, `Defaulter`/`Validator` implementations.

**RBAC** -- `//+kubebuilder:rbac` with `groups=<GROUP>`, ClusterRole/Role YAML under `config/rbac/` or any YAML with `apiGroups` containing GROUP and `resources` containing PLURAL.

**Manifests** -- Sample CR YAML (`kind: <KIND>`), test fixtures, Helm templates generating CRs, Kustomize overlays referencing the CRD.

**Client usage** -- Generated clients/informers/listers, dynamic client calls with the GVR, E2E tests, any `.go` file accessing CRD struct fields by name.

## 5. Impact Assessment
For each changed field, classify every referencing file:

| Level | Criteria |
|-------|----------|
| MUST UPDATE | Code directly reads/writes the changed field (struct access, JSON path, webhook validation) |
| SHOULD UPDATE | Code references the parent resource but not the specific field (Reconcile, generic watches) |
| INFORMATIONAL | Test fixtures, sample manifests, docs |

If no field-level diff available, classify all as SHOULD UPDATE with a note.

## 6. Output
Lead with summary: fields added, removed, type-changed. Then impact map grouped by level (MUST UPDATE first):
```
| File | Type | Impact | Reason |
|------|------|--------|--------|
| internal/controller/foo_controller.go | Controller | MUST UPDATE | reads .spec.removedField |
| config/rbac/role.yaml | RBAC | SHOULD UPDATE | grants access to foos |
| config/samples/foo_v1alpha1.yaml | Sample CR | INFORMATIONAL | contains example CR |
```
No preamble. Summary first, then table.

## 7. Idempotency
Read-only. No files created or modified. Safe to re-run.

$ARGUMENTS
