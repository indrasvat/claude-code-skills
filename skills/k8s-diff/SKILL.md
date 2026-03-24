---
name: k8s-diff
description: >
  Render Kubernetes manifests (Helm, Kustomize, raw YAML) and diff against a live
  cluster or previous render, flagging risky changes. Use when the user says "k8s
  diff", "manifest diff", "helm diff", "kustomize diff", "what changed in k8s",
  "compare manifests", "show k8s changes", "what will deploy", "dry run deploy",
  "preview deploy", "cluster drift", or wants to see Kubernetes resource changes
  before applying.
allowed-tools: Bash, Read, Grep, Glob
argument-hint: <path-to-manifests> [--context <k8s-context>]
---

# K8s Manifest Diff

Render manifests, diff against cluster or git, flag risks. Read-only.

## 1. Prerequisites
- `command -v kubectl` -- REQUIRED. Abort immediately if missing.
- `helm`, `kustomize` -- optional, detected from input. `kubectl kustomize` as fallback.
- If `--context` in `$ARGUMENTS`, pass `--context <value>` to all kubectl calls.
- Run `kubectl cluster-info` to test access. If unreachable, set `CLUSTER_AVAILABLE=false`
  and continue (git-based diff still works). Print `kubectl config current-context` if available.
- Fail fast only if kubectl binary is missing.

## 2. Detection
Determine type from input path in `$ARGUMENTS`:
- `Chart.yaml` in directory --> Helm (`helm template`).
- `kustomization.yaml`/`kustomization.yml` --> Kustomize (`kubectl kustomize`).
- Plain `.yaml`/`.yml` --> raw YAML (`cat`). Single file always uses raw mode.

## 3. Render
Render to temp file (`mktemp`, cleaned up via `trap` on exit):
- Helm: `helm template <release> <chart-path> [--values values.yaml] > "$RENDERED"`
- Kustomize: `kubectl kustomize <dir> > "$RENDERED"`
- Raw: `cat <files> > "$RENDERED"`
Split into individual resources keyed by `apiVersion/kind/namespace/name`.

## 4. Diff
**Live cluster diff** (when `--context` present or cluster reachable):
Fetch live version per resource: `kubectl get <kind> <name> -n <ns> -o yaml`. Strip `.metadata.managedFields` and `kubectl.kubernetes.io/last-applied-configuration` annotation. Compare with `diff -u`.

**Git diff** (no cluster target):
Render the same manifests at `git merge-base HEAD main`. Diff with `diff -u`.

## 5. Risk Flags
Scan each diff hunk:

| Level | Patterns |
|-------|----------|
| CRITICAL | Namespace deletion, PV/PVC removal, RBAC escalation (new ClusterRoleBinding, added verbs) |
| HIGH | Resource limits reduced >50%, replicas to 0, image tag to `latest` |
| MEDIUM | New CRD apiVersion, Service port change, ConfigMap key removal |
| LOW | Label/annotation changes, resource request adjustments |

## 6. Secret Masking
Before display, scan for keys matching `password`, `secret`, `token`, `key`, `credential` (case-insensitive). Replace values with `[REDACTED]` in both rendered and live YAML.

## 7. Resource Identity
Match by `apiVersion/kind/namespace/name`. Use `-` as namespace for cluster-scoped resources.
- In render but not cluster: **NEW**. In cluster but not render: **ORPHANED**.

## 8. Output
Print in order:
1. Summary: `N added, M modified, K removed`
2. Risk table (if any):
```
| Resource | Risk | Detail |
|----------|------|--------|
| apps/v1/Deployment/prod/api | CRITICAL | replicas: 3 -> 0 |
```
3. Full unified diff with secrets redacted.
No preamble. Lead with summary tables.

## 9. Idempotency
Strictly read-only. Temp files only, cleaned on exit. Never applies, patches, or deletes resources.

$ARGUMENTS
